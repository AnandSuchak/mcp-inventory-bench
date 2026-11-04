#!/usr/bin/env python3
"""
Telemetry Pilot Runner
Project: mcp-inventory-bench
Author: Anand S. Suchak

Executes a small, rigorous live telemetry pilot covering all 6 experimental arms
with real Google Gemini calls (zero caching, fail-closed live mode).
Specifically includes reactive tasks requiring multiple attempts to verify multi-turn token summation.
Captures full per-call provider envelopes, usageMetadata, and separate timing metrics.
"""

import sys
import os
import json
import time
import copy
import hashlib
import datetime
from pathlib import Path
from typing import Dict, Any, List

WORKSPACE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE))

from trace.paraphraser import generate_pilot2_blinded_tasks, BlindedTask
from trace.predictor import MultiLabelLinearPredictor
from trace.llm_client import LiveLLMClient
from trace.validator import SchemaValidator
from trace.task_evaluator import evaluate_task_correctness
from trace.slicer import (
    create_invariant_schema,
    format_fragment_identifier,
    estimate_tokens
)
from trace.recomposer import recompose_schema, CONSTRAINT_INLINE_SPECS
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA

PILOT_OUT_DIR = WORKSPACE / "datasets" / "dataset_pilot_telemetry"
PILOT_OUT_DIR.mkdir(parents=True, exist_ok=True)

TASK_CONDITIONED_IDS = set(CONSTRAINT_INLINE_SPECS.keys())

def get_clean_task_constraints(task: BlindedTask) -> List[str]:
    return [c for c in task.target_constraints if c in TASK_CONDITIONED_IDS]

