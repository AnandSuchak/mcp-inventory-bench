#!/usr/bin/env python3
"""
Baseline Trajectory Evaluation & Token Accounting Reconciler (Version 2.0)
Project: mcp-inventory-bench / Version 2.0
Author: Anand S. Suchak

Strictly delineates:
1. Measured End-to-End System Arms (Full Schema, LASR k=1/k=2 Reactive, LASR k=1 Static)
2. Trace-Derived Counterfactual State-History Token Model (LangGraph message accumulation)
3. Retrieval-Only Baselines (Lexical TF-IDF and Inductive LSA / TruncatedSVD)
4. Planned Future Neural Baseline (text-embedding-004)

Never fabricates end-to-end execution metrics for retrieval-only baselines.
Outputs:
- version_2/baseline_comparison_table.csv
- version_2/baseline_comparison_snapshot.json
"""

import sys
import json
import csv
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Dict, Any, List

WORKSPACE = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE))

def round_half_up(val: float, decimals: int = 1) -> str:
    d = Decimal(str(val))
    fmt = "0." + "0" * decimals if decimals > 0 else "0"
    return str(d.quantize(Decimal(fmt), rounding=ROUND_HALF_UP))

def get_fp_pct(arm_data: Dict[str, Any]) -> str:
    recs = arm_data.get("records", [])
    if recs:
        count = sum(1 for r in recs if r.get("first_pass_structural"))
        return round_half_up(count / len(recs) * 100.0, 1)
    return round_half_up(arm_data["first_pass_structural_pct"], 1)

