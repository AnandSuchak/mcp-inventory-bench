"""
Unit Tests for Trace Data Models (Dataset A Records)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Target: trace.models.Trace, Attempt, SchemaExposureRecord, ValidationErrorRecord
Validates JSON serialization round-tripping, ledger calculations, and schema version metadata.
"""

import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trace.models import Trace, Attempt, SchemaExposureRecord, ValidationErrorRecord

class TestTraceModels(unittest.TestCase):
    """Test suite for fine-grained trace data models."""

    def test_trace_serialization_round_trip(self):
        """Verify complete serialization and deserialization of a Trace record."""
        trace = Trace(
            task_id="TASK-001",
            category="Regex-constrained fields",
            user_intent="Create PO with custom vendor ID",
            tool_name="create_purchase_order",
            model="gpt-4o-mini",
            model_version="2026-Q1"
        )
        # Add ledger record
        trace.schema_exposure_ledger.append(SchemaExposureRecord(
            fragment="level_1_base",
            tokens=120,
            attempt=1,
            reason="INITIAL_LEVEL_1"
        ))
        trace.schema_exposure_ledger.append(SchemaExposureRecord(
            fragment="supplier_id.pattern",
            tokens=18,
            attempt=2,
            reason="CONSTRAINT_VIOLATION_PATTERN"
        ))
        trace.total_schema_tokens_exposed = 138

        # Add Attempt 1 (Fail)
        trace.attempts.append(Attempt(
            attempt_number=1,
            schema_fragments_exposed=["level_1_base"],
            schema_token_count=120,
            model_response='{"supplier_id": "bad-id"}',
            arguments={"supplier_id": "bad-id"},
            validation_status="FAIL",
            validation_errors=[
                ValidationErrorRecord(
                    keyword="pattern",
                    path="/supplier_id",
                    message="does not match pattern",
                    schema_path="properties/supplier_id/pattern",
                    failed_value="bad-id"
                )
            ],
            latency_ms=1.5
        ))

        # Add Attempt 2 (Success)
        trace.attempts.append(Attempt(
            attempt_number=2,
            schema_fragments_exposed=["level_1_base", "supplier_id.pattern"],
            schema_token_count=138,
            model_response='{"supplier_id": "SUP-TEXAS-SEMI"}',
            arguments={"supplier_id": "SUP-TEXAS-SEMI"},
            validation_status="SUCCESS",
            validation_errors=[],
            latency_ms=1.2
        ))
        trace.final_outcome = "SUCCESS"
        trace.tokens_to_success = 138

        # Serialize to dict and back
        raw_dict = trace.to_dict()
        reconstructed = Trace.from_dict(raw_dict)

        self.assertEqual(reconstructed.task_id, "TASK-001")
        self.assertEqual(reconstructed.final_outcome, "SUCCESS")
        self.assertEqual(reconstructed.tokens_to_success, 138)
        self.assertEqual(len(reconstructed.attempts), 2)
        self.assertEqual(reconstructed.attempts[0].validation_status, "FAIL")
        self.assertEqual(reconstructed.attempts[1].validation_status, "SUCCESS")
        self.assertEqual(len(reconstructed.schema_exposure_ledger), 2)
        self.assertEqual(reconstructed.schema_exposure_ledger[1].fragment, "supplier_id.pattern")

    def test_schema_version_mcp_spec(self):
        """Verify trace records standard MCP 2026-07-28 Draft 2020-12 specification."""
        trace = Trace()
        self.assertIn("2026-07-28", trace.schema_version)
        self.assertIn("draft-2020-12", trace.schema_version)

if __name__ == "__main__":
    unittest.main()
