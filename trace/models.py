"""
Trace Data Models (Dataset A: Observational Execution Traces)
Project: mcp-inventory-bench
Author: Anand S. Suchak

Defines fine-grained scientific records for MCP tool-calling execution traces,
per-attempt validation outcomes, schema exposure ledgers, and token accounting.
Conforms to MCP 2026-07-28 specification with Draft 2020-12 JSON Schema validation.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
import uuid
import time
import datetime

@dataclass
class ValidationErrorRecord:
    """Detailed record of a single JSON Schema validation error."""
    keyword: str                  # e.g., 'pattern', 'minimum', 'enum', 'required'
    path: str                     # e.g., '/vendor_id' or '/items/0/sku'
    message: str                  # Human-readable validator message
    schema_path: str              # Schema path, e.g., 'properties/vendor_id/pattern'
    failed_value: Any = None      # The argument value that triggered the violation

@dataclass
class SchemaExposureRecord:
    """Ledger entry tracking incremental schema fragment exposure to the model."""
    fragment: str                 # e.g., 'vendor_id.pattern', 'items.sku.format'
    tokens: int                   # Number of schema tokens contained in this fragment
    attempt: int                  # Attempt number where this fragment was exposed
    reason: str                   # e.g., 'INITIAL_LEVEL_1', 'PATTERN_MISMATCH', 'ENUM_VIOLATION'
    timestamp: float = field(default_factory=time.time)

@dataclass
class Attempt:
    """A single reasoning/invocation attempt within an execution trace."""
    attempt_number: int
    schema_fragments_exposed: List[str]
    schema_token_count: int
    model_response: str
    arguments: Dict[str, Any]
    validation_status: str        # 'SUCCESS' or 'FAIL'
    validation_errors: List[ValidationErrorRecord] = field(default_factory=list)
    latency_ms: float = 0.0
    response_id: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0

@dataclass
class Trace:
    """Complete observational execution trace for a single closed-loop task."""
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    timestamp: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    git_commit: str = ""
    prompt_version: str = "v1.0-level1-dynamic-repair"
    model: str = "gpt-4o-mini-mock"
    model_version: str = "2026-Q1"
    task_id: str = ""
    category: str = "Explicit valid inputs"
    user_intent: str = ""
    tool_name: str = ""
    schema_version: str = "2026-07-28/draft-2020-12"
    provenance: Dict[str, Any] = field(default_factory=dict)
    attempts: List[Attempt] = field(default_factory=list)
    schema_exposure_ledger: List[SchemaExposureRecord] = field(default_factory=list)
    total_schema_tokens_exposed: int = 0
    tokens_to_success: Optional[int] = None
    final_outcome: str = "PENDING"  # 'SUCCESS', 'FAIL', 'ABORTED'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trace":
        attempts_data = data.pop("attempts", [])
        ledger_data = data.pop("schema_exposure_ledger", [])

        attempts = []
        for a in attempts_data:
            errs_data = a.pop("validation_errors", [])
            errs = [ValidationErrorRecord(**e) for e in errs_data]
            attempts.append(Attempt(validation_errors=errs, **a))

        ledger = [SchemaExposureRecord(**item) for item in ledger_data]
        return cls(attempts=attempts, schema_exposure_ledger=ledger, **data)
