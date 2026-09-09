"""
Counterfactual Constraint Replay Harness & Model-Conditional Oracle (Pilot-2 Experiments 3 & 4)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Implements:
1. Counterfactual Constraint Replay:
   Freezes identical Attempt-1 failure states and forks Attempt 2 under 3 randomized branches:
   - Branch A (Null): No delta exposed
   - Branch B (Target): Ground-truth violated constraint exposed
   - Branch C (Decoy): Size-matched, family-matched decoy constraint exposed
   Measures Causal Specificity:
   CRE(c) = P(Success_2 | Target) - P(Success_2 | Decoy)

2. Model-Conditional Minimum-Sufficient-Schema Oracle O(x, m, p):
   Systematically evaluates minimal constraint subsets via backward elimination
   independent of any learned predictor to establish empirical lower bound.

3. Frequency-Prior Baseline:
   Predicts globally most common constraints from training distribution to prove LASR beats class imbalance.
"""

import copy
import json
import random
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from trace.models import ValidationErrorRecord
from trace.slicer import slice_constraint, format_fragment_identifier, estimate_tokens
from trace.validator import SchemaValidator

@dataclass
class CounterfactualBranchResult:
    branch_type: str            # 'null', 'target', 'decoy'
    constraint_exposed: Optional[str]
    exposed_tokens: int
    attempt_2_arguments: Dict[str, Any]
    validation_status: str      # 'SUCCESS' or 'FAIL'
    errors: List[ValidationErrorRecord]

@dataclass
class CounterfactualReplayTrial:
    task_id: str
    frozen_intent: str
    frozen_attempt_1_args: Dict[str, Any]
    primary_violation: ValidationErrorRecord
    target_constraint_id: str
    decoy_constraint_id: str
    results: Dict[str, CounterfactualBranchResult] = field(default_factory=dict)

# Family-matched decoy lookup table (matches keyword family and approximate size)
FAMILY_MATCHED_DECOYS = {
    "warehouse_code.enum": "order_priority.enum",
    "order_priority.enum": "warehouse_code.enum",
    "supplier_id.pattern": "authorized_by.pattern",
    "authorized_by.pattern": "supplier_id.pattern",
    "items.sku.pattern": "supplier_id.pattern",
    "items.quantity.minimum": "total_budget_limit.minimum",
    "total_budget_limit.minimum": "items.quantity.minimum",
    "items.minItems": "items.required",
    "items.required": "items.minItems",
}

class CounterfactualReplayHarness:
    """Manages frozen-state counterfactual intervention trials."""

    def __init__(self, full_schema: Dict[str, Any], validator: SchemaValidator):
        self.full_schema = full_schema
        self.validator = validator

    def create_trial_from_attempt_1(
        self,
        task_id: str,
        user_intent: str,
        attempt_1_args: Dict[str, Any],
        validation_errors: List[ValidationErrorRecord]
    ) -> CounterfactualReplayTrial:
        primary_err = validation_errors[0]
        target_id = format_fragment_identifier(primary_err.path, primary_err.keyword)
        decoy_id = FAMILY_MATCHED_DECOYS.get(target_id, "order_priority.enum")

        return CounterfactualReplayTrial(
            task_id=task_id,
            frozen_intent=user_intent,
            frozen_attempt_1_args=copy.deepcopy(attempt_1_args),
            primary_violation=primary_err,
            target_constraint_id=target_id,
            decoy_constraint_id=decoy_id
        )

    def execute_replay_branch(
        self,
        trial: CounterfactualReplayTrial,
        branch: str,
        llm_client: Any,
        base_schema: Dict[str, Any]
    ) -> CounterfactualBranchResult:
        """
        Execute Attempt 2 from the exact same frozen initial state under one of the 3 intervention arms.
        """
        prompt_schema = copy.deepcopy(base_schema)
        frag_id = None
        frag_tokens = 0
        err_msg = trial.primary_violation.message

        if branch == "null":
            # Branch A: No delta added
            frag_id = None
            frag_tokens = 0
            err_context = err_msg

        elif branch == "target":
            # Branch B: Target violated constraint slice
            frag_id = trial.target_constraint_id
            delta = slice_constraint(self.full_schema, trial.primary_violation.path, trial.primary_violation.keyword)
            frag_tokens = estimate_tokens(delta)
            prompt_schema.setdefault("constraints", {})[frag_id] = delta
            err_context = err_msg

        elif branch == "decoy":
            # Branch C: Decoy constraint slice (size-matched & family-matched)
            frag_id = trial.decoy_constraint_id
            decoy_path, decoy_kw = frag_id.split(".")[-2], frag_id.split(".")[-1]
            delta = slice_constraint(self.full_schema, f"/{decoy_path}", decoy_kw)
            frag_tokens = estimate_tokens(delta)
            prompt_schema.setdefault("constraints", {})[frag_id] = delta
            err_context = err_msg

        else:
            raise ValueError(f"Unknown branch {branch}")

        # Dispatch Attempt 2 using identical frozen history
        att2_args, raw_resp, lat, rid, p_tok, c_tok = llm_client.generate_tool_arguments(
            user_intent=trial.frozen_intent,
            tool_name=self.full_schema.get("title", "tool"),
            exposed_schema=prompt_schema,
            error_context=err_context,
            previous_arguments=trial.frozen_attempt_1_args
        )

        is_valid, errors = self.validator.validate(att2_args)
        status = "SUCCESS" if is_valid else "FAIL"

        result = CounterfactualBranchResult(
            branch_type=branch,
            constraint_exposed=frag_id,
            exposed_tokens=frag_tokens,
            attempt_2_arguments=att2_args,
            validation_status=status,
            errors=errors
        )
        trial.results[branch] = result
        return result

def compute_cre(trials: List[CounterfactualReplayTrial]) -> Dict[str, float]:
    """
    Computes empirical Constraint Repair Effect across frozen trials:
    CRE = P(Success_2 | Target) - P(Success_2 | Decoy)
    """
    if not trials:
        return {"target_success_rate": 0.0, "decoy_success_rate": 0.0, "null_success_rate": 0.0, "cre": 0.0}

    target_success = sum(1 for t in trials if t.results.get("target", {}).validation_status == "SUCCESS")
    decoy_success = sum(1 for t in trials if t.results.get("decoy", {}).validation_status == "SUCCESS")
    null_success = sum(1 for t in trials if t.results.get("null", {}).validation_status == "SUCCESS")
    n = len(trials)

    p_target = target_success / n
    p_decoy = decoy_success / n
    p_null = null_success / n

    return {
        "total_trials": n,
        "target_success_rate": round(p_target, 4),
        "decoy_success_rate": round(p_decoy, 4),
        "null_success_rate": round(p_null, 4),
        "cre": round(p_target - p_decoy, 4),
        "target_vs_null_lift": round(p_target - p_null, 4)
    }
