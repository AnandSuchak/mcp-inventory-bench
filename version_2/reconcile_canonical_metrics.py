#!/usr/bin/env python3
"""
Canonical Metric Reconciliation & Consistency Validator (Version 2.0.3)
Project: mcp-inventory-bench / Version 2.0.3
Author: Anand S. Suchak

Recomputes all canonical benchmark metrics directly from raw frozen datasets:
1. Primary Benchmark (N=32 Gemini Flash-Lite evaluation runs across 6 arms)
2. Empirical Model Turnaround & AST Latency Hierarchy (556 cache traces, 1000 AST samples, Monte Carlo task trajectory)
3. Diagnostic Schema Retrieval Curves (TF-IDF & LSA/TruncatedSVD at k=1,2,3,5 computed with normalized gold labels)
4. Cross-Schema Mechanism Stress Test (N=64 per-task simulation records across 4 domains derived in-memory)
5. LangGraph Counterfactual State Accumulation Model (N=32 modeled trajectories)
6. H1 Intent Prediction Evaluation (N=32 tasks, 10,000 bootstrap replicates, Monte Carlo permutation test with plus-one correction, cluster sensitivity)

Modes:
- --check (default): Pure read-only audit. Computes canonical metrics in memory,
  verifies disk artifacts (canonical_metrics.json, tables, prose, CSVs) without touching them.
- --regenerate: Explicit operator command. Computes canonical metrics, compares with existing,
  reports differences, and safely updates version_2/canonical_metrics.json.
- --test-regression: Verifies that tampering with reported values triggers check failure.
"""

import sys
import os
import glob
import json
import csv
import math
import random
import hashlib
import statistics
import argparse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

def round_half_up(val: float, decimals: int = 1) -> float:
    d = Decimal(str(val))
    fmt = "0." + "0" * decimals if decimals > 0 else "0"
    return float(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))

def compute_file_sha256(filepath: Path) -> str:
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def get_release_version(workspace: Path) -> str:
    v_file = workspace / "version_2" / "RELEASE_VERSION"
    if not v_file.exists():
        raise FileNotFoundError(f"Missing release version file: {v_file}")
    ver = v_file.read_text(encoding="utf-8").strip()
    if not ver:
        raise ValueError(f"Empty release version file: {v_file}")
    return ver

def percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    sorted_vals = sorted(vals)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)

def derive_primary_benchmark(workspace: Path) -> Dict[str, Any]:
    rel_path = "datasets/frozen_benchmark_n32/invariant_optimization_summary.json"
    raw_path = workspace / rel_path
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing raw frozen benchmark: {raw_path}")
    
    file_hash = compute_file_sha256(raw_path)
    
    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    sb = data.get("systems_benchmark", {})
    expected_arms = ["full", "ci_k1_reactive", "ci_k2_reactive", "ci_k1_static", "ci_k0", "oracle_reactive"]
    for arm in expected_arms:
        if arm not in sb:
            raise KeyError(f"Missing arm {arm} in systems_benchmark")
            
    arm_task_ids = {}
    canonical_arms = {}
    for arm in expected_arms:
        recs = sb[arm].get("records", [])
        if len(recs) != 32:
            raise ValueError(f"Arm {arm} has {len(recs)} records; expected 32")
        t_ids = [r["task_id"] for r in recs]
        if len(set(t_ids)) != 32:
            raise ValueError(f"Duplicate task IDs in arm {arm}")
        arm_task_ids[arm] = sorted(t_ids)
        
        total_tokens = 0
        struct_succ = 0
        sem_succ = 0
        tts_vals = []
        first_pass_struct = 0
        first_pass_hier = 0
        s0_tokens_list = []
        exp_tokens_list = []
        
        for r in recs:
            tot = sum(a.get("prompt_tokens", 0) + a.get("completion_tokens", 0) for a in r.get("attempts", []))
            total_tokens += tot
            if r.get("first_pass_structural"):
                first_pass_struct += 1
            if r.get("first_pass_structural") and r.get("first_pass_semantic"):
                first_pass_hier += 1
            if r.get("final_structural_success"):
                struct_succ += 1
                task_tts_pc = sum(a.get("prompt_tokens", 0) + a.get("completion_tokens", 0) for a in r.get("attempts", []))
                tts_vals.append(task_tts_pc)
            if r.get("final_semantic_correctness"):
                sem_succ += 1
            s0_tokens_list.append(r.get("s0_schema_tokens", 0))
            exp_tokens_list.append(r.get("reactive_expansion_tokens", 0))
                
        mean_tts = statistics.mean(tts_vals) if tts_vals else 0.0
        canonical_arms[arm] = {
            "tasks_count": 32,
            "total_workload_tokens": total_tokens,
            "mean_tokens_per_task": round(total_tokens / 32.0, 1),
            "mean_initial_s0_tokens": round(statistics.mean(s0_tokens_list), 4),
            "mean_initial_s0_tokens_display": round_half_up(statistics.mean(s0_tokens_list), 1),
            "mean_reactive_expansion_tokens": round(statistics.mean(exp_tokens_list), 4),
            "mean_reactive_expansion_tokens_display": round_half_up(statistics.mean(exp_tokens_list), 1),
            "first_pass_structural_count": first_pass_struct,
            "first_pass_structural_pct": round_half_up((first_pass_struct / 32.0) * 100.0, 1),
            "first_pass_structural_pct_unrounded": round((first_pass_struct / 32.0) * 100.0, 4),
            "first_pass_hierarchical_count": first_pass_hier,
            "first_pass_hierarchical_pct": round_half_up((first_pass_hier / 32.0) * 100.0, 1),
            "first_pass_hierarchical_pct_unrounded": round((first_pass_hier / 32.0) * 100.0, 4),
            "final_structural_success_count": struct_succ,
            "final_structural_success_pct": round_half_up((struct_succ / 32.0) * 100.0, 1),
            "final_semantic_correctness_count": sem_succ,
            "final_semantic_correctness_pct": round_half_up((sem_succ / 32.0) * 100.0, 1),
            "mean_tts_conditioned_on_success": round(mean_tts, 1)
        }
    
    ref_tasks = arm_task_ids["full"]
    for arm, t_ids in arm_task_ids.items():
        if t_ids != ref_tasks:
            raise ValueError(f"Task ID mismatch between 'full' and '{arm}'")
            
    full_tokens = canonical_arms["full"]["total_workload_tokens"]
    full_tts = canonical_arms["full"]["mean_tts_conditioned_on_success"]
    
    for arm, stats in canonical_arms.items():
        tot = stats["total_workload_tokens"]
        stats["workload_token_savings_pct"] = round(((full_tokens - tot) / full_tokens) * 100.0, 2)
        tts = stats["mean_tts_conditioned_on_success"]
        stats["tts_token_savings_pct"] = round(((full_tts - tts) / full_tts) * 100.0, 2)
        
    return {
        "status": "VERIFIED_PRIMARY_BENCHMARK",
        "reference_dataset": rel_path,
        "source_sha256": file_hash,
        "formula": "recorded_prompt_candidate_tokens = prompt_tokens + completion_tokens; workload_token_savings_pct = (full_tokens - arm_tokens) / full_tokens * 100",
        "arms": canonical_arms
    }

