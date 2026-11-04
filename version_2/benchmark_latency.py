#!/usr/bin/env python3
"""
Wall-Clock AST Splicing and Recomposition Latency Benchmark (Version 2.0)
Project: mcp-inventory-bench / Version 2.0
Author: Anand S. Suchak

Executes controlled, microsecond-accurate wall-clock benchmarking of:
1. Deterministic AST slicing (slice_constraint_timed)
2. Deterministic AST recomposition (recompose_schema_timed)
across 1,000 iterations for realistic enterprise schema bundles.

Generates:
- version_2/latency_benchmark_measurements.csv (raw per-iteration timings)
- version_2/latency_benchmark_summary.json (p50, p90, p95, p99, mean, stdev)
"""

import sys
import json
import csv
import math
import statistics
from pathlib import Path
from typing import List, Dict, Any

WORKSPACE = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE))

from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.slicer import create_invariant_schema
from version_2.recomposer_v2 import slice_constraint_timed, recompose_schema_timed

def percentile(vals: List[float], p: float) -> float:
    if not vals:
        return 0.0
    sorted_vals = sorted(vals)
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = (len(sorted_vals) - 1) * p
    lo, hi = math.floor(pos), math.ceil(pos)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)

def run_latency_benchmark(num_iterations: int = 1000):
    full_schema = FULL_PURCHASE_ORDER_SCHEMA
    base_schema = create_invariant_schema(full_schema)

    # Representative test bundles
    test_bundles = [
        ("single_enum", ["warehouse_code.enum"]),
        ("single_pattern", ["authorized_by.pattern"]),
        ("k2_typical", ["warehouse_code.enum", "authorized_by.pattern"]),
        ("k2_numeric", ["order_priority.enum", "total_budget_limit.maximum"]),
        ("k3_complex", ["warehouse_code.enum", "order_priority.enum", "items.quantity.minimum"]),
        ("recovery_step", ["items.sku.pattern", "total_budget_limit.maximum"])
    ]

    # Slicing test cases
    slice_cases = [
        ("slice_enum", "/warehouse_code", "enum"),
        ("slice_pattern", "/authorized_by", "pattern"),
        ("slice_nested_min", "/items/0/quantity", "minimum"),
        ("slice_required", "/", "required"),
        ("slice_max", "/total_budget_limit", "maximum")
    ]

    # Warmup runs (JIT/cache warmup)
    for _ in range(100):
        for _, b in test_bundles:
            recompose_schema_timed(base_schema, b, full_schema)
        for _, p, k in slice_cases:
            slice_constraint_timed(full_schema, p, k)

    measurements: List[Dict[str, Any]] = []
    recompose_latencies_ms: List[float] = []
    slice_latencies_ms: List[float] = []
    total_pipeline_latencies_ms: List[float] = []

    print(f"Running {num_iterations} latency benchmark iterations...")
    for i in range(num_iterations):
        bundle_name, bundle = test_bundles[i % len(test_bundles)]
        slice_name, s_path, s_kw = slice_cases[i % len(slice_cases)]

        # 1. Measure Slice
        delta, slice_ns = slice_constraint_timed(full_schema, s_path, s_kw)
        slice_ms = slice_ns / 1_000_000.0
        slice_latencies_ms.append(slice_ms)

        # 2. Measure Recompose
        rec_schema, rec_ns, bdown = recompose_schema_timed(base_schema, bundle, full_schema)
        rec_ms = rec_ns / 1_000_000.0
        recompose_latencies_ms.append(rec_ms)

        pipeline_ms = slice_ms + rec_ms
        total_pipeline_latencies_ms.append(pipeline_ms)

        measurements.append({
            "iteration": i + 1,
            "bundle_type": bundle_name,
            "bundle_size": len(bundle),
            "slice_case": slice_name,
            "slice_latency_us": round(slice_ns / 1000.0, 3),
            "slice_latency_ms": round(slice_ms, 6),
            "recompose_latency_us": round(rec_ns / 1000.0, 3),
            "recompose_latency_ms": round(rec_ms, 6),
            "total_ast_latency_ms": round(pipeline_ms, 6)
        })

    # Summary Statistics
    def stats_dict(vals: List[float]):
        return {
            "samples": len(vals),
            "mean_ms": round(statistics.mean(vals), 6),
            "stdev_ms": round(statistics.stdev(vals), 6),
            "min_ms": round(min(vals), 6),
            "p50_ms": round(percentile(vals, 0.50), 6),
            "p90_ms": round(percentile(vals, 0.90), 6),
            "p95_ms": round(percentile(vals, 0.95), 6),
            "p99_ms": round(percentile(vals, 0.99), 6),
            "max_ms": round(max(vals), 6),
            "p50_us": round(percentile(vals, 0.50) * 1000.0, 2),
            "p99_us": round(percentile(vals, 0.99) * 1000.0, 2),
        }

    summary = {
        "benchmark_name": "LASR-MCP AST Splicing & Recomposition Wall-Clock Benchmark",
        "iterations": num_iterations,
        "timing_method": "time.perf_counter_ns()",
        "environment": {
            "python_version": sys.version,
            "os": sys.platform
        },
        "ast_slice_latency": stats_dict(slice_latencies_ms),
        "ast_recomposition_latency": stats_dict(recompose_latencies_ms),
        "total_ast_pipeline_latency": stats_dict(total_pipeline_latencies_ms)
    }

    out_dir = Path(__file__).parent
    csv_file = out_dir / "latency_benchmark_measurements.csv"
    json_file = out_dir / "latency_benchmark_summary.json"

    # Write CSV
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(measurements[0].keys()))
        writer.writeheader()
        writer.writerows(measurements)

    # Write JSON
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\nBenchmark Complete!")
    print(f"AST Slicing: p50 = {summary['ast_slice_latency']['p50_ms']:.4f} ms ({summary['ast_slice_latency']['p50_us']:.1f} us), p99 = {summary['ast_slice_latency']['p99_ms']:.4f} ms ({summary['ast_slice_latency']['p99_us']:.1f} us)")
    print(f"AST Recomposition: p50 = {summary['ast_recomposition_latency']['p50_ms']:.4f} ms ({summary['ast_recomposition_latency']['p50_us']:.1f} us), p99 = {summary['ast_recomposition_latency']['p99_ms']:.4f} ms ({summary['ast_recomposition_latency']['p99_us']:.1f} us)")
    print(f"Total Pipeline: p50 = {summary['total_ast_pipeline_latency']['p50_ms']:.4f} ms ({summary['total_ast_pipeline_latency']['p50_us']:.1f} us), p99 = {summary['total_ast_pipeline_latency']['p99_ms']:.4f} ms ({summary['total_ast_pipeline_latency']['p99_us']:.1f} us)")
    print(f"Artifacts saved to {csv_file.name} and {json_file.name}")

if __name__ == "__main__":
    run_latency_benchmark(1000)
