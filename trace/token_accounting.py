"""
Comprehensive Token Accounting & Budget Auditor
Project: mcp-inventory-bench
Author: Anand S. Suchak

Implements fine-grained token accounting for multi-attempt MCP tool execution.
Strictly separates:
1. Provider Generation Tokens:
   - provider_prompt_tokens (includes serialized schema embedded in user prompt)
   - provider_candidate_tokens
   - provider_total_tokens (when supplied by provider usageMetadata)
   - recorded_prompt_candidate_tokens = provider_prompt_tokens + provider_candidate_tokens
2. Architectural Diagnostics (separate heuristic estimates, NEVER double-counted into provider totals):
   - estimated_schema_exposure_tokens
   - prediction overexposure tokens
   - oracle gap tokens
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
import json

@dataclass
class AttemptTokenBreakdown:
    """Per-attempt granular token accounting record."""
    attempt_number: int
    provider_prompt_tokens: int            # Provider-reported prompt tokens (includes embedded schema)
    provider_candidate_tokens: int         # Provider-reported generated tokens
    recorded_prompt_candidate_tokens: int  # provider_prompt_tokens + provider_candidate_tokens
    provider_total_tokens: Optional[int]   # Provider usageMetadata.totalTokenCount
    estimated_schema_exposure_tokens: int  # Separate heuristic estimate of schema constraints exposed
    cumulative_recorded_prompt_candidate_tokens: int  # Running sum of recorded P+C tokens
    cumulative_provider_total_tokens: Optional[int]   # Running sum of provider_total_tokens
    # Backwards compatibility aliases
    base_prompt_tokens: int = 0
    total_schema_tokens: int = 0
    completion_tokens: int = 0
    attempt_total_tokens: int = 0          # Synonymous with recorded_prompt_candidate_tokens
    cumulative_tts: int = 0                # Synonymous with cumulative_recorded_prompt_candidate_tokens

@dataclass
class TaskTokenAccount:
    """Complete lifecycle token audit for a single evaluation task."""
    task_id: str
    semantic_cluster: str
    schema_level: str                      # '1A', '1B', '1C', '1D', 'full', 'reactive', 'ci_k0', etc.
    attempts: List[AttemptTokenBreakdown] = field(default_factory=list)
    final_outcome: str = "PENDING"         # 'SUCCESS', 'FAIL'
    tokens_to_success: Optional[int] = None # P+C TTS if final_outcome == 'SUCCESS'
    tokens_to_success_provider_total: Optional[int] = None # Provider total TTS if SUCCESS
    schema_exposure_to_success: Optional[int] = None # Schema exposure footprint at success
    total_cumulative_tokens: int = 0       # Total recorded P+C tokens
    total_provider_total_tokens: Optional[int] = None # Total provider-reported total tokens
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
        completion_tokens: int,
        provider_total_tokens: Optional[int] = None,
        provider_usage_metadata: Optional[Dict[str, Any]] = None
    ) -> AttemptTokenBreakdown:
        """
        Record an attempt. The serialized tool schema is included in prompt text;
        base_prompt_tokens (provider prompt tokens) already accounts for it.
        recorded_prompt_candidate_tokens = base_prompt_tokens + completion_tokens.
        Do NOT add total_schema_tokens to this subtotal.
        """
        prompt_cand_tokens = base_prompt_tokens + completion_tokens
        prov_total = provider_total_tokens
        if prov_total is None and provider_usage_metadata:
            prov_total = provider_usage_metadata.get("totalTokenCount")

        prev_cumulative_pc = self.attempts[-1].cumulative_recorded_prompt_candidate_tokens if self.attempts else 0
        cumulative_pc = prev_cumulative_pc + prompt_cand_tokens

        prev_cumulative_pt = self.attempts[-1].cumulative_provider_total_tokens if self.attempts else 0
        cumulative_pt = (prev_cumulative_pt + prov_total) if (prev_cumulative_pt is not None and prov_total is not None) else None

        breakdown = AttemptTokenBreakdown(
            attempt_number=attempt_number,
            provider_prompt_tokens=base_prompt_tokens,
            provider_candidate_tokens=completion_tokens,
            recorded_prompt_candidate_tokens=prompt_cand_tokens,
            provider_total_tokens=prov_total,
            estimated_schema_exposure_tokens=total_schema_tokens,
            cumulative_recorded_prompt_candidate_tokens=cumulative_pc,
            cumulative_provider_total_tokens=cumulative_pt,
            # Backwards compatibility fields
            base_prompt_tokens=base_prompt_tokens,
            total_schema_tokens=total_schema_tokens,
            completion_tokens=completion_tokens,
            attempt_total_tokens=prompt_cand_tokens,
            cumulative_tts=cumulative_pc
        )
        self.attempts.append(breakdown)
        self.total_cumulative_tokens = cumulative_pc
        self.total_provider_total_tokens = cumulative_pt
        self.final_schema_tokens_exposed = total_schema_tokens
        return breakdown

    def finalize(self, outcome: str, oracle_tokens: Optional[int] = None):
        self.final_outcome = outcome
        if outcome == "SUCCESS":
            self.tokens_to_success = self.total_cumulative_tokens
            self.tokens_to_success_provider_total = self.total_provider_total_tokens
            self.schema_exposure_to_success = self.final_schema_tokens_exposed
        else:
            self.tokens_to_success = None
            self.tokens_to_success_provider_total = None
            self.schema_exposure_to_success = None

        if oracle_tokens is not None:
            self.oracle_minimal_schema_tokens = oracle_tokens
            self.prediction_overexposure_tokens = max(0, self.final_schema_tokens_exposed - oracle_tokens)
            # Oracle gap: total cumulative tokens used vs ideal 1-pass Oracle run
            est_oracle_tts = self.attempts[0].provider_prompt_tokens + self.attempts[0].provider_candidate_tokens if self.attempts else oracle_tokens
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

    pt_tts_list = [a.tokens_to_success_provider_total for a in successful_tasks if a.tokens_to_success_provider_total is not None]
    avg_pt_tts = sum(pt_tts_list) / len(pt_tts_list) if pt_tts_list else None

    schema_exposed_list = [a.final_schema_tokens_exposed for a in accounts]
    avg_schema_exposed = sum(schema_exposed_list) / total_tasks

    total_experiment_tokens = sum(a.total_cumulative_tokens for a in accounts)
    total_prov_tokens = sum(a.total_provider_total_tokens for a in accounts if a.total_provider_total_tokens is not None) if all(a.total_provider_total_tokens is not None for a in accounts) else None

    overexposure_list = [a.prediction_overexposure_tokens for a in accounts if a.prediction_overexposure_tokens is not None]
    avg_overexposure = sum(overexposure_list) / len(overexposure_list) if overexposure_list else 0.0

    oracle_gap_list = [a.oracle_gap_tokens for a in accounts if a.oracle_gap_tokens is not None]
    avg_oracle_gap = sum(oracle_gap_list) / len(oracle_gap_list) if oracle_gap_list else 0.0

    return {
        "total_tasks": total_tasks,
        "success_rate_pct": round(success_rate, 2),
        "mean_tts_prompt_candidate": round(avg_tts, 2),
        "mean_tts_provider_total": round(avg_pt_tts, 2) if avg_pt_tts is not None else None,
        "mean_schema_tokens_exposed": round(avg_schema_exposed, 2),
        "mean_prediction_overexposure": round(avg_overexposure, 2),
        "mean_oracle_gap": round(avg_oracle_gap, 2),
        "total_recorded_prompt_candidate_tokens": total_experiment_tokens,
        "total_provider_total_tokens": total_prov_tokens
    }
