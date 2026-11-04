"""
Deterministic Schema Recomposer & Slicer with Wall-Clock Microsecond Instrumentation (Version 2.0)
Project: mcp-inventory-bench / Version 2.0
Author: Anand S. Suchak

Instruments schema slicing and AST tree merge functions with nanosecond precision
using time.perf_counter_ns(). Measures actual wall-clock execution time without I/O
or network overhead.
"""

from typing import Dict, Any, List, Tuple, Optional
import copy
import time
import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE))

from trace.recomposer import CONSTRAINT_INLINE_SPECS, get_nested_dict, extract_from_path, ensure_nested_item_structure
from trace.slicer import slice_constraint

def slice_constraint_timed(
    full_schema: Dict[str, Any],
    error_path: str,
    validator_keyword: str
) -> Tuple[Dict[str, Any], int]:
    """
    Measure exact wall-clock duration of extracting a minimal schema constraint delta.
    
    :return: (delta_dict, duration_ns)
    """
    t0 = time.perf_counter_ns()
    delta = slice_constraint(full_schema, error_path, validator_keyword)
    t1 = time.perf_counter_ns()
    return delta, (t1 - t0)

def recompose_schema_timed(
    base_schema: Dict[str, Any],
    constraint_ids: List[str],
    full_schema: Dict[str, Any]
) -> Tuple[Dict[str, Any], int, Dict[str, Any]]:
    """
    Structurally inline a list of constraint IDs directly into the native JSON Schema tree,
    measuring exact wall-clock nanosecond execution time.

    :param base_schema: Minimal base schema.
    :param constraint_ids: List of constraint IDs.
    :param full_schema: Ground-truth JSON Schema.
    :return: (recomposed_schema, total_duration_ns, metrics_breakdown)
    """
    t_start = time.perf_counter_ns()
    
    # Clone base schema
    t_clone_0 = time.perf_counter_ns()
    recomposed = copy.deepcopy(base_schema)
    t_clone_1 = time.perf_counter_ns()
    
    # Item structure check
    has_item_constraints = any(cid.startswith("items.") for cid in constraint_ids)
    if has_item_constraints:
        ensure_nested_item_structure(recomposed, full_schema)
    t_struct_1 = time.perf_counter_ns()

    merged_count = 0
    for cid in constraint_ids:
        if cid not in CONSTRAINT_INLINE_SPECS:
            continue
            
        spec = CONSTRAINT_INLINE_SPECS[cid]
        target_path = spec["target_path"]
        source_path = spec["source_path"]
        kw = spec["keyword"]

        # Fetch exact constraint value from full schema
        source_node = extract_from_path(full_schema, source_path)
        if not source_node or not isinstance(source_node, dict) or kw not in source_node:
            continue
        constraint_val = copy.deepcopy(source_node[kw])

        # Locate target dictionary in recomposed schema
        target_node = get_nested_dict(recomposed, target_path, create_missing=True)

        # Merge keyword directly in-tree
        target_node[kw] = constraint_val

        if "default" in source_node and "default" not in target_node:
            target_node["default"] = copy.deepcopy(source_node["default"])
            
        merged_count += 1

    t_end = time.perf_counter_ns()
    total_ns = t_end - t_start
    
    breakdown = {
        "clone_duration_ns": (t_clone_1 - t_clone_0),
        "structure_prep_ns": (t_struct_1 - t_clone_1),
        "merge_duration_ns": (t_end - t_struct_1),
        "total_duration_ns": total_ns,
        "total_duration_us": total_ns / 1000.0,
        "total_duration_ms": total_ns / 1_000_000.0,
        "constraints_merged": merged_count
    }
    
    return recomposed, total_ns, breakdown
