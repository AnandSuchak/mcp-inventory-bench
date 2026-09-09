"""
Unit Tests for Schema Slicer (Deterministic Constraint Slicing)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Target: trace.slicer.slice_constraint, format_fragment_identifier
Validates minimal constraint extraction, array nesting traversal, and determinism.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trace.slicer import slice_constraint, format_fragment_identifier, estimate_tokens
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA

class TestSchemaSlicer(unittest.TestCase):
    """Test suite for deterministic schema constraint slicer."""

    def setUp(self):
        self.schema = FULL_PURCHASE_ORDER_SCHEMA

    def test_slice_root_pattern_constraint(self):
        """Verify slicing /supplier_id + pattern returns only supplier_id pattern constraint."""
        delta = slice_constraint(self.schema, "/supplier_id", "pattern")
        self.assertIn("supplier_id", delta)
        self.assertIn("pattern", delta["supplier_id"])
        self.assertEqual(delta["supplier_id"]["pattern"], "^SUP-[A-Z0-9]{4,12}-[A-Z0-9]{3,6}$")
        # Ensure no extraneous properties leaked into delta
        self.assertNotIn("warehouse_code", delta)
        self.assertNotIn("items", delta)

    def test_slice_root_enum_constraint(self):
        """Verify slicing /warehouse_code + enum extracts only warehouse enum values."""
        delta = slice_constraint(self.schema, "/warehouse_code", "enum")
        self.assertIn("warehouse_code", delta)
        self.assertIn("enum", delta["warehouse_code"])
        self.assertIn("WH-US-EAST", delta["warehouse_code"]["enum"])
        self.assertEqual(len(delta["warehouse_code"]["enum"]), 5)

    def test_slice_nested_array_constraint(self):
        """Verify slicing /items/0/sku + pattern extracts nested array items schema."""
        delta = slice_constraint(self.schema, "/items/0/sku", "pattern")
        self.assertIn("items", delta)
        self.assertEqual(delta["items"]["type"], "array")
        self.assertIn("items", delta["items"])
        self.assertIn("sku", delta["items"]["items"])
        self.assertEqual(delta["items"]["items"]["sku"]["pattern"], "^SKU-[0-9]{5}$")

    def test_slice_nested_numeric_minimum(self):
        """Verify slicing /items/0/quantity + minimum extracts minimum bound."""
        delta = slice_constraint(self.schema, "/items/0/quantity", "minimum")
        self.assertIn("items", delta)
        self.assertEqual(delta["items"]["items"]["quantity"]["minimum"], 10)

    def test_slice_required_constraint(self):
        """Verify slicing required property returns required list."""
        delta = slice_constraint(self.schema, "/", "required")
        self.assertIn("required", delta)
        self.assertIn("supplier_id", delta["required"])
        self.assertIn("authorized_by", delta["required"])

    def test_format_fragment_identifier(self):
        """Verify human-readable exposure identifiers are formatted cleanly."""
        f1 = format_fragment_identifier("/supplier_id", "pattern")
        self.assertEqual(f1, "supplier_id.pattern")

        f2 = format_fragment_identifier("/items/0/sku", "pattern")
        self.assertEqual(f2, "items.sku.pattern")

        f3 = format_fragment_identifier("/items/3/quantity", "minimum")
        self.assertEqual(f3, "items.quantity.minimum")

    def test_slicer_determinism_and_purity(self):
        """Verify slicer produces bit-for-bit identical output on repeated executions."""
        delta1 = slice_constraint(self.schema, "/supplier_id", "pattern")
        delta2 = slice_constraint(self.schema, "/supplier_id", "pattern")
        self.assertEqual(delta1, delta2)

        tok1 = estimate_tokens(delta1)
        tok2 = estimate_tokens(delta2)
        self.assertEqual(tok1, tok2)
        self.assertGreater(tok1, 0)
        self.assertLess(tok1, 60) # Minimal isolated token footprint

if __name__ == "__main__":
    unittest.main()
