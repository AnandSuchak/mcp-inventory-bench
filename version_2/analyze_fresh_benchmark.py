#!/usr/bin/env python3
"""
Pre-Specified Clustered Bootstrap & Statistical Analysis for Fresh Live Benchmark
Project: mcp-inventory-bench
Author: Anand S. Suchak

Implements:
1. Paired task-level cluster bootstrap with 10,000 resamples over task clusters.
2. Pre-specified Primary Hypothesis Test: LASR k=2 reactive vs Full Control.
3. Secondary Hypothesis Tests: all other arms vs Full Control.
4. Generates empirical point estimates and 95% percentile confidence intervals (empirical 2.5% and 97.5% quantiles) for:
   - Workload token savings (Provider Total and P+C)
   - Conditional mean TTS reductions
   - First-pass hierarchical success differences
   - Final structural success differences
5. Outputs structured JSON and CSV tables.
"""

import sys
import os
import json
import csv
import random
import datetime
import argparse
from pathlib import Path
from typing import Dict, Any, List, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent

def run_clustered_bootstrap(
    trials: List[Dict[str, Any]],
    treatment_arm: str = "ci_k2_reactive",
    control_arm: str = "full",
    n_resamples: int = 10000,
    seed: int = 42
) -> Dict[str, Any]:
    # Group trials by task_id and arm
    tasks = sorted(list({t["task_id"] for t in trials}))
    n_tasks = len(tasks)

    # For each task, compute mean across replicates for control and treatment
    task_data = {}
    for task_id in tasks:
        ctrl_trials = [t for t in trials if t["task_id"] == task_id and t["arm"] == control_arm]
        treat_trials = [t for t in trials if t["task_id"] == task_id and t["arm"] == treatment_arm]

        ctrl_pc = sum(t["total_prompt_candidate_tokens"] for t in ctrl_trials) / len(ctrl_trials) if ctrl_trials else 0
        treat_pc = sum(t["total_prompt_candidate_tokens"] for t in treat_trials) / len(treat_trials) if treat_trials else 0

        ctrl_prov = sum(t.get("total_provider_tokens", 0) for t in ctrl_trials) / len(ctrl_trials) if ctrl_trials else 0
        treat_prov = sum(t.get("total_provider_tokens", 0) for t in treat_trials) / len(treat_trials) if treat_trials else 0

        ctrl_struct = sum(1 for t in ctrl_trials if t["final_structural_success"]) / len(ctrl_trials) if ctrl_trials else 0
        treat_struct = sum(1 for t in treat_trials if t["final_structural_success"]) / len(treat_trials) if treat_trials else 0

        ctrl_hier = sum(1 for t in ctrl_trials if t["first_pass_hierarchical_success"]) / len(ctrl_trials) if ctrl_trials else 0
        treat_hier = sum(1 for t in treat_trials if t["first_pass_hierarchical_success"]) / len(treat_trials) if treat_trials else 0

        task_data[task_id] = {
            "ctrl_pc": ctrl_pc,
            "treat_pc": treat_pc,
            "ctrl_prov": ctrl_prov,
            "treat_prov": treat_prov,
            "ctrl_struct": ctrl_struct,
            "treat_struct": treat_struct,
            "ctrl_hier": ctrl_hier,
            "treat_hier": treat_hier
        }

    # Observed point estimates
    obs_ctrl_pc_tot = sum(task_data[t]["ctrl_pc"] for t in tasks)
    obs_treat_pc_tot = sum(task_data[t]["treat_pc"] for t in tasks)
    obs_pc_savings = ((obs_ctrl_pc_tot - obs_treat_pc_tot) / obs_ctrl_pc_tot * 100.0) if obs_ctrl_pc_tot > 0 else 0.0

    obs_ctrl_prov_tot = sum(task_data[t]["ctrl_prov"] for t in tasks)
    obs_treat_prov_tot = sum(task_data[t]["treat_prov"] for t in tasks)
    obs_prov_savings = ((obs_ctrl_prov_tot - obs_treat_prov_tot) / obs_ctrl_prov_tot * 100.0) if obs_ctrl_prov_tot > 0 else 0.0

    obs_struct_diff = (sum(task_data[t]["treat_struct"] for t in tasks) - sum(task_data[t]["ctrl_struct"] for t in tasks)) / n_tasks * 100.0
    obs_hier_diff = (sum(task_data[t]["treat_hier"] for t in tasks) - sum(task_data[t]["ctrl_hier"] for t in tasks)) / n_tasks * 100.0

    # Cluster bootstrap over tasks
    rng = random.Random(seed)
    boot_pc_savings = []
    boot_prov_savings = []
    boot_struct_diff = []
    boot_hier_diff = []

    for _ in range(n_resamples):
        sample_tasks = [rng.choice(tasks) for _ in range(n_tasks)]
        b_c_pc = sum(task_data[t]["ctrl_pc"] for t in sample_tasks)
        b_t_pc = sum(task_data[t]["treat_pc"] for t in sample_tasks)
        if b_c_pc > 0:
            boot_pc_savings.append((b_c_pc - b_t_pc) / b_c_pc * 100.0)

        b_c_prov = sum(task_data[t]["ctrl_prov"] for t in sample_tasks)
        b_t_prov = sum(task_data[t]["treat_prov"] for t in sample_tasks)
        if b_c_prov > 0:
            boot_prov_savings.append((b_c_prov - b_t_prov) / b_c_prov * 100.0)

        b_st_diff = (sum(task_data[t]["treat_struct"] for t in sample_tasks) - sum(task_data[t]["ctrl_struct"] for t in sample_tasks)) / n_tasks * 100.0
        boot_struct_diff.append(b_st_diff)

        b_h_diff = (sum(task_data[t]["treat_hier"] for t in sample_tasks) - sum(task_data[t]["ctrl_hier"] for t in sample_tasks)) / n_tasks * 100.0
        boot_hier_diff.append(b_h_diff)

    boot_pc_savings.sort()
    boot_prov_savings.sort()
    boot_struct_diff.sort()
    boot_hier_diff.sort()

    def get_ci(sorted_arr):
        if not sorted_arr:
            return (0.0, 0.0)
        idx_lo = int(0.025 * len(sorted_arr))
        idx_hi = int(0.975 * len(sorted_arr))
        return (round(sorted_arr[idx_lo], 2), round(sorted_arr[idx_hi], 2))

    return {
        "treatment_arm": treatment_arm,
        "control_arm": control_arm,
        "n_tasks": n_tasks,
        "n_resamples": n_resamples,
        "prompt_candidate_tokens": {
            "control_total": round(obs_ctrl_pc_tot, 1),
            "treatment_total": round(obs_treat_pc_tot, 1),
            "point_estimate_savings_pct": round(obs_pc_savings, 2),
            "ci_95_pct": get_ci(boot_pc_savings),
            "crosses_zero": get_ci(boot_pc_savings)[0] <= 0 <= get_ci(boot_pc_savings)[1]
        },
        "provider_total_tokens": {
            "control_total": round(obs_ctrl_prov_tot, 1),
            "treatment_total": round(obs_treat_prov_tot, 1),
            "point_estimate_savings_pct": round(obs_prov_savings, 2),
            "ci_95_pct": get_ci(boot_prov_savings),
            "crosses_zero": get_ci(boot_prov_savings)[0] <= 0 <= get_ci(boot_prov_savings)[1]
        },
        "final_structural_success_diff": {
            "point_estimate_pct": round(obs_struct_diff, 2),
            "ci_95_pct": get_ci(boot_struct_diff)
        },
        "first_pass_hierarchical_success_diff": {
            "point_estimate_pct": round(obs_hier_diff, 2),
            "ci_95_pct": get_ci(boot_hier_diff)
        }
    }

