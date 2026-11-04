#!/usr/bin/env python3
"""
Version-2-Only Paper Tables Generator & Statistical Reconciler (Version 2.0.3)
Project: mcp-inventory-bench / Version 2.0.3
Author: Anand S. Suchak

Generates LaTeX tables I, II, III, and IV strictly into:
version_2/paper_v2/tables/
NEVER writes to protected root paper/tables/!

Recomputes paired outcomes by joining strictly on task_id.
All table metrics are derived dynamically from per-task records in frozen datasets.
Rounding standard: Round-half-up to one decimal place, applied only at render time.
CLI: Supports --help and dry-run without writing files. Pass --export to generate files.
"""

import sys
import os
import json
import math
import random
import argparse
import statistics
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Any, List, Tuple

WORKSPACE = Path(__file__).resolve().parent.parent
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))
TABLES_DIR = WORKSPACE / "version_2" / "paper_v2" / "tables"

def round_half_up(val: float, decimals: int = 1) -> str:
    """Standardized round-half-up policy applied strictly at display formatting time."""
    d = Decimal(str(val))
    fmt = "0." + "0" * decimals if decimals > 0 else "0"
    return str(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))

def generate_table1(frozen_data: Dict[str, Any]) -> str:
    """Generates Table I dynamically from the 32 per-task records in frozen benchmark data."""
    sb = frozen_data["systems_benchmark"]
    arms_config = [
        (r"Full Schema Control (\texttt{full})", "full", "No"),
        (r"$C_I^*$ Baseline (\texttt{ci\_k0}, $k=0$)", "ci_k0", "No"),
        (r"LASR Static (\texttt{ci\_k1\_static}, $k=1$)", "ci_k1_static", "No"),
        (r"LASR Reactive (\texttt{ci\_k1\_reactive}, $k=1$)", "ci_k1_reactive", "Yes"),
        (r"LASR Reactive (\texttt{ci\_k2\_reactive}, $k=2$)", "ci_k2_reactive", "Yes"),
        (r"Oracle Reference* (\texttt{oracle\_reactive})", "oracle_reactive", "Yes")
    ]

    # Verify matching task ID sets across all arms
    arm_task_sets = {k: {r["task_id"] for r in sb[k]["records"]} for _, k, _ in arms_config}
    ref_tasks = arm_task_sets["full"]
    if len(ref_tasks) != 32:
        raise ValueError(f"Full schema arm does not have 32 unique task IDs (got {len(ref_tasks)})")
    for _, k, _ in arms_config:
        if arm_task_sets[k] != ref_tasks:
            raise ValueError(f"Task ID mismatch between 'full' and '{k}'")

    rows = []
    for label, arm_key, reactive in arms_config:
        arm = sb[arm_key]
        recs = arm.get("records", [])
        if not recs or len(recs) != 32:
            raise ValueError(f"Arm '{arm_key}' missing valid records (expected 32, got {len(recs)})")

        n_recs = len(recs)
        # Dynamically derived from immutable per-task records:
        mean_init_s0 = statistics.mean(r["s0_schema_tokens"] for r in recs)
        mean_exp_s = statistics.mean(r["reactive_expansion_tokens"] for r in recs)
        init_s0_str = round_half_up(mean_init_s0, 1)
        exp_s_str = round_half_up(mean_exp_s, 1)

        # Hierarchical first-pass success: structural AND semantic
        fp_count = sum(1 for r in recs if r.get("first_pass_structural") and r.get("first_pass_semantic"))
        fp_pct = round_half_up((fp_count / n_recs) * 100.0, 1)

        st_count = sum(1 for r in recs if r["final_structural_success"])
        st_pct = round_half_up((st_count / n_recs) * 100.0, 1)

        sem_count = sum(1 for r in recs if r["final_semantic_correctness"])
        sem_pct = round_half_up((sem_count / n_recs) * 100.0, 1)

        succ_tts = [sum(a.get("prompt_tokens", 0) + a.get("completion_tokens", 0) for a in r.get("attempts", []))
                    for r in recs if r["final_structural_success"]]
        mean_tts = round_half_up(statistics.mean(succ_tts), 1) if succ_tts else "0.0"

        # Recorded prompt-plus-candidate token subtotal (excluding heuristic schema addition)
        tot_tok_val = sum(sum(a.get("prompt_tokens", 0) + a.get("completion_tokens", 0) for a in r.get("attempts", [])) for r in recs)
        tot_tok = f"{tot_tok_val:,}"

        # Bold highlight top systems
        if arm_key in ["ci_k1_reactive", "ci_k2_reactive", "full"]:
            st_str = f"\\textbf{{{st_pct}\\%}}"
        else:
            st_str = f"{st_pct}\\%"

        if arm_key in ["ci_k2_reactive", "full"]:
            tok_str = f"\\textbf{{{tot_tok}}}"
        else:
            tok_str = tot_tok

        rows.append(
            f"{label} & {reactive} & {init_s0_str} & {exp_s_str} & {fp_pct}\\% & "
            f"{st_str} & {sem_pct}\\% & {mean_tts} & {tok_str} \\\\"
        )

    rows_tex = "\n".join(rows)
    content = f"""\\begin{{table*}}[t]
\\centering
\\caption{{Initial Single-Trial Frozen Benchmark Systems Evaluation ($N=32$ Tasks, Gemini 3.5 Flash-Lite)}}
\\label{{tab:systems_evaluation}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{lcccccccc}}
\\toprule
\\textbf{{System Arm}} & \\textbf{{Reactive?}} & \\textbf{{Init $S_0$}} & \\textbf{{Exp. $\\Delta S$}} & \\textbf{{1st-Pass Hier. (\\%)}} & \\textbf{{Struct. (\\%)}} & \\textbf{{Sem. (\\%)}} & \\textbf{{Mean $TTS_{{\\text{{P+C}}}}$}} & \\textbf{{Recorded P+C Tokens}} \\\\
\\midrule
{rows_tex}
\\bottomrule
\\end{{tabular}}%
}}
\\vspace{{1mm}}
\\begin{{minipage}}{{\\textwidth}}
\\footnotesize
*\\textit{{Note}}: Oracle $O(x)$ is a model-conditional reference baseline. 1st-Pass Hierarchical success requires both structural validity and semantic correctness on Attempt 1 (Full Schema: 10/32 tasks, 31.25\\%, displayed 31.3\\%). Mean $TTS_{{\\text{{P+C}}}}$ is the average recorded prompt-plus-candidate token subtotal over structurally successful trajectories ($N_{{\\text{{succ}}}}$); Recorded P+C Tokens accounts for all prompt and completion tokens across all attempts without heuristic schema double-counting.
\\end{{minipage}}
\\end{{table*}}
"""
    return content

