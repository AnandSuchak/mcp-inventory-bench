"""
Run a balanced 16-task sample of Experiment 1 to evaluate H1
Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from trace.paraphraser import generate_pilot2_blinded_tasks
from trace.llm_client import LiveLLMClient
from trace.runner_pilot2 import Pilot2ExperimentRunner
from trace.analyze_pilot2 import analyze_experiment1_matrix

output_file = Path("datasets/dataset_b_pilot/exp1_traces.jsonl")
output_file.parent.mkdir(parents=True, exist_ok=True)

all_tasks = generate_pilot2_blinded_tasks()

# Select a balanced 16-task sample (4 tasks per cluster, 2 train, 2 test)
selected = []
counts = {}
for t in all_tasks:
    c = t.semantic_cluster
    if counts.get(c, 0) < 4:
        selected.append(t)
        counts[c] = counts.get(c, 0) + 1

print(f"[*] Selected {len(selected)} balanced blinded tasks across 4 semantic clusters:")
for c, cnt in counts.items():
    print(f"    - {c}: {cnt} tasks")

client = LiveLLMClient(provider="gemini", model="gemini-3.5-flash-lite")
runner = Pilot2ExperimentRunner(llm_client=client, max_attempts=3, cache_enabled=True)

traces = []
accounts = []
for idx, task in enumerate(selected, 1):
    print(f"[{idx}/{len(selected)}] Running blinded task {task.task_id} ({task.semantic_cluster[:16]})...", end="", flush=True)
    trace, account = runner.run_task(task, schema_level="1C")
    traces.append(trace)
    accounts.append(account)
    print(f" Outcome: {trace.final_outcome} ({len(trace.attempts)} attempts, {account.total_cumulative_tokens} tokens)")

with open(output_file, "w", encoding="utf-8") as f:
    for t in traces:
        f.write(json.dumps(t.to_dict()) + "\n")

print(f"\n[+] Traces successfully saved to {output_file}")
analyze_experiment1_matrix(output_file)
