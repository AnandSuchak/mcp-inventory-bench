"""
Unit tests for Multi-Label Constraint Bundle Predictor
Project: mcp-inventory-bench
Author: Anand S. Suchak
"""

import pytest
from trace.paraphraser import generate_pilot2_blinded_tasks
from trace.predictor import FrequencyPriorPredictor, MultiLabelLinearPredictor, evaluate_predictions

class TestPredictors:
    def test_frequency_prior_baseline(self):
        all_tasks = generate_pilot2_blinded_tasks()
        train_tasks = [t for t in all_tasks if t.split == "train"]
        test_tasks = [t for t in all_tasks if t.split == "test"]

        freq = FrequencyPriorPredictor(train_tasks)
        pred = freq.predict_bundle("Restock warehouse east", k=2)
        assert len(pred) == 2
        assert isinstance(pred, list)

    def test_semantic_predictor_beats_frequency_prior(self):
        all_tasks = generate_pilot2_blinded_tasks()
        train_tasks = [t for t in all_tasks if t.split == "train"]
        test_tasks = [t for t in all_tasks if t.split == "test"]

        freq = FrequencyPriorPredictor(train_tasks)
        ml = MultiLabelLinearPredictor(train_tasks)

        y_true = [t.target_constraints for t in test_tasks]
        y_pred_freq = [freq.predict_bundle(t.user_intent, k=2) for t in test_tasks]
        y_pred_ml = [ml.predict_bundle(t.user_intent, k=2) for t in test_tasks]

        eval_freq = evaluate_predictions(y_true, y_pred_freq)
        eval_ml = evaluate_predictions(y_true, y_pred_ml)

        # Assert Semantic Predictor decisively outperforms Frequency Prior
        assert eval_ml["precision"] > eval_freq["precision"]
        assert eval_ml["recall"] > eval_freq["recall"]
        assert eval_ml["f1"] > eval_freq["f1"]
        assert eval_ml["f1"] >= 0.80
        assert eval_freq["f1"] <= 0.35