def run_pilot_task(
    task: BlindedTask,
    base_schema: Dict[str, Any],
    initial_constraints: List[str],
    arm_name: str,
    reactive_enabled: bool,
    client: LiveLLMClient,
    validator: SchemaValidator,
    max_attempts: int = 3,
    call_records_sink: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    active_constraints = set(initial_constraints)
    exposed_schema = recompose_schema(base_schema, list(active_constraints), FULL_PURCHASE_ORDER_SCHEMA) if arm_name != "full" else copy.deepcopy(FULL_PURCHASE_ORDER_SCHEMA)
    s0_tokens = estimate_tokens(exposed_schema)

    total_pc_tokens = 0
    total_provider_tokens = 0
    final_structural_success = False
    final_semantic_correctness = False
    first_pass_structural = False
    first_pass_semantic = False
    attempts_history = []
    error_context = None
    previous_args = None
    prev_schema_tokens = s0_tokens
    total_reactive_expansion_tokens = 0

    for attempt in range(1, max_attempts + 1):
        curr_schema_tokens = estimate_tokens(exposed_schema)
        delta_s_t = (curr_schema_tokens - prev_schema_tokens) if attempt > 1 else 0
        total_reactive_expansion_tokens += delta_s_t
        prev_schema_tokens = curr_schema_tokens

        # Call live API directly with zero caching
        res = client.generate_tool_arguments(
            user_intent=task.user_intent,
            tool_name="create_purchase_order",
            exposed_schema=exposed_schema,
            error_context=error_context,
            previous_arguments=previous_args,
            task_id=task.task_id,
            arm_name=arm_name,
            replicate_id=0,
            attempt_id=attempt
        )
        args, raw_resp, lat, rid, p_tok, c_tok = res

        cr = res.call_record
        if call_records_sink is not None:
            call_records_sink.append(cr)

        prov_total = cr.get("usage_metadata", {}).get("provider_total_tokens")
        attempt_pc = p_tok + c_tok
        total_pc_tokens += attempt_pc
        if prov_total is not None:
            total_provider_tokens += prov_total

        is_valid, validation_errors = validator.validate(args)
        is_correct, semantic_failures = evaluate_task_correctness(task, args)

        attempts_history.append({
            "attempt": attempt,
            "call_id": cr.get("call_id"),
            "response_id": rid,
            "is_valid": is_valid,
            "is_correct": is_correct,
            "schema_tokens": curr_schema_tokens,
            "delta_schema_tokens": delta_s_t,
            "provider_prompt_tokens": p_tok,
            "provider_candidate_tokens": c_tok,
            "provider_total_tokens": prov_total,
            "recorded_prompt_candidate_tokens": attempt_pc,
            "estimated_schema_exposure_tokens": curr_schema_tokens,
            "validation_errors": [e.message for e in validation_errors],
            "semantic_failures": semantic_failures,
            "tokens": attempt_pc,
            "logical_latency_ms": lat,
            "network_latency_ms": cr.get("timing", {}).get("network_latency_ms", 0.0)
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
        "total_tts_prompt_candidate": total_pc_tokens if final_structural_success else 0,
        "total_tts_provider_total": total_provider_tokens if final_structural_success else 0,
        "total_prompt_candidate_tokens": total_pc_tokens,
        "total_provider_tokens": total_provider_tokens,
        "attempts": attempts_history
    }

def run_pilot():
    print("=" * 80)
    print("RUNNING LIVE TELEMETRY PILOT (ALL 6 ARMS, ZERO CACHING)")
    print("=" * 80)

    # Initialize live client with fail_closed
    client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite", seed=42, fail_closed=True)
    validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)

    all_tasks = generate_pilot2_blinded_tasks()
    train_tasks = [t for t in all_tasks if t.split == "train"]
    test_tasks = [t for t in all_tasks if t.split == "test"]
    predictor = MultiLabelLinearPredictor(train_tasks)

    # Select representative pilot tasks covering clusters
    # Task 0 (Cluster 1: routine regional) has specific constraints that fail CI k=0 on attempt 1
    # Task 8 (Cluster 2: expedited emergency)
    pilot_task = test_tasks[0]  # Standard test task 0
    print(f"[*] Pilot Task ID: {pilot_task.task_id} ({pilot_task.semantic_cluster})")

    optimal_base = create_invariant_schema(FULL_PURCHASE_ORDER_SCHEMA)

    arms = [
        ("full", False),
        ("ci_k0", False),
        ("ci_k1_static", False),
        ("ci_k1_reactive", True),
        ("ci_k2_reactive", True),
        ("oracle_reactive", True)
    ]

    pilot_records = []
    raw_call_records = []
    t_pilot_start = time.time()

    for arm_name, is_reactive in arms:
        print(f"\n[+] Executing Pilot Arm: {arm_name} (Reactive={is_reactive})...")
        if arm_name == "full":
            constraints = []
        elif arm_name == "ci_k0":
            constraints = []
        elif arm_name in ("ci_k1_static", "ci_k1_reactive"):
            constraints = [c for c in predictor.predict_bundle(pilot_task.user_intent, k=4) if c in TASK_CONDITIONED_IDS][:1]
        elif arm_name == "ci_k2_reactive":
            constraints = [c for c in predictor.predict_bundle(pilot_task.user_intent, k=4) if c in TASK_CONDITIONED_IDS][:2]
        elif arm_name == "oracle_reactive":
            constraints = get_clean_task_constraints(pilot_task)

        rec = run_pilot_task(
            task=pilot_task,
            base_schema=optimal_base,
            initial_constraints=constraints,
            arm_name=arm_name,
            reactive_enabled=is_reactive,
            client=client,
            validator=validator,
            max_attempts=3,
            call_records_sink=raw_call_records
        )
        pilot_records.append(rec)
        print(f"    - {arm_name}: Attempts={rec['attempts_needed']} | FinalStruct={rec['final_structural_success']} | P+C Toks={rec['total_prompt_candidate_tokens']} | ProvToks={rec['total_provider_tokens']}")

    t_pilot_end = time.time()
    elapsed_sec = round(t_pilot_end - t_pilot_start, 2)

    # Save summary and call records
    summary_path = PILOT_OUT_DIR / "pilot_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "pilot_timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "elapsed_seconds": elapsed_sec,
            "provider": client.provider,
            "requested_model": client.model,
            "seed": client.seed,
            "task_id": pilot_task.task_id,
            "arms_tested": [a[0] for a in arms],
            "total_calls": len(raw_call_records),
            "records": pilot_records
        }, f, indent=2)

    raw_calls_path = PILOT_OUT_DIR / "pilot_call_records.jsonl"
    with open(raw_calls_path, "w", encoding="utf-8") as f:
        for cr in raw_call_records:
            f.write(json.dumps(cr) + "\n")

    # Manifest
    manifest_path = PILOT_OUT_DIR / "pilot_manifest.json"
    manifest_data = {
        "manifest_name": "LASR-MCP Telemetry Pilot Manifest",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "elapsed_seconds": elapsed_sec,
        "provider": client.provider,
        "model": client.model,
        "total_calls": len(raw_call_records),
        "total_arms": len(arms),
        "artifacts": {
            "pilot_summary.json": {
                "sha256": hashlib.sha256(summary_path.read_bytes()).hexdigest(),
                "size_bytes": summary_path.stat().st_size
            },
            "pilot_call_records.jsonl": {
                "sha256": hashlib.sha256(raw_calls_path.read_bytes()).hexdigest(),
                "size_bytes": raw_calls_path.stat().st_size
            }
        }
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    print("\n" + "=" * 80)
    print(f"PILOT EXECUTION COMPLETE in {elapsed_sec}s.")
    print(f"Summary written to: {summary_path}")
    print(f"Raw calls written to: {raw_calls_path}")
    print(f"Manifest written to: {manifest_path}")
    print("=" * 80)

if __name__ == "__main__":
    run_pilot()
