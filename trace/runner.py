"""
Observational Trace Runner (Dataset A Collection Engine)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Executes multi-turn schema resolution experiments where the model begins with a
restricted (Level-1) view and receives sliced constraint deltas only upon validation errors.
Preserves the full hidden schema as the experimental control.
"""

import sys
import time
import copy
import json
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable

sys.path.insert(0, str(Path(__file__).parent.parent))

from trace.models import Trace, Attempt, SchemaExposureRecord, ValidationErrorRecord
from trace.validator import SchemaValidator
from trace.slicer import slice_constraint, format_fragment_identifier, estimate_tokens
from trace.writer import TraceWriter

# ==============================================================================
# Full Hidden Schema Definitions (Experimental Control)
# Level 1: stripped of constraints (pattern, enum, minimum, etc.)
# Full Hidden: complete Draft 2020-12 constraints
# ==============================================================================

FULL_PURCHASE_ORDER_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "create_purchase_order",
    "type": "object",
    "properties": {
        "supplier_id": {
            "type": "string",
            "pattern": "^SUP-[A-Z0-9]{4,12}-[A-Z0-9]{3,6}$",
            "description": "Standard vendor identifier format SUP-XXXX-XXXX"
        },
        "warehouse_code": {
            "type": "string",
            "enum": ["WH-US-EAST", "WH-US-WEST", "WH-EU-CENTRAL", "WH-APAC-SOUTH", "WH-LATAM-NORTH"],
            "description": "Authorized regional warehouse code"
        },
        "order_priority": {
            "type": "string",
            "enum": ["STANDARD", "EXPEDITED", "CRITICAL"],
            "default": "STANDARD"
        },
        "total_budget_limit": {
            "type": "number",
            "minimum": 100.0,
            "maximum": 500000.0,
            "description": "Max allowable authorization ceiling"
        },
        "items": {
            "type": "array",
            "minItems": 1,
            "maxItems": 50,
            "items": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "pattern": "^SKU-[0-9]{5}$",
                        "description": "Unique SKU code format SKU-XXXXX"
                    },
                    "quantity": {
                        "type": "integer",
                        "minimum": 10,
                        "maximum": 10000,
                        "description": "Quantity to reorder, must meet MOQ >= 10"
                    },
                    "unit_cost": {
                        "type": "number",
                        "minimum": 0.01,
                        "description": "Contract unit price"
                    }
                },
                "required": ["sku", "quantity", "unit_cost"],
                "additionalProperties": False
            }
        },
        "authorized_by": {
            "type": "string",
            "pattern": "^[a-z]{3,8}\\.[a-z]{3,8}@enterprise\\.mock$",
            "description": "Corporate email signature of the authorizing agent"
        }
    },
    "required": ["supplier_id", "warehouse_code", "items", "authorized_by"],
    "additionalProperties": False
}

