"""
Unit Tests for Semantic Task Correctness Evaluator
Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import pytest
from trace.paraphraser import BlindedTask
from trace.task_evaluator import evaluate_task_correctness, extract_requested_quantity, extract_requested_destination

def test_extract_quantity():
    assert extract_requested_quantity("Please order 50 units for eastern depot") == 50
    assert extract_requested_quantity("Refill inventory with sixty units of parts") == 60
    assert extract_requested_quantity("Restock thirty assemblies") == 30

def test_extract_destination():
    assert extract_requested_destination("route forty units to our east coast facility") == "WH-US-EAST"
    assert extract_requested_destination("deliver thirty parts to west regional hub") == "WH-US-WEST"

def test_evaluate_task_correctness_valid():
    task = BlindedTask(
        task_id="TEST-001",
        semantic_cluster="routine_regional_replenish",
        intent_family="family_c",
        user_intent="Restock our east depot with 50 units using our standard vendor agreement.",
        split="test",
        target_constraints=[]
    )
    args = {
        "supplier_id": "SUP-ACME1234-US",
        "warehouse_code": "WH-US-EAST",
        "items": [{"sku": "SKU-10001", "quantity": 50, "unit_cost": 12.5}],
        "authorized_by": "john.smith@enterprise.mock",
        "order_priority": "STANDARD"
    }
    is_correct, failures = evaluate_task_correctness(task, args)
    assert is_correct is True
    assert len(failures) == 0

def test_evaluate_task_correctness_wrong_destination():
    task = BlindedTask(
        task_id="TEST-002",
        semantic_cluster="routine_regional_replenish",
        intent_family="family_c",
        user_intent="Restock our east depot with 50 units using our standard vendor agreement.",
        split="test",
        target_constraints=[]
    )
    args = {
        "supplier_id": "SUP-ACME1234-US",
        "warehouse_code": "WH-US-WEST", # Mismatch!
        "items": [{"sku": "SKU-10001", "quantity": 50, "unit_cost": 12.5}],
        "authorized_by": "john.smith@enterprise.mock",
        "order_priority": "STANDARD"
    }
    is_correct, failures = evaluate_task_correctness(task, args)
    assert is_correct is False
    assert any("Destination mismatch" in f for f in failures)
