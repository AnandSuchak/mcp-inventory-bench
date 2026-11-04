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
        # Attempt 1 succeeds: provider prompt = 800, candidate = 60
        # Serialized schema is already included in prompt text;
        # recorded P+C is 800 + 60 = 860, not 800 + 180 + 60.
        att1 = acc.add_attempt(
            attempt_number=1,
            base_prompt_tokens=800,
            base_schema_tokens=180,
            new_delta_tokens=0,
            total_schema_tokens=180,
            completion_tokens=60
        )
        assert att1.attempt_total_tokens == 860
        assert att1.cumulative_tts == 860

        acc.finalize("SUCCESS", oracle_tokens=160)
        assert acc.tokens_to_success == 860
        assert acc.prediction_overexposure_tokens == 20
        assert acc.oracle_gap_tokens == 0

    def test_multi_attempt_cumulative_tts(self):
        acc = TaskTokenAccount(
            task_id="TEST-002",
            semantic_cluster="expedited_emergency_order",
            schema_level="1A"
        )
        # Attempt 1 fails: prompt = 800, candidate = 50 -> 850 tokens
        acc.add_attempt(
            attempt_number=1,
            base_prompt_tokens=800,
            base_schema_tokens=120,
            new_delta_tokens=0,
            total_schema_tokens=120,
            completion_tokens=50
        ) # Total = 850, Cumulative = 850

        # Attempt 2 succeeds after receiving feedback:
        # prompt = 850, candidate = 45 -> 895 tokens
        # Cumulative = 850 + 895 = 1745 tokens (no double counting of schema tokens)
        acc.add_attempt(
            attempt_number=2,
            base_prompt_tokens=850,
            base_schema_tokens=120,
            new_delta_tokens=15,
            total_schema_tokens=135,
            completion_tokens=45
        )

        acc.finalize("SUCCESS", oracle_tokens=135)
        assert acc.tokens_to_success == 1745
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
        assert metrics["mean_tts_prompt_candidate"] == 550.0
        assert metrics["total_recorded_prompt_candidate_tokens"] == 1100
        assert metrics["mean_schema_tokens_exposed"] == 100.0
        assert metrics["mean_prediction_overexposure"] == 20.0