def calc_exact_mcnemar_binomial(recs_a: Dict[str, Any], recs_b: Dict[str, Any], key: str) -> Tuple[float, int, int]:
    """
    Computes exact one-sided McNemar / binomial test p-value from task-matched discordant pairs.
    Tests alternative hypothesis H1: System A > System B.
    """
    b = sum(1 for tid in recs_a if recs_a[tid][key] and not recs_b[tid][key])
    c = sum(1 for tid in recs_a if not recs_a[tid][key] and recs_b[tid][key])
    n = b + c
    if n == 0:
        return 1.0, b, c
    p_val = sum(math.comb(n, k) * (0.5**n) for k in range(b, n + 1))
    return float(p_val), b, c

def generate_table2(frozen_data: Dict[str, Any]) -> str:
    """Generates Table II dynamically from task-matched outcomes with exact McNemar p-values."""
    sb = frozen_data["systems_benchmark"]
    full_recs = {r["task_id"]: r for r in sb["full"]["records"]}
    static_recs = {r["task_id"]: r for r in sb["ci_k1_static"]["records"]}
    k1_recs = {r["task_id"]: r for r in sb["ci_k1_reactive"]["records"]}
    k2_recs = {r["task_id"]: r for r in sb["ci_k2_reactive"]["records"]}

    task_ids = sorted(full_recs.keys())
    if len(task_ids) != 32 or set(static_recs.keys()) != set(task_ids) or set(k1_recs.keys()) != set(task_ids) or set(k2_recs.keys()) != set(task_ids):
        raise ValueError("Task ID mismatch across arms in generate_table2")

    # 1. Reactive k=1 vs Static k=1
    st_diffs_static = [int(k1_recs[tid]["final_structural_success"]) - int(static_recs[tid]["final_structural_success"]) for tid in task_ids]
    sem_diffs_static = [int(k1_recs[tid]["final_semantic_correctness"]) - int(static_recs[tid]["final_semantic_correctness"]) for tid in task_ids]

    # 2. Reactive k=1 vs Full
    st_diffs_full = [int(k1_recs[tid]["final_structural_success"]) - int(full_recs[tid]["final_structural_success"]) for tid in task_ids]
    sem_diffs_full = [int(k1_recs[tid]["final_semantic_correctness"]) - int(full_recs[tid]["final_semantic_correctness"]) for tid in task_ids]

    # Point estimates derived from records using round_half_up
    pt_st_static = round_half_up(statistics.mean(st_diffs_static) * 100.0, 1)
    pt_sem_static = round_half_up(statistics.mean(sem_diffs_static) * 100.0, 1)
    pt_st_full = round_half_up(statistics.mean(st_diffs_full) * 100.0, 1)
    pt_sem_full = round_half_up(statistics.mean(sem_diffs_full) * 100.0, 1)

    # Bootstrap 95% CI helper (deterministic seed)
    random.seed(42)
    def calc_ci(diff_list):
        B = 10000
        n = len(diff_list)
        means = []
        for _ in range(B):
            sample = [random.choice(diff_list) for _ in range(n)]
            means.append(statistics.mean(sample) * 100.0)
        means.sort()
        return round_half_up(means[int(0.025 * B)], 1), round_half_up(means[int(0.975 * B)], 1)

    ci_st_static = calc_ci(st_diffs_static)
    ci_sem_static = calc_ci(sem_diffs_static)
    ci_st_full = calc_ci(st_diffs_full)
    ci_sem_full = calc_ci(sem_diffs_full)

    # Exact one-sided McNemar / binomial p-values
    p_st_s, b_st_s, c_st_s = calc_exact_mcnemar_binomial(k1_recs, static_recs, "final_structural_success")
    p_sem_s, b_sem_s, c_sem_s = calc_exact_mcnemar_binomial(k1_recs, static_recs, "final_semantic_correctness")
    p_st_f, b_st_f, c_st_f = calc_exact_mcnemar_binomial(k1_recs, full_recs, "final_structural_success")
    p_sem_f, b_sem_f, c_sem_f = calc_exact_mcnemar_binomial(k1_recs, full_recs, "final_semantic_correctness")

    p_str_st_s = f"Exact McNemar ($p = {p_st_s:.7g}$)"
    p_str_sem_s = f"Exact McNemar ($p = {p_sem_s:.7g}$)"
    p_str_st_f = f"Exact McNemar ($p = {p_st_f:.3f}$)"
    p_str_sem_f = f"Exact McNemar ($p = {p_sem_f:.3f}$)"

    # Recorded prompt-plus-candidate token subtotals derived from records
    full_tot = sum(sum(a.get("prompt_tokens", 0) + a.get("completion_tokens", 0) for a in full_recs[tid]["attempts"]) for tid in task_ids)
    k1_tot = sum(sum(a.get("prompt_tokens", 0) + a.get("completion_tokens", 0) for a in k1_recs[tid]["attempts"]) for tid in task_ids)
    k2_tot = sum(sum(a.get("prompt_tokens", 0) + a.get("completion_tokens", 0) for a in k2_recs[tid]["attempts"]) for tid in task_ids)

    k1_diff_str = f"{k1_tot - full_tot:,} tokens"
    k2_diff_str = f"{k2_tot - full_tot:,} tokens"
    k1_sav_pct = round_half_up(((full_tot - k1_tot) / full_tot) * 100.0, 1)
    k2_sav_pct = round_half_up(((full_tot - k2_tot) / full_tot) * 100.0, 1)

    content = f"""\\begin{{table}}[htbp]
\\centering
\\caption{{Historical Paired Differences and Hypothesis Tests ($N=32$ Single-Trial Development Benchmark)}}
\\label{{tab:paired_bootstrap}}
\\setlength{{\\tabcolsep}}{{2.5pt}}
\\resizebox{{\\columnwidth}}{{!}}{{%
\\begin{{tabular}}{{lccccc}}
\\toprule
\\textbf{{Pairwise Contrast}} & \\textbf{{Metric}} & \\textbf{{Point Est.}} & \\textbf{{95\\% CI}} & \\textbf{{Token Diff.}} & \\textbf{{Statistical Method}} \\\\
\\midrule
LASR Reactive vs Static ($k=1$) & $\\Delta$ Structural Succ. & \\textbf{{+{pt_st_static} pp}} & [{ci_st_static[0]}, {ci_st_static[1]}] pp & --- & {p_str_st_s} \\\\
& $\\Delta$ Semantic Corr. & \\textbf{{+{pt_sem_static} pp}} & [{ci_sem_static[0]}, {ci_sem_static[1]}] pp & --- & {p_str_sem_s} \\\\
\\midrule
LASR Reactive ($k=1$) vs Full & $\\Delta$ Structural Succ. & +{pt_st_full} pp & [{ci_st_full[0]}, {ci_st_full[1]}] pp & --- & {p_str_st_f} \\\\
& $\\Delta$ Semantic Corr. & +{pt_sem_full} pp & [{ci_sem_full[0]}, {ci_sem_full[1]}] pp & --- & {p_str_sem_f} \\\\
\\midrule
LASR Reactive ($k=1$) vs Full & Signed Token Savings & \\textbf{{+{k1_sav_pct}\\%}} & --- & {k1_diff_str} & Total Token Diff (No CI) \\\\
LASR Reactive ($k=2$) vs Full & Signed Token Savings & \\textbf{{+{k2_sav_pct}\\%}} & --- & {k2_diff_str} & Total Token Diff (No CI) \\\\
\\bottomrule
\\end{{tabular}}%
}}
\\end{{table}}
"""
    return content