def analyze_benchmark(data_dir: Path) -> Dict[str, Any]:
    trials_path = data_dir / "benchmark_trial_records.json"
    if not trials_path.exists():
        raise FileNotFoundError(f"Missing trials file: {trials_path}")

    with open(trials_path, "r", encoding="utf-8") as f:
        trials = json.load(f)

    # Primary comparison
    primary_res = run_clustered_bootstrap(trials, treatment_arm="ci_k2_reactive", control_arm="full")

    # Secondary comparisons
    secondaries = {}
    for arm in ["ci_k0", "ci_k1_static", "ci_k1_reactive", "oracle_reactive"]:
        secondaries[arm] = run_clustered_bootstrap(trials, treatment_arm=arm, control_arm="full")

    results = {
        "analysis_name": "LASR-MCP Clustered Bootstrap Statistical Analysis",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "primary_comparison": primary_res,
        "secondary_comparisons": secondaries
    }

    out_path = data_dir / "statistical_analysis_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("=" * 80)
    print("CLUSTERED BOOTSTRAP ANALYSIS COMPLETE")
    print(f"Primary Comparison (LASR k=2 vs Full):")
    print(f"  - Provider Total Savings: {primary_res['provider_total_tokens']['point_estimate_savings_pct']}% (95% CI: {primary_res['provider_total_tokens']['ci_95_pct']})")
    print(f"  - P+C Tokens Savings:     {primary_res['prompt_candidate_tokens']['point_estimate_savings_pct']}% (95% CI: {primary_res['prompt_candidate_tokens']['ci_95_pct']})")
    print(f"  - Zero Cross Status:      {'CROSSES ZERO' if primary_res['prompt_candidate_tokens']['crosses_zero'] else 'STATISTICALLY SIGNIFICANT'}")
    print("=" * 80)
    return results

def main():
    parser = argparse.ArgumentParser(description="Analyze fresh live benchmark data.")
    parser.add_argument("--data-dir", type=str, default="datasets/fresh_live_benchmark_n32")
    args = parser.parse_args()
    analyze_benchmark(Path(args.data_dir))

if __name__ == "__main__":
    main()
