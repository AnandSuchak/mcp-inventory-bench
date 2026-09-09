"""
Deterministic Schema Recomposer
Project: mcp-inventory-bench
Author: Anand S. Suchak

Merges predicted or reactive constraint bundles directly in-tree into
a minimal base JSON Schema (e.g. Level-1C), producing standard, structurally valid
JSON Schema Draft 2020-12 specifications without external metadata dictionaries.
"""

from typing import Dict, Any, List, Tuple
import copy
import re

# Comprehensive metadata mapping constraint IDs to full schema locations and keywords
CONSTRAINT_INLINE_SPECS = {
    "warehouse_code.enum": {
        "target_path": ["properties", "warehouse_code"],
        "source_path": ["properties", "warehouse_code"],
        "keyword": "enum"
    },
    "authorized_by.pattern": {
        "target_path": ["properties", "authorized_by"],
        "source_path": ["properties", "authorized_by"],
        "keyword": "pattern"
    },
    "order_priority.enum": {
        "target_path": ["properties", "order_priority"],
        "source_path": ["properties", "order_priority"],
        "keyword": "enum"
    },
    "total_budget_limit.maximum": {
        "target_path": ["properties", "total_budget_limit"],
        "source_path": ["properties", "total_budget_limit"],
        "keyword": "maximum"
    },
    "total_budget_limit.minimum": {
        "target_path": ["properties", "total_budget_limit"],
        "source_path": ["properties", "total_budget_limit"],
        "keyword": "minimum"
    },
    "supplier_id.pattern": {
        "target_path": ["properties", "supplier_id"],
        "source_path": ["properties", "supplier_id"],
        "keyword": "pattern"
    },
    "items.minItems": {
        "target_path": ["properties", "items"],
        "source_path": ["properties", "items"],
        "keyword": "minItems"
    },
    "items.maxItems": {
        "target_path": ["properties", "items"],
        "source_path": ["properties", "items"],
        "keyword": "maxItems"
    },
    "items.required": {
        "target_path": ["properties", "items", "items"],
        "source_path": ["properties", "items", "items"],
        "keyword": "required"
    },
    "items.sku.pattern": {
        "target_path": ["properties", "items", "items", "properties", "sku"],
        "source_path": ["properties", "items", "items", "properties", "sku"],
        "keyword": "pattern"
    },
    "items.quantity.minimum": {
        "target_path": ["properties", "items", "items", "properties", "quantity"],
        "source_path": ["properties", "items", "items", "properties", "quantity"],
        "keyword": "minimum"
    },
    "items.quantity.maximum": {
        "target_path": ["properties", "items", "items", "properties", "quantity"],
        "source_path": ["properties", "items", "items", "properties", "quantity"],
        "keyword": "maximum"
    },
    "items.unit_cost.minimum": {
        "target_path": ["properties", "items", "items", "properties", "unit_cost"],
        "source_path": ["properties", "items", "items", "properties", "unit_cost"],
        "keyword": "minimum"
    }
}

def get_nested_dict(d: Dict[str, Any], path: List[str], create_missing: bool = True) -> Dict[str, Any]:
    """Traverse or create a nested dictionary path."""
    curr = d
    for step in path:
        if step not in curr:
            if create_missing:
                curr[step] = {}
            else:
                return {}
        curr = curr[step]
    return curr

def extract_from_path(d: Dict[str, Any], path: List[str]) -> Any:
    """Retrieve value at nested path."""
    curr = d
    for step in path:
        if not isinstance(curr, dict) or step not in curr:
            return None
        curr = curr[step]
    return curr

def ensure_nested_item_structure(base_schema: Dict[str, Any], full_schema: Dict[str, Any]) -> None:
    """
    Ensure array property 'items' has proper property types if items are referenced.
    When constraints inside items are requested, the base schema's items.items
    must include the basic property type definitions (sku: string, quantity: integer, unit_cost: number).
    """
    if "properties" in base_schema and "items" in base_schema["properties"]:
        items_def = base_schema["properties"]["items"]
        if items_def.get("type") == "array":
            if "items" not in items_def or not isinstance(items_def["items"], dict):
                items_def["items"] = {"type": "object"}
            
            # Ensure properties subdict exists
            if "properties" not in items_def["items"]:
                items_def["items"]["properties"] = {}
                
            full_item_props = extract_from_path(full_schema, ["properties", "items", "items", "properties"])
            if full_item_props and isinstance(full_item_props, dict):
                for p_name, p_val in full_item_props.items():
                    if p_name not in items_def["items"]["properties"]:
                        # Expose base type only (stripped)
                        items_def["items"]["properties"][p_name] = {"type": p_val.get("type", "string")}

def recompose_schema(
    base_schema: Dict[str, Any],
    constraint_ids: List[str],
    full_schema: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Structurally inline a list of constraint IDs directly into the native JSON Schema tree.

    :param base_schema: Minimal stripped schema (e.g. Level-1C).
    :param constraint_ids: List of constraint IDs (e.g. ['warehouse_code.enum', 'items.sku.pattern']).
    :param full_schema: Ground-truth Draft 2020-12 schema containing exact constraint definitions.
    :return: A clean, 100% standard Draft 2020-12 JSON Schema with constraints merged in-tree.
    """
    recomposed = copy.deepcopy(base_schema)
    
    # Check if any constraint targets nested items
    has_item_constraints = any(cid.startswith("items.") for cid in constraint_ids)
    if has_item_constraints:
        ensure_nested_item_structure(recomposed, full_schema)

    for cid in constraint_ids:
        if cid not in CONSTRAINT_INLINE_SPECS:
            continue
            
        spec = CONSTRAINT_INLINE_SPECS[cid]
        target_path = spec["target_path"]
        source_path = spec["source_path"]
        kw = spec["keyword"]

        # 1. Fetch exact constraint value from full schema
        source_node = extract_from_path(full_schema, source_path)
        if not source_node or not isinstance(source_node, dict) or kw not in source_node:
            continue
        constraint_val = copy.deepcopy(source_node[kw])

        # 2. Locate target dictionary in recomposed schema
        target_node = get_nested_dict(recomposed, target_path, create_missing=True)

        # 3. Merge keyword directly in-tree
        target_node[kw] = constraint_val

        # Also copy property description or default if it provides critical contextual guidance without leakage
        if "default" in source_node and "default" not in target_node:
            target_node["default"] = copy.deepcopy(source_node["default"])

    return recomposed
