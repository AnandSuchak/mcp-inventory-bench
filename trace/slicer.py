"""
Deterministic Schema Constraint Slicer
Project: mcp-inventory-bench
Author: Anand S. Suchak

Extracts minimal schema delta fragments based on JSON Schema validator errors.
Pure, deterministic function: No LLM, no network, no database dependencies.
"""

from typing import Dict, Any, List
import re

def estimate_tokens(obj: Any) -> int:
    """Accurate token count heuristic for schema fragments."""
    import json
    text = json.dumps(obj)
    words = len(re.findall(r'\w+|[^\w\s]', text))
    return max(1, words)

def _get_schema_property(properties: Dict[str, Any], key: str) -> Dict[str, Any]:
    """Retrieve property definition or empty dict."""
    return properties.get(key, {})

def slice_constraint(
    full_schema: Dict[str, Any],
    error_path: str,
    validator_keyword: str
) -> Dict[str, Any]:
    """
    Extract the minimal schema constraint delta corresponding to a validation error.

    :param full_schema: Complete Draft 2020-12 tool JSON Schema.
    :param error_path: JSON pointer path of error (e.g. '/vendor_id', '/items/0/sku', or '/').
    :param validator_keyword: JSON Schema keyword (e.g. 'pattern', 'minimum', 'enum', 'required').
    :return: Minimal sub-schema containing only the constraint violated.
    """
    if not full_schema:
        return {}

    # Normalize error path into tokens
    cleaned_path = error_path.strip("/")
    parts = [p for p in cleaned_path.split("/") if p] if cleaned_path else []

    # Special case: 'required' error at root or object level
    if validator_keyword == "required":
        if not parts:
            # Missing property at root level
            req_list = full_schema.get("required", [])
            return {"required": req_list}
        else:
            # Missing property in nested object
            curr = full_schema
            for p in parts:
                if p.isdigit():
                    curr = curr.get("items", {})
                else:
                    curr = curr.get("properties", {}).get(p, {})
            return {"required": curr.get("required", [])}

    # Traverse properties down the error path
    curr_schema = full_schema
    nested_path_keys = []

    for part in parts:
        if part.isdigit():
            # Array index: traverse into array items
            if curr_schema.get("type") == "array" and "items" in curr_schema:
                curr_schema = curr_schema["items"]
                nested_path_keys.append("__ARRAY_ITEMS__")
        else:
            # Object property
            props = curr_schema.get("properties", {})
            if part in props:
                curr_schema = props[part]
                nested_path_keys.append(part)
            else:
                # Property not directly under 'properties' (could be definitions/$defs)
                break

    # Extract the specific keyword constraint from curr_schema
    constraint_val = curr_schema.get(validator_keyword)
    if constraint_val is None:
        # Fallback: if keyword not found directly (e.g. type mismatch), return basic type
        constraint_val = curr_schema.get("type", "any")

    leaf_delta = {validator_keyword: constraint_val}

    # Reconstruct minimal nested hierarchy backwards
    result = leaf_delta
    for key in reversed(nested_path_keys):
        if key == "__ARRAY_ITEMS__":
            result = {"type": "array", "items": result}
        else:
            result = {key: result}

    return result

def format_fragment_identifier(error_path: str, validator_keyword: str) -> str:
    """Format human-readable schema exposure identifier, e.g. 'vendor_id.pattern'."""
    cleaned = error_path.strip("/").replace("/", ".")
    if cleaned:
        # Strip array indices like .0.
        cleaned = re.sub(r'\.\d+\.', '.', cleaned)
        cleaned = re.sub(r'\.\d+$', '', cleaned)
        return f"{cleaned}.{validator_keyword}"
    return validator_keyword

# ==============================================================================
# Experiment 2: Schema Budget Levels (1A, 1B, 1C, 1D) with Sanitized Descriptions
# Eliminates hidden-constraint leakage (e.g. no format or regex clues in text).
# ==============================================================================

