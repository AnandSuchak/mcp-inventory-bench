"""
Pilot-2 Experiment 1 & 2 Execution Runner
Project: mcp-inventory-bench
Author: Anand S. Suchak

Executes:
1. Experiment 1: Semantic Generalization across 80 Blinded Tasks.
   - Evaluates whether semantic cluster S predicts constraint requirement c above base rate.
   - Generates the formal P(c | S) cross-cluster matrix.
   - Evaluates Frequency-Prior baseline vs. semantic signal.

2. Experiment 2: Schema Budget Curve (1A, 1B, 1C, 1D).
   - Measures first-pass success rate, retry count, schema exposure, and cumulative TTS.
   - Plots the Pareto frontier between initial schema footprint and tool execution reliability.

Integrates first-class TokenAccounting and local response caching to prevent duplicate API cost.
"""

import os
import sys
import time
import copy
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).parent.parent))

from trace.models import Trace, Attempt, SchemaExposureRecord, ValidationErrorRecord
from trace.validator import SchemaValidator
from trace.slicer import (
    slice_constraint,
    format_fragment_identifier,
    estimate_tokens,
    create_schema_level_1a,
    create_schema_level_1b,
    create_schema_level_1c,
    create_schema_level_1d
)
from trace.paraphraser import generate_pilot2_blinded_tasks, BlindedTask
from trace.token_accounting import TaskTokenAccount, compute_aggregate_token_metrics
from trace.llm_client import LiveLLMClient
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA

# Local disk cache to guarantee zero redundant LLM API calls
CACHE_DIR = Path(__file__).parent.parent / "datasets" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def get_cache_key(model: str, system_prompt: str, user_content: str) -> str:
    h = hashlib.sha256((model + ":" + system_prompt + ":" + user_content).encode("utf-8")).hexdigest()
    return h

def load_cached_response(cache_key: str) -> Optional[Dict[str, Any]]:
    cache_file = CACHE_DIR / f"{cache_key}.json"
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return None

def save_cached_response(cache_key: str, data: Dict[str, Any]):
    cache_file = CACHE_DIR / f"{cache_key}.json"
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(data, f)

