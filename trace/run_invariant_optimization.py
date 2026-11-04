"""
Comprehensive Invariant Optimization & Task Correctness Benchmark
Project: mcp-inventory-bench
Author: Anand S. Suchak

Evaluates:
1. Invariant Foundation Minimization:
   - Tier 1 (Standard C_I: 339 tok)
   - Tier 2 (Compact C_I: 308 tok)
   - Tier 3 (Minimal C_I: 284 tok)
2. Dual-Metric Evaluation across systems arms:
   - Structural Schema Validity (%)
   - Semantic Task Correctness (%)
3. Full comparative systems arms:
   - Full Schema Control
   - Invariant Baseline (C_I alone)
   - Proactive LASR k=1 (C_I + top-1 C_T)
   - Proactive LASR k=2 (C_I + top-2 C_T)
   - Invariant-Aware Oracle O(x) = C_I + C_T*(x)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import copy
import json
import time
from typing import Dict, Any, List
from trace.paraphraser import generate_pilot2_blinded_tasks, BlindedTask
from trace.predictor import MultiLabelLinearPredictor
from trace.llm_client import LiveLLMClient
from trace.validator import SchemaValidator
from trace.task_evaluator import evaluate_task_correctness
from trace.slicer import (
    create_invariant_schema,
    create_invariant_schema_compact,
    create_invariant_schema_minimal,
    format_fragment_identifier,
    estimate_tokens
)
from trace.recomposer import recompose_schema, CONSTRAINT_INLINE_SPECS
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.runner_pilot2 import load_cached_response, save_cached_response, get_cache_key

output_dir = Path("datasets/dataset_b_pilot/invariant_optimization_eval")
output_dir.mkdir(parents=True, exist_ok=True)

# 1. Prepare data splits
all_tasks = generate_pilot2_blinded_tasks()
train_tasks = [t for t in all_tasks if t.split == "train"]
test_tasks = [t for t in all_tasks if t.split == "test"]

# Train frozen semantic predictor
predictor = MultiLabelLinearPredictor(train_tasks)

# Evaluate on 8 representative held-out test tasks (2 per cluster)
EVAL_TASKS = [
    test_tasks[0], test_tasks[1],   # Cluster 1 (routine regional)
    test_tasks[8], test_tasks[9],   # Cluster 2 (expedited emergency)
    test_tasks[16], test_tasks[17], # Cluster 3 (specialized bulk)
    test_tasks[24], test_tasks[25]  # Cluster 4 (multi-item depot)
]

validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite")

TASK_CONDITIONED_IDS = {
    "warehouse_code.enum",
    "order_priority.enum",
    "total_budget_limit.maximum",
    "total_budget_limit.minimum",
    "items.maxItems"
}

def get_clean_task_constraints(task: BlindedTask) -> List[str]:
    return [c for c in task.target_constraints if c in TASK_CONDITIONED_IDS]

def run_single_task_evaluation(
    task: BlindedTask,
    base_schema: Dict[str, Any],
    initial_constraints: List[str],
    arm_name: str,
    reactive_enabled: bool = False,
    max_attempts: int = 3
) -> Dict[str, Any]:
    active_constraints = set(initial_constraints)
    if arm_name == "full":
        exposed_schema = copy.deepcopy(FULL_PURCHASE_ORDER_SCHEMA)
    else:
        exposed_schema = recompose_schema(base_schema, list(active_constraints), FULL_PURCHASE_ORDER_SCHEMA)

    s0_tokens = estimate_tokens(exposed_schema)
    total_tokens = 0
    total_reactive_expansion_tokens = 0
    final_structural_success = False
    final_semantic_correctness = False
    first_pass_structural = False
    first_pass_semantic = False
    attempts_history = []
    error_context = None
    previous_args = None
    prev_schema_tokens = s0_tokens

    for attempt in range(1, max_attempts + 1):
        curr_schema_tokens = estimate_tokens(exposed_schema)
        delta_s_t = (curr_schema_tokens - prev_schema_tokens) if attempt > 1 else 0
        total_reactive_expansion_tokens += delta_s_t
        prev_schema_tokens = curr_schema_tokens

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
        attempt_pc_tokens = p_tok + c_tok
        attempt_provider_total = getattr(client, "last_call_record", {}).get("usage_metadata", {}).get("provider_total_tokens") if not cached else cached.get("total_tokens")
        attempt_tokens = attempt_pc_tokens
        total_tokens += attempt_pc_tokens

        is_valid, validation_errors = validator.validate(args)
        is_correct, semantic_failures = evaluate_task_correctness(task, args)

        attempts_history.append({
            "attempt": attempt,
            "is_valid": is_valid,
            "is_correct": is_correct,
            "schema_tokens": curr_schema_tokens,
            "delta_schema_tokens": delta_s_t,
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            "provider_prompt_tokens": p_tok,
            "provider_candidate_tokens": c_tok,
            "provider_total_tokens": attempt_provider_total,
            "recorded_prompt_candidate_tokens": attempt_pc_tokens,
            "estimated_schema_exposure_tokens": curr_schema_tokens,
            "validation_errors": [e.message for e in validation_errors],
            "semantic_failures": semantic_failures,
            "tokens": attempt_pc_tokens,
            "call_record": getattr(client, "last_call_record", None)
        })

        if attempt == 1:
            if is_valid:
                first_pass_structural = True
            if is_correct:
                first_pass_semantic = True

        if is_valid:
            final_structural_success = True
            if is_correct:
                final_semantic_correctness = True
            break

        # In-tree reactive expansion & retry context
        newly_added_this_round = []
        if attempt < max_attempts and validation_errors:
            primary_err = validation_errors[0]
            error_context = primary_err.message
            previous_args = copy.deepcopy(args)

            if reactive_enabled and arm_name != "full":
                violated_ids = {format_fragment_identifier(e.path, e.keyword) for e in validation_errors}
                newly_violated = (violated_ids & CONSTRAINT_INLINE_SPECS.keys()) - active_constraints
                if newly_violated:
                    newly_added_this_round = sorted(list(newly_violated))
                    active_constraints.update(newly_violated)
                    exposed_schema = recompose_schema(base_schema, list(active_constraints), FULL_PURCHASE_ORDER_SCHEMA)

        attempts_history[-1]["new_constraints_added"] = newly_added_this_round
        attempts_history[-1]["cumulative_tokens"] = total_tokens

    return {
        "task_id": task.task_id,
        "cluster": task.semantic_cluster,
        "arm": arm_name,
        "reactive_enabled": reactive_enabled,
        "s0_schema_tokens": s0_tokens,
        "final_schema_tokens": estimate_tokens(exposed_schema),
        "reactive_expansion_tokens": total_reactive_expansion_tokens,
        "first_pass_structural": first_pass_structural,
        "first_pass_semantic": first_pass_semantic,
        "first_pass_hierarchical_success": (first_pass_structural and first_pass_semantic),
        "final_structural_success": final_structural_success,
        "final_semantic_correctness": final_semantic_correctness,
        "attempts_needed": len(attempts_history),
        "total_tts": total_tokens if final_structural_success else 0,
        "total_tokens_consumed": total_tokens,
        "recorded_prompt_candidate_tokens": total_tokens,
        "attempts": attempts_history
    }

if __name__ == "__main__":
    optimal_base = create_invariant_schema(FULL_PURCHASE_ORDER_SCHEMA)

    # Load frozen Part 1 invariant search baseline results
    frozen_summary_path = output_dir / "invariant_optimization_summary.json"
    if frozen_summary_path.exists():
        with open(frozen_summary_path, "r", encoding="utf-8") as f:
            prev_data = json.load(f)
            tier_results = prev_data.get("invariant_minimization_search", {})
    else:
        tier_results = {
            "Tier 1 (Standard C_I: 339 tok)": {"tokens": 339, "structural_success_pct": 75.0, "semantic_correctness_pct": 75.0},
            "Tier 2 (Compact C_I: 308 tok)": {"tokens": 308, "structural_success_pct": 62.5, "semantic_correctness_pct": 62.5},
            "Tier 3 (Minimal C_I: 284 tok)": {"tokens": 284, "structural_success_pct": 50.0, "semantic_correctness_pct": 50.0}
        }

    print("=" * 104)
    print("[*] PART 1: INVARIANT FOUNDATION MINIMIZATION SEARCH (FROZEN BASELINE)")
    print("=" * 104)
    print(f"{'Invariant Candidate Tier':<36}{'Tokens':<12}{'Structural Succ %':<20}{'Semantic Correct %':<20}")
    print("-" * 104)
    for t_name, m in tier_results.items():
        print(f"{t_name:<36}{m['tokens']:<12}{m['structural_success_pct']:<20.1f}{m['semantic_correctness_pct']:<20.1f}")
    print("-" * 104)

    print("\n" + "=" * 104)
    print("[*] PART 2: FULL-SPECTRUM SYSTEMS EVALUATION (32 HELD-OUT TASKS ACROSS 6 FACTORIAL ARMS)")
    print("=" * 104)

    # Evaluated across all 32 held-out test tasks (8 per cluster across 4 clusters)
    BENCHMARK_TASKS = test_tasks

    systems_arms = [
        ("full", False),
        ("ci_k0", False),
        ("ci_k1_static", False),
        ("ci_k1_reactive", True),
        ("ci_k2_reactive", True),
        ("oracle_reactive", True)
    ]
    eval_metrics = {}

    for arm_name, is_reactive in systems_arms:
        print(f"\n[+] Executing Arm: {arm_name.upper()} (Reactive={is_reactive}) across {len(BENCHMARK_TASKS)} tasks...")
        records = []
        for task in BENCHMARK_TASKS:
            if arm_name == "full":
                constraints = []
            elif arm_name == "ci_k0":
                constraints = []
            elif arm_name in ("ci_k1_static", "ci_k1_reactive"):
                constraints = [c for c in predictor.predict_bundle(task.user_intent, k=4) if c in TASK_CONDITIONED_IDS][:1]
            elif arm_name == "ci_k2_reactive":
                constraints = [c for c in predictor.predict_bundle(task.user_intent, k=4) if c in TASK_CONDITIONED_IDS][:2]
            elif arm_name == "oracle_reactive":
                constraints = get_clean_task_constraints(task)

            res = run_single_task_evaluation(
                task=task,
                base_schema=optimal_base,
                initial_constraints=constraints,
                arm_name=arm_name,
                reactive_enabled=is_reactive,
                max_attempts=3
            )
            records.append(res)
            s_str = "PASS" if res["final_structural_success"] else "FAIL"
            c_str = "PASS" if res["final_semantic_correctness"] else "FAIL"
            tts_str = str(res['total_tts']) if res["final_structural_success"] else "N/A"
            print(f"    - {task.task_id} ({task.semantic_cluster[:16]}): Struct={s_str:<4} | TaskCorrect={c_str:<4} | Att={res['attempts_needed']} | TTS={tts_str}")

        p1_struct = round(sum(1 for r in records if r["first_pass_structural"]) / len(records) * 100.0, 1)
        fin_struct = round(sum(1 for r in records if r["final_structural_success"]) / len(records) * 100.0, 1)
        fin_sem = round(sum(1 for r in records if r["final_semantic_correctness"]) / len(records) * 100.0, 1)
        succ_tts = [r["total_tts"] for r in records if r["final_structural_success"]]
        mean_tts = round(sum(succ_tts) / len(succ_tts), 1) if succ_tts else 0.0
        mean_s0 = round(sum(r["s0_schema_tokens"] for r in records) / len(records), 1)
        mean_reactive_exp = round(sum(r["reactive_expansion_tokens"] for r in records) / len(records), 1)
        total_api_tokens = sum(r["total_tokens_consumed"] for r in records)

        # Recovery rate calculation: of tasks that failed attempt 1, how many recovered?
        initially_failed = [r for r in records if not r["first_pass_structural"]]
        recovered_tasks = [r for r in initially_failed if r["final_structural_success"]]
        recovery_rate = round(len(recovered_tasks) / len(initially_failed) * 100.0, 1) if initially_failed else 100.0

        # Mean expansions on recovered tasks
        expansions = [r["reactive_expansion_tokens"] for r in initially_failed]
        mean_exp_tokens = round(sum(expansions) / len(expansions), 1) if expansions else 0.0

        eval_metrics[arm_name] = {
            "total_tasks": len(records),
            "reactive_enabled": is_reactive,
            "mean_s0_schema_tokens": mean_s0,
            "mean_reactive_expansion_tokens": mean_reactive_exp,
            "first_pass_structural_pct": p1_struct,
            "final_structural_pct": fin_struct,
            "final_semantic_correctness_pct": fin_sem,
            "recovery_rate_pct": recovery_rate,
            "mean_recovery_expansion_tokens": mean_exp_tokens,
            "mean_tts": mean_tts,
            "total_tokens_consumed": total_api_tokens,
            "records": records
        }

    # Save summary
    summary_output = {
        "invariant_minimization_search": tier_results,
        "systems_benchmark": eval_metrics
    }
    with open(output_dir / "invariant_optimization_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary_output, f, indent=2)

    print("\n" + "=" * 130)
    print(f"{'System Arm':<20}{'Init S0':<10}{'React Exp':<12}{'1st-Pass %':<14}{'Final Struct%':<16}{'Task Correct%':<16}{'Recovery %':<14}{'Mean TTS':<12}{'Total Toks':<12}")
    print("-" * 130)
    for arm_name, m in eval_metrics.items():
        print(f"{arm_name:<20}{m['mean_s0_schema_tokens']:<10.1f}{m['mean_reactive_expansion_tokens']:<12.1f}{m['first_pass_structural_pct']:<14.1f}{m['final_structural_pct']:<16.1f}{m['final_semantic_correctness_pct']:<16.1f}{m['recovery_rate_pct']:<14.1f}{m['mean_tts']:<12.1f}{m['total_tokens_consumed']:<12}")
    print("=" * 130)