SANITIZED_NEUTRAL_DESCRIPTIONS = {
    "supplier_id": "Identifier of the vendor or supplier.",
    "warehouse_code": "Code of the target distribution facility.",
    "order_priority": "Operational priority level of the replenishment request.",
    "total_budget_limit": "Maximum authorized financial expenditure.",
    "items": "Collection of line items to order.",
    "sku": "Unique product stock keeping unit code.",
    "quantity": "Number of units to replenish.",
    "unit_cost": "Agreed unit price per item.",
    "authorized_by": "Contact signature of the authorizing agent."
}

def create_schema_level_1a(full_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Level 1A: Property names + raw data types only (minimalist structural IDL)."""
    schema = {
        "title": full_schema.get("title", "tool"),
        "type": "object",
        "properties": {}
    }
    for prop, meta in full_schema.get("properties", {}).items():
        base_meta = {"type": meta.get("type", "string")}
        if meta.get("type") == "array":
            base_meta["items"] = {"type": "object"}
        schema["properties"][prop] = base_meta
    return schema

def create_schema_level_1b(full_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Level 1B: Property names + raw data types + sanitized constraint-neutral descriptions."""
    schema = create_schema_level_1a(full_schema)
    for prop in schema["properties"]:
        schema["properties"][prop]["description"] = SANITIZED_NEUTRAL_DESCRIPTIONS.get(prop, "Operational tool parameter.")
    return schema

def create_schema_level_1c(full_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Level 1C: Property names + raw data types + requiredness lists."""
    schema = create_schema_level_1a(full_schema)
    if "required" in full_schema:
        schema["required"] = list(full_schema["required"])
    return schema

def create_schema_level_1d(full_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Level 1D: Property names + raw data types + sanitized descriptions + requiredness lists."""
    schema = create_schema_level_1b(full_schema)
    if "required" in full_schema:
        schema["required"] = list(full_schema["required"])
    return schema

def create_invariant_schema(full_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Invariant Foundation (C_I):
    The minimal safe structural schema that is universally required for any syntactically
    valid tool call, regardless of task intent.

    Exposes:
    - Base properties, types, and top-level requiredness list
    - Format pattern for supplier_id
    - Format pattern for authorized_by
    - Array structure for items: object items with sku, quantity, unit_cost
    - Invariant: items.minItems = 1
    - Invariant: items.sku.pattern = '^SKU-[0-9]{5}$'
    - Invariant: items.quantity.minimum = 10
    - Invariant: items.items.required = ['sku', 'quantity', 'unit_cost']

    Leaves task-dependent constraints (warehouse_code.enum, order_priority.enum,
    total_budget_limit.maximum, etc.) to dynamic LASR resolution.
    """
    schema = {
        "$schema": full_schema.get("$schema", "https://json-schema.org/draft/2020-12/schema"),
        "title": full_schema.get("title", "create_purchase_order"),
        "type": "object",
        "properties": {
            "supplier_id": {
                "type": "string",
                "pattern": "^SUP-[A-Z0-9]{4,12}-[A-Z0-9]{3,6}$"
            },
            "warehouse_code": {"type": "string"},
            "order_priority": {"type": "string"},
            "total_budget_limit": {"type": "number"},
            "items": {
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "object",
                    "properties": {
                        "sku": {"type": "string", "pattern": "^SKU-[0-9]{5}$"},
                        "quantity": {"type": "integer", "minimum": 10},
                        "unit_cost": {"type": "number"}
                    },
                    "required": ["sku", "quantity", "unit_cost"]
                }
            },
            "authorized_by": {
                "type": "string",
                "pattern": "^[a-z]{3,8}\\.[a-z]{3,8}@enterprise\\.mock$"
            }
        },
        "required": list(full_schema.get("required", ["supplier_id", "warehouse_code", "items", "authorized_by"]))
    }
    return schema