def create_level_1_schema(full_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce the restricted Level-1 view: contains property names and basic types,
    but strips regex patterns, enums, min/max bounds, and nested constraints.
    """
    l1 = {
        "title": full_schema.get("title", "tool"),
        "type": "object",
        "properties": {}
    }
    for prop, meta in full_schema.get("properties", {}).items():
        base_meta = {"type": meta.get("type", "string")}
        if "description" in meta:
            base_meta["description"] = meta["description"]
        if meta.get("type") == "array" and "items" in meta:
            base_meta["items"] = {"type": "object"}
        l1["properties"][prop] = base_meta

    # Include required list as baseline structural expectation
    if "required" in full_schema:
        l1["required"] = full_schema["required"]
    return l1

class TaskDefinition:
    """Definition of an evaluation task for trace collection."""
    def __init__(
        self,
        task_id: str,
        category: str,
        user_intent: str,
        initial_arguments: Dict[str, Any],
        correction_generator: Optional[Callable[[Dict[str, Any], ValidationErrorRecord], Dict[str, Any]]] = None
    ):
        self.task_id = task_id
        self.category = category
        self.user_intent = user_intent
        self.initial_arguments = initial_arguments
        self.correction_generator = correction_generator

from trace.llm_client import LiveLLMClient

class TraceRunner:
    """Executes closed-loop observational trace collection experiments."""

    def __init__(
        self,
        full_schema: Dict[str, Any] = FULL_PURCHASE_ORDER_SCHEMA,
        tool_name: str = "create_purchase_order",
        single_error: bool = True,
        max_attempts: int = 4,
        llm_client: Optional[LiveLLMClient] = None,
        writer: Optional[TraceWriter] = None
    ):
        self.full_schema = full_schema
        self.tool_name = tool_name
        self.single_error = single_error
        self.max_attempts = max_attempts
        self.validator = SchemaValidator(full_schema)
        self.llm_client = llm_client or LiveLLMClient()
        self.writer = writer or TraceWriter()

    def run_trace(self, task: TaskDefinition) -> Trace:
        """
        Execute a single observational trace:
        1. Initialize Level 1 schema and exposure ledger
        2. Attempt 1: Validate initial model arguments
        3. If fail: Slice minimal constraint delta, expose to model, and retry
        4. Record all attempts, latencies, tokens, and final outcome
        """
        prov = self.llm_client.get_provenance_metadata()
        trace = Trace(
            task_id=task.task_id,
            category=task.category,
            user_intent=task.user_intent,
            tool_name=self.tool_name,
            model=prov["model"],
            model_version=f"{prov['provider']}:{prov['api_mode']}",
            git_commit=prov.get("git_commit", ""),
            prompt_version=prov.get("prompt_version", "v1.0-level1-dynamic-repair"),
            schema_version=prov.get("schema_version", "2026-07-28/draft-2020-12"),
            provenance=prov
        )

        # Level 1 Schema Exposure
        level1 = create_level_1_schema(self.full_schema)
        l1_tokens = estimate_tokens(level1)
        trace.schema_exposure_ledger.append(SchemaExposureRecord(
            fragment="level_1_base_schema",
            tokens=l1_tokens,
            attempt=1,
            reason="INITIAL_LEVEL_1"
        ))
        trace.total_schema_tokens_exposed = l1_tokens

        exposed_fragments = ["level_1_base_schema"]
        exposed_schema = copy.deepcopy(level1)
        raw_response_text = ""
        model_call_latency = 0.0
        resp_id = ""
        p_tok = 0
        c_tok = 0

        if self.llm_client.api_mode == "live":
            # Real LLM call for Attempt 1
            current_args, raw_response_text, model_call_latency, resp_id, p_tok, c_tok = self.llm_client.generate_tool_arguments(
                user_intent=task.user_intent,
                tool_name=self.tool_name,
                exposed_schema=exposed_schema
            )
        else:
            current_args = copy.deepcopy(task.initial_arguments)
            raw_response_text = json.dumps(current_args)
            resp_id = f"pilot-resp-{task.task_id}-att1"
            p_tok = l1_tokens
            c_tok = estimate_tokens(current_args)

        for attempt_num in range(1, self.max_attempts + 1):
            t_start = time.perf_counter()
            is_valid, validation_errors = self.validator.validate(current_args)
            validation_latency_ms = round((time.perf_counter() - t_start) * 1000, 3)

            attempt = Attempt(
                attempt_number=attempt_num,
                schema_fragments_exposed=list(exposed_fragments),
                schema_token_count=trace.total_schema_tokens_exposed,
                model_response=raw_response_text,
                arguments=copy.deepcopy(current_args),
                validation_status="SUCCESS" if is_valid else "FAIL",
                validation_errors=validation_errors,
                latency_ms=round(model_call_latency + validation_latency_ms, 3),
                response_id=resp_id,
                prompt_tokens=p_tok,
                completion_tokens=c_tok
            )
            trace.attempts.append(attempt)

            if is_valid:
                trace.final_outcome = "SUCCESS"
                trace.tokens_to_success = sum(a.prompt_tokens + a.completion_tokens for a in trace.attempts)
                trace.schema_exposure_to_success = trace.total_schema_tokens_exposed
                break

            # If failed, extract constraint slice
            if attempt_num < self.max_attempts:
                # In single_error mode, process the first validation error
                err_to_process = validation_errors[0] if self.single_error else validation_errors[0]
                delta_slice = slice_constraint(self.full_schema, err_to_process.path, err_to_process.keyword)
                fragment_id = format_fragment_identifier(err_to_process.path, err_to_process.keyword)
                delta_tokens = estimate_tokens(delta_slice)

                # Record in ledger
                trace.schema_exposure_ledger.append(SchemaExposureRecord(
                    fragment=fragment_id,
                    tokens=delta_tokens,
                    attempt=attempt_num + 1,
                    reason=f"CONSTRAINT_VIOLATION_{err_to_process.keyword.upper()}"
                ))
                trace.total_schema_tokens_exposed += delta_tokens
                exposed_fragments.append(fragment_id)

                # Update composite exposed schema with new delta
                exposed_schema.setdefault("constraints", {})[fragment_id] = delta_slice

                # Generate corrected arguments
                if self.llm_client.api_mode == "live":
                    current_args, raw_response_text, model_call_latency, resp_id, p_tok, c_tok = self.llm_client.generate_tool_arguments(
                        user_intent=task.user_intent,
                        tool_name=self.tool_name,
                        exposed_schema=exposed_schema,
                        error_context=err_to_process.message,
                        previous_arguments=current_args
                    )
                elif task.correction_generator:
                    current_args = task.correction_generator(current_args, err_to_process)
                    raw_response_text = json.dumps(current_args)
                    resp_id = f"pilot-resp-{task.task_id}-att{attempt_num+1}"
                    c_tok = estimate_tokens(current_args)
                else:
                    current_args = self._default_correct_argument(current_args, err_to_process)
                    raw_response_text = json.dumps(current_args)
                    resp_id = f"pilot-resp-{task.task_id}-att{attempt_num+1}"
                    c_tok = estimate_tokens(current_args)

        if trace.final_outcome != "SUCCESS":
            trace.final_outcome = "FAIL"

        return trace

    def _default_correct_argument(self, args: Dict[str, Any], err: ValidationErrorRecord) -> Dict[str, Any]:
        """Heuristic correction rule for synthetic agent self-correction."""
        corrected = copy.deepcopy(args)
        path = err.path.strip("/")
        kw = err.keyword

        if kw == "pattern":
            if "supplier_id" in path:
                corrected["supplier_id"] = "SUP-TEXAS-SEMI"
            elif "sku" in path:
                if "items" in corrected and len(corrected["items"]) > 0:
                    corrected["items"][0]["sku"] = "SKU-10042"
            elif "authorized_by" in path:
                corrected["authorized_by"] = "anand.suchak@enterprise.mock"
        elif kw == "enum":
            if "warehouse_code" in path:
                corrected["warehouse_code"] = "WH-US-EAST"
            elif "order_priority" in path:
                corrected["order_priority"] = "STANDARD"
        elif kw == "minimum":
            if "quantity" in path:
                if "items" in corrected and len(corrected["items"]) > 0:
                    corrected["items"][0]["quantity"] = 50 # Meet MOQ
            elif "total_budget_limit" in path:
                corrected["total_budget_limit"] = 500.0
        elif kw == "required":
            if "authorized_by" in err.message:
                corrected["authorized_by"] = "anand.suchak@enterprise.mock"
            elif "items" in err.message:
                corrected["items"] = [{"sku": "SKU-10042", "quantity": 50, "unit_cost": 24.50}]

        return corrected

# ==============================================================================
# Curated Task Suite Generator: 100 Traces across 7 Structured Categories
# ==============================================================================

def generate_curated_100_tasks() -> List[TaskDefinition]:
    """
    Generates exactly 100 structured tasks across the 7 required categories:
    1. Explicit valid inputs (15)
    2. Missing/ambiguous IDs (15)
    3. Invalid enum situations (15)
    4. Regex-constrained fields (15)
    5. Numeric constraints (15)
    6. Nested/array fields (15)
    7. Mixed/ambiguous cases (10)
    """
    tasks: List[TaskDefinition] = []

    # Category 1: Explicit valid inputs (15 tasks)
    for i in range(1, 16):
        tasks.append(TaskDefinition(
            task_id=f"TASK-CAT1-VALID-{i:03d}",
            category="Explicit valid inputs",
            user_intent=f"Order 50 units of SKU-100{i:02d} for East warehouse under standard terms.",
            initial_arguments={
                "supplier_id": "SUP-TEXAS-SEMI",
                "warehouse_code": "WH-US-EAST",
                "order_priority": "STANDARD",
                "total_budget_limit": 25000.0,
                "items": [{"sku": f"SKU-100{i:02d}", "quantity": 50, "unit_cost": 45.0}],
                "authorized_by": "agent.ops@enterprise.mock"
            }
        ))

    # Category 2: Missing/ambiguous IDs (15 tasks)
    for i in range(1, 16):
        tasks.append(TaskDefinition(
            task_id=f"TASK-CAT2-MISSING-ID-{i:03d}",
            category="Missing/ambiguous IDs",
            user_intent=f"Reorder low stock items without specifying authorization signature.",
            initial_arguments={
                "supplier_id": "SUP-TEXAS-SEMI",
                "warehouse_code": "WH-US-WEST",
                "items": [{"sku": f"SKU-100{i:02d}", "quantity": 40, "unit_cost": 30.0}]
                # Missing 'authorized_by'
            }
        ))

    # Category 3: Invalid enum situations (15 tasks)
    invalid_wh_codes = ["EAST-COAST-HUB", "WH-NEW-YORK", "LONDON-CENTER", "TOKYO-WAREHOUSE", "MIAMI-DOCK"]
    for i in range(1, 16):
        bad_code = invalid_wh_codes[(i - 1) % len(invalid_wh_codes)]
        tasks.append(TaskDefinition(
            task_id=f"TASK-CAT3-ENUM-{i:03d}",
            category="Invalid enum situations",
            user_intent=f"Replenish stock for regional depot {bad_code}.",
            initial_arguments={
                "supplier_id": "SUP-TEXAS-SEMI",
                "warehouse_code": bad_code,
                "items": [{"sku": f"SKU-100{i:02d}", "quantity": 35, "unit_cost": 15.0}],
                "authorized_by": "agent.procure@enterprise.mock"
            }
        ))

    # Category 4: Regex-constrained fields (15 tasks)
    bad_vendor_ids = ["vendor-texas", "12345", "SUPPLIER_TEXAS", "TEXAS-SEMI", "sup-texas-semi"]
    for i in range(1, 16):
        bad_vendor = bad_vendor_ids[(i - 1) % len(bad_vendor_ids)]
        tasks.append(TaskDefinition(
            task_id=f"TASK-CAT4-REGEX-{i:03d}",
            category="Regex-constrained fields",
            user_intent=f"Send PO using informal vendor handle '{bad_vendor}'.",
            initial_arguments={
                "supplier_id": bad_vendor,
                "warehouse_code": "WH-US-EAST",
                "items": [{"sku": f"SKU-100{i:02d}", "quantity": 25, "unit_cost": 50.0}],
                "authorized_by": "anand.suchak@enterprise.mock"
            }
        ))

    # Category 5: Numeric constraints (15 tasks)
    for i in range(1, 16):
        # Quantity violates MOQ minimum (MOQ is 10, agent orders 2 to 5)
        bad_qty = (i % 8) + 1
        tasks.append(TaskDefinition(
            task_id=f"TASK-CAT5-NUMERIC-{i:03d}",
            category="Numeric constraints",
            user_intent=f"Order small top-up sample of {bad_qty} units (below MOQ).",
            initial_arguments={
                "supplier_id": "SUP-TEXAS-SEMI",
                "warehouse_code": "WH-EU-CENTRAL",
                "items": [{"sku": f"SKU-100{i:02d}", "quantity": bad_qty, "unit_cost": 80.0}],
                "authorized_by": "ops.lead@enterprise.mock"
            }
        ))

    # Category 6: Nested/array fields (15 tasks)
    for i in range(1, 16):
        # SKU regex violation inside items array: 'ITEM-123' instead of 'SKU-XXXXX'
        tasks.append(TaskDefinition(
            task_id=f"TASK-CAT6-NESTED-{i:03d}",
            category="Nested/array fields",
            user_intent=f"Submit multi-line order with unformatted SKU string.",
            initial_arguments={
                "supplier_id": "SUP-TEXAS-SEMI",
                "warehouse_code": "WH-APAC-SOUTH",
                "items": [{"sku": f"ITEM-{i}", "quantity": 50, "unit_cost": 22.0}],
                "authorized_by": "apac.lead@enterprise.mock"
            }
        ))

    # Category 7: Mixed/ambiguous cases (10 tasks)
    for i in range(1, 11):
        tasks.append(TaskDefinition(
            task_id=f"TASK-CAT7-MIXED-{i:03d}",
            category="Mixed/ambiguous cases",
            user_intent=f"Urgent replenishment with multiple informal parameters.",
            initial_arguments={
                "supplier_id": f"vendor-{i}",
                "warehouse_code": "WH-US-EAST",
                "items": [{"sku": f"SKU-100{i:02d}", "quantity": 4, "unit_cost": 99.0}],
                "authorized_by": "informal-user"
            }
        ))

    return tasks

def generate_targeted_real_tasks(n_per_category: int = 3) -> List[TaskDefinition]:
    """
    Selects a balanced, targeted subset of tasks across all 7 categories
    (default: 3 per category = 21 tasks) for initial real-model validation.
    """
    all_tasks = generate_curated_100_tasks()
    selected = []
    category_counts: Dict[str, int] = {}

    for t in all_tasks:
        c = t.category
        if category_counts.get(c, 0) < n_per_category:
            selected.append(t)
            category_counts[c] = category_counts.get(c, 0) + 1

    return selected

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Observational Trace Runner (Dataset A)")
    parser.add_argument("--mode", choices=["pilot", "live"], default="pilot", help="Execution mode (pilot: mock harness validation, live: real LLM API)")
    parser.add_argument("--provider", choices=["openai", "gemini", "anthropic", "groq"], default=None, help="LLM API provider")
    parser.add_argument("--model", type=str, default=None, help="Target model identifier")
    parser.add_argument("--api-key", type=str, default=None, help="API key override")
    parser.add_argument("--n-per-cat", type=int, default=3, help="Number of tasks per category (3 -> 21 total, 15 -> 100 total)")
    parser.add_argument("--full-100", action="store_true", help="Run full 100 tasks suite")

    args = parser.parse_args()

    client = LiveLLMClient(
        provider=args.provider if args.mode == "live" else "mock_pilot",
        model=args.model,
        api_key=args.api_key
    )

    runner = TraceRunner(single_error=True, llm_client=client)

    if args.full_100:
        tasks = generate_curated_100_tasks()
    else:
        tasks = generate_targeted_real_tasks(n_per_category=args.n_per_cat)

    print(f"\n======================================================================")
    print(f"[*] OBSERVATIONAL TRACE RUNNER | Mode: {client.api_mode.upper()} | Provider: {client.provider} | Model: {client.model}")
    print(f"[*] Executing {len(tasks)} tasks across 7 categories...")
    print(f"======================================================================")

    traces = []
    for idx, t in enumerate(tasks, 1):
        print(f"  [{idx}/{len(tasks)}] Running task: {t.task_id} ({t.category})...", end="", flush=True)
        res_trace = runner.run_trace(t)
        traces.append(res_trace)
        print(f" Outcome: {res_trace.final_outcome} ({len(res_trace.attempts)} attempts)")

    runner.writer.write_traces_batch(traces)
    manifest = runner.writer.refresh_manifest()
    print(f"\n[+] Finished! Traces logged to {runner.writer.traces_file}")
    print(f"[+] Total traces: {manifest['total_traces']} | Total attempts: {manifest['total_attempts']} | Tokens exposed: {manifest['total_schema_tokens_exposed']}")
    print(f"[+] Categories: {json.dumps(manifest['categories'], indent=2)}")
    print(f"[+] Outcomes: {json.dumps(manifest['outcomes'], indent=2)}")