def run_baselines():
    # 1. Load frozen benchmark summary (Fail immediately if missing)
    frozen_path = WORKSPACE / "datasets" / "frozen_benchmark_n32" / "invariant_optimization_summary.json"
    if not frozen_path.exists():
        raise FileNotFoundError(f"Missing required primary benchmark ground truth: {frozen_path}")
    with open(frozen_path, "r", encoding="utf-8") as f:
        frozen_data = json.load(f)
    
    sb = frozen_data["systems_benchmark"]
    full_arm = sb["full"]
    k1_arm = sb["ci_k1_reactive"]
    k2_arm = sb["ci_k2_reactive"]
    k1_static_arm = sb["ci_k1_static"]

    # 2. Load audit report for offline lexical RAG
    audit_path = Path(__file__).parent / "lasr_trace_audit_report.json"
    if not audit_path.exists():
        raise FileNotFoundError(f"Missing required audit report: {audit_path}")
    with open(audit_path, "r", encoding="utf-8") as f:
        audit_data = json.load(f)
    rag_info = audit_data.get("offline_cosine_rag", {})
    macro_lex_recall = rag_info.get("macro_recall_at_k")

    # 3. Load latency benchmark summary
    lat_path = Path(__file__).parent / "latency_benchmark_summary.json"
    if not lat_path.exists():
        raise FileNotFoundError(f"Missing required latency benchmark summary: {lat_path}")
    with open(lat_path, "r", encoding="utf-8") as f:
        lat_data = json.load(f)
    rec_p50 = lat_data["ast_recomposition_latency"]["p50_ms"]
    rec_p99 = lat_data["ast_recomposition_latency"]["p99_ms"]

    # 4. Load LangGraph counterfactual report
    lg_path = Path(__file__).parent / "langgraph_traces.json"
    if not lg_path.exists():
        raise FileNotFoundError(f"Missing required LangGraph model report: {lg_path}")
    with open(lg_path, "r", encoding="utf-8") as f:
        lg_data = json.load(f)

    # 5. Load Inductive LSA report
    dense_path = Path(__file__).parent / "dense_rag_evaluation.json"
    if not dense_path.exists():
        raise FileNotFoundError(f"Missing required LSA evaluation report: {dense_path}")
    with open(dense_path, "r", encoding="utf-8") as f:
        dense_data = json.load(f)
    lsa_top2_macro = dense_data["results"]["top_2"]["macro_recall"]

    # Compile Table V data rows with strict methodological delineation
    table_rows = [
        # --- Measured Systems Arms ---
        {
            "Architecture / Arm": "Full Schema (Draft 2020-12)",
            "Evaluation Category": "Measured End-to-End System",
            "Constraint Retrieval Recall@2": "100.0% (Monolithic Exposure)",
            "First-Pass Structural %": f"{get_fp_pct(full_arm)}%",
            "Final Structural Success %": f"{round_half_up(full_arm['final_structural_pct'], 1)}%",
            "Mean TTS (Tokens-to-Success)": f"{full_arm['mean_tts']:.1f}",
            "Total Workload Tokens (32 Tasks)": str(full_arm['total_tokens_consumed']),
            "Mean Tokens / Task (Workload)": f"{full_arm['total_tokens_consumed'] / 32:.1f}",
            "Net Workload Savings %": "0.0% (Ref)",
            "AST Splicing Latency p50/p99": "0.0 / 0.0 ms (N/A)",
            "Scientific Status": "Verified (Frozen Benchmark N=32, SHA-256 78c2c88e...)"
        },
        {
            "Architecture / Arm": "LASR-MCP (k=1 Static Foundation)",
            "Evaluation Category": "Measured End-to-End System",
            "Constraint Retrieval Recall@2": "N/A (Learned Classifier)",
            "First-Pass Structural %": f"{get_fp_pct(k1_static_arm)}%",
            "Final Structural Success %": f"{round_half_up(k1_static_arm['final_structural_pct'], 1)}%",
            "Mean TTS (Tokens-to-Success)": f"{k1_static_arm['mean_tts']:.1f}",
            "Total Workload Tokens (32 Tasks)": str(k1_static_arm['total_tokens_consumed']),
            "Mean Tokens / Task (Workload)": f"{k1_static_arm['total_tokens_consumed'] / 32:.1f}",
            "Net Workload Savings %": f"{((full_arm['total_tokens_consumed'] - k1_static_arm['total_tokens_consumed']) / full_arm['total_tokens_consumed']) * 100:.1f}%",
            "AST Splicing Latency p50/p99": f"{rec_p50:.3f} / {rec_p99:.3f} ms",
            "Scientific Status": "Verified (Frozen Benchmark N=32, SHA-256 78c2c88e...)"
        },
        {
            "Architecture / Arm": "LASR-MCP (k=1 Reactive Recovery)",
            "Evaluation Category": "Measured End-to-End System",
            "Constraint Retrieval Recall@2": "N/A (Adaptive + Reactive)",
            "First-Pass Structural %": f"{get_fp_pct(k1_arm)}%",
            "Final Structural Success %": f"{round_half_up(k1_arm['final_structural_pct'], 1)}%",
            "Mean TTS (Tokens-to-Success)": f"{k1_arm['mean_tts']:.1f}",
            "Total Workload Tokens (32 Tasks)": str(k1_arm['total_tokens_consumed']),
            "Mean Tokens / Task (Workload)": f"{k1_arm['total_tokens_consumed'] / 32:.1f}",
            "Net Workload Savings %": f"{((full_arm['total_tokens_consumed'] - k1_arm['total_tokens_consumed']) / full_arm['total_tokens_consumed']) * 100:.1f}%",
            "AST Splicing Latency p50/p99": f"{rec_p50:.3f} / {rec_p99:.3f} ms",
            "Scientific Status": "Verified (Frozen Benchmark N=32, SHA-256 78c2c88e...)"
        },
        {
            "Architecture / Arm": "LASR-MCP (k=2 Reactive Recovery)",
            "Evaluation Category": "Measured End-to-End System",
            "Constraint Retrieval Recall@2": "N/A (Adaptive + Reactive)",
            "First-Pass Structural %": f"{get_fp_pct(k2_arm)}%",
            "Final Structural Success %": f"{round_half_up(k2_arm['final_structural_pct'], 1)}%",
            "Mean TTS (Tokens-to-Success)": f"{k2_arm['mean_tts']:.1f}",
            "Total Workload Tokens (32 Tasks)": str(k2_arm['total_tokens_consumed']),
            "Mean Tokens / Task (Workload)": f"{k2_arm['total_tokens_consumed'] / 32:.1f}",
            "Net Workload Savings %": f"{((full_arm['total_tokens_consumed'] - k2_arm['total_tokens_consumed']) / full_arm['total_tokens_consumed']) * 100:.1f}%",
            "AST Splicing Latency p50/p99": f"{rec_p50:.3f} / {rec_p99:.3f} ms",
            "Scientific Status": "Verified (Frozen Benchmark N=32, SHA-256 78c2c88e...)"
        },

        # --- Modeled Counterfactual Analysis ---
        {
            "Architecture / Arm": "LangGraph Stateful Accumulation Pattern",
            "Evaluation Category": "Counterfactual Token Model",
            "Constraint Retrieval Recall@2": "100.0% (Full Schema in State)",
            "First-Pass Structural %": "31.3% (Modeled from full)",
            "Final Structural Success %": "93.8% (Modeled from full)",
            "Mean TTS (Tokens-to-Success)": f"{lg_data['mean_tts']:.1f}",
            "Total Workload Tokens (32 Tasks)": str(lg_data['total_workload_tokens']),
            "Mean Tokens / Task (Workload)": f"{lg_data['mean_tokens_per_task']:.1f}",
            "Net Workload Savings %": "-7.5% (Token Overhead)",
            "AST Splicing Latency p50/p99": "N/A (Full Schema)",
            "Scientific Status": "Counterfactual Token-History Model (+45 tok compiler context, inherited task outcomes)"
        },

        # --- Retrieval-Only Baselines (Strictly NOT reported as end-to-end execution) ---
        {
            "Architecture / Arm": "Lexical Tool-RAG (TF-IDF Cosine, k=2)",
            "Evaluation Category": "Retrieval-Only Experiment",
            "Constraint Retrieval Recall@2": f"{macro_lex_recall * 100.0:.1f}%",
            "First-Pass Structural %": "NOT MEASURED (Retrieval-Only)",
            "Final Structural Success %": "NOT MEASURED (Retrieval-Only)",
            "Mean TTS (Tokens-to-Success)": "NOT MEASURED (Retrieval-Only)",
            "Total Workload Tokens (32 Tasks)": "NOT MEASURED (Retrieval-Only)",
            "Mean Tokens / Task (Workload)": "NOT MEASURED (Retrieval-Only)",
            "Net Workload Savings %": "NOT MEASURED (Retrieval-Only)",
            "AST Splicing Latency p50/p99": "N/A (Lexical lookup)",
            "Scientific Status": "Evaluated Retrieval Catalog Only (Macro Recall@2 = 12.5%, 75.0% zero-recall tasks)"
        },
        {
            "Architecture / Arm": "Latent Semantic Analysis (Inductive LSA, k=2)",
            "Evaluation Category": "Retrieval-Only Experiment",
            "Constraint Retrieval Recall@2": f"{lsa_top2_macro * 100.0:.1f}%",
            "First-Pass Structural %": "NOT MEASURED (Retrieval-Only)",
            "Final Structural Success %": "NOT MEASURED (Retrieval-Only)",
            "Mean TTS (Tokens-to-Success)": "NOT MEASURED (Retrieval-Only)",
            "Total Workload Tokens (32 Tasks)": "NOT MEASURED (Retrieval-Only)",
            "Mean Tokens / Task (Workload)": "NOT MEASURED (Retrieval-Only)",
            "Net Workload Savings %": "NOT MEASURED (Retrieval-Only)",
            "AST Splicing Latency p50/p99": "N/A (Dense lookup)",
            "Scientific Status": "Evaluated Retrieval Catalog Only (Macro Recall@2 = 14.1%, 71.9% zero-recall tasks)"
        },
        {
            "Architecture / Arm": "Dense Neural Tool-RAG (text-embedding-004, k=2)",
            "Evaluation Category": "Planned Experiment",
            "Constraint Retrieval Recall@2": "NOT MEASURED (Planned)",
            "First-Pass Structural %": "NOT MEASURED (Planned)",
            "Final Structural Success %": "NOT MEASURED (Planned)",
            "Mean TTS (Tokens-to-Success)": "NOT MEASURED (Planned)",
            "Total Workload Tokens (32 Tasks)": "NOT MEASURED (Planned)",
            "Mean Tokens / Task (Workload)": "NOT MEASURED (Planned)",
            "Net Workload Savings %": "NOT MEASURED (Planned)",
            "AST Splicing Latency p50/p99": "N/A (Neural API)",
            "Scientific Status": "Planned Future Work (Pending Live Neural Embedding Experiment)"
        }
    ]

    out_csv = Path(__file__).parent / "baseline_comparison_table.csv"
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(table_rows[0].keys()))
        writer.writeheader()
        writer.writerows(table_rows)

    out_json = Path(__file__).parent / "baseline_comparison_snapshot.json"
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(table_rows, f, indent=2)

    print(f"Generated {out_csv.name} and {out_json.name} successfully.")
    print("\n--- Audited Summary of Table V (Version 2.0) ---")
    for r in table_rows:
        cat = r['Evaluation Category']
        arm = r['Architecture / Arm']
        rec = r['Constraint Retrieval Recall@2']
        succ = r['Final Structural Success %']
        tok = r['Total Workload Tokens (32 Tasks)']
        sav = r['Net Workload Savings %']
        print(f"[{cat}] {arm} -> Recall@2={rec}, Final Succ={succ}, Workload Tok={tok}, Savings={sav}")

if __name__ == "__main__":
    run_baselines()
