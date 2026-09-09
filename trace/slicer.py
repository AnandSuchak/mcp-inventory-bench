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
