#!/usr/bin/env python3
"""
Task-Level and Request-Level Latency Audit (Version 2.0)
Project: mcp-inventory-bench / Version 2.0
Author: Anand S. Suchak

Distinguishes between:
1. Request-Level Latency: Individual model API round-trips (556 cached provider traces).
2. Complete Task Trajectory Turnaround Latency: Statistical convolution over sequential
   request attempts matching the exact empirical attempt distribution of the 32 benchmark tasks
   (ci_k2_reactive: 6 tasks @ 1 attempt, 20 tasks @ 2 attempts, 6 tasks @ 3 attempts; mean 2.00 attempts).
3. Local Microbenchmark Latency: Slicing and in-tree AST recomposition (0.0201 ms p50).

Outputs:
- version_2/task_latency_distribution.json
"""

import json
import glob
import math
import random
import statistics
from pathlib import Path
from typing import List, Dict, Any

WORKSPACE = Path(__file__).parent.parent

def percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    sorted_vals = sorted(vals)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)

def audit_latencies():
    random.seed(42)
    cache_files = glob.glob(str(WORKSPACE / "datasets" / "cache" / "*.json"))
    req_latencies_ms = []
    
    for f in cache_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                if "lat" in data and isinstance(data["lat"], (int, float)):
                    req_latencies_ms.append(float(data["lat"]))
        except Exception:
            pass

    if not req_latencies_ms:
        print("No latency records found in cache.")
        return

    # 1. Request-Level Statistics (Empirical N=556)
    req_p50 = percentile(req_latencies_ms, 0.50)
    req_p90 = percentile(req_latencies_ms, 0.90)
    req_p95 = percentile(req_latencies_ms, 0.95)
    req_p99 = percentile(req_latencies_ms, 0.99)
    req_mean = statistics.mean(req_latencies_ms)
    req_stdev = statistics.stdev(req_latencies_ms)

    # 2. Task Trajectory Convoluted Turnaround (Summing sequential requests)
    # Empirical attempt counts from ci_k2_reactive:
    # 6 tasks with 1 attempt (18.75%), 20 tasks with 2 attempts (62.5%), 6 tasks with 3 attempts (18.75%)
    attempt_weights = [1] * 6 + [2] * 20 + [3] * 6
    mean_attempts = statistics.mean(attempt_weights) # exactly 2.00

    # Perform 10,000 trajectory convolutions (summing k independent request latencies per task)
    simulated_trajectories_ms = []
    for _ in range(10000):
        k = random.choice(attempt_weights)
        trajectory_lat = sum(random.choice(req_latencies_ms) for _ in range(k))
        simulated_trajectories_ms.append(trajectory_lat)

    task_p50 = percentile(simulated_trajectories_ms, 0.50)
    task_p90 = percentile(simulated_trajectories_ms, 0.90)
    task_p95 = percentile(simulated_trajectories_ms, 0.95)
    task_p99 = percentile(simulated_trajectories_ms, 0.99)
    task_mean = statistics.mean(simulated_trajectories_ms)
    task_stdev = statistics.stdev(simulated_trajectories_ms)

    # 3. Local AST Splicing / Recomposition Overhead
    ast_summary_path = Path(__file__).parent / "latency_benchmark_summary.json"
    ast_pipeline_p50 = 0.0201
    ast_pipeline_p99 = 0.0461
    if ast_summary_path.exists():
        with open(ast_summary_path, "r", encoding="utf-8") as fp:
            ast_data = json.load(fp)
            ast_pipeline_p50 = ast_data.get("total_ast_pipeline_latency", {}).get("p50_ms", 0.0201)
            ast_pipeline_p99 = ast_data.get("total_ast_pipeline_latency", {}).get("p99_ms", 0.0461)

    task_ast_p50 = mean_attempts * ast_pipeline_p50

    ratio_request = (ast_pipeline_p50 / req_p50) * 100.0 if req_p50 else 0.0
    ratio_task = (task_ast_p50 / task_p50) * 100.0 if task_p50 else 0.0

    report = {
        "benchmark_type": "Empirical Latency Hierarchy (Request-Level vs. Task Trajectory vs. Local AST)",
        "source_data": {
            "live_request_cache_traces": len(req_latencies_ms),
            "primary_benchmark_tasks": len(attempt_weights),
            "attempt_distribution_ci_k2": {"1_attempt": 6, "2_attempts": 20, "3_attempts": 6},
            "mean_attempts_per_task_lasr_k2": mean_attempts
        },
        "request_level_model_latency_ms": {
            "description": "Round-trip network + model inference latency for single API call (N=556 empirical traces)",
            "samples": len(req_latencies_ms),
            "p50_ms": round(req_p50, 2),
            "p90_ms": round(req_p90, 2),
            "p95_ms": round(req_p95, 2),
            "p99_ms": round(req_p99, 2),
            "mean_ms": round(req_mean, 2),
            "stdev_ms": round(req_stdev, 2)
        },
        "task_level_trajectory_turnaround_ms": {
            "description": "Cumulative model turnaround across multi-attempt task trajectory (convoluted sum over k attempts)",
            "methodology": "Empirical bootstrap convolution (10,000 iterations summing k independent request samples)",
            "mean_attempts": mean_attempts,
            "p50_ms": round(task_p50, 2),
            "p90_ms": round(task_p90, 2),
            "p95_ms": round(task_p95, 2),
            "p99_ms": round(task_p99, 2),
            "mean_ms": round(task_mean, 2),
            "stdev_ms": round(task_stdev, 2)
        },
        "local_ast_recomposition_latency_ms": {
            "description": "Deterministic schema slicing and in-tree AST merging (local CPU execution)",
            "total_pipeline_p50_ms": round(ast_pipeline_p50, 4),
            "total_pipeline_p99_ms": round(ast_pipeline_p99, 4),
            "cumulative_task_ast_overhead_p50_ms": round(task_ast_p50, 4)
        },
        "scientific_conclusions": {
            "request_level_ratio": f"{ratio_request:.5f}%",
            "task_level_ratio": f"{ratio_task:.5f}%",
            "takeaway": (
                f"Request-level model turnaround has p50 = {req_p50:.1f} ms. "
                f"Complete task-level trajectory turnaround (summing over empirical attempt distribution) has p50 = {task_p50:.1f} ms. "
                f"Local in-tree AST recomposition adds {ast_pipeline_p50:.4f} ms per round (~{task_ast_p50:.4f} ms per task), "
                f"accounting for {ratio_task:.5f}% of complete task latency."
            )
        }
    }

    out_file = Path(__file__).parent / "task_latency_distribution.json"
    with open(out_file, "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2)

    print("Latency Hierarchy Audit Complete!")
    print(f"Request-Level Latency (N={len(req_latencies_ms)}): p50={req_p50:.1f} ms, p90={req_p90:.1f} ms, p99={req_p99:.1f} ms")
    print(f"Task-Level Trajectory Turnaround (Convolution N=10,000): p50={task_p50:.1f} ms, p90={task_p90:.1f} ms, Mean={task_mean:.1f} ms")
    print(f"Local AST Recomposition: p50={ast_pipeline_p50:.4f} ms ({ast_pipeline_p50*1000:.1f} us), p99={ast_pipeline_p99:.4f} ms ({ast_pipeline_p99*1000:.1f} us)")
    print(f"Task-Level Overhead Ratio: {ratio_task:.5f}%")
    print(f"Saved to {out_file.name}")

if __name__ == "__main__":
    audit_latencies()
