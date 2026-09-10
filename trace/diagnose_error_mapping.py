"""
Diagnostic test to inspect error messages on C3 tasks under ci_k1 and ci_k2
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from trace.paraphraser import generate_pilot2_blinded_tasks
from trace.validator import SchemaValidator
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.slicer import create_invariant_schema
from trace.recomposer import recompose_schema
from trace.slicer import format_fragment_identifier

tasks = [t for t in generate_pilot2_blinded_tasks() if t.split == "test" and t.semantic_cluster == "specialized_bulk_procurement"][:2]
base = create_invariant_schema(FULL_PURCHASE_ORDER_SCHEMA)
validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)

# Let's inspect a mock failed attempt typical of C3
mock_bad_args = {
    "supplier_id": "SUP-ACME1234-US",
    "warehouse_code": "WH-EAST-01",
    "order_priority": "standard",
    "items": [{"sku": "SKU-10001", "quantity": 100, "unit_cost": 5.0}],
    "authorized_by": "john.smith@enterprise.mock"
}

is_valid, errors = validator.validate(mock_bad_args)
print("Validation errors:")
for e in errors:
    frag = format_fragment_identifier(e.path, e.keyword)
    print(f"  Path: {e.path} | Keyword: {e.keyword} | Frag: {frag} | Msg: {e.message}")