def derive_latencies(workspace: Path) -> Dict[str, Any]:
    cache_files = sorted(glob.glob(str(workspace / "datasets" / "cache" / "*.json")))
    if len(cache_files) != 556:
        raise ValueError(f"Expected 556 cache traces, found {len(cache_files)}")
    
    latencies = []
    for cf in cache_files:
        with open(cf, "r", encoding="utf-8") as f:
            rec = json.load(f)
        if "lat" not in rec or type(rec["lat"]) not in (int, float) or math.isnan(rec["lat"]) or math.isinf(rec["lat"]) or rec["lat"] < 0:
            raise ValueError(f"Invalid or non-finite 'lat' field in cache trace {cf}")
        latencies.append(float(rec["lat"]))
        
    req_p50 = percentile(latencies, 0.50)
    req_p90 = percentile(latencies, 0.90)
    req_p95 = percentile(latencies, 0.95)
    req_p99 = percentile(latencies, 0.99)
    req_mean = statistics.mean(latencies)
    req_stdev = statistics.stdev(latencies)
    
    ast_rel = "version_2/latency_benchmark_measurements.csv"
    ast_file = workspace / ast_rel
    if not ast_file.exists():
        raise FileNotFoundError(f"Missing AST latency CSV: {ast_file}")
    
    ast_hash = compute_file_sha256(ast_file)
    ast_samples = []
    with open(ast_file, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].isdigit() and len(row) >= 9:
                val = float(row[8])
                if math.isnan(val) or math.isinf(val) or val < 0:
                    raise ValueError(f"Invalid non-finite latency measurement in CSV: {row}")
                ast_samples.append(val)
                
    if len(ast_samples) != 1000:
        raise ValueError(f"Expected 1000 AST latency samples, found {len(ast_samples)}")
        
    ast_p50 = percentile(ast_samples, 0.50)
    ast_p90 = percentile(ast_samples, 0.90)
    ast_p99 = percentile(ast_samples, 0.99)
    ast_mean = statistics.mean(ast_samples)
    
    ast_to_req_p50_ratio_pct = (ast_p50 / req_p50) * 100.0
    
    random.seed(42)
    attempt_weights = [1] * 6 + [2] * 20 + [3] * 6
    sim_trajectories = []
    for _ in range(10000):
        k = random.choice(attempt_weights)
        sim_trajectories.append(sum(random.choice(latencies) for _ in range(k)))
        
    sim_p50 = percentile(sim_trajectories, 0.50)
    sim_p90 = percentile(sim_trajectories, 0.90)
    sim_p99 = percentile(sim_trajectories, 0.99)
    sim_mean = statistics.mean(sim_trajectories)
    
    return {
        "status": "VERIFIED_LATENCY_HIERARCHY",
        "provenance": {
            "cache_traces_count": len(cache_files),
            "ast_measurements_csv": ast_rel,
            "ast_measurements_sha256": ast_hash
        },
        "request_level_model_turnaround_ms": {
            "samples": len(latencies),
            "p50_ms": round(req_p50, 2),
            "p90_ms": round(req_p90, 2),
            "p95_ms": round(req_p95, 2),
            "p99_ms": round(req_p99, 2),
            "mean_ms": round(req_mean, 2),
            "stdev_ms": round(req_stdev, 2)
        },
        "local_ast_pipeline_latency_ms": {
            "samples": len(ast_samples),
            "p50_ms": round(ast_p50, 4),
            "p50_us": round(ast_p50 * 1000, 1),
            "p90_ms": round(ast_p90, 4),
            "p99_ms": round(ast_p99, 4),
            "p99_us": round(ast_p99 * 1000, 1),
            "mean_ms": round(ast_mean, 6),
            "overhead_ratio_to_request_p50_pct": round(ast_to_req_p50_ratio_pct, 5),
            "ratio_display": f"{ast_to_req_p50_ratio_pct:.5f}%"
        },
        "simulated_task_trajectory_turnaround_ms": {
            "methodology": "Monte Carlo convolution over empirical attempts (10,000 samples, seed=42)",
            "attempts_distribution": {"1_attempt": 6, "2_attempts": 20, "3_attempts": 6},
            "p50_ms": round(sim_p50, 2),
            "p90_ms": round(sim_p90, 2),
            "p99_ms": round(sim_p99, 2),
            "mean_ms": round(sim_mean, 2)
        }
    }

