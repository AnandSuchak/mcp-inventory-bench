import copy
import pytest
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA
from trace.slicer import create_invariant_schema, format_fragment_identifier, estimate_tokens
from trace.recomposer import recompose_schema, CONSTRAINT_INLINE_SPECS
from trace.validator import SchemaValidator

def test_violated_constraint_extraction():
    validator = SchemaValidator(FULL_PURCHASE_ORDER_SCHEMA)
    mock_bad_args = {'supplier_id': 'SUP-ACME1234-US', 'warehouse_code': 'INVALID-WH-999', 'order_priority': 'standard', 'items': [{'sku': 'SKU-10001', 'quantity': 100, 'unit_cost': 5.0}], 'authorized_by': 'john.smith@enterprise.mock'}
    is_valid, errors = validator.validate(mock_bad_args)
    assert not is_valid
    violated_ids = {format_fragment_identifier(e.path, e.keyword) for e in errors}
    assert 'warehouse_code.enum' in violated_ids
    assert 'order_priority.enum' in violated_ids

def test_reactive_constraint_exact_once_addition():
    active_constraints = {'order_priority.enum'}
    raw_violated = ['warehouse_code.enum', 'warehouse_code.enum', 'unknown_field.format']
    new_constraints = set(raw_violated) & CONSTRAINT_INLINE_SPECS.keys() - active_constraints
    assert new_constraints == {'warehouse_code.enum'}
    active_constraints.update(new_constraints)
    assert active_constraints == {'order_priority.enum', 'warehouse_code.enum'}
    second_pass = set(raw_violated) & CONSTRAINT_INLINE_SPECS.keys() - active_constraints
    assert len(second_pass) == 0

def test_native_in_tree_schema_expansion():
    base_schema = create_invariant_schema(FULL_PURCHASE_ORDER_SCHEMA)
    assert 'enum' not in base_schema['properties']['warehouse_code']
    recomposed = recompose_schema(base_schema, ['warehouse_code.enum'], FULL_PURCHASE_ORDER_SCHEMA)
    assert 'enum' in recomposed['properties']['warehouse_code']
    assert recomposed['properties']['warehouse_code']['enum'] == ['WH-US-EAST', 'WH-US-WEST', 'WH-EU-CENTRAL', 'WH-APAC-SOUTH', 'WH-LATAM-NORTH']
    assert recomposed['properties']['supplier_id']['pattern'] == '^SUP-[A-Z0-9]{4,12}-[A-Z0-9]{3,6}$'

def test_unrelated_constraints_not_added():
    base_schema = create_invariant_schema(FULL_PURCHASE_ORDER_SCHEMA)
    recomposed = recompose_schema(base_schema, ['warehouse_code.enum'], FULL_PURCHASE_ORDER_SCHEMA)
    assert 'maximum' not in recomposed['properties']['total_budget_limit']
    assert 'enum' not in recomposed['properties']['order_priority']

def test_incremental_token_accounting():
    base_schema = create_invariant_schema(FULL_PURCHASE_ORDER_SCHEMA)
    s0 = estimate_tokens(base_schema)
    assert s0 == 339
    schema_t1 = recompose_schema(base_schema, ['warehouse_code.enum'], FULL_PURCHASE_ORDER_SCHEMA)
    s1 = estimate_tokens(schema_t1)
    delta_s1 = s1 - s0
    assert delta_s1 > 0
    assert s1 == s0 + delta_s1
    schema_t2 = recompose_schema(base_schema, ['warehouse_code.enum'], FULL_PURCHASE_ORDER_SCHEMA)
    s2 = estimate_tokens(schema_t2)
    delta_s2 = s2 - s1
    assert delta_s2 == 0

def test_recovery_idempotence_across_repeated_failures():
    active_constraints = {'order_priority.enum'}
    attempt1_errors = ['warehouse_code.enum']
    new_c1 = set(attempt1_errors) & CONSTRAINT_INLINE_SPECS.keys() - active_constraints
    assert new_c1 == {'warehouse_code.enum'}
    active_constraints.update(new_c1)
    
    # Attempt 2: identical failure repeats
    attempt2_errors = ['warehouse_code.enum']
    new_c2 = set(attempt2_errors) & CONSTRAINT_INLINE_SPECS.keys() - active_constraints
    assert len(new_c2) == 0
    assert active_constraints == {'order_priority.enum', 'warehouse_code.enum'}
    
    # Attempt 3: new distinct constraint violated
    attempt3_errors = ['total_budget_limit.maximum']
    new_c3 = set(attempt3_errors) & CONSTRAINT_INLINE_SPECS.keys() - active_constraints
    assert new_c3 == {'total_budget_limit.maximum'}
    active_constraints.update(new_c3)
    assert active_constraints == {'order_priority.enum', 'warehouse_code.enum', 'total_budget_limit.maximum'}