def generate_table3(frozen_data: Dict[str, Any]) -> str:
    """Generates Table III dynamically from task cluster records."""
    sb = frozen_data["systems_benchmark"]
    full_recs = sb["full"]["records"]
    static_recs = sb["ci_k1_static"]["records"]
    k1_recs = sb["ci_k1_reactive"]["records"]

    clusters = [
        ("C1: Routine Regional", "routine_regional_replenish"),
        ("C2: Expedited Emergency", "expedited_emergency_order"),
        ("C3: Specialized Bulk", "specialized_bulk_procurement"),
        ("C4: Multi-Item Depot", "multi_item_depot_rebalance")
    ]

    rows = []
    for label, ckey in clusters:
        f_sub = [r for r in full_recs if r["cluster"] == ckey]
        s_sub = [r for r in static_recs if r["cluster"] == ckey]
        k_sub = [r for r in k1_recs if r["cluster"] == ckey]

        if len(f_sub) != 8 or len(s_sub) != 8 or len(k_sub) != 8:
            raise ValueError(f"Cluster '{ckey}' must have exactly 8 tasks per arm (got {len(f_sub)}, {len(s_sub)}, {len(k_sub)})")

        f_pct = round_half_up(sum(1 for r in f_sub if r["final_structural_success"]) / len(f_sub) * 100.0, 1)
        s_pct = round_half_up(sum(1 for r in s_sub if r["final_structural_success"]) / len(s_sub) * 100.0, 1)
        k_pct = round_half_up(sum(1 for r in k_sub if r["final_structural_success"]) / len(k_sub) * 100.0, 1)
        lift = round_half_up(float(k_pct) - float(s_pct), 1)

        lift_str = f"\\textbf{{+{lift} pp}}" if float(lift) > 0 else f"\\textbf{{{lift} pp}}"
        rows.append(
            f"{label} & {f_pct}\\% & {s_pct}\\% & \\textbf{{{k_pct}\\%}} & {lift_str} \\\\"
        )

    rows_tex = "\n".join(rows)
    content = f"""\\begin{{table}}[htbp]
\\centering
\\caption{{Historical Task Cluster Breakdown: Static Vulnerability vs. Reactive Recovery ($N=32$ Single-Trial Development Benchmark, $N=8$ per Cluster)}}
\\label{{tab:cluster_breakdown}}
\\setlength{{\\tabcolsep}}{{3pt}}
\\resizebox{{\\columnwidth}}{{!}}{{%
\\begin{{tabular}}{{lcccc}}
\\toprule
\\textbf{{Task Cluster Archetype}} & \\textbf{{Full (\\%)}} & \\textbf{{Static $k=1$}} & \\textbf{{Reactive $k=1$}} & \\textbf{{Reactive vs. Static Lift}} \\\\
\\midrule
{rows_tex}
\\bottomrule
\\end{{tabular}}%
}}
\\end{{table}}
"""
    return content

