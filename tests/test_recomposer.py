"""
Unit Tests for Deterministic Schema Recomposer
Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import pytest
import copy
from trace.recomposer import recompose_schema, CONSTRAINT_INLINE_SPECS
from trace.slicer import create_schema_level_1c
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA

def test_recompose_single_top_level_constraint():
    base = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)
    assert "enum" not in base["properties"]["warehouse_code"]

    recomposed = recompose_schema(base, ["warehouse_code.enum"], FULL_PURCHASE_ORDER_SCHEMA)
    assert "enum" in recomposed["properties"]["warehouse_code"]
    assert recomposed["properties"]["warehouse_code"]["enum"] == FULL_PURCHASE_ORDER_SCHEMA["properties"]["warehouse_code"]["enum"]
    # No auxiliary 'constraints' key
    assert "constraints" not in recomposed

def test_recompose_pattern_constraint():
    base = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)
    assert "pattern" not in base["properties"]["authorized_by"]

    recomposed = recompose_schema(base, ["authorized_by.pattern"], FULL_PURCHASE_ORDER_SCHEMA)
    assert "pattern" in recomposed["properties"]["authorized_by"]
    assert recomposed["properties"]["authorized_by"]["pattern"] == FULL_PURCHASE_ORDER_SCHEMA["properties"]["authorized_by"]["pattern"]

def test_recompose_nested_item_bundle():
    base = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)
    bundle = ["items.required", "items.sku.pattern", "items.quantity.minimum"]

    recomposed = recompose_schema(base, bundle, FULL_PURCHASE_ORDER_SCHEMA)

    item_node = recomposed["properties"]["items"]["items"]
    assert "properties" in item_node
    assert "sku" in item_node["properties"]
    assert "quantity" in item_node["properties"]
    assert "unit_cost" in item_node["properties"]
    
    assert item_node["properties"]["sku"]["pattern"] == "^SKU-[0-9]{5}$"
    assert item_node["properties"]["quantity"]["minimum"] == 10
    assert item_node["required"] == ["sku", "quantity", "unit_cost"]

def test_recompose_multiple_heterogeneous_constraints():
    base = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)
    bundle = [
        "warehouse_code.enum",
        "authorized_by.pattern",
        "items.minItems",
        "supplier_id.pattern"
    ]

    recomposed = recompose_schema(base, bundle, FULL_PURCHASE_ORDER_SCHEMA)

    assert "enum" in recomposed["properties"]["warehouse_code"]
    assert "pattern" in recomposed["properties"]["authorized_by"]
    assert recomposed["properties"]["items"]["minItems"] == 1
    assert "pattern" in recomposed["properties"]["supplier_id"]
    assert "constraints" not in recomposed
