"""
Unit tests for Token Accounting & Budget Auditor
Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import pytest
from trace.token_accounting import TaskTokenAccount, compute_aggregate_token_metrics

class TestTokenAccounting:
    def test_single_attempt_success_accounting(self):
        acc = TaskTokenAccount(
            task_id="TEST-001",
            semantic_cluster="routine_regional_replenish",
            schema_level="1C"
        )
        # Attempt 1 succeeds
        att1 = acc.add_attempt(
            attempt_number=1,
            base_prompt_tokens=800,
            base_schema_tokens=180,
            new_delta_tokens=0,
            total_schema_tokens=180,
            completion_tokens=60
        )
        assert att1.attempt_total_tokens == 1040
        assert att1.cumulative_tts == 1040

        acc.finalize("SUCCESS", oracle_tokens=160)
        assert acc.tokens_to_success == 1040
        assert acc.prediction_overexposure_tokens == 20
        assert acc.oracle_gap_tokens == 20

    def test_multi_attempt_cumulative_tts(self):
        acc = TaskTokenAccount(
            task_id="TEST-002",
            semantic_cluster="expedited_emergency_order",
            schema_level="1A"
        )
        # Attempt 1 fails
        acc.add_attempt(
            attempt_number=1,
            base_prompt_tokens=800,
            base_schema_tokens=120,
            new_delta_tokens=0,
            total_schema_tokens=120,
            completion_tokens=50
        ) # Total = 970, Cumulative = 970

        # Attempt 2 succeeds after receiving a 15-token delta slice
        acc.add_attempt(
            attempt_number=2,
            base_prompt_tokens=850, # Prompt + error message feedback
            base_schema_tokens=120,
            new_delta_tokens=15,
            total_schema_tokens=135,
            completion_tokens=45
        ) # Total = 850 + 135 + 45 = 1030, Cumulative = 970 + 1030 = 2000

        acc.finalize("SUCCESS", oracle_tokens=135)
        assert acc.tokens_to_success == 2000
        assert acc.final_schema_tokens_exposed == 135
        assert acc.prediction_overexposure_tokens == 0

    def test_aggregate_token_metrics_calculation(self):
        acc1 = TaskTokenAccount(task_id="T1", semantic_cluster="C1", schema_level="1B")
        acc1.add_attempt(1, 500, 100, 0, 100, 50)
        acc1.finalize("SUCCESS", oracle_tokens=80)

        acc2 = TaskTokenAccount(task_id="T2", semantic_cluster="C1", schema_level="1B")
        acc2.add_attempt(1, 500, 100, 0, 100, 50)
        acc2.finalize("FAIL", oracle_tokens=80)

        metrics = compute_aggregate_token_metrics([acc1, acc2])
        assert metrics["total_tasks"] == 2
        assert metrics["success_rate_pct"] == 50.0
        assert metrics["mean_tts"] == 650.0
        assert metrics["mean_schema_tokens_exposed"] == 100.0
        assert metrics["mean_prediction_overexposure"] == 20.0