def derive_retrieval(workspace: Path) -> Dict[str, Any]:
    from version_2.run_dense_rag_baseline import compute_retrieval_metrics
    schema_path = workspace / "version_2" / "full_schema.json"
    tasks_path = workspace / "version_2" / "benchmark_tasks_n32.json"
    
    with open(schema_path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
        
    report, csv_rows = compute_retrieval_metrics(schema, tasks)
    tfidf = report.get("tfidf_results", {})
    lsa = report.get("lsa_results", {})
    
    return {
        "status": "VERIFIED_RETRIEVAL_DIAGNOSTICS",
        "description": "Inductive LSA and Lexical TF-IDF diagnostic recall on 32 tasks vs 27 schema chunks with normalized gold targets",
        "source_schema": "version_2/full_schema.json",
        "source_tasks": "version_2/benchmark_tasks_n32.json",
        "gold_label_normalization": report.get("gold_label_normalization", {}),
        "tfidf_curve": tfidf,
        "lsa_curve": lsa
    }

def derive_cross_schema(workspace: Path) -> Dict[str, Any]:
    import version_2.derive_cross_schema_metrics as dcsm
    raw_path = workspace / "datasets" / "cross_schema_validation" / "cross_schema_results.json"
    if not raw_path.exists():
        raise FileNotFoundError(f"Missing cross-schema results: {raw_path}")
    raw_hash = compute_file_sha256(raw_path)
    derived = dcsm.derive_metrics(raw_path)
    
    return {
        "status": "VERIFIED_CROSS_SCHEMA_STRESS_TEST",
        "study_characterization": "Deterministic simulation-based mechanism stress test (word/punctuation heuristic token estimates)",
        "source_dataset": "datasets/cross_schema_validation/cross_schema_results.json",
        "source_sha256": raw_hash,
        "derived_summary": derived
    }

def derive_langgraph(workspace: Path) -> Dict[str, Any]:
    lg_rel = "version_2/langgraph_traces.json"
    lg_path = workspace / lg_rel
    if not lg_path.exists():
        raise FileNotFoundError(f"Missing LangGraph traces: {lg_path}")
    lg_hash = compute_file_sha256(lg_path)
    with open(lg_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    trajs = data.get("trajectories", [])
    if len(trajs) != 32:
        raise ValueError(f"Expected 32 LangGraph trajectories, found {len(trajs)}")
    
    tot_tokens = sum(t["total_tokens_consumed"] for t in trajs)
    if tot_tokens != 69119:
        raise ValueError(f"LangGraph total tokens mismatch: {tot_tokens} != 69119")
        
    for t in trajs:
        att_sum = sum(a["total_attempt_tokens"] for a in t["attempts"])
        if t["total_tokens_consumed"] != att_sum:
            raise ValueError(f"LangGraph attempt sum mismatch for task {t['task_id']}")
            
    return {
        "status": "VERIFIED_LANGGRAPH_COUNTERFACTUAL",
        "characterization": "Counterfactual state-history accumulation token model (+45 tok compiler context)",
        "source_dataset": lg_rel,
        "source_sha256": lg_hash,
        "total_workload_tokens": tot_tokens,
        "mean_tokens_per_task": round(tot_tokens / 32.0, 1),
        "overhead_vs_full_schema_pct": round(((tot_tokens - 61853) / 61853) * 100.0, 2),
        "savings_lasr_k2_vs_langgraph_pct": round(((tot_tokens - 50276) / tot_tokens) * 100.0, 2),
        "overhead_vs_lasr_k2_pct": round(((tot_tokens - 50276) / 50276) * 100.0, 2)
    }

def derive_h1_predictor(workspace: Path) -> Dict[str, Any]:
    import version_2.reproduce_h1_predictor as rh1
    # Pure in-memory computation from ground-truth task intent definitions
    report = rh1.compute_h1_evaluation()
    
    h1_rel = "version_2/h1_predictor_evaluation.json"
    h1_path = workspace / h1_rel
    h1_hash = compute_file_sha256(h1_path) if h1_path.exists() else None

    source_hashes = {
        "trace/paraphraser.py": compute_file_sha256(workspace / "trace" / "paraphraser.py"),
        "trace/predictor.py": compute_file_sha256(workspace / "trace" / "predictor.py"),
        "version_2/reproduce_h1_predictor.py": compute_file_sha256(workspace / "version_2" / "reproduce_h1_predictor.py"),
        "datasets/frozen_benchmark_n32/invariant_optimization_summary.json": compute_file_sha256(workspace / "datasets" / "frozen_benchmark_n32" / "invariant_optimization_summary.json")
    }
    
    return {
        "status": "VERIFIED_H1_PREDICTOR",
        "source_dataset": h1_rel,
        "source_sha256": h1_hash,
        "provenance_source_hashes": source_hashes,
        "evaluation_summary": report["metrics_summary"],
        "cluster_dependence_sensitivity": report["cluster_dependence_sensitivity"],
        "overlap_analysis": report["overlap_analysis"],
        "per_task_results": report["per_task_results"]
    }

def derive_all_canonical_metrics(workspace: Path) -> Dict[str, Any]:
    release_ver = get_release_version(workspace)
    return {
        "release_version": release_ver,
        "provenance": {
            "generator": "version_2/reconcile_canonical_metrics.py",
            "workspace_relative": "version_2",
            "primary_source_hashes": {
                "datasets/frozen_benchmark_n32/invariant_optimization_summary.json": "78c2c88ed5128e0f296fa29e0c258589b516f3adb14b0b8da491fa73bc3ffc11",
                "datasets/cross_schema_validation/cross_schema_results.json": "b3d57636f9834ff536204acfe88454c9620228bb67705f1b3caa40e0d562302a"
            }
        },
        "primary_benchmark": derive_primary_benchmark(workspace),
        "latency_hierarchy": derive_latencies(workspace),
        "retrieval_diagnostics": derive_retrieval(workspace),
        "cross_schema_stress_test": derive_cross_schema(workspace),
        "langgraph_counterfactual": derive_langgraph(workspace),
        "h1_intent_prediction": derive_h1_predictor(workspace)
    }

def audit_check(workspace: Path) -> Tuple[bool, List[str]]:
    """
    Pure read-only audit check. Does not overwrite or touch any files on disk.
    Computes expected canonical metrics in memory, compares with existing disk artifacts.
    """
    errors = []
    
    # 1. Check canonical_metrics.json existence
    canon_path = workspace / "version_2" / "canonical_metrics.json"
    if not canon_path.exists():
        errors.append(f"Missing canonical artifact: {canon_path}. Run with --regenerate to initialize.")
        return False, errors
        
    try:
        with open(canon_path, "r", encoding="utf-8") as f:
            disk_canon = json.load(f)
    except Exception as e:
        errors.append(f"Failed to parse {canon_path}: {e}")
        return False, errors

    # Check for machine-specific paths in disk_canon
    canon_text = canon_path.read_text(encoding="utf-8")
    if "C:\\" in canon_text or "c:\\" in canon_text or "file:///c:" in canon_text or "file:///C:" in canon_text:
        errors.append("canonical_metrics.json: Machine-specific absolute paths detected in artifact")

    # Check version string matches RELEASE_VERSION
    expected_version = get_release_version(workspace)
    if disk_canon.get("release_version") != expected_version:
        errors.append(f"canonical_metrics.json: release_version '{disk_canon.get('release_version')}' != RELEASE_VERSION '{expected_version}'")

    # 2. Derive canonical metrics in memory from pinned sources
    try:
        in_mem_canon = derive_all_canonical_metrics(workspace)
    except Exception as e:
        errors.append(f"In-memory canonical derivation failed: {e}")
        return False, errors

    # 3. Compare primary benchmark fields between disk_canon and in_mem_canon
    pb_disk = disk_canon.get("primary_benchmark", {}).get("arms", {})
    pb_mem = in_mem_canon.get("primary_benchmark", {}).get("arms", {})
    for arm in ["full", "ci_k1_reactive", "ci_k2_reactive", "ci_k1_static"]:
        if arm not in pb_disk:
            errors.append(f"canonical_metrics.json: Missing arm '{arm}'")
            continue
        d_tok = pb_disk[arm].get("total_workload_tokens")
        m_tok = pb_mem[arm].get("total_workload_tokens")
        if d_tok != m_tok:
            errors.append(f"canonical_metrics.json: Arm '{arm}' tokens mismatch: disk={d_tok}, derived={m_tok}")
        d_fp = pb_disk[arm].get("first_pass_structural_pct")
        m_fp = pb_mem[arm].get("first_pass_structural_pct")
        if d_fp != m_fp:
            errors.append(f"canonical_metrics.json: Arm '{arm}' first_pass mismatch: disk={d_fp}, derived={m_fp}")
        d_st_cnt = pb_disk[arm].get("final_structural_success_count")
        m_st_cnt = pb_mem[arm].get("final_structural_success_count")
        if d_st_cnt != m_st_cnt:
            errors.append(f"canonical_metrics.json: Arm '{arm}' final structural count mismatch: disk={d_st_cnt}, derived={m_st_cnt}")
        d_st_pct = pb_disk[arm].get("final_structural_success_pct")
        m_st_pct = pb_mem[arm].get("final_structural_success_pct")
        if d_st_pct != m_st_pct:
            errors.append(f"canonical_metrics.json: Arm '{arm}' final structural pct mismatch: disk={d_st_pct}, derived={m_st_pct}")
        d_h_cnt = pb_disk[arm].get("first_pass_hierarchical_count")
        m_h_cnt = pb_mem[arm].get("first_pass_hierarchical_count")
        if d_h_cnt != m_h_cnt:
            errors.append(f"canonical_metrics.json: Arm '{arm}' first_pass_hierarchical_count mismatch: disk={d_h_cnt}, derived={m_h_cnt}")
        d_h_pct = pb_disk[arm].get("first_pass_hierarchical_pct")
        m_h_pct = pb_mem[arm].get("first_pass_hierarchical_pct")
        if d_h_pct != m_h_pct:
            errors.append(f"canonical_metrics.json: Arm '{arm}' first_pass_hierarchical_pct mismatch: disk={d_h_pct}, derived={m_h_pct}")

    # Latency comparison
    lat_disk = disk_canon.get("latency_hierarchy", {}).get("local_ast_pipeline_latency_ms", {})
    lat_mem = in_mem_canon.get("latency_hierarchy", {}).get("local_ast_pipeline_latency_ms", {})
    if lat_disk.get("p50_us") != lat_mem.get("p50_us"):
        errors.append(f"canonical_metrics.json: AST p50_us mismatch: disk={lat_disk.get('p50_us')}, derived={lat_mem.get('p50_us')}")
    if lat_disk.get("ratio_display") != lat_mem.get("ratio_display"):
        errors.append(f"canonical_metrics.json: Latency ratio display mismatch: disk={lat_disk.get('ratio_display')}, derived={lat_mem.get('ratio_display')}")

    # Cross-schema comparison
    cs_disk = disk_canon.get("cross_schema_stress_test", {}).get("derived_summary", {})
    cs_mem = in_mem_canon.get("cross_schema_stress_test", {}).get("derived_summary", {})
    disk_macro_sav = cs_disk.get("unweighted_macro_mean", {}).get("exact_macro_mean_savings_pct")
    mem_macro_sav = cs_mem.get("unweighted_macro_mean", {}).get("exact_macro_mean_savings_pct")
    if disk_macro_sav != mem_macro_sav:
        errors.append(f"canonical_metrics.json: Cross-schema macro savings mismatch: disk={disk_macro_sav}, derived={mem_macro_sav}")

    # 4. Check H1 intent prediction artifacts & canonical subtree
    h1_disk_subtree = disk_canon.get("h1_intent_prediction", {})
    h1_mem_subtree = in_mem_canon.get("h1_intent_prediction", {})
    d_delta = h1_disk_subtree.get("evaluation_summary", {}).get("paired_delta", {}).get("exact_f1_difference")
    m_delta = h1_mem_subtree.get("evaluation_summary", {}).get("paired_delta", {}).get("exact_f1_difference")
    if d_delta != m_delta:
        errors.append(f"canonical_metrics.json: H1 delta F1 mismatch: disk={d_delta}, derived={m_delta}")

    h1_json_path = workspace / "version_2" / "h1_predictor_evaluation.json"
    if not h1_json_path.exists():
        errors.append(f"Missing {h1_json_path}")
    else:
        try:
            with open(h1_json_path, "r", encoding="utf-8") as fp:
                h1_file_data = json.load(fp)
            file_f1 = h1_file_data.get("metrics_summary", {}).get("lasr_predictive_model", {}).get("mean_f1")
            mem_f1 = h1_mem_subtree.get("evaluation_summary", {}).get("lasr_predictive_model", {}).get("mean_f1")
            if file_f1 != mem_f1:
                errors.append(f"h1_predictor_evaluation.json: LASR mean F1 mismatch: file={file_f1}, derived={mem_f1}")
            file_delta = h1_file_data.get("metrics_summary", {}).get("paired_delta", {}).get("exact_f1_difference")
            if file_delta != m_delta:
                errors.append(f"h1_predictor_evaluation.json: Paired delta mismatch: file={file_delta}, derived={m_delta}")
            
            # Verify per-task row count and match
            file_per_task = h1_file_data.get("per_task_results", [])
            mem_per_task = h1_mem_subtree.get("per_task_results", [])
            if len(file_per_task) != 32:
                errors.append(f"h1_predictor_evaluation.json: Expected 32 per-task results, found {len(file_per_task)}")
            for idx, (fr, mr) in enumerate(zip(file_per_task, mem_per_task)):
                if fr.get("task_id") != mr.get("task_id") or fr.get("f1_delta") != mr.get("f1_delta"):
                    errors.append(f"h1_predictor_evaluation.json: Task {fr.get('task_id')} row mismatch at index {idx}")
                    break
        except Exception as e:
            errors.append(f"Failed to validate {h1_json_path}: {e}")

    h1_csv_path = workspace / "version_2" / "h1_predictor_evaluation.csv"
    if not h1_csv_path.exists():
        errors.append(f"Missing {h1_csv_path}")
    else:
        try:
            with open(h1_csv_path, "r", encoding="utf-8") as fp:
                csv_reader = list(csv.DictReader(fp))
            if len(csv_reader) != 32:
                errors.append(f"h1_predictor_evaluation.csv: Expected 32 rows, found {len(csv_reader)}")
            for idx, (cr, mr) in enumerate(zip(csv_reader, in_mem_h1 := h1_mem_subtree.get("per_task_results", []))):
                if cr.get("task_id") != mr.get("task_id") or float(cr.get("f1_delta", 0)) != mr.get("f1_delta"):
                    errors.append(f"h1_predictor_evaluation.csv: Row mismatch at task {cr.get('task_id')}")
                    break
        except Exception as e:
            errors.append(f"Failed to validate {h1_csv_path}: {e}")

    # 5. Check Retrieval Diagnostics (curves, CSV, JSON)
    ret_disk = disk_canon.get("retrieval_diagnostics", {})
    ret_mem = in_mem_canon.get("retrieval_diagnostics", {})
    for k in [1, 2, 3, 5]:
        d_tf = ret_disk.get("tfidf_curve", {}).get(f"top_{k}", {}).get("macro_recall_pct")
        m_tf = ret_mem.get("tfidf_curve", {}).get(f"top_{k}", {}).get("macro_recall_pct")
        if d_tf != m_tf:
            errors.append(f"canonical_metrics.json: TF-IDF k={k} macro recall mismatch: disk={d_tf}, derived={m_tf}")
        d_lsa = ret_disk.get("lsa_curve", {}).get(f"top_{k}", {}).get("macro_recall_pct")
        m_lsa = ret_mem.get("lsa_curve", {}).get(f"top_{k}", {}).get("macro_recall_pct")
        if d_lsa != m_lsa:
            errors.append(f"canonical_metrics.json: LSA k={k} macro recall mismatch: disk={d_lsa}, derived={m_lsa}")

    ret_json_path = workspace / "version_2" / "dense_rag_evaluation.json"
    if not ret_json_path.exists():
        errors.append(f"Missing {ret_json_path}")
    else:
        try:
            with open(ret_json_path, "r", encoding="utf-8") as fp:
                ret_file_data = json.load(fp)
            for k in [1, 2, 3, 5]:
                f_tf = ret_file_data.get("tfidf_results", {}).get(f"top_{k}", {}).get("macro_recall_pct")
                m_tf = ret_mem.get("tfidf_curve", {}).get(f"top_{k}", {}).get("macro_recall_pct")
                if f_tf != m_tf:
                    errors.append(f"dense_rag_evaluation.json: TF-IDF k={k} macro recall mismatch: file={f_tf}, derived={m_tf}")
                f_lsa = ret_file_data.get("lsa_results", {}).get(f"top_{k}", {}).get("macro_recall_pct")
                m_lsa = ret_mem.get("lsa_curve", {}).get(f"top_{k}", {}).get("macro_recall_pct")
                if f_lsa != m_lsa:
                    errors.append(f"dense_rag_evaluation.json: LSA k={k} macro recall mismatch: file={f_lsa}, derived={m_lsa}")
        except Exception as e:
            errors.append(f"Failed to validate {ret_json_path}: {e}")

    ret_csv_path = workspace / "version_2" / "retrieval_evaluation_curve.csv"
    if not ret_csv_path.exists():
        errors.append(f"Missing {ret_csv_path}")
    else:
        try:
            with open(ret_csv_path, "r", encoding="utf-8") as fp:
                ret_rows = list(csv.DictReader(fp))
            if len(ret_rows) != 8:
                errors.append(f"retrieval_evaluation_curve.csv: Expected 8 rows, found {len(ret_rows)}")
            for row in ret_rows:
                method = row.get("Retriever")
                k = int(row.get("k", 0))
                rec_str = row.get("Macro Recall %", "").replace("%", "")
                rec_val = float(rec_str)
                curve_key = "tfidf_curve" if "TF-IDF" in method else "lsa_curve"
                exp_val = ret_mem.get(curve_key, {}).get(f"top_{k}", {}).get("macro_recall_pct")
                if abs(rec_val - exp_val) > 0.001:
                    errors.append(f"retrieval_evaluation_curve.csv: {method} k={k} macro recall mismatch: file={rec_val}, derived={exp_val}")
        except Exception as e:
            errors.append(f"Failed to validate {ret_csv_path}: {e}")

    # 6. Check cross_schema_derived_summary.json on disk matches in-memory derivation
    cs_path = workspace / "version_2" / "cross_schema_derived_summary.json"
    if not cs_path.exists():
        errors.append(f"Missing {cs_path}")
    else:
        with open(cs_path, "r", encoding="utf-8") as f:
            cs_disk_summary = json.load(f)
        val = cs_disk_summary.get("pooled_workload_aggregate", {}).get("pooled_workload_savings_pct")
        if val != 22.5:
            errors.append(f"cross_schema_derived_summary.json: pooled_workload_savings_pct != 22.5 (found {val})")
        if cs_disk_summary.get("unweighted_macro_mean", {}).get("exact_macro_mean_savings_pct") != cs_mem["unweighted_macro_mean"]["exact_macro_mean_savings_pct"]:
            errors.append("cross_schema_derived_summary.json: macro savings does not match in-memory derivation")

    # 7. Check baseline_comparison_table.csv
    csv_path = workspace / "version_2" / "baseline_comparison_table.csv"
    if not csv_path.exists():
        errors.append(f"Missing {csv_path}")
    else:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = {r["Architecture / Arm"]: r for r in reader}
            
        full_row = rows.get("Full Schema (Draft 2020-12)")
        if not full_row or full_row.get("Total Workload Tokens (32 Tasks)") != "61853":
            errors.append("baseline_comparison_table.csv: Full schema tokens mismatch (expected 61853)")
        if not full_row or "31.3%" not in full_row.get("First-Pass Structural %", "") and "31.25%" not in full_row.get("First-Pass Structural %", ""):
            errors.append("baseline_comparison_table.csv: Full schema first pass 31.3% missing")
            
        k2_row = rows.get("LASR-MCP (k=2 Reactive Recovery)")
        if not k2_row or k2_row.get("Total Workload Tokens (32 Tasks)") != "50276":
            errors.append("baseline_comparison_table.csv: LASR k=2 tokens mismatch (expected 50276)")
        if not k2_row or "18.7%" not in k2_row.get("Net Workload Savings %", ""):
            errors.append("baseline_comparison_table.csv: LASR k=2 savings mismatch (expected 18.7%)")
            
        lg_row = rows.get("LangGraph Stateful Accumulation Pattern")
        if not lg_row or lg_row.get("Total Workload Tokens (32 Tasks)") != "69119":
            errors.append("baseline_comparison_table.csv: LangGraph tokens mismatch (expected 69119)")

    # 8. Check baseline_comparison_snapshot.json
    snap_path = workspace / "version_2" / "baseline_comparison_snapshot.json"
    if not snap_path.exists():
        errors.append(f"Missing {snap_path}")
    else:
        with open(snap_path, "r", encoding="utf-8") as f:
            snap_data = json.load(f)
        snap_rows = {r["Architecture / Arm"]: r for r in snap_data}
        if "Full Schema (Draft 2020-12)" not in snap_rows or snap_rows["Full Schema (Draft 2020-12)"]["Total Workload Tokens (32 Tasks)"] != "61853":
            errors.append("baseline_comparison_snapshot.json: Full schema tokens mismatch")
        if "LASR-MCP (k=2 Reactive Recovery)" not in snap_rows or snap_rows["LASR-MCP (k=2 Reactive Recovery)"]["Total Workload Tokens (32 Tasks)"] != "50276":
            errors.append("baseline_comparison_snapshot.json: LASR k=2 tokens mismatch")
        if "LangGraph Stateful Accumulation Pattern" not in snap_rows or snap_rows["LangGraph Stateful Accumulation Pattern"]["Total Workload Tokens (32 Tasks)"] != "69119":
            errors.append("baseline_comparison_snapshot.json: LangGraph tokens mismatch")

    # 9. Verify Table artifacts byte-for-byte against deterministic in-memory generator
    from version_2.generate_paper_tables_v2 import generate_all_tables
    expected_tables = generate_all_tables(export=False)
    for t_name, exp_content in expected_tables.items():
        t_path = workspace / "version_2" / "paper_v2" / "tables" / t_name
        if not t_path.exists():
            errors.append(f"Missing table artifact: {t_name}")
        else:
            act_content = t_path.read_text(encoding="utf-8")
            if act_content.strip() != exp_content.strip():
                errors.append(f"{t_name}: File content diverges from deterministic generator (cell or formatting mismatch)")

    # 9b. Check Table 1 LaTeX (numeric cell level & Init S0 / Exp delta S)
    t1_path = workspace / "version_2" / "paper_v2" / "tables" / "table1_systems_evaluation.tex"
    if not t1_path.exists():
        errors.append(f"Missing {t1_path}")
    else:
        t1_text = t1_path.read_text(encoding="utf-8")
        # Check primary token totals
        for tok in ["61,853", "50,276", "51,594", "56,947"]:
            if tok not in t1_text:
                errors.append(f"table1_systems_evaluation.tex: Token total {tok} missing")
        # Check Mean TTS
        for tts in ["1864.4", "1571.1", "1612.3"]:
            if tts not in t1_text:
                errors.append(f"table1_systems_evaluation.tex: Mean TTS {tts} missing")
        # Check First-pass hierarchical %
        if "31.3\\%" not in t1_text:
            errors.append("table1_systems_evaluation.tex: First-pass 31.3% missing")
        # Check Final structural % (must not be tampered to 5.0%)
        if "100.0\\%" not in t1_text:
            errors.append("table1_systems_evaluation.tex: Final structural 100.0% missing")
        # Check Init S0 and Exp delta S derived means
        for s0_str in ["552.0", "339.0", "361.1", "366.8"]:
            if s0_str not in t1_text:
                errors.append(f"table1_systems_evaluation.tex: Init S0 mean {s0_str} missing")
        for exp_str in ["45.4", "43.8", "48.3"]:
            if exp_str not in t1_text:
                errors.append(f"table1_systems_evaluation.tex: Exp delta S mean {exp_str} missing")

    # 10. Check Table 2 LaTeX (exact p-values, paired differences, bootstrap CIs)
    t2_path = workspace / "version_2" / "paper_v2" / "tables" / "table2_paired_bootstrap.tex"
    if not t2_path.exists():
        errors.append(f"Missing {t2_path}")
    else:
        t2_text = t2_path.read_text(encoding="utf-8")
        if "p = 0.0078125" not in t2_text:
            errors.append("table2_paired_bootstrap.tex: Exact McNemar p=0.0078125 missing")
        if "p = 0.250" not in t2_text or "p = 0.500" not in t2_text:
            errors.append("table2_paired_bootstrap.tex: Exact McNemar p=0.250 or p=0.500 missing")
        if "+21.9 pp" not in t2_text:
            errors.append("table2_paired_bootstrap.tex: Point estimate +21.9 pp missing")
        if "-10,259" not in t2_text or "-11,577" not in t2_text:
            errors.append("table2_paired_bootstrap.tex: Workload token difference (-10,259 / -11,577) missing")

    # 11. Check Table 3 LaTeX (Cluster breakdown lifts)
    t3_path = workspace / "version_2" / "paper_v2" / "tables" / "table3_cluster_breakdown.tex"
    if not t3_path.exists():
        errors.append(f"Missing {t3_path}")
    else:
        t3_text = t3_path.read_text(encoding="utf-8")
        if "Observed Lift" not in t3_text and "Reactive vs. Static Lift" not in t3_text:
            errors.append("table3_cluster_breakdown.tex: 'Reactive vs. Static Lift' header missing")
        if "+50.0 pp" not in t3_text or "+25.0 pp" not in t3_text or "+12.5 pp" not in t3_text:
            errors.append("table3_cluster_breakdown.tex: Cluster lifts missing or tampered")

    # 12. Check Table 4 LaTeX (Cross-Schema Table)
    t4_path = workspace / "version_2" / "paper_v2" / "tables" / "table4_cross_schema.tex"
    if not t4_path.exists():
        errors.append(f"Missing {t4_path}")
    else:
        t4_text = t4_path.read_text(encoding="utf-8")
        if "54,657" not in t4_text or "42,369" not in t4_text:
            errors.append("table4_cross_schema.tex: Note must cite 54,657 -> 42,369 pooled tokens")
        if "66,720" in t4_text or "51,708" in t4_text:
            errors.append("table4_cross_schema.tex: Legacy token counts found")
        if "316.8" not in t4_text:
            errors.append("table4_cross_schema.tex: Macro invariant floor 316.8 missing")
        if "361.3" not in t4_text:
            errors.append("table4_cross_schema.tex: Mean initial S0 (361.3) missing")
        if "553.3" not in t4_text:
            errors.append("table4_cross_schema.tex: Macro full schema size (553.3) missing")
        if "22.3\\%" not in t4_text:
            errors.append("table4_cross_schema.tex: Four-domain macro savings (22.3%) missing")
        if "22.5\\%" not in t4_text:
            errors.append("table4_cross_schema.tex: Pooled savings (22.5%) missing")
        if "25.2\\%" not in t4_text:
            errors.append("table4_cross_schema.tex: Shipment creation savings 25.2% missing or tampered")

    # 13. Check Section 04 Results LaTeX
    sec4_path = workspace / "version_2" / "paper_v2" / "sections" / "04_results.tex"
    if not sec4_path.exists():
        errors.append(f"Missing {sec4_path}")
    else:
        sec4_text = sec4_path.read_text(encoding="utf-8")
        if "3,407.1" not in sec4_text or "0.0201" not in sec4_text or "0.00059\\%" not in sec4_text:
            errors.append("04_results.tex: Latency hierarchy or ratio mismatch")
        if "+0.613" not in sec4_text and "+0.6125" not in sec4_text:
            errors.append("04_results.tex: H1 delta (+0.613) missing")
        if "15.6\\%" not in sec4_text or "16.1\\%" not in sec4_text:
            errors.append("04_results.tex: Normalized Top-2 retrieval recall (15.6% / 16.1%) missing")
        if "21 of 32" not in sec4_text:
            errors.append("04_results.tex: Zero-hit count (21 of 32) missing")
        if "0.125" not in sec4_text:
            errors.append("04_results.tex: Cluster sensitivity p=0.125 disclosure missing")

    # 14. Check Section 05 Cross-Schema Results LaTeX
    sec5_path = workspace / "version_2" / "paper_v2" / "sections" / "05_cross_schema_results.tex"
    if not sec5_path.exists():
        errors.append(f"Missing {sec5_path}")
    else:
        sec5_text = sec5_path.read_text(encoding="utf-8")
        if "22.3\\%" not in sec5_text:
            errors.append("05_cross_schema_results.tex: Four-domain macro mean 22.3% missing")
        if "22.7\\%" not in sec5_text:
            errors.append("05_cross_schema_results.tex: Three-domain macro mean 22.7% missing")
        if "22.5\\%" not in sec5_text:
            errors.append("05_cross_schema_results.tex: Pooled token reduction 22.5% missing")

    # 14b. Check Section 07 Discussion LaTeX (Exploratory live sensitivity and limitation disclosure)
    sec7_path = workspace / "version_2" / "paper_v2" / "sections" / "07_discussion.tex"
    if not sec7_path.exists():
        errors.append(f"Missing {sec7_path}")
    else:
        sec7_text = sec7_path.read_text(encoding="utf-8")
        if "Exploratory Live Replication and Sensitivity Analysis" not in sec7_text:
            errors.append("07_discussion.tex: Missing required exploratory live replication section")
        if "285 newly observed unique" not in sec7_text:
            errors.append("07_discussion.tex: Missing disclosure of 285 unique live response entries")
        if "cross zero" not in sec7_text:
            errors.append("07_discussion.tex: Missing disclosure that live paired bootstrap intervals cross zero")

    # 15. Check README_V2.md
    readme_path = workspace / "version_2" / "README_V2.md"
    if not readme_path.exists():
        errors.append(f"Missing {readme_path}")
    else:
        rm_text = readme_path.read_text(encoding="utf-8")
        if "50,276" not in rm_text or "61,853" not in rm_text:
            errors.append("README_V2.md: Primary workload token totals missing")
        if "file:///c:" in rm_text or "file:///C:" in rm_text:
            errors.append("README_V2.md: Nonportable absolute file URI links detected")
        if "baseline_trajectories.json" in rm_text:
            errors.append("README_V2.md: Stale reference to baseline_trajectories.json (must use baseline_comparison_snapshot.json)")

    # 16. Check Datasets Manifest and Metadata Provenance
    frozen_manifest = workspace / "datasets" / "frozen_benchmark_n32" / "MANIFEST.sha256"
    if not frozen_manifest.exists():
        errors.append("datasets/frozen_benchmark_n32/MANIFEST.sha256 missing")
    else:
        m_hash = compute_file_sha256(frozen_manifest)
        if m_hash != "71e87aeefc5b10f7b5bc99571ecaf430b24b9f1811fa4dd3d47af50e84951c0b":
            errors.append(f"datasets/frozen_benchmark_n32/MANIFEST.sha256 hash mismatch: expected 71e87aeefc5b10f7b5bc99571ecaf430b24b9f1811fa4dd3d47af50e84951c0b, got {m_hash}")
        m_lines = [l.strip() for l in frozen_manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(m_lines) != 1 or "invariant_optimization_summary.json" not in m_lines[0]:
            errors.append("datasets/frozen_benchmark_n32/MANIFEST.sha256 must strictly list invariant_optimization_summary.json only")

    meta_file = workspace / "datasets" / "frozen_benchmark_n32" / "metadata.json"
    if not meta_file.exists():
        errors.append("datasets/frozen_benchmark_n32/metadata.json missing")
    else:
        meta_hash = compute_file_sha256(meta_file)
        if meta_hash != "ab8ca76d5ef47826ba95d28046b1b6181f001055fccf2490e659102249f72c91":
            errors.append(f"datasets/frozen_benchmark_n32/metadata.json hash mismatch: expected ab8ca76d5ef47826ba95d28046b1b6181f001055fccf2490e659102249f72c91, got {meta_hash}")

    return (len(errors) == 0, errors)

# Backward-compatible alias
validate_all_targets = audit_check

def regenerate_canonical_metrics(workspace: Path) -> Tuple[bool, str]:
    """
    Operator-triggered generation command.
    Derives canonical metrics from raw evidence and writes version_2/canonical_metrics.json.
    Reports changes relative to existing artifact if present.
    """
    print("[REGENERATE] Computing canonical metrics from raw pinned sources...")
    new_metrics = derive_all_canonical_metrics(workspace)
    
    out_path = workspace / "version_2" / "canonical_metrics.json"
    diff_report = []
    
    if out_path.exists():
        try:
            with open(out_path, "r", encoding="utf-8") as f:
                old_metrics = json.load(f)
            # Compare top-level keys
            for k in new_metrics:
                if k not in old_metrics:
                    diff_report.append(f"Added top-level section: {k}")
                elif new_metrics[k] != old_metrics[k]:
                    diff_report.append(f"Updated section: {k}")
        except Exception as e:
            diff_report.append(f"Could not parse existing artifact for diff: {e}")
    else:
        diff_report.append("Creating new canonical_metrics.json artifact")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(new_metrics, f, indent=2)
        
    print(f"[REGENERATE] Wrote {out_path.name} successfully.")
    diff_str = "\n".join(f"  - {d}" for d in diff_report) if diff_report else "  (No differences detected)"
    print(f"[REGENERATE] Diff report:\n{diff_str}")
    return True, diff_str

def test_regression_behavior(workspace: Path):
    print("[REGRESSION TEST] Testing that tampering with reported table values triggers validation failure...")
    csv_path = workspace / "version_2" / "baseline_comparison_table.csv"
    orig_content = csv_path.read_text(encoding="utf-8")
    try:
        tampered_content = orig_content.replace("50276", "99999")
        csv_path.write_text(tampered_content, encoding="utf-8")
        passed, errors = audit_check(workspace)
        if passed:
            raise AssertionError("Regression test FAILED: Tampered token total in CSV did not trigger error!")
        print(f"[REGRESSION TEST] Success: Tampered CSV value correctly caught: {errors}")
    finally:
        csv_path.write_text(orig_content, encoding="utf-8")
        print("[REGRESSION TEST] Original baseline table restored.")
        
    passed, errors = audit_check(workspace)
    print(f"[REGRESSION TEST] Post-restoration validation passed: {passed}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Canonical Metric Reconciliation & Consistency Validator")
    parser.add_argument("--check", action="store_true", default=True, help="Run pure read-only audit check (default)")
    parser.add_argument("--regenerate", action="store_true", help="Explicitly regenerate canonical_metrics.json from evidence")
    parser.add_argument("--test-regression", action="store_true", help="Run regression test on tampering detection")
    args = parser.parse_args()
    
    if args.regenerate:
        success, report = regenerate_canonical_metrics(WORKSPACE)
        if not success:
            sys.exit(1)
        passed, errors = audit_check(WORKSPACE)
        if not passed:
            print("[WARNING] Post-regeneration audit found discrepancies:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("[SUCCESS] Canonical metrics regenerated and audit checks passed!")
    elif args.test_regression:
        test_regression_behavior(WORKSPACE)
    else:
        passed, errors = audit_check(WORKSPACE)
        if not passed:
            print("[ERROR] Canonical audit check failed with findings:")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("[SUCCESS] Pure read-only canonical audit passed! All targets match canonical evidence.")

if __name__ == "__main__":
    main()
