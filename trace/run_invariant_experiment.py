"""
Invariant Foundation & Task-Conditioned Bundle Scaling Experiment
Project: mcp-inventory-bench
Author: Anand S. Suchak

Evaluates the refined two-tier schema architecture across held-out test tasks:
S(x) = C_I + C_T(x)

Compares:
1. Arm C_I (k=0): Invariant foundation alone (339 tokens)
2. Arm C_I + k=1: C_I + top-1 predicted task constraint
3. Arm C_I + k=2: C_I + top-2 predicted task constraints (LASR precision mode)
4. Arm C_I + k=3: C_I + top-3 predicted task constraints (LASR recall mode)
5. Arm True Oracle: C_I + exact minimal sufficient task constraints C_T*(x)
6. Arm Full Control: Complete 552-token schema

Measures:
- First-Pass Success Rate (%)
- Final Success Rate (%)
- Cumulative Tokens-to-Success (TTS)
- Schema Footprint Tokens
- Relative Token Reduction vs. Full Schema (%)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import copy
import json
from typing import Dict, Any, List
from trace.paraphraser import generate_pilot2_blinded_tasks, BlindedTask
from trace.predictor import MultiLabelLinearPredictor
from trace.llm_client import LiveLLMClient
from trace.validator import SchemaValidator
from trace.slicer import create_invariant_schema, estimate_tokens
from trace.recomposer import recompose_schema
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.runner_pilot2 import load_cached_response, save_cached_response, get_cache_key

output_dir = Path("datasets/dataset_b_pilot/invariant_scaling_eval")
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Prepare data splits
all_tasks = generate_pilot2_blinded_tasks()
train_tasks = [t for t in all_tasks if t.split == "train"]
test_tasks = [t for t in all_tasks if t.split == "test"]

# Train frozen semantic predictor
predictor = MultiLabelLinearPredictor(train_tasks)

# We evaluate on 8 representative held-out test tasks (2 per cluster)
EVAL_TASKS = [
    test_tasks[0], test_tasks[1],  # Cluster 1 (routine regional)
    test_tasks[8], test_tasks[9],  # Cluster 2 (expedited emergency)
    test_tasks[16], test_tasks[17], # Cluster 3 (specialized bulk)
    test_tasks[24], test_tasks[25]  # Cluster 4 (multi-item depot)
]

validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite")
base_ci = create_invariant_schema(FULL_PURCHASE_ORDER_SCHEMA)

# Task-conditioned constraints (excluding invariant rules already in C_I)
TASK_CONDITIONED_IDS = {
    "warehouse_code.enum",
    "order_priority.enum",
    "total_budget_limit.maximum",
    "total_budget_limit.minimum",
    "items.maxItems"
}

def get_clean_task_constraints(task: BlindedTask) -> List[str]:
    """Extract only the task-conditioned constraints for this task."""
    return [c for c in task.target_constraints if c in TASK_CONDITIONED_IDS]

def run_evaluation_arm(task: BlindedTask, arm_name: str, max_attempts: int = 3) -> Dict[str, Any]:
    """Execute a task under a specific Invariant + Task Bundle arm."""
    if arm_name == "full":
        exposed_schema = copy.deepcopy(FULL_PURCHASE_ORDER_SCHEMA)
    elif arm_name == "ci_k0":
        exposed_schema = copy.deepcopy(base_ci)
    elif arm_name == "ci_k1":
        # Predict top task-conditioned constraint
        preds = [c for c in predictor.predict_bundle(task.user_intent, k=4) if c in TASK_CONDITIONED_IDS][:1]
        exposed_schema = recompose_schema(base_ci, preds, FULL_PURCHASE_ORDER_SCHEMA)
    elif arm_name == "ci_k2":
        preds = [c for c in predictor.predict_bundle(task.user_intent, k=4) if c in TASK_CONDITIONED_IDS][:2]
        exposed_schema = recompose_schema(base_ci, preds, FULL_PURCHASE_ORDER_SCHEMA)
    elif arm_name == "ci_k3":
        preds = [c for c in predictor.predict_bundle(task.user_intent, k=4) if c in TASK_CONDITIONED_IDS][:3]
        exposed_schema = recompose_schema(base_ci, preds, FULL_PURCHASE_ORDER_SCHEMA)
    elif arm_name == "oracle":
        # True Oracle: C_I + exact task-conditioned target constraints
        task_c = get_clean_task_constraints(task)
        exposed_schema = recompose_schema(base_ci, task_c, FULL_PURCHASE_ORDER_SCHEMA)
    else:
        raise ValueError(f"Unknown arm: {arm_name}")

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

        # Setup retry feedback & reactive in-tree expansion
        if attempt < max_attempts and validation_errors:
            primary_err = validation_errors[0]
            error_context = primary_err.message
            previous_args = copy.deepcopy(args)

    return {
        "task_id": task.task_id,
        "cluster": task.semantic_cluster,
        "arm": arm_name,
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
    arms = ["full", "ci_k0", "ci_k1", "ci_k2", "ci_k3", "oracle"]
    arm_metrics = {}

    print("=" * 96)
    print("[*] INVARIANT FOUNDATION & TASK-CONDITIONED BUNDLE SCALING (C_I + k)")
    print(f"[*] Testing {len(EVAL_TASKS)} Held-Out Tasks across {len(arms)} Systems Arms")
    print("=" * 96)

    for arm in arms:
        print(f"\n[+] Executing Arm: {arm.upper()}...")
        records = []
        for task in EVAL_TASKS:
            res = run_evaluation_arm(task, arm, max_attempts=3)
            records.append(res)
            p1_str = "PASS" if res["first_pass"] else "FAIL"
            fin_str = "PASS" if res["final_success"] else "FAIL"
            print(f"    - {task.task_id} ({task.semantic_cluster[:18]}): Att1={p1_str:<4} | Final={fin_str:<4} | TTS={res['total_tts']}")

        p1_cnt = sum(1 for r in records if r["first_pass"])
        fin_cnt = sum(1 for r in records if r["final_success"])
        succ_tts = [r["total_tts"] for r in records if r["final_success"]]
        mean_tts = round(sum(succ_tts) / len(succ_tts), 1) if succ_tts else 0.0
        mean_init = round(sum(r["init_schema_tokens"] for r in records) / len(records), 1)

        arm_metrics[arm] = {
            "total_tasks": len(EVAL_TASKS),
            "first_pass_pct": round(p1_cnt / len(EVAL_TASKS) * 100.0, 1),
            "final_success_pct": round(fin_cnt / len(EVAL_TASKS) * 100.0, 1),
            "mean_init_schema_tokens": mean_init,
            "mean_tts": mean_tts,
            "total_tokens_consumed": sum(r["total_tokens_consumed"] for r in records),
            "records": records
        }

    # Save summary
    with open(output_dir / "invariant_bundle_scaling_summary.json", "w", encoding="utf-8") as f:
        json.dump(arm_metrics, f, indent=2)

    print("\n" + "=" * 96)
    print(f"{'System Arm':<22}{'Init Schema':<14}{'1st-Pass %':<14}{'Final Succ %':<14}{'Mean TTS':<12}")
    print("-" * 96)
    for arm, m in arm_metrics.items():
        print(f"{arm:<22}{m['mean_init_schema_tokens']:<14.1f}{m['first_pass_pct']:<14.1f}{m['final_success_pct']:<14.1f}{m['mean_tts']:<12.1f}")
    print("=" * 96)
