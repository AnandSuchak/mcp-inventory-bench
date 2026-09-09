"""
Unit tests for Pilot-2 Schema Budget Levels and Blinded Paraphraser
Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import pytest
from trace.slicer import (
    create_schema_level_1a,
    create_schema_level_1b,
    create_schema_level_1c,
    create_schema_level_1d,
    estimate_tokens
)
from trace.paraphraser import generate_pilot2_blinded_tasks
from trace.runner import FULL_PURCHASE_ORDER_SCHEMA

class TestSchemaBudgetLevels:
    """Validates that Schema Budget Levels 1A-1D enforce strict structural and leakage boundaries."""

    def test_level_1a_names_and_types_only(self):
        s1a = create_schema_level_1a(FULL_PURCHASE_ORDER_SCHEMA)
        assert "properties" in s1a
        assert "required" not in s1a
        for prop, meta in s1a["properties"].items():
            assert "type" in meta
            assert "description" not in meta
            assert "pattern" not in meta
            assert "enum" not in meta
            assert "minimum" not in meta

    def test_level_1b_sanitized_neutral_descriptions_no_leakage(self):
        s1b = create_schema_level_1b(FULL_PURCHASE_ORDER_SCHEMA)
        assert "properties" in s1b
        assert "required" not in s1b
        for prop, meta in s1b["properties"].items():
            assert "description" in meta
            desc = meta["description"]
            # Assert no regex or enum leakage strings in sanitized descriptions
            assert "SUP-" not in desc
            assert "WH-" not in desc
            assert "STANDARD" not in desc
            assert "format" not in desc.lower() or "SUP" not in desc

    def test_level_1c_names_types_and_requiredness(self):
        s1c = create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA)
        assert "required" in s1c
        assert set(s1c["required"]) == set(FULL_PURCHASE_ORDER_SCHEMA["required"])
        for prop, meta in s1c["properties"].items():
            assert "description" not in meta

    def test_level_1d_complete_baseline(self):
        s1d = create_schema_level_1d(FULL_PURCHASE_ORDER_SCHEMA)
        assert "required" in s1d
        for prop, meta in s1d["properties"].items():
            assert "description" in meta

    def test_monotonic_token_budget_growth(self):
        tok_1a = estimate_tokens(create_schema_level_1a(FULL_PURCHASE_ORDER_SCHEMA))
        tok_1b = estimate_tokens(create_schema_level_1b(FULL_PURCHASE_ORDER_SCHEMA))
        tok_1c = estimate_tokens(create_schema_level_1c(FULL_PURCHASE_ORDER_SCHEMA))
        tok_1d = estimate_tokens(create_schema_level_1d(FULL_PURCHASE_ORDER_SCHEMA))
        tok_full = estimate_tokens(FULL_PURCHASE_ORDER_SCHEMA)

        assert tok_1a < tok_1b
        assert tok_1a < tok_1c
        assert tok_1b < tok_1d
        assert tok_1d < tok_full

class TestBlindedParaphraser:
    """Validates the non-leaking, template-stratified split of blinded tasks."""

    def test_task_count_and_split_ratios(self):
        tasks = generate_pilot2_blinded_tasks()
        assert len(tasks) == 80
        train = [t for t in tasks if t.split == "train"]
        test = [t for t in tasks if t.split == "test"]
        assert len(train) == 48
        assert len(test) == 32

    def test_template_family_isolation_no_leakage(self):
        tasks = generate_pilot2_blinded_tasks()
        train_families = set(t.intent_family for t in tasks if t.split == "train")
        test_families = set(t.intent_family for t in tasks if t.split == "test")
        # Ensure zero overlap between template families across train and test
        assert len(train_families.intersection(test_families)) == 0

    def test_zero_category_label_leakage_in_prompts(self):
        tasks = generate_pilot2_blinded_tasks()
        for t in tasks:
            assert "CAT1" not in t.user_intent
            assert "ENUM" not in t.user_intent
            assert "REGEX" not in t.user_intent
            assert "VALID" not in t.user_intent
