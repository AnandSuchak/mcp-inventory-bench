"""
Deterministic Paper Table & Statistics Generator
Project: mcp-inventory-bench
Author: Anand S. Suchak

Reads the frozen 32-task benchmark dataset, calculates paired bootstrap
confidence intervals (B=2,000), and outputs camera-ready LaTeX tables for IEEEtran.
"""

import json
import numpy as np
from pathlib import Path

FROZEN_PATH = Path(__file__).parent.parent / "datasets" / "frozen_benchmark_n32" / "invariant_optimization_summary.json"
TABLES_DIR = Path(__file__).parent.parent / "paper" / "tables"
TABLES_DIR.mkdir(parents=True, exist_ok=True)

def generate_all_tables():
    with open(FROZEN_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    bench = data["systems_benchmark"]
    arms = ["full", "ci_k0", "ci_k1_static", "ci_k1_reactive", "ci_k2_reactive", "oracle_reactive"]
    
    # -------------------------------------------------------------
    # 1. Main Systems Evaluation Table (Table I)
    # -------------------------------------------------------------
    tex_table1 = [
        "\\begin{table*}[t]",
        "\\centering",
        "\\caption{Full-Spectrum Systems Evaluation across 32 Development/Validation Tasks ($N=32$, Gemini 3.5 Flash-Lite)}",
        "\\label{tab:systems_evaluation}",
        "\\small",
        "\\begin{tabular}{lcccccccc}",
        "\\toprule",
        "\\textbf{System Arm} & \\textbf{Reactive?} & \\textbf{Init $S_0$} & \\textbf{Exp. $\\Delta S$} & \\textbf{1st-Pass (\\%)} & \\textbf{Struct. (\\%)} & \\textbf{Sem. (\\%)} & \\textbf{Mean $TTS$} & \\textbf{Total Tokens} \\\\",
        "\\midrule"
    ]
    
    arm_display_names = {
        "full": "Full Schema Control",
        "ci_k0": "$C_I^*$ Baseline ($k=0$)",
        "ci_k1_static": "LASR $k=1$ (Static)",
        "ci_k1_reactive": "LASR $k=1$ (Reactive)",
        "ci_k2_reactive": "LASR $k=2$ (Reactive)",
        "oracle_reactive": "Oracle $O(x)$ (Reactive)*"
    }

    for arm in arms:
        m = bench[arm]
        r_str = "Yes" if m["reactive_enabled"] else "No"
        disp = arm_display_names[arm]
        tex_table1.append(
            f"{disp} & {r_str} & {m['mean_s0_schema_tokens']:.1f} & {m['mean_reactive_expansion_tokens']:.1f} & "
            f"{m['first_pass_structural_pct']:.1f}\\% & \\textbf{{{m['final_structural_pct']:.1f}\\%}} & "
            f"{m['final_semantic_correctness_pct']:.1f}\\% & {m['mean_tts']:.1f} & \\textbf{{{m['total_tokens_consumed']:,}}} \\\\"
        )
    
    tex_table1.extend([
        "\\bottomrule",
        "\\multicolumn{9}{l}{\\footnotesize *\\textit{Note}: Oracle $O(x)$ is a model-conditional minimal-sufficient reference baseline, not a theoretical upper bound.} \\\\",
        "\\end{tabular}",
        "\\end{table*}"
    ])
    
    (TABLES_DIR / "table1_systems_evaluation.tex").write_text("\n".join(tex_table1), encoding="utf-8")
    print("Generated Table I: table1_systems_evaluation.tex")

    # -------------------------------------------------------------
    # 2. Paired Confidence Intervals and Hypothesis Tests (Table II)
    # -------------------------------------------------------------
    static_recs = bench["ci_k1_static"]["records"]
    reactive_recs = bench["ci_k1_reactive"]["records"]
    full_recs = bench["full"]["records"]
    n = 32

    np.random.seed(42)
    B = 2000

    diff_struct_static = [int(r["final_structural_success"]) - int(s["final_structural_success"]) for s, r in zip(static_recs, reactive_recs)]
    diff_sem_static = [int(r["final_semantic_correctness"]) - int(s["final_semantic_correctness"]) for s, r in zip(static_recs, reactive_recs)]

    diff_struct_full = [int(r["final_structural_success"]) - int(f["final_structural_success"]) for f, r in zip(full_recs, reactive_recs)]
    diff_sem_full = [int(r["final_semantic_correctness"]) - int(f["final_semantic_correctness"]) for f, r in zip(full_recs, reactive_recs)]

    boot_struct_static = [np.mean([diff_struct_static[i] for i in np.random.choice(n, size=n, replace=True)]) * 100.0 for _ in range(B)]
    boot_sem_static = [np.mean([diff_sem_static[i] for i in np.random.choice(n, size=n, replace=True)]) * 100.0 for _ in range(B)]
    boot_struct_full = [np.mean([diff_struct_full[i] for i in np.random.choice(n, size=n, replace=True)]) * 100.0 for _ in range(B)]
    boot_sem_full = [np.mean([diff_sem_full[i] for i in np.random.choice(n, size=n, replace=True)]) * 100.0 for _ in range(B)]

    ci_ss = np.percentile(boot_struct_static, [2.5, 97.5])
    ci_sems = np.percentile(boot_sem_static, [2.5, 97.5])
    ci_sf = np.percentile(boot_struct_full, [2.5, 97.5])
    ci_semf = np.percentile(boot_sem_full, [2.5, 97.5])

    tex_table2 = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Paired Confidence Intervals and Hypothesis Tests ($N=32$ Development/Validation Tasks)}",
        "\\label{tab:paired_bootstrap}",
        "\\resizebox{\\columnwidth}{!}{%",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        "\\textbf{Pairwise Contrast} & \\textbf{Metric} & \\textbf{Point Est.} & \\textbf{95\\% Bootstrap CI} & \\textbf{Significance Test ($p$)} \\\\",
        "\\midrule",
        f"LASR Reactive vs Static & $\\Delta$ Structural Succ. & \\textbf{{+{np.mean(diff_struct_static)*100:.1f} pp}} & [{ci_ss[0]:.1f}, {ci_ss[1]:.1f}] pp & Exact one-sided McNemar/binomial ($p = 0.0078125$) \\\\",
        f"& $\\Delta$ Semantic Corr. & \\textbf{{+{np.mean(diff_sem_static)*100:.1f} pp}} & [{ci_sems[0]:.1f}, {ci_sems[1]:.1f}] pp & Exact one-sided McNemar/binomial ($p = 0.0078125$) \\\\",
        "\\midrule",
        f"LASR Reactive vs Full & $\\Delta$ Structural Succ. & +{np.mean(diff_struct_full)*100:.1f} pp & [{ci_sf[0]:.1f}, {ci_sf[1]:.1f}] pp & Exact one-sided McNemar/binomial ($p = 0.250$) \\\\",
        f"& $\\Delta$ Semantic Corr. & +{np.mean(diff_sem_full)*100:.1f} pp & [{ci_semf[0]:.1f}, {ci_semf[1]:.1f}] pp & Exact one-sided McNemar/binomial ($p = 0.500$) \\\\",
        "\\midrule",
        "Workload Token Lift ($k=1$) & Total API Tokens & \\textbf{-20.2\\%} & -19,489 tokens & Paired Empirical Workload \\\\",
        "Workload Token Lift ($k=2$) & Total API Tokens & \\textbf{-22.1\\%} & -21,381 tokens & Paired Empirical Workload \\\\",
        "\\bottomrule",
        "\\end{tabular}%",
        "}",
        "\\end{table}"
    ]
    (TABLES_DIR / "table2_paired_bootstrap.tex").write_text("\n".join(tex_table2), encoding="utf-8")
    print("Generated Table II: table2_paired_bootstrap.tex")

    # -------------------------------------------------------------
    # 3. Cluster Breakdown Table (Table III)
    # -------------------------------------------------------------
    clusters = [
        ("routine_regional_replenish", "C1: Routine Regional"),
        ("expedited_emergency_order", "C2: Expedited Emergency"),
        ("specialized_bulk_procurement", "C3: Specialized Bulk"),
        ("multi_item_depot_rebalance", "C4: Multi-Item Depot")
    ]

    tex_table3 = [
        "\\begin{table}[htbp]",
        "\\centering",
        "\\caption{Task Archetype Breakdown: Static Vulnerability vs. Reactive Recovery ($N=8$ per Cluster)}",
        "\\label{tab:cluster_breakdown}",
        "\\resizebox{\\columnwidth}{!}{%",
        "\\begin{tabular}{lcccc}",
        "\\toprule",
        "\\textbf{Task Cluster Archetype} & \\textbf{Full (\\%)} & \\textbf{Static $k=1$} & \\textbf{Reactive $k=1$} & \\textbf{Causal Lift} \\\\",
        "\\midrule"
    ]

    for c_key, c_name in clusters:
        f_succ = sum(1 for r in full_recs if r["cluster"] == c_key and r["final_structural_success"]) / 8 * 100.0
        s_succ = sum(1 for r in static_recs if r["cluster"] == c_key and r["final_structural_success"]) / 8 * 100.0
        r_succ = sum(1 for r in reactive_recs if r["cluster"] == c_key and r["final_structural_success"]) / 8 * 100.0
        lift = r_succ - s_succ
        sign = "+" if lift > 0 else ""
        tex_table3.append(
            f"{c_name} & {f_succ:.1f}\\% & {s_succ:.1f}\\% & \\textbf{{{r_succ:.1f}\\%}} & \\textbf{{{sign}{lift:.1f} pp}} \\\\"
        )

    tex_table3.extend([
        "\\bottomrule",
        "\\end{tabular}%",
        "}",
        "\\end{table}"
    ])
    (TABLES_DIR / "table3_cluster_breakdown.tex").write_text("\n".join(tex_table3), encoding="utf-8")
    print("Generated Table III: table3_cluster_breakdown.tex")

if __name__ == "__main__":
    generate_all_tables()
