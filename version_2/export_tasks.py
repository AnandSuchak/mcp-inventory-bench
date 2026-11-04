#!/usr/bin/env python3
"""Export the 32 test evaluation benchmark tasks for trace audit and baseline evaluation.
Saves to version_2/benchmark_tasks_n32.json with JSON Pointer schema IDs.
"""
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE))

from trace.paraphraser import generate_pilot2_blinded_tasks

DOT_TO_POINTER = {
    "warehouse_code.enum": "/properties/warehouse_code/enum",
    "authorized_by.pattern": "/properties/authorized_by/pattern",
    "supplier_id.pattern": "/properties/supplier_id/pattern",
    "order_priority.enum": "/properties/order_priority/enum",
    "total_budget_limit.maximum": "/properties/total_budget_limit/maximum",
    "items.quantity.minimum": "/properties/items/items/properties/quantity/minimum",
}

def export_tasks():
    all_tasks = generate_pilot2_blinded_tasks()
    test_tasks = [t for t in all_tasks if t.split == "test"]
    
    records = []
    for t in test_tasks:
        pointer_targets = [DOT_TO_POINTER.get(c, c) for c in t.target_constraints]
        records.append({
            "task_id": t.task_id,
            "semantic_cluster": t.semantic_cluster,
            "intent_family": t.intent_family,
            "user_intent": t.user_intent,
            "query": t.user_intent,
            "target_constraints": pointer_targets,
            "target_constraints_dot": t.target_constraints,
            "arm": "lasr_k1_reactive"
        })
    
    out_file = Path(__file__).parent / "benchmark_tasks_n32.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
    print(f"Exported {len(records)} test tasks to {out_file}")

if __name__ == "__main__":
    export_tasks()
