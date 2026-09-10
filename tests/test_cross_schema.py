"""
Unit tests for Cross-Schema Robustness Evaluation and General In-Tree Recomposition.
"""

import json
import hashlib
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator

from trace.cross_schema_benchmark import (
    FULL_PURCHASE_ORDER_SCHEMA,
    FULL_INVENTORY_ADJUSTMENT_SCHEMA,
    FULL_SHIPMENT_SCHEMA,
    FULL_REFUND_SCHEMA,
    INVARIANT_INVENTORY_ADJUSTMENT_SCHEMA,
    INVARIANT_SHIPMENT_SCHEMA,
    INVARIANT_REFUND_SCHEMA,
    ADJUSTMENT_SPECS,
    SHIPMENT_SPECS,
    REFUND_SPECS,
    generic_recompose_schema,
    validate_submission,
    evaluate_cross_schema_semantic,
    generate_cross_schema_tasks,
    WORKSPACE
)

def test_all_schemas_are_valid_draft202012():
    """Verify all 4 enterprise schemas are valid JSON Schema Draft 2020-12 specifications."""
    schemas = [
        FULL_PURCHASE_ORDER_SCHEMA,
        FULL_INVENTORY_ADJUSTMENT_SCHEMA,
        FULL_SHIPMENT_SCHEMA,
        FULL_REFUND_SCHEMA,
        INVARIANT_INVENTORY_ADJUSTMENT_SCHEMA,
        INVARIANT_SHIPMENT_SCHEMA,
        INVARIANT_REFUND_SCHEMA
    ]
    for s in schemas:
        Draft202012Validator.check_schema(s)

def test_generic_in_tree_recomposition():
    """Verify generic AST recomposition injects missing constraints directly into schema."""
    # Test inventory adjustment enum injection
    base = INVARIANT_INVENTORY_ADJUSTMENT_SCHEMA
    assert "enum" not in base["properties"]["adjustment_type"]
    
    recomposed = generic_recompose_schema(
        base,
        ["adjustment_type.enum"],
        FULL_INVENTORY_ADJUSTMENT_SCHEMA,
        ADJUSTMENT_SPECS
    )
    assert "enum" in recomposed["properties"]["adjustment_type"]
    assert "CYCLE_COUNT" in recomposed["properties"]["adjustment_type"]["enum"]

def test_multi_error_path_extraction():
    """Verify validator extracts precise JSON pointer paths and RFC keywords."""
    invalid_sub = {
        "adjustment_id": "ADJ-1029384",
        "warehouse_code": "INVALID_WH",
        "sku": "SKU-10001",
        "quantity_delta": 50,
        "adjustment_type": "INVALID_TYPE",
        "reason_code": "INVALID_REASON",
        "supervisor_id": "SUPV-A9912",
        "authorized_by": "ops.lead@enterprise.mock"
    }
    is_valid, msgs, path_keywords = validate_submission(FULL_INVENTORY_ADJUSTMENT_SCHEMA, invalid_sub)
    assert not is_valid
    assert len(msgs) >= 3
    
    extracted_paths = [pk[0] for pk in path_keywords]
    assert "warehouse_code" in extracted_paths
    assert "adjustment_type" in extracted_paths
    assert "reason_code" in extracted_paths

def test_cross_schema_manifest_integrity():
    """Verify cross-schema benchmark results match cryptographic SHA-256 manifest."""
    results_file = WORKSPACE / "datasets" / "cross_schema_validation" / "cross_schema_results.json"
    manifest_file = WORKSPACE / "datasets" / "cross_schema_validation" / "MANIFEST.sha256"
    
    assert results_file.exists(), "cross_schema_results.json must exist"
    assert manifest_file.exists(), "MANIFEST.sha256 must exist"
    
    actual_hash = hashlib.sha256(results_file.read_bytes()).hexdigest()
    manifest_content = manifest_file.read_text(encoding="utf-8").strip()
    expected_hash = manifest_content.split()[0]
    
    assert actual_hash == expected_hash, f"Hash mismatch: actual {actual_hash} != expected {expected_hash}"

def test_cross_schema_tasks_structure():
    """Verify 32 blinded cross-schema tasks (8 per schema, 4 explicit, 4 ambiguous)."""
    tasks = generate_cross_schema_tasks()
    assert len(tasks) == 4
    for s_name, task_list in tasks.items():
        assert len(task_list) == 8
        explicit_tasks = [t for t in task_list if t["type"] == "explicit"]
        ambiguous_tasks = [t for t in task_list if t["type"] == "ambiguous"]
        assert len(explicit_tasks) == 4
        assert len(ambiguous_tasks) == 4