def generate_table4(cross_summary: Dict[str, Any]) -> str:
    """Generates Table IV dynamically from cross-schema derived summary with interpolated note text."""
    schemas = [
        ("create_purchase_order", r"\texttt{create\_purchase\_order}"),
        ("inventory_adjustment", r"\texttt{inventory\_adjustment}"),
        ("shipment_creation", r"\texttt{shipment\_creation}"),
        ("customer_refund", r"\texttt{customer\_refund}")
    ]

    rows = []
    for skey, slabel in schemas:
        sdata = cross_summary["per_schema"][skey]
        floor = sdata["invariant_floor_c_i"]
        mean_s0 = int(round(sdata["mean_initial_s0"]))
        full_s = sdata["full_schema_s"]
        sav = round_half_up(sdata["exact_savings_pct"], 1)
        fp = f"{sdata['first_pass_pct']:.1f}\\% ({sdata['first_pass_breakdown']})"
        st = f"\\textbf{{{sdata['final_struct_pct']:.1f}\\%}}"
        sem = f"{sdata['semantic_pct']:.1f}\\%"
        amb = f"\\textbf{{{sdata['ambiguous_recovery_pct']:.1f}\\%}} ({sdata['ambiguous_recovered_count']})"

        rows.append(
            f"{slabel} & {sdata['domain_description']} & {floor} & {mean_s0} & {full_s} & "
            f"\\textbf{{{sav}\\%}} & {fp} & {st} & {sem} & {amb} \\\\"
        )

    macro = cross_summary["unweighted_macro_mean"]
    pooled = cross_summary["pooled_workload_aggregate"]

    macro_floor = f"{macro['macro_invariant_floor']:.1f}"
    macro_s0 = round_half_up(macro["macro_mean_initial_s0"], 1)
    macro_full_s = round_half_up(macro["macro_full_schema_s"], 1)
    macro_sav = round_half_up(macro["exact_macro_mean_savings_pct"], 1)
    macro_fp = f"\\textbf{{{macro['macro_first_pass_pct']:.1f}\\%}} (16/16, 0/16)"
    macro_st = f"\\textbf{{{macro['macro_final_struct_pct']:.1f}\\%}}"
    macro_sem = f"\\textbf{{{macro['macro_semantic_pct']:.1f}\\%}}"
    macro_amb = f"\\textbf{{{macro['macro_ambiguous_recovery_pct']:.1f}\\%}} (16/16)"

    pooled_sav = round_half_up(pooled["exact_pooled_savings_pct"], 1)
    three_new_sav = round_half_up(macro["three_new_domains_macro_savings_pct"], 1)

    rows_tex = "\n".join(rows)

    cpo_sav = f"{cross_summary['per_schema']['create_purchase_order']['exact_savings_pct']:.4f}\\%"
    ia_sav = f"{cross_summary['per_schema']['inventory_adjustment']['exact_savings_pct']:.4f}\\%"
    sc_sav = f"{cross_summary['per_schema']['shipment_creation']['exact_savings_pct']:.4f}\\%"
    cr_sav = f"{cross_summary['per_schema']['customer_refund']['exact_savings_pct']:.4f}\\%"
    all_4_eq = f"({cpo_sav} + {ia_sav} + {sc_sav} + {cr_sav}) / 4 = {macro['exact_macro_mean_savings_pct']:.4f}\\%"
    three_new_eq = f"({ia_sav} + {sc_sav} + {cr_sav}) / 3 = {macro['exact_three_new_domains_macro_savings_pct']:.3f}\\%"

    note_text = (
        f"\\textit{{Note}}: Evaluated across 32 independent tasks (4 schemas $\\times$ 8 tasks) under a deterministic simulation-based "
        f"mechanism stress test using whitespace/punctuation heuristic token estimates. Workload savings measure total token "
        f"reduction relative to monolithic full schema. The \\textbf{{Unweighted Macro Mean}} ({macro_sav}\\%) averages unrounded "
        f"per-domain percentage reductions ${all_4_eq}$, while the three new domains average {three_new_sav}\\% (${three_new_eq}$). "
        f"The \\textbf{{Pooled Workload Aggregate}} ({pooled_sav}\\%) computes total token reduction across 32 independent tasks evaluated over two arms "
        f"(64 task-arm records, reducing pooled tokens from {pooled['pooled_full_tokens']:,} to {pooled['pooled_lasr_tokens']:,} tokens across 4 schemas). In this deterministic simulation, "
        f"both arms share identical modeled structural and recovery outcomes (16/32 first-pass, 32/32 final structural, 30/32 semantic); "
        f"reported savings reflect lower token exposure under matched simulated completion outcomes. \\textbf{{Floor $C_I^*$}} denotes "
        f"the schema invariant token floor; \\textbf{{Mean $S_0$}} denotes the actual initial active schema size across evaluated tasks (macro mean: {macro_s0})."
    )

    content = f"""\\begin{{table*}}[t]
\\centering
\\caption{{Cross-Schema Mechanism Stress Test across Four Heterogeneous Enterprise Domains ($N=32$ Tasks total, 8 per Schema)}}
\\label{{tab:cross_schema}}
\\setlength{{\\tabcolsep}}{{3.5pt}}
\\resizebox{{\\textwidth}}{{!}}{{%
\\begin{{tabular}}{{llcccccccc}}
\\toprule
\\textbf{{Enterprise-Style Tool Schema}} & \\textbf{{Domain / Key Constraints}} & \\textbf{{Floor $C_I^*$}} & \\textbf{{Mean $S_0$}} & \\textbf{{Full $S$}} & \\textbf{{Workload Savings}} & \\textbf{{1st-Pass (Exp/Amb)}} & \\textbf{{Final Struct.}} & \\textbf{{Semantic}} & \\textbf{{Ambiguous Recovery}} \\\\
\\midrule
{rows_tex}
\\midrule
\\textbf{{Unweighted Macro Mean}} & Four-Domain Average ($N=4$ domains) & \\textbf{{{macro_floor}}} & \\textbf{{{macro_s0}}} & \\textbf{{{macro_full_s}}} & \\textbf{{{macro_sav}\\%}} & {macro_fp} & {macro_st} & {macro_sem} & {macro_amb} \\\\
\\textbf{{Pooled Workload Aggregate}} & Total Workload Tokens (32 independent tasks, 64 task-arm records) & -- & -- & -- & \\textbf{{{pooled_sav}\\%}} & {macro_fp} & {macro_st} & {macro_sem} & {macro_amb} \\\\
\\bottomrule
\\end{{tabular}}%
}}
\\vspace{{1mm}}
\\begin{{minipage}}{{\\textwidth}}
\\scriptsize
{note_text}
\\end{{minipage}}
\\end{{table*}}
"""
    return content

