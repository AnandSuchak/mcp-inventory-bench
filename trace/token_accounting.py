"""
Comprehensive Token Accounting & Budget Auditor
Project: mcp-inventory-bench
Author: Anand S. Suchak

Implements fine-grained token accounting for multi-attempt MCP tool execution.
Strictly separates:
1. Experimental Task Execution Tokens (base prompt, schema baseline, schema deltas, completions, cumulative TTS).
2. Infrastructure Tokens (paraphrase generation, benchmark debugging, calibration runs).

Calculates Core Research Metrics:
- Tokens-to-Success (TTS): Cumulative tokens (prompt + schema + completion) consumed across attempts until success.
- Schema Exposure Footprint: Number of schema constraint tokens exposed to the LLM context.
- Prediction Overexposure: Excess schema tokens exposed that were not in the minimal sufficient Oracle set O(x).
- Oracle Gap: Total tokens consumed above the Oracle lower bound.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import json

@dataclass
class AttemptTokenBreakdown:
    """Per-attempt granular token accounting record."""
    attempt_number: int
    base_prompt_tokens: int        # System prompt + task instructions
    base_schema_tokens: int        # Initial schema level tokens (1A, 1B, 1C, 1D, or Full)
    new_delta_tokens: int          # Sliced constraint deltas exposed in this attempt
    total_schema_tokens: int       # base_schema_tokens + cumulative delta tokens exposed so far
    completion_tokens: int         # Tokens generated in tool argument output
    attempt_total_tokens: int      # prompt + schema + completion for this attempt
    cumulative_tts: int            # Running sum of attempt_total_tokens across all attempts so far

@dataclass
class TaskTokenAccount:
    """Complete lifecycle token audit for a single evaluation task."""
    task_id: str
    semantic_cluster: str
    schema_level: str              # '1A', '1B', '1C', '1D', 'full', 'reactive', 'proactive', 'oracle'
    attempts: List[AttemptTokenBreakdown] = field(default_factory=list)
    final_outcome: str = "PENDING" # 'SUCCESS', 'FAIL'
    tokens_to_success: Optional[int] = None # TTS if final_outcome == 'SUCCESS'
    total_cumulative_tokens: int = 0
    final_schema_tokens_exposed: int = 0
    oracle_minimal_schema_tokens: Optional[int] = None
    prediction_overexposure_tokens: Optional[int] = None
    oracle_gap_tokens: Optional[int] = None

    def add_attempt(
        self,
        attempt_number: int,
        base_prompt_tokens: int,
        base_schema_tokens: int,
        new_delta_tokens: int,
        total_schema_tokens: int,
        completion_tokens: int
    ) -> AttemptTokenBreakdown:
        attempt_total = base_prompt_tokens + total_schema_tokens + completion_tokens
        prev_cumulative = self.attempts[-1].cumulative_tts if self.attempts else 0
        cumulative = prev_cumulative + attempt_total

        breakdown = AttemptTokenBreakdown(
            attempt_number=attempt_number,
            base_prompt_tokens=base_prompt_tokens,
            base_schema_tokens=base_schema_tokens,
            new_delta_tokens=new_delta_tokens,
            total_schema_tokens=total_schema_tokens,
            completion_tokens=completion_tokens,
            attempt_total_tokens=attempt_total,
            cumulative_tts=cumulative
        )
        self.attempts.append(breakdown)
        self.total_cumulative_tokens = cumulative
        self.final_schema_tokens_exposed = total_schema_tokens
        return breakdown

    def finalize(self, outcome: str, oracle_tokens: Optional[int] = None):
        self.final_outcome = outcome
        if outcome == "SUCCESS":
            self.tokens_to_success = self.total_cumulative_tokens
        else:
            self.tokens_to_success = None

        if oracle_tokens is not None:
            self.oracle_minimal_schema_tokens = oracle_tokens
            # Overexposure: schema tokens exposed beyond what Oracle required
            self.prediction_overexposure_tokens = max(0, self.final_schema_tokens_exposed - oracle_tokens)
            # Oracle gap: total cumulative tokens used vs ideal 1-pass Oracle run
            # An ideal Oracle run would use: base_prompt + oracle_schema + avg_completion
            est_oracle_tts = self.attempts[0].base_prompt_tokens + oracle_tokens + self.attempts[0].completion_tokens if self.attempts else oracle_tokens
            self.oracle_gap_tokens = max(0, self.total_cumulative_tokens - est_oracle_tts)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

def compute_aggregate_token_metrics(accounts: List[TaskTokenAccount]) -> Dict[str, Any]:
    """Computes academic benchmark summary metrics across a batch of task accounts."""
    if not accounts:
        return {}

    total_tasks = len(accounts)
    successful_tasks = [a for a in accounts if a.final_outcome == "SUCCESS"]
    success_rate = (len(successful_tasks) / total_tasks) * 100.0

    tts_list = [a.tokens_to_success for a in successful_tasks if a.tokens_to_success is not None]
    avg_tts = sum(tts_list) / len(tts_list) if tts_list else 0.0

    schema_exposed_list = [a.final_schema_tokens_exposed for a in accounts]
    avg_schema_exposed = sum(schema_exposed_list) / total_tasks

    total_experiment_tokens = sum(a.total_cumulative_tokens for a in accounts)

    overexposure_list = [a.prediction_overexposure_tokens for a in accounts if a.prediction_overexposure_tokens is not None]
    avg_overexposure = sum(overexposure_list) / len(overexposure_list) if overexposure_list else 0.0

    oracle_gap_list = [a.oracle_gap_tokens for a in accounts if a.oracle_gap_tokens is not None]
    avg_oracle_gap = sum(oracle_gap_list) / len(oracle_gap_list) if oracle_gap_list else 0.0

    return {
        "total_tasks": total_tasks,
        "success_rate_pct": round(success_rate, 2),
        "mean_tts": round(avg_tts, 2),
        "mean_schema_tokens_exposed": round(avg_schema_exposed, 2),
        "mean_prediction_overexposure": round(avg_overexposure, 2),
        "mean_oracle_gap": round(avg_oracle_gap, 2),
        "total_experiment_tokens_consumed": total_experiment_tokens
    }
