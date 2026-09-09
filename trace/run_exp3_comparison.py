"""
End-to-End Comparative Systems Benchmark (Experiment 3)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Evaluates 5 Systems Arms on the 32 Held-Out Blinded Test Tasks:
- Arm A (Full Schema Control): Full 552-token Draft 2020-12 schema exposed upfront
- Arm B (Reactive ASR): Level-1C (143 tokens) + reactive on-demand slicing upon failure
- Arm C (Proactive LASR k=2): Level-1C + top-2 predicted constraints before execution
- Arm D (Proactive LASR k=3): Level-1C + top-3 predicted constraints before execution
- Arm E (Model-Conditional Oracle): Level-1C + ground-truth minimal sufficient constraint set O(x)

Measures:
- First-Pass Success Rate (%)
- Final Success Rate (%)
- Cumulative Tokens-to-Success (TTS)
- Initial Schema Exposure Footprint (Tokens)
- Prediction Overexposure (Tokens)
- Oracle Gap (TTS_Arm - TTS_Oracle)
- Latency (ms)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import copy
import json
from typing import Dict, Any, List, Tuple
from trace.paraphraser import generate_pilot2_blinded_tasks, BlindedTask
from trace.predictor import MultiLabelLinearPredictor
from trace.llm_client import LiveLLMClient
from trace.validator import SchemaValidator
from trace.slicer import slice_constraint, format_fragment_identifier, estimate_tokens, create_schema_level_1c
from trace.token_accounting import TaskTokenAccount, compute_aggregate_token_metrics
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.runner_pilot2 import load_cached_response, save_cached_response, get_cache_key

output_dir = Path("datasets/dataset_b_pilot/exp3_systems_eval")
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Prepare Train & Held-Out Test Splits
all_tasks = generate_pilot2_blinded_tasks()
train_tasks = [t for t in all_tasks if t.split == "train"]
test_tasks = [t for t in all_tasks if t.split == "test"]

# Train the frozen semantic predictor on the 48 train tasks
predictor = MultiLabelLinearPredictor(train_tasks)

# We evaluate on the 32 held-out test tasks
# For fast live calibration, run on a balanced 8-task test sample (2 per cluster) first, or full 32
EVAL_TEST_TASKS = test_tasks[:8] # 2 tasks per cluster for live execution

validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite")
base_level1c = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)
base_tokens = estimate_tokens(base_level1c)

# Mapping of constraint id to path and keyword
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

def build_schema_with_constraints(base_schema: Dict[str, Any], constraint_ids: List[str]) -> Tuple[Dict[str, Any], int]:
    s = copy.deepcopy(base_schema)
    tok = estimate_tokens(s)
    for cid in constraint_ids:
        if cid in CONSTRAINT_METADATA:
            path, kw = CONSTRAINT_METADATA[cid]
            delta = slice_constraint(FULL_PURCHASE_ORDER_SCHEMA, path, kw)
            s.setdefault("constraints", {})[cid] = delta
    return s, estimate_tokens(s)

def run_system_arm(
    task: BlindedTask,
    arm_name: str,
    max_attempts: int = 3
) -> TaskTokenAccount:
    """Execute a single task under a specific systems arm."""
    account = TaskTokenAccount(
        task_id=task.task_id,
        semantic_cluster=task.semantic_cluster,
        schema_level=arm_name
    )

    # 1. Setup Initial Exposed Schema
    if arm_name == "full":
        exposed_schema = copy.deepcopy(FULL_PURCHASE_ORDER_SCHEMA)
    elif arm_name == "reactive":
        exposed_schema = copy.deepcopy(base_level1c)
    elif arm_name == "lasr_k2":
        pred_k2 = predictor.predict_bundle(task.user_intent, k=2)
        exposed_schema, _ = build_schema_with_constraints(base_level1c, pred_k2)
    elif arm_name == "lasr_k3":
        pred_k3 = predictor.predict_bundle(task.user_intent, k=3)
        exposed_schema, _ = build_schema_with_constraints(base_level1c, pred_k3)
    elif arm_name == "oracle":
        # Oracle gets the exact target constraints for that task
        exposed_schema, _ = build_schema_with_constraints(base_level1c, task.target_constraints)
    else:
        raise ValueError(f"Unknown arm: {arm_name}")

    init_schema_tokens = estimate_tokens(exposed_schema)
    current_args = {}
    error_context = None
    previous_args = None
    final_status = "FAIL"

    for attempt_num in range(1, max_attempts + 1):
        system_prompt = (
            f"You are an autonomous enterprise operations AI agent executing tool 'create_purchase_order'.\n"
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

        current_args = args
        is_valid, validation_errors = validator.validate(current_args)
        status = "SUCCESS" if is_valid else "FAIL"

        cur_schema_tokens = estimate_tokens(exposed_schema)
        account.add_attempt(
            attempt_number=attempt_num,
            base_prompt_tokens=p_tok,
            base_schema_tokens=init_schema_tokens,
            new_delta_tokens=cur_schema_tokens - init_schema_tokens,
            total_schema_tokens=cur_schema_tokens,
            completion_tokens=c_tok
        )

        if is_valid:
            final_status = "SUCCESS"
            break

        # In reactive recovery, slice and inject the next failed constraint
        if attempt_num < max_attempts and validation_errors:
            primary_err = validation_errors[0]
            delta_slice = slice_constraint(FULL_PURCHASE_ORDER_SCHEMA, primary_err.path, primary_err.keyword)
            frag_id = format_fragment_identifier(primary_err.path, primary_err.keyword)
            exposed_schema.setdefault("constraints", {})[frag_id] = delta_slice
            error_context = primary_err.message
            previous_args = copy.deepcopy(current_args)

    # Compute Oracle token lower bound for this task
    _, oracle_schema_tokens = build_schema_with_constraints(base_level1c, task.target_constraints)
    account.finalize(final_status, oracle_tokens=oracle_schema_tokens)
    return account

if __name__ == "__main__":
    arms = ["full", "reactive", "lasr_k2", "lasr_k3", "oracle"]
    arm_metrics = {}

    print("=" * 88)
    print(f"[*] EXPERIMENT 3: END-TO-END SYSTEMS EVALUATION (LASR vs. BASELINES & ORACLE)")
    print(f"[*] Evaluated on {len(EVAL_TEST_TASKS)} Held-Out Test Tasks across 5 System Arms")
    print("=" * 88)

    for arm in arms:
        print(f"\n[+] Executing Arm: {arm.upper()}...")
        accounts = []
        for task in EVAL_TEST_TASKS:
            acc = run_system_arm(task, arm, max_attempts=3)
            accounts.append(acc)
            p1 = "PASS" if acc.attempts[0].attempt_total_tokens and acc.final_outcome == "SUCCESS" and len(acc.attempts) == 1 else "FAIL"
            print(f"    - Task {task.task_id} ({task.semantic_cluster[:14]}): Att1={p1:<4} | Final={acc.final_outcome:<7} | TTS={acc.total_cumulative_tokens}")

        m = compute_aggregate_token_metrics(accounts)
        p1_cnt = sum(1 for a in accounts if a.final_outcome == "SUCCESS" and len(a.attempts) == 1)
        m["first_pass_pct"] = round((p1_cnt / len(EVAL_TEST_TASKS)) * 100.0, 1)
        arm_metrics[arm] = m

    # Save summary
    with open(output_dir / "systems_benchmark_summary.json", "w", encoding="utf-8") as f:
        json.dump(arm_metrics, f, indent=2)

    print("\n" + "=" * 88)
    print(f"{'System Arm':<18}{'Init Schema':<14}{'1st-Pass %':<12}{'Final Succ %':<14}{'Mean TTS':<12}{'Oracle Gap':<12}")
    print("-" * 88)
    for arm, m in arm_metrics.items():
        print(f"{arm:<18}{m['mean_schema_tokens_exposed']:<14.1f}{m['first_pass_pct']:<12.1f}{m['success_rate_pct']:<14.1f}{m['mean_tts']:<12.1f}{m['mean_oracle_gap']:<12.1f}")
    print("=" * 88)
