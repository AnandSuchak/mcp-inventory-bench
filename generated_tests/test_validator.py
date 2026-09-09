"""
Unit Tests for SchemaValidator (JSON Schema Draft 2020-12 Protocol)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Target: trace.validator.SchemaValidator
Validates strict Draft 2020-12 argument validation, error structures, and JSON pointers.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trace.validator import SchemaValidator
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA

class TestSchemaValidator(unittest.TestCase):
    """Test suite for strict Draft 2020-12 argument validation."""

    def setUp(self):
        self.validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
        self.valid_payload = {
            "supplier_id": "SUP-TEXAS-SEMI",
            "warehouse_code": "WH-US-EAST",
            "order_priority": "STANDARD",
            "total_budget_limit": 5000.0,
            "items": [
                {
                    "sku": "SKU-10042",
                    "quantity": 50,
                    "unit_cost": 25.0
                }
            ],
            "authorized_by": "anand.suchak@enterprise.mock"
        }

    def test_valid_payload_passes(self):
        """Verify compliant arguments return is_valid=True with zero errors."""
        is_valid, errors = self.validator.validate(self.valid_payload)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_regex_pattern_violation(self):
        """Verify pattern violation returns structured error with path and keyword."""
        bad_payload = dict(self.valid_payload)
        bad_payload["supplier_id"] = "invalid-vendor-123"

        is_valid, errors = self.validator.validate(bad_payload)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
        
        pattern_err = next(e for e in errors if e.keyword == "pattern")
        self.assertEqual(pattern_err.path, "/supplier_id")
        self.assertEqual(pattern_err.failed_value, "invalid-vendor-123")
        self.assertIn("pattern", pattern_err.schema_path)

    def test_enum_violation(self):
        """Verify enum violation returns structured error."""
        bad_payload = dict(self.valid_payload)
        bad_payload["warehouse_code"] = "UNKNOWN-WH-DOCK"

        is_valid, errors = self.validator.validate(bad_payload)
        self.assertFalse(is_valid)
        
        enum_err = next(e for e in errors if e.keyword == "enum")
        self.assertEqual(enum_err.path, "/warehouse_code")
        self.assertEqual(enum_err.failed_value, "UNKNOWN-WH-DOCK")

    def test_numeric_minimum_violation(self):
        """Verify numeric minimum (MOQ) violation is detected inside array items."""
        bad_payload = dict(self.valid_payload)
        bad_payload["items"] = [
            {"sku": "SKU-10042", "quantity": 2, "unit_cost": 25.0} # Below MOQ 10
        ]

        is_valid, errors = self.validator.validate(bad_payload)
        self.assertFalse(is_valid)

        min_err = next(e for e in errors if e.keyword == "minimum")
        self.assertEqual(min_err.path, "/items/0/quantity")
        self.assertEqual(min_err.failed_value, 2)

    def test_missing_required_property(self):
        """Verify missing required top-level property returns 'required' error."""
        bad_payload = dict(self.valid_payload)
        del bad_payload["authorized_by"]

        is_valid, errors = self.validator.validate(bad_payload)
        self.assertFalse(is_valid)

        req_err = next(e for e in errors if e.keyword == "required")
        self.assertIn("authorized_by", req_err.message)

if __name__ == "__main__":
    unittest.main()
