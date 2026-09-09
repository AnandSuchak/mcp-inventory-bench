"""
Empirical Analyzer for Pilot-2 Experiments 1 & 2
Project: mcp-inventory-bench
Author: Anand S. Suchak

Computes:
1. Experiment 1: Semantic Generalization Matrix P(c | S)
   - Evaluates whether semantic cluster S predicts constraint requirement c above background base rate P(c).
   - Computes Constraint Predictability Gap CPG(c, S) = P(c | S) - P(c | S')
   - Compares against Frequency-Prior Baseline.

2. Experiment 2: Schema Budget Curve (1A, 1B, 1C, 1D)
   - Evaluates First-Pass Success Rate vs. Initial Schema Tokens vs. Mean TTS.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter, defaultdict

def analyze_experiment1_matrix(traces_file: Path) -> Dict[str, Any]:
    if not traces_file.exists():
        print(f"[!] Traces file not found: {traces_file}")
        return {}

    traces = []
    with open(traces_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                traces.append(json.loads(line.strip()))

    total_tasks = len(traces)
    if total_tasks == 0:
        print("[!] No traces found.")
        return {}

    cluster_counts = Counter()
    cluster_constraint_counts = defaultdict(Counter)
    global_constraint_counts = Counter()

    for t in traces:
        cluster = t.get("category", "unknown")
        cluster_counts[cluster] += 1
        ledger = t.get("schema_exposure_ledger", [])
        constraints_in_trace = set(entry["fragment"] for entry in ledger if entry.get("reason", "").startswith("CONSTRAINT_VIOLATION"))

        for c in constraints_in_trace:
            cluster_constraint_counts[cluster][c] += 1
            global_constraint_counts[c] += 1

    all_clusters = sorted(list(cluster_counts.keys()))
    top_constraints = [c for c, _ in global_constraint_counts.most_common(6)]

    print("\n" + "=" * 84)
    print(f"[*] EXPERIMENT 1: SEMANTIC GENERALIZATION MATRIX P(c | S)")
    print(f"[*] Evaluated on {total_tasks} Blinded Tasks across {len(all_clusters)} Semantic Clusters")
    print("=" * 84)

    header = f"{'Constraint Fragment':<30}" + "".join([f"{c[:12]:>14}" for c in all_clusters]) + f"{'Base P(c)':>12}"
    print(header)
    print("-" * len(header))

    matrix_data = {}
    for c in top_constraints:
        row_str = f"{c:<30}"
        p_global = global_constraint_counts[c] / total_tasks
        matrix_data[c] = {"base_p": round(p_global, 3), "clusters": {}}

        for cluster in all_clusters:
            n_cluster = cluster_counts[cluster]
            p_cluster = cluster_constraint_counts[cluster][c] / n_cluster if n_cluster > 0 else 0.0
            row_str += f"{p_cluster:>14.3f}"
            matrix_data[c]["clusters"][cluster] = round(p_cluster, 3)

        row_str += f"{p_global:>12.3f}"
        print(row_str)

    print("\n[+] CONSTRAINT PREDICTABILITY GAPS CPG(c, S) = P(c|S) - P(c|S'):")
    cpg_data = {}
    for c in top_constraints:
        cpg_data[c] = {}
        for s in all_clusters:
            p_s = matrix_data[c]["clusters"][s]
            other_tasks = total_tasks - cluster_counts[s]
            other_hits = global_constraint_counts[c] - cluster_constraint_counts[s][c]
            p_other = other_hits / other_tasks if other_tasks > 0 else 0.0
            gap = p_s - p_other
            cpg_data[c][s] = round(gap, 3)
            if abs(gap) >= 0.20:
                print(f"    - [{s[:14]}] {c:<26}: P(c|S)={p_s:.2f} vs P(c|S')={p_other:.2f} -> CPG = {gap:+.3f}")

    print("=" * 84)
    return {"matrix": matrix_data, "cpg": cpg_data}
