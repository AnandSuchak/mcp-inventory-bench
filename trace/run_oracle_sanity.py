"""
Oracle Sanity Check Experiment
Project: mcp-inventory-bench
Author: Anand S. Suchak

Compares 3 Schema Representation Conditions across 4 Representative Held-Out Tasks (1 per cluster):
- Condition A (Full Schema Control): Full 552-token Draft 2020-12 schema.
- Condition B (Recomposed Minimal Oracle Bundle): Level-1C + exact target constraints inlined in-tree.
- Condition C (Fragmented Oracle Bundle): Level-1C + exact target constraints attached under 'constraints: {}'.

Measures:
- Attempt 1 Pass Rate (%)
- Final Task Success Rate (%)
- Residual Validation Error Count
- Cumulative Tokens-to-Success (TTS)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import copy
import json
from typing import Dict, Any, List
from trace.paraphraser import generate_pilot2_blinded_tasks, BlindedTask
from trace.llm_client import LiveLLMClient
from trace.validator import SchemaValidator
from trace.slicer import slice_constraint, format_fragment_identifier, estimate_tokens, create_schema_level_1c
from trace.recomposer import recompose_schema
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.runner_pilot2 import load_cached_response, save_cached_response, get_cache_key

output_dir = Path("datasets/dataset_b_pilot/oracle_sanity_check")
output_dir.mkdir(parents=True, exist_ok=True)

all_tasks = generate_pilot2_blinded_tasks()
test_tasks = [t for t in all_tasks if t.split == "test"]

# Select 1 representative task per semantic cluster from held-out test set
selected_tasks = []
seen_clusters = set()
for t in test_tasks:
    if t.semantic_cluster not in seen_clusters:
        selected_tasks.append(t)
        seen_clusters.add(t.semantic_cluster)
    if len(selected_tasks) == 4:
        break

validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite")
base_level1c = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)

CONSTRAINT_METADATA = {
    "warehouse_code.enum": ("/warehouse_code", "enum"),
    "authorized_by.pattern": ("/authorized_by", "pattern"),
    "order_priority.enum": ("/order_priority", "enum"),
    "total_budget_limit.maximum": ("/total_budget_limit", "maximum"),
    "items.quantity.minimum": ("/items/0/quantity", "minimum"),
    "supplier_id.pattern": ("/supplier_id", "pattern"),
    "items.minItems": ("/items", "minItems"),
    "items.sku.pattern": ("/items/0/sku", "pattern"),
    "items.required": ("/items/0", "required")
}

def build_fragmented_schema(base_schema: Dict[str, Any], constraint_ids: List[str]) -> Dict[str, Any]:
    s = copy.deepcopy(base_schema)
    for cid in constraint_ids:
        if cid in CONSTRAINT_METADATA:
            path, kw = CONSTRAINT_METADATA[cid]
            delta = slice_constraint(FULL_PURCHASE_ORDER_SCHEMA, path, kw)
            s.setdefault("constraints", {})[cid] = delta
    return s

def execute_condition(task: BlindedTask, condition_name: str, max_attempts: int = 3) -> Dict[str, Any]:
    # 1. Build initial schema according to condition
    if condition_name == "Condition A (Full Schema)":
        exposed_schema = copy.deepcopy(FULL_PURCHASE_ORDER_SCHEMA)
    elif condition_name == "Condition B (In-Tree Recomposed Oracle)":
        exposed_schema = recompose_schema(base_level1c, task.target_constraints, FULL_PURCHASE_ORDER_SCHEMA)
    elif condition_name == "Condition C (Fragmented Oracle)":
        exposed_schema = build_fragmented_schema(base_level1c, task.target_constraints)
    else:
        raise ValueError(f"Unknown condition {condition_name}")

    init_tokens = estimate_tokens(exposed_schema)
    total_tokens = 0
    final_success = False
    first_pass = False
    attempts_history = []
    error_context = None
    previous_args = None

    for attempt in range(1, max_attempts + 1):
        system_prompt = (
            "You are an autonomous enterprise operations AI agent executing tool 'create_purchase_order'.\n"
            "You MUST output ONLY a valid JSON object containing the exact tool arguments required.\n"
            "Do not include any conversational filler, markdown formatting blocks, or explanations."
        )
        user_content = f"User Intent: {task.user_intent}\n\nAvailable Tool Schema Specification:\n{json.dumps(exposed_schema, indent=2)}\n"
        if error_context:
            user_content += (
                f"\nYour previous arguments failed validation with this error:\n{error_context}\n"
                f"Previous arguments attempted:\n{json.dumps(previous_args or {}, indent=2)}\n"
                "Please correct your arguments based strictly on the newly exposed schema constraints above."
            )

        cache_key = get_cache_key(client.model, system_prompt, user_content)
        cached = load_cached_response(cache_key)
        if cached:
            args = cached["args"]
            p_tok = cached["p_tok"]
            c_tok = cached["c_tok"]
        else:
            args, raw_resp, lat, rid, p_tok, c_tok = client.generate_tool_arguments(
                user_intent=task.user_intent,
                tool_name="create_purchase_order",
                exposed_schema=exposed_schema,
                error_context=error_context,
                previous_arguments=previous_args
            )
            save_cached_response(cache_key, {
                "args": args, "raw_resp": raw_resp, "p_tok": p_tok, "c_tok": c_tok,
                "resp_id": rid, "lat": lat
            })

        curr_schema_tok = estimate_tokens(exposed_schema)
        attempt_tokens = p_tok + c_tok
        total_tokens += attempt_tokens

        is_valid, validation_errors = validator.validate(args)
        attempts_history.append({
            "attempt": attempt,
            "is_valid": is_valid,
            "error_count": len(validation_errors),
            "errors": [e.message for e in validation_errors],
            "tokens": attempt_tokens,
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            "recorded_prompt_candidate_tokens": attempt_tokens,
            "estimated_schema_exposure_tokens": curr_schema_tok
        })

        if attempt == 1 and is_valid:
            first_pass = True

        if is_valid:
            final_success = True
            break

        # Setup retry feedback
        if attempt < max_attempts and validation_errors:
            primary_err = validation_errors[0]
            error_context = primary_err.message
            previous_args = copy.deepcopy(args)

    return {
        "task_id": task.task_id,
        "cluster": task.semantic_cluster,
        "condition": condition_name,
        "init_schema_tokens": init_tokens,
        "first_pass": first_pass,
        "final_success": final_success,
        "attempts_needed": len(attempts_history),
        "total_tts": total_tokens if final_success else 0,
        "total_tokens_consumed": total_tokens,
        "final_error_count": attempts_history[-1]["error_count"] if not final_success else 0,
        "attempts": attempts_history
    }

if __name__ == "__main__":
    conditions = [
        "Condition A (Full Schema)",
        "Condition B (In-Tree Recomposed Oracle)",
        "Condition C (Fragmented Oracle)"
    ]

    print("=" * 96)
    print("[*] ORACLE SANITY CHECK: IN-TREE RECOMPOSITION VS. FRAGMENTED VS. FULL SCHEMA")
    print(f"[*] Testing {len(selected_tasks)} Representative Held-Out Tasks across 3 Schema Conditions")
    print("=" * 96)

    results = {c: [] for c in conditions}

    for c in conditions:
        print(f"\n[+] Executing {c}...")
        for task in selected_tasks:
            res = execute_condition(task, c, max_attempts=3)
            results[c].append(res)
            p1_str = "PASS" if res["first_pass"] else "FAIL"
            fin_str = "PASS" if res["final_success"] else "FAIL"
            print(f"    - {task.task_id} ({task.semantic_cluster[:18]}): Att1={p1_str:<4} | Final={fin_str:<4} | Err={res['final_error_count']} | TTS={res['total_tts']}")

    # Save detailed results
    with open(output_dir / "oracle_sanity_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n" + "=" * 96)
    print(f"{'Condition':<40}{'Init Tok':<12}{'1st-Pass %':<14}{'Final Succ %':<14}{'Mean TTS':<12}")
    print("-" * 96)
    for c in conditions:
        items = results[c]
        p1_rate = round(sum(1 for x in items if x["first_pass"]) / len(items) * 100.0, 1)
        fin_rate = round(sum(1 for x in items if x["final_success"]) / len(items) * 100.0, 1)
        mean_init = round(sum(x["init_schema_tokens"] for x in items) / len(items), 1)
        succ_tts = [x["total_tts"] for x in items if x["final_success"]]
        mean_tts = round(sum(succ_tts) / len(succ_tts), 1) if succ_tts else 0.0
        print(f"{c:<40}{mean_init:<12.1f}{p1_rate:<14.1f}{fin_rate:<14.1f}{mean_tts:<12.1f}")
    print("=" * 96)