class Pilot2ExperimentRunner:
    """Orchestrates Experiment 1 and Experiment 2 with token auditing and strict provenance."""

    def __init__(
        self,
        llm_client: LiveLLMClient,
        max_attempts: int = 4,
        cache_enabled: bool = True
    ):
        self.client = llm_client
        self.validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
        self.max_attempts = max_attempts
        self.cache_enabled = cache_enabled

    def run_task(
        self,
        task: BlindedTask,
        schema_level: str = "1C"
    ) -> Tuple[Trace, TaskTokenAccount]:
        """
        Execute a single blinded task under a specified initial schema budget level.
        Tracks granular token consumption via TaskTokenAccount.
        """
        if schema_level == "1A":
            init_schema = create_schema_level_1a(FULL_PURCHASE_ORDER_SCHEMA)
        elif schema_level == "1B":
            init_schema = create_schema_level_1b(FULL_PURCHASE_ORDER_SCHEMA)
        elif schema_level == "1C":
            init_schema = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)
        elif schema_level == "1D":
            init_schema = create_schema_level_1d(FULL_PURCHASE_ORDER_SCHEMA)
        elif schema_level == "full":
            init_schema = copy.deepcopy(FULL_PURCHASE_ORDER_SCHEMA)
        else:
            raise ValueError(f"Unknown schema level: {schema_level}")

        base_schema_tokens = estimate_tokens(init_schema)
        account = TaskTokenAccount(
            task_id=task.task_id,
            semantic_cluster=task.semantic_cluster,
            schema_level=schema_level
        )

        trace = Trace(
            task_id=task.task_id,
            category=task.semantic_cluster,
            user_intent=task.user_intent,
            tool_name=FULL_PURCHASE_ORDER_SCHEMA.get("title", "tool"),
            model=self.client.model,
            provenance=self.client.get_provenance_metadata()
        )

        exposed_schema = copy.deepcopy(init_schema)
        current_args: Dict[str, Any] = {}
        error_context: Optional[str] = None
        previous_args: Optional[Dict[str, Any]] = None
        final_status = "FAIL"

        for attempt_num in range(1, self.max_attempts + 1):
            # Formulate prompt payloads
            system_prompt = (
                f"You are an autonomous enterprise operations AI agent executing tool 'create_purchase_order'.\n"
                "You MUST output ONLY a valid JSON object containing the exact tool arguments required.\n"
                "Do not include any conversational filler, markdown formatting blocks, or explanations."
            )
            user_content = f"User Intent: {task.user_intent}\n\nAvailable Tool Schema Specification:\n{json.dumps(exposed_schema, indent=2)}\n"
            if error_context:
                user_content += (
                    f"\nYour previous arguments failed validation with this error:\n{error_context}\n"
                    f"Previous arguments attempted:\n{json.dumps(previous_args or {}, indent=2)}\n"
                    "Please correct your arguments based strictly on the newly exposed schema constraints above."
                )

            cache_key = get_cache_key(self.client.model, system_prompt, user_content)
            cached = load_cached_response(cache_key) if self.cache_enabled else None

            if cached:
                args = cached["args"]
                raw_resp = cached["raw_resp"]
                p_tok = cached["p_tok"]
                c_tok = cached["c_tok"]
                resp_id = cached.get("resp_id", "cached")
                lat = cached.get("lat", 0.0)
            else:
                args, raw_resp, lat, resp_id, p_tok, c_tok = self.client.generate_tool_arguments(
                    user_intent=task.user_intent,
                    tool_name="create_purchase_order",
                    exposed_schema=exposed_schema,
                    error_context=error_context,
                    previous_arguments=previous_args
                )
                if self.cache_enabled:
                    save_cached_response(cache_key, {
                        "args": args, "raw_resp": raw_resp, "p_tok": p_tok, "c_tok": c_tok,
                        "resp_id": resp_id, "lat": lat
                    })

            current_args = args
            is_valid, validation_errors = self.validator.validate(current_args)
            status = "SUCCESS" if is_valid else "FAIL"

            cur_schema_tokens = estimate_tokens(exposed_schema)
            new_delta = cur_schema_tokens - base_schema_tokens

            # Account tokens for this attempt
            account.add_attempt(
                attempt_number=attempt_num,
                base_prompt_tokens=p_tok,
                base_schema_tokens=base_schema_tokens,
                new_delta_tokens=new_delta,
                total_schema_tokens=cur_schema_tokens,
                completion_tokens=c_tok
            )

            attempt = Attempt(
                attempt_number=attempt_num,
                schema_fragments_exposed=list(exposed_schema.get("constraints", {}).keys()),
                schema_token_count=cur_schema_tokens,
                model_response=raw_resp,
                arguments=copy.deepcopy(current_args),
                validation_status=status,
                validation_errors=validation_errors,
                latency_ms=lat,
                response_id=resp_id,
                prompt_tokens=p_tok,
                completion_tokens=c_tok
            )
            trace.attempts.append(attempt)

            if is_valid:
                final_status = "SUCCESS"
                trace.final_outcome = "SUCCESS"
                trace.tokens_to_success = account.total_cumulative_tokens
                trace.tokens_to_success_provider_total = account.total_provider_total_tokens
                trace.schema_exposure_to_success = cur_schema_tokens
                break

            # If validation failed, extract next constraint slice
            if attempt_num < self.max_attempts and validation_errors:
                primary_err = validation_errors[0]
                delta_slice = slice_constraint(FULL_PURCHASE_ORDER_SCHEMA, primary_err.path, primary_err.keyword)
                frag_id = format_fragment_identifier(primary_err.path, primary_err.keyword)
                frag_tokens = estimate_tokens(delta_slice)

                trace.schema_exposure_ledger.append(SchemaExposureRecord(
                    fragment=frag_id,
                    tokens=frag_tokens,
                    attempt=attempt_num + 1,
                    reason=f"CONSTRAINT_VIOLATION_{primary_err.keyword.upper()}"
                ))
                exposed_schema.setdefault("constraints", {})[frag_id] = delta_slice
                error_context = primary_err.message
                previous_args = copy.deepcopy(current_args)

        account.finalize(final_status)
        trace.total_schema_tokens_exposed = account.final_schema_tokens_exposed
        return trace, account

if __name__ == "__main__":
    print("Pilot-2 Runner initialized successfully.")
