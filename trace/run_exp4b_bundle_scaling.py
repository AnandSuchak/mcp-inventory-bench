"""
Experiment 4B: Incremental Constraint Bundle Scaling Experiment
Project: mcp-inventory-bench
Author: Anand S. Suchak

Evaluates the foundational question discovered in Experiment 4:
"How many simultaneous relevant constraints does the LLM need to see to achieve task success?"

For the frozen Attempt-1 failed states, tests incremental bundle exposure sizes:
- Bundle k=0: Baseline Level-1 (0 additional constraint slices)
- Bundle k=1: Top 1 violated constraint slice exposed
- Bundle k=2: Top 2 co-occurring violated constraint slices exposed
- Bundle k=3: Top 3 co-occurring violated constraint slices exposed
- Bundle k=4: Top 4 co-occurring violated constraint slices exposed
- Bundle k=All: All violated constraint slices exposed (Oracle Bundle for Attempt 2)

Measures:
- Attempt-2 Task Success Rate (%)
- Residual Error Count
- Schema Tokens Exposed
- Total Cumulative Tokens-to-Success (TTS)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
import copy
from trace.llm_client import LiveLLMClient
from trace.validator import SchemaValidator
from trace.slicer import slice_constraint, format_fragment_identifier, estimate_tokens, create_schema_level_1c
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.models import ValidationErrorRecord

# 1. Load frozen Attempt-1 failure states from Experiment 1
exp1_file = Path("datasets/dataset_b_pilot/exp1_traces.jsonl")
if not exp1_file.exists():
    print(f"[!] Exp1 traces not found: {exp1_file}")
    sys.exit(1)

failed_trials = []
with open(exp1_file, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            t = json.loads(line.strip())
            if t.get("attempts") and t["attempts"][0].get("validation_status") == "FAIL":
                failed_trials.append(t)

# Select 4 representative frozen trials across the 4 semantic clusters
cluster_trials = {}
for t in failed_trials:
    c = t.get("category", "unknown")
    if c not in cluster_trials:
        cluster_trials[c] = t

trials = list(cluster_trials.values())
print(f"[*] Running Bundle Scaling Experiment on {len(trials)} frozen trials across 4 clusters:")
for t in trials:
    print(f"    - {t['task_id']} ({t['category'][:16]}): {len(t['attempts'][0]['validation_errors'])} initial errors")

validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite")
base_schema = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)
base_tokens = estimate_tokens(base_schema)

bundle_sizes = [0, 1, 2, 3, 4]
results_by_k = {k: [] for k in bundle_sizes}

print("\n" + "=" * 84)
print("[*] EXPERIMENT 4B: INCREMENTAL CONSTRAINT BUNDLE SCALING (k = 0 to 4)")
print("=" * 84)

for k in bundle_sizes:
    print(f"\n[+] Testing Bundle Size k = {k} exposed constraints:")
    for t in trials:
        task_id = t["task_id"]
        user_intent = t["user_intent"]
        att1 = t["attempts"][0]
        att1_args = att1["arguments"]
        errors = [ValidationErrorRecord(**e) for e in att1["validation_errors"]]

        # Extract unique constraint fragments needed from all errors
        unique_deltas = {}
        for err in errors:
            frag_id = format_fragment_identifier(err.path, err.keyword)
            if frag_id not in unique_deltas:
                unique_deltas[frag_id] = (err.path, err.keyword)

        # Select top k constraint deltas to expose
        selected_frags = list(unique_deltas.keys())[:k]

        prompt_schema = copy.deepcopy(base_schema)
        added_tokens = 0
        error_msgs = []
        for fid in selected_frags:
            epath, ekw = unique_deltas[fid]
            delta = slice_constraint(FULL_PURCHASE_ORDER_SCHEMA, epath, ekw)
            prompt_schema.setdefault("constraints", {})[fid] = delta
            added_tokens += estimate_tokens(delta)

        # Combine error context for the exposed constraints
        for err in errors:
            fid = format_fragment_identifier(err.path, err.keyword)
            if fid in selected_frags:
                error_msgs.append(err.message)

        err_context = "\n".join(error_msgs) if error_msgs else "Initial parameters failed validation."
        total_schema_tokens = base_tokens + added_tokens

        # Dispatch Attempt 2
        att2_args, raw_resp, lat, rid, p_tok, c_tok = client.generate_tool_arguments(
            user_intent=user_intent,
            tool_name="create_purchase_order",
            exposed_schema=prompt_schema,
            error_context=err_context,
            previous_arguments=att1_args
        )

        is_valid, post_errors = validator.validate(att2_args)
        status = "SUCCESS" if is_valid else "FAIL"
        tts = (att1["prompt_tokens"] + att1["completion_tokens"]) + (p_tok + c_tok)

        trial_record = {
            "task_id": task_id,
            "cluster": t["category"],
            "bundle_size_k": k,
            "constraints_exposed": selected_frags,
            "schema_tokens": total_schema_tokens,
            "validation_status": status,
            "residual_errors": len(post_errors),
            "tokens_consumed": tts
        }
        results_by_k[k].append(trial_record)
        print(f"    - Task {task_id} (k={k}): Status={status:<7} | Remaining Errors: {len(post_errors)} | Schema Tokens: {total_schema_tokens} | Cum Tokens: {tts}")

# Save detailed trial logs
out_dir = Path("datasets/dataset_b_pilot/exp4b_bundle_scaling")
out_dir.mkdir(parents=True, exist_ok=True)
with open(out_dir / "bundle_scaling_results.json", "w", encoding="utf-8") as f:
    json.dump(results_by_k, f, indent=2)

print("\n" + "=" * 84)
print(f"{'Bundle Size k':<15}{'Mean Schema Tok':<18}{'Success Rate':<16}{'Mean Residual Errs':<22}{'Mean Cum Tokens':<15}")
print("-" * 84)
for k in bundle_sizes:
    records = results_by_k[k]
    n = len(records)
    succ = sum(1 for r in records if r["validation_status"] == "SUCCESS")
    succ_pct = (succ / n) * 100.0
    mean_schema = sum(r["schema_tokens"] for r in records) / n
    mean_errs = sum(r["residual_errors"] for r in records) / n
    mean_tokens = sum(r["tokens_consumed"] for r in records) / n
    print(f"k = {k:<11}{mean_schema:<18.1f}{succ_pct:<16.1f}%{mean_errs:<22.1f}{mean_tokens:<15.1f}")
print("=" * 84)
