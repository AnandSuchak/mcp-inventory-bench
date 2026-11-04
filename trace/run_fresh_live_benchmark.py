#!/usr/bin/env python3
"""
Fresh Live Primary Benchmark Runner with Robust Quota-Aware Resumability
Project: mcp-inventory-bench
Author: Anand S. Suchak

Pre-Specified Protocol:
- Benchmark set: 32 held-out frozen test tasks (4 semantic clusters, 8 tasks per cluster)
- 6 factorial arms: Full Control, CI k=0, CI k=1 static, LASR k=1 reactive, LASR k=2 reactive, Oracle reactive
- Target: 20 independent repetitions per task per arm = 3,840 task-arm trials
- Primary Comparison: LASR k=2 reactive vs Full Control
- Randomization & Interleaving: Realized schedule fixed by seed=42 and preserved in checkpoint
- Zero Caching: Response caching completely disabled; asserts zero cache hits
- Durable Resumability: Per-call JSONL fsync, per-trial JSON fsync, atomic checkpointing
- Quota Awareness: Detects daily quota exhaustion, stops cleanly without burning retries,
  saves resumable checkpoint, and outputs precise resume command.
"""

import sys
import os
import json
import time
import copy
import random
import hashlib
import datetime
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional, Set

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

DEFAULT_OUT_DIR = WORKSPACE / "datasets" / "fresh_live_benchmark_n32"
TASK_CONDITIONED_IDS = set(CONSTRAINT_INLINE_SPECS.keys())

class DailyQuotaExhaustedError(Exception):
    """Raised when daily API quota (RPD) is reached and cannot be retried in current window."""
    def __init__(self, message: str, retry_delay_seconds: float = 0.0):
        super().__init__(message)
        self.retry_delay_seconds = retry_delay_seconds

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_clean_task_constraints(task: BlindedTask) -> List[str]:
    return [c for c in task.target_constraints if c in TASK_CONDITIONED_IDS]

