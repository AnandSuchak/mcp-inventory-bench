"""
Run Experiment 4: Counterfactual Constraint Replay & Causal Specificity (CRE)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Evaluates Hypothesis H4 / H0 (Causal Specificity):
Freezes the exact Attempt-1 failed state (same prompt, same args, same error)
and forks Attempt 2 into 3 parallel branches:
  Branch A (Null): No additional constraint delta
  Branch B (Target): Ground-truth violated constraint delta exposed
  Branch C (Decoy): Size-matched & family-matched irrelevant constraint delta exposed

Computes:
  CRE(c) = P(Success_2 | Target) - P(Success_2 | Decoy)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from trace.llm_client import LiveLLMClient
from trace.validator import SchemaValidator
from trace.slicer import create_schema_level_1c
from trace.counterfactual_harness import CounterfactualReplayHarness, compute_cre
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.models import ValidationErrorRecord

# 1. Load the frozen Attempt-1 failure states from Experiment 1 traces
exp1_file = Path("datasets/dataset_b_pilot/exp1_traces.jsonl")
if not exp1_file.exists():
    print(f"[!] Experiment 1 traces not found: {exp1_file}")
    sys.exit(1)

traces = []
with open(exp1_file, "r", encoding="utf-8") as f:
    for line in f:
        if line.strip():
            traces.append(json.loads(line.strip()))

# Filter tasks where Attempt 1 failed validation
failed_attempts_1 = []
for t in traces:
    attempts = t.get("attempts", [])
    if attempts and attempts[0].get("validation_status") == "FAIL":
        failed_attempts_1.append(t)

print(f"[*] Found {len(failed_attempts_1)} frozen Attempt-1 failure states.")
# Take a balanced sample of 8 frozen trials (2 per semantic cluster)
trials_to_run = []
counts = {}
for t in failed_attempts_1:
    c = t.get("category", "unknown")
    if counts.get(c, 0) < 2:
        trials_to_run.append(t)
        counts[c] = counts.get(c, 0) + 1

print(f"[*] Running Counterfactual Replay on {len(trials_to_run)} trials (3 branches each = {len(trials_to_run)*3} Attempt-2 dispatches):")
for c, cnt in counts.items():
    print(f"    - {c}: {cnt} trials")

validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
harness = CounterfactualReplayHarness(FULL_PURCHASE_ORDER_SCHEMA, validator)
client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite")
base_schema = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)

completed_trials = []
for idx, t in enumerate(trials_to_run, 1):
    task_id = t["task_id"]
    user_intent = t["user_intent"]
    att1 = t["attempts"][0]
    att1_args = att1["arguments"]
    errs_raw = att1["validation_errors"]
    validation_errs = [ValidationErrorRecord(**e) for e in errs_raw]

    trial = harness.create_trial_from_attempt_1(task_id, user_intent, att1_args, validation_errs)
    print(f"\n[{idx}/{len(trials_to_run)}] Trial {task_id}: Target={trial.target_constraint_id} | Decoy={trial.decoy_constraint_id}")

    # Branch A: Null
    print("    - Running Branch A (Null)...", end="", flush=True)
    res_null = harness.execute_replay_branch(trial, "null", client, base_schema)
    print(f" Result: {res_null.validation_status}")

    # Branch B: Target
    print("    - Running Branch B (Target)...", end="", flush=True)
    res_target = harness.execute_replay_branch(trial, "target", client, base_schema)
    print(f" Result: {res_target.validation_status}")

    # Branch C: Decoy
    print("    - Running Branch C (Decoy)...", end="", flush=True)
    res_decoy = harness.execute_replay_branch(trial, "decoy", client, base_schema)
    print(f" Result: {res_decoy.validation_status}")

    completed_trials.append(trial)

# Save completed trials to JSONL
out_dir = Path("datasets/dataset_b_pilot/exp4_counterfactual")
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / "counterfactual_replay_trials.jsonl"

with open(out_file, "w", encoding="utf-8") as f:
    for tr in completed_trials:
        data = {
            "task_id": tr.task_id,
            "frozen_intent": tr.frozen_intent,
            "target_constraint_id": tr.target_constraint_id,
            "decoy_constraint_id": tr.decoy_constraint_id,
            "results": {
                b: {
                    "branch": r.branch_type,
                    "constraint": r.constraint_exposed,
                    "tokens": r.exposed_tokens,
                    "status": r.validation_status,
                    "errors": [e.message for e in r.errors]
                }
                for b, r in tr.results.items()
            }
        }
        f.write(json.dumps(data) + "\n")

print(f"\n[+] Counterfactual trials logged to {out_file}")

# Compute and report empirical CRE
cre_report = compute_cre(completed_trials)
print("\n" + "=" * 84)
print("[*] EXPERIMENT 4: COUNTERFACTUAL CONSTRAINT REPAIR EFFECT (CRE)")
print("=" * 84)
print(f"Total Frozen Trials Evaluated: {cre_report['total_trials']}")
print(f"  - Branch A (Null) Success Rate   : {cre_report['null_success_rate']*100:.1f}%")
print(f"  - Branch B (Target) Success Rate : {cre_report['target_success_rate']*100:.1f}%")
print(f"  - Branch C (Decoy) Success Rate  : {cre_report['decoy_success_rate']*100:.1f}%")
print(f"\n[+] Empirical Constraint Repair Effect (CRE = Target - Decoy): {cre_report['cre']:+.4f} ({cre_report['cre']*100:+.1f}%)")
print(f"[+] Specificity Lift over Null (Target - Null)                : {cre_report['target_vs_null_lift']:+.4f} ({cre_report['target_vs_null_lift']*100:+.1f}%)")
print("=" * 84)