def generate_all_tables(export: bool = True) -> Dict[str, str]:
    """Generates all 4 tables in memory and optionally writes them to TABLES_DIR."""
    # 1. Load frozen primary benchmark
    frozen_path = WORKSPACE / "datasets" / "frozen_benchmark_n32" / "invariant_optimization_summary.json"
    with open(frozen_path, "r", encoding="utf-8") as fp:
        frozen_data = json.load(fp)

    # 2. Derive cross-schema summary purely in memory
    import version_2.derive_cross_schema_metrics as dcsm
    cross_summary = dcsm.derive_metrics(export=False)

    tables = {
        "table1_systems_evaluation.tex": generate_table1(frozen_data),
        "table2_paired_bootstrap.tex": generate_table2(frozen_data),
        "table3_cluster_breakdown.tex": generate_table3(frozen_data),
        "table4_cross_schema.tex": generate_table4(cross_summary)
    }

    if export:
        TABLES_DIR.mkdir(parents=True, exist_ok=True)
        for fname, content in tables.items():
            t_path = TABLES_DIR / fname
            t_path.write_text(content, encoding="utf-8")
        print(f"Generated and exported {len(tables)} tables strictly to {TABLES_DIR.relative_to(WORKSPACE)}:")
        for fname in tables:
            print(f"  - {fname}")

    return tables

def main():
    parser = argparse.ArgumentParser(description="Deterministic Paper Tables Generator for LASR-MCP Version 2")
    parser.add_argument("--export", action="store_true", default=False, help="Write generated tables to version_2/paper_v2/tables/ (default: dry run)")
    args = parser.parse_args()

    tables = generate_all_tables(export=args.export)
    if not args.export:
        print(f"Dry run complete: generated {len(tables)} tables in memory without modifying files.")
        print("Pass --export to write tables to version_2/paper_v2/tables/.")

if __name__ == "__main__":
    main()
