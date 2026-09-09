"""
Run Experiment 2: Schema Budget Curve (Levels 1A, 1B, 1C, 1D, and Full)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Evaluates identical task sets across 5 schema exposure budgets:
- Level 1A: Names + Types
- Level 1B: Names + Types + Neutral Descriptions
- Level 1C: Names + Types + Requiredness
- Level 1D: Names + Types + Descriptions + Requiredness
- Full: Complete Draft 2020-12 Schema

Measures First-Pass Success, Total Tokens-to-Success (TTS), and Schema Tokens Exposed.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from trace.paraphraser import generate_pilot2_blinded_tasks
from trace.llm_client import LiveLLMClient
from trace.runner_pilot2 import Pilot2ExperimentRunner
from trace.token_accounting import compute_aggregate_token_metrics

output_dir = Path("datasets/dataset_b_pilot/exp2_budget_curve")
output_dir.mkdir(parents=True, exist_ok=True)

# Select 4 representative tasks (1 per semantic cluster)
all_tasks = generate_pilot2_blinded_tasks()
eval_tasks = [
    next(t for t in all_tasks if t.semantic_cluster == "routine_regional_replenish"),
    next(t for t in all_tasks if t.semantic_cluster == "expedited_emergency_order"),
    next(t for t in all_tasks if t.semantic_cluster == "specialized_bulk_procurement"),
    next(t for t in all_tasks if t.semantic_cluster == "multi_item_depot_rebalance"),
]

client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite")
runner = Pilot2ExperimentRunner(llm_client=client, max_attempts=2, cache_enabled=True)

budget_levels = ["1A", "1B", "1C", "1D", "full"]
summary_results = {}

print("=" * 84)
print("[*] EXPERIMENT 2: SCHEMA BUDGET CURVE EVALUATION")
print("=" * 84)

for level in budget_levels:
    print(f"\n[+] Testing Schema Budget Level: {level}")
    level_accounts = []
    level_traces = []

    for task in eval_tasks:
        print(f"    - Task {task.task_id} ({task.semantic_cluster[:16]})...", end="", flush=True)
        trace, account = runner.run_task(task, schema_level=level)
        level_traces.append(trace)
        level_accounts.append(account)
        first_pass = "PASS" if trace.attempts[0].validation_status == "SUCCESS" else "FAIL"
        print(f" Att 1: {first_pass} | Final: {trace.final_outcome} | Cumulative Tokens: {account.total_cumulative_tokens}")

    metrics = compute_aggregate_token_metrics(level_accounts)
    first_pass_successes = sum(1 for t in level_traces if t.attempts[0].validation_status == "SUCCESS")
    metrics["first_pass_success_pct"] = round((first_pass_successes / len(eval_tasks)) * 100.0, 2)
    summary_results[level] = metrics

    # Save traces for this level
    with open(output_dir / f"budget_{level}_traces.jsonl", "w", encoding="utf-8") as f:
        for t in level_traces:
            f.write(json.dumps(t.to_dict()) + "\n")

print("\n" + "=" * 84)
print(f"{'Budget Level':<15}{'Init Schema Tok':<18}{'1st-Pass Success':<18}{'Final Success':<16}{'Mean TTS':<12}")
print("-" * 84)
for lvl, m in summary_results.items():
    print(f"{lvl:<15}{m['mean_schema_tokens_exposed']:<18.1f}{m['first_pass_success_pct']:<18.1f}%{m['success_rate_pct']:<16.1f}%{m['mean_tts']:<12.1f}")
print("=" * 84)