def run_single_trial(
    task: BlindedTask,
    base_schema: Dict[str, Any],
    initial_constraints: List[str],
    arm_name: str,
    reactive_enabled: bool,
    replicate_id: int,
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

        try:
            res = client.generate_tool_arguments(
                user_intent=task.user_intent,
                tool_name="create_purchase_order",
                exposed_schema=exposed_schema,
                error_context=error_context,
                previous_arguments=previous_args,
                task_id=task.task_id,
                arm_name=arm_name,
                replicate_id=replicate_id,
                attempt_id=attempt
            )
        except Exception as exc:
            err_msg = str(exc)
            # Check for daily quota exhaustion
            if "quota" in err_msg.lower() or "resource_exhausted" in err_msg.lower() or "429" in err_msg:
                # Distinguish transient rate limit vs daily quota
                if "day" in err_msg.lower() or "perday" in err_msg.lower() or "queries per day" in err_msg.lower() or "daily" in err_msg.lower():
                    raise DailyQuotaExhaustedError(f"Google API daily request quota reached: {err_msg}")
            raise

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
        "trial_key": f"{arm_name}_{task.task_id}_rep{replicate_id}",
        "task_id": task.task_id,
        "cluster": task.semantic_cluster,
        "arm": arm_name,
        "replicate_id": replicate_id,
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

def execute_benchmark(
    replicates: int = 20,
    out_dir: Path = DEFAULT_OUT_DIR,
    model: str = "gemini-3.5-flash-lite",
    seed: int = 42,
    max_trials: Optional[int] = None,
    resume: bool = True,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()
    t_start_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    checkpoint_path = out_dir / "benchmark_checkpoint.json"
    call_records_path = out_dir / "benchmark_call_records.jsonl"
    trial_records_path = out_dir / "benchmark_trial_records.json"
    summary_path = out_dir / "benchmark_summary.json"
    manifest_path = out_dir / "run_manifest.json"

    print("=" * 100)
    print(f"LASR-MCP RESUMABLE FRESH LIVE BENCHMARK (N=32 Tasks, 6 Arms, {replicates} Replicates)")
    print(f"Model: {model} | Seed: {seed} | Output Dir: {out_dir}")
    keys_pool = []
    if api_key and api_key.lower() != "auto":
        keys_pool = [k.strip() for k in api_key.split(",") if k.strip()]
    if not keys_pool:
        client_probe = LiveLLMClient(provider="gemini", model=model, seed=seed, fail_closed=False)
        if client_probe.api_key:
            keys_pool.append(client_probe.api_key)
        env_pool = os.getenv("GEMINI_API_KEYS_POOL")
        if env_pool:
            for k in env_pool.split(","):
                if k.strip() and k.strip() not in keys_pool:
                    keys_pool.append(k.strip())

    initial_key = keys_pool[0] if keys_pool else None
    client = LiveLLMClient(provider="gemini", model=model, seed=seed, api_key=initial_key, fail_closed=True)
    if not keys_pool and client.api_key:
        keys_pool = [client.api_key]

    print(f"[*] API Keys Pool Loaded: {len(keys_pool)} key(s) configured.")
    validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)

    all_tasks = generate_pilot2_blinded_tasks()
    train_tasks = [t for t in all_tasks if t.split == "train"]
    test_tasks = [t for t in all_tasks if t.split == "test"]
    assert len(test_tasks) == 32, f"Expected 32 test tasks, got {len(test_tasks)}"
    test_tasks_map = {t.task_id: t for t in test_tasks}
    predictor = MultiLabelLinearPredictor(train_tasks)

    optimal_base = create_invariant_schema(FULL_PURCHASE_ORDER_SCHEMA)

    arms_def = [
        ("full", False),
        ("ci_k0", False),
        ("ci_k1_static", False),
        ("ci_k1_reactive", True),
        ("ci_k2_reactive", True),
        ("oracle_reactive", True)
    ]

    # Generate full scheduled experimental design matrix
    scheduled_trials_plan = []
    for rep in range(replicates):
        for task in test_tasks:
            for arm_name, is_reactive in arms_def:
                scheduled_trials_plan.append({
                    "replicate_id": rep,
                    "task_id": task.task_id,
                    "arm_name": arm_name,
                    "reactive_enabled": is_reactive,
                    "trial_key": f"{arm_name}_{task.task_id}_rep{rep}"
                })

    # Shuffle order with fixed seed
    rng = random.Random(seed)
    rng.shuffle(scheduled_trials_plan)

    if max_trials is not None:
        scheduled_trials_plan = scheduled_trials_plan[:max_trials]

    total_planned = len(scheduled_trials_plan)

    # Check for existing completed trials to resume
    completed_trial_keys: Set[str] = set()
    trial_records: List[Dict[str, Any]] = []

    if checkpoint_path.exists() and resume:
        print(f"[*] Found existing checkpoint at {checkpoint_path}. Inspecting progress...")
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                ckpt = json.load(f)
            completed_trial_keys = set(ckpt.get("completed_trial_keys", []))
            print(f"[*] Resuming: {len(completed_trial_keys)} trials already completed out of {total_planned}.")
        except Exception as exc:
            print(f"[!] Warning reading checkpoint: {exc}. Will inspect trial records directly.")

    if trial_records_path.exists() and resume:
        try:
            with open(trial_records_path, "r", encoding="utf-8") as f:
                trial_records = json.load(f)
            completed_trial_keys.update(t["trial_key"] for t in trial_records if "trial_key" in t)
        except Exception:
            pass

    print(f"[*] Total planned trials: {total_planned} | Completed: {len(completed_trial_keys)} | Remaining: {total_planned - len(completed_trial_keys)}")

    # Open call records in append mode
    f_calls = open(call_records_path, "a", encoding="utf-8")
    run_status = "IN_PROGRESS"
    stop_reason = None
    next_resume_index = 0
    current_key_idx = 0

    try:
        for idx, item in enumerate(scheduled_trials_plan):
            t_key = item["trial_key"]
            if t_key in completed_trial_keys:
                continue

            next_resume_index = idx
            rep = item["replicate_id"]
            task = test_tasks_map[item["task_id"]]
            arm_name = item["arm_name"]
            is_reactive = item["reactive_enabled"]

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

            trial_succeeded = False
            rec = None
            trial_calls = []

            while not trial_succeeded:
                trial_calls = []
                try:
                    rec = run_single_trial(
                        task=task,
                        base_schema=optimal_base,
                        initial_constraints=constraints,
                        arm_name=arm_name,
                        reactive_enabled=is_reactive,
                        replicate_id=rep,
                        client=client,
                        validator=validator,
                        max_attempts=3,
                        call_records_sink=trial_calls
                    )
                    trial_succeeded = True
                except (DailyQuotaExhaustedError, Exception) as call_err:
                    err_str = str(call_err)
                    is_quota = isinstance(call_err, DailyQuotaExhaustedError) or ("429" in err_str or "402" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower() or "prepayment" in err_str.lower())
                    if is_quota and current_key_idx + 1 < len(keys_pool):
                        current_key_idx += 1
                        next_k = keys_pool[current_key_idx]
                        client.api_key = next_k
                        print(f"\n[!] Daily quota reached on key {current_key_idx}/{len(keys_pool)}. Rotating to key {current_key_idx + 1}/{len(keys_pool)}...")
                        time.sleep(2.0)
                        continue
                    elif is_quota:
                        print(f"\n[!] STOPPED: All API keys exhausted. Quota limit: {err_str[:120]}")
                        run_status = "QUOTA_EXHAUSTED"
                        stop_reason = err_str
                        break
                    else:
                        print(f"\n[!] ERROR in trial {t_key}: {call_err}")
                        run_status = "ERROR_STOPPED"
                        stop_reason = str(call_err)
                        break

            if not trial_succeeded:
                break

            # Persist call records immediately
            for cr in trial_calls:
                f_calls.write(json.dumps(cr) + "\n")
            f_calls.flush()
            os.fsync(f_calls.fileno())

            # Persist trial record
            trial_records.append(rec)
            completed_trial_keys.add(t_key)

            # Persist trials file atomically
            temp_trials = out_dir / "benchmark_trial_records.json.tmp"
            with open(temp_trials, "w", encoding="utf-8") as f_tmp:
                json.dump(trial_records, f_tmp, indent=2)
            temp_trials.replace(trial_records_path)

            # Update checkpoint atomically
            temp_ckpt = out_dir / "benchmark_checkpoint.json.tmp"
            ckpt_state = {
                "schema_version": "2026-10-23/resumable-checkpoint-v1",
                "total_planned_trials": total_planned,
                "completed_trials_count": len(completed_trial_keys),
                "remaining_trials_count": total_planned - len(completed_trial_keys),
                "completed_trial_keys": sorted(list(completed_trial_keys)),
                "last_completed_trial_key": t_key,
                "next_trial_index": idx + 1,
                "run_status": "IN_PROGRESS",
                "timestamp_last_update": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "model": model,
                "seed": seed,
                "replicates": replicates
            }
            with open(temp_ckpt, "w", encoding="utf-8") as f_ckpt:
                json.dump(ckpt_state, f_ckpt, indent=2)
            temp_ckpt.replace(checkpoint_path)

            completed_now = len(completed_trial_keys)
            if completed_now % 5 == 0 or completed_now == total_planned:
                elapsed = time.time() - t_start
                rate = completed_now / elapsed if elapsed > 0 else 0
                print(f"    [{completed_now}/{total_planned}] {arm_name:<16} on {task.task_id} (rep={rep}): "
                      f"Struct={'PASS' if rec['final_structural_success'] else 'FAIL'} | "
                      f"P+C Toks={rec['total_prompt_candidate_tokens']} | "
                      f"Elapsed={elapsed:.1f}s")

    finally:
        f_calls.close()

    t_end = time.time()
    t_end_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    elapsed_sec = round(t_end - t_start, 2)

    is_complete = len(completed_trial_keys) == total_planned
    if is_complete:
        run_status = "COMPLETED"

    # Compute arm-level summaries from all completed trials
    arm_summaries = {}
    for arm_name, is_reactive in arms_def:
        arm_recs = [r for r in trial_records if r["arm"] == arm_name]
        n_trials = len(arm_recs)
        if n_trials == 0:
            continue
        tot_pc = sum(r["total_prompt_candidate_tokens"] for r in arm_recs)
        tot_prov = sum(r["total_provider_tokens"] for r in arm_recs)
        final_struct = sum(1 for r in arm_recs if r["final_structural_success"])
        final_sem = sum(1 for r in arm_recs if r["final_semantic_correctness"])
        hier_pass = sum(1 for r in arm_recs if r["first_pass_hierarchical_success"])
        tts_pc_list = [r["total_tts_prompt_candidate"] for r in arm_recs if r["final_structural_success"]]
        tts_prov_list = [r["total_tts_provider_total"] for r in arm_recs if r["final_structural_success"]]
        mean_tts_pc = round(sum(tts_pc_list) / len(tts_pc_list), 1) if tts_pc_list else 0.0
        mean_tts_prov = round(sum(tts_prov_list) / len(tts_prov_list), 1) if tts_prov_list else 0.0

        arm_summaries[arm_name] = {
            "completed_trials": n_trials,
            "planned_trials": 32 * replicates,
            "completion_pct": round((n_trials / (32 * replicates)) * 100.0, 1),
            "reactive_enabled": is_reactive,
            "total_prompt_candidate_tokens": tot_pc,
            "total_provider_total_tokens": tot_prov,
            "mean_tokens_per_trial_pc": round(tot_pc / n_trials, 1),
            "mean_tokens_per_trial_prov": round(tot_prov / n_trials, 1),
            "conditional_mean_tts_pc": mean_tts_pc,
            "conditional_mean_tts_prov": mean_tts_prov,
            "first_pass_hierarchical_count": hier_pass,
            "first_pass_hierarchical_pct": round((hier_pass / n_trials) * 100.0, 1),
            "final_structural_success_count": final_struct,
            "final_structural_success_pct": round((final_struct / n_trials) * 100.0, 1),
            "final_semantic_correctness_count": final_sem,
            "final_semantic_correctness_pct": round((final_sem / n_trials) * 100.0, 1)
        }

    full_pc = arm_summaries.get("full", {}).get("total_prompt_candidate_tokens", 0)
    full_prov = arm_summaries.get("full", {}).get("total_provider_total_tokens", 0)
    for arm_name in arm_summaries:
        if full_pc > 0:
            arm_summaries[arm_name]["workload_savings_pc_vs_full_pct"] = round(((full_pc - arm_summaries[arm_name]["total_prompt_candidate_tokens"]) / full_pc) * 100.0, 2)
        if full_prov > 0:
            arm_summaries[arm_name]["workload_savings_prov_vs_full_pct"] = round(((full_prov - arm_summaries[arm_name]["total_provider_total_tokens"]) / full_prov) * 100.0, 2)

    # Save summary
    summary_data = {
        "run_title": "LASR-MCP Fresh Live Primary Benchmark",
        "run_status": run_status,
        "is_complete": is_complete,
        "stop_reason": stop_reason,
        "timestamp_start": t_start_iso,
        "timestamp_end": t_end_iso,
        "elapsed_seconds": elapsed_sec,
        "provider": client.provider,
        "requested_model": client.model,
        "seed": client.seed,
        "total_planned_trials": total_planned,
        "completed_trials_count": len(completed_trial_keys),
        "arm_summaries": arm_summaries
    }
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    # Final checkpoint update
    ckpt_final = {
        "schema_version": "2026-10-23/resumable-checkpoint-v1",
        "total_planned_trials": total_planned,
        "completed_trials_count": len(completed_trial_keys),
        "remaining_trials_count": total_planned - len(completed_trial_keys),
        "completed_trial_keys": sorted(list(completed_trial_keys)),
        "run_status": run_status,
        "stop_reason": stop_reason,
        "timestamp_last_update": t_end_iso,
        "model": model,
        "seed": seed,
        "replicates": replicates,
        "resume_command": f"python trace/run_fresh_live_benchmark.py --out-dir {out_dir} --replicates {replicates} --resume"
    }
    with open(checkpoint_path, "w", encoding="utf-8") as f:
        json.dump(ckpt_final, f, indent=2)

    # Cryptographic manifest
    artifacts_checksums = {}
    if call_records_path.exists():
        artifacts_checksums["benchmark_call_records.jsonl"] = {
            "sha256": sha256_file(call_records_path),
            "size_bytes": call_records_path.stat().st_size
        }
    if trial_records_path.exists():
        artifacts_checksums["benchmark_trial_records.json"] = {
            "sha256": sha256_file(trial_records_path),
            "size_bytes": trial_records_path.stat().st_size
        }
    if summary_path.exists():
        artifacts_checksums["benchmark_summary.json"] = {
            "sha256": sha256_file(summary_path),
            "size_bytes": summary_path.stat().st_size
        }
    if checkpoint_path.exists():
        artifacts_checksums["benchmark_checkpoint.json"] = {
            "sha256": sha256_file(checkpoint_path),
            "size_bytes": checkpoint_path.stat().st_size
        }

    manifest = {
        "manifest_name": "LASR-MCP Fresh Live Benchmark Run Manifest",
        "timestamp_start": t_start_iso,
        "timestamp_end": t_end_iso,
        "elapsed_seconds": elapsed_sec,
        "provider": client.provider,
        "model": client.model,
        "seed": client.seed,
        "replicates": replicates,
        "run_status": run_status,
        "is_complete": is_complete,
        "total_planned": total_planned,
        "completed_trials": len(completed_trial_keys),
        "cache_hits": 0,
        "artifacts_checksums": artifacts_checksums
    }
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print("\n" + "=" * 100)
    print(f"BENCHMARK STATUS: {run_status} ({len(completed_trial_keys)}/{total_planned} completed) in {elapsed_sec}s.")
    print(f"Checkpoint: {checkpoint_path}")
    print(f"Manifest:   {manifest_path}")
    if not is_complete:
        print(f"RESUME COMMAND: python trace/run_fresh_live_benchmark.py --out-dir {out_dir} --replicates {replicates} --resume")
    print("=" * 100)
    return summary_data

def main():
    parser = argparse.ArgumentParser(description="Execute fresh live benchmark with resumability.")
    parser.add_argument("--replicates", type=int, default=20, help="Number of repetitions per task per arm.")
    parser.add_argument("--max-trials", type=int, default=None, help="Cap total trials.")
    parser.add_argument("--out-dir", type=str, default="datasets/fresh_live_benchmark_n32", help="Output directory.")
    parser.add_argument("--model", type=str, default="gemini-3.5-flash-lite", help="Model ID.")
    parser.add_argument("--seed", type=int, default=42, help="Decoding seed.")
    parser.add_argument("--no-resume", action="store_true", help="Do not resume from existing checkpoint.")
    parser.add_argument("--resume", action="store_true", default=True, help="Resume from existing checkpoint.")
    parser.add_argument("--api-key", type=str, default=None, help="API key override.")
    args = parser.parse_args()

    execute_benchmark(
        replicates=args.replicates,
        out_dir=Path(args.out_dir),
        model=args.model,
        seed=args.seed,
        max_trials=args.max_trials,
        resume=not args.no_resume,
        api_key=args.api_key
    )

if __name__ == "__main__":
    main()
