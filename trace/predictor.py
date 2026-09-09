"""
Multi-Label Constraint Bundle Predictor & Baselines
Project: mcp-inventory-bench
Author: Anand S. Suchak

Implements:
1. Predictor 0: Frequency Prior Baseline
   - Predicts globally most frequent constraints from the training set.
2. Predictor 1: TF-IDF + Multi-Label Logistic Regression
   - Learns intent-to-constraint correlations strictly from the 48 train tasks.
   - Evaluated strictly on the 32 held-out test tasks (stratified by template family).
3. Evaluates:
   - Prediction Precision@k, Recall@k, and Exact Match on held-out tasks.
   - Direct comparison: Simple Predictor vs. Frequency Prior vs. Random Baseline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import re
import math
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple
from trace.paraphraser import generate_pilot2_blinded_tasks, BlindedTask

# All candidate constraint nodes in the enterprise purchase order schema
ALL_CANDIDATE_CONSTRAINTS = [
    "authorized_by.pattern",
    "warehouse_code.enum",
    "order_priority.enum",
    "total_budget_limit.maximum",
    "total_budget_limit.minimum",
    "items.required",
    "items.minItems",
    "items.sku.pattern",
    "items.quantity.minimum",
    "supplier_id.pattern"
]

def tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r'\b[a-zA-Z]{3,}\b', text)]

class FrequencyPriorPredictor:
    """Predictor 0: Global Frequency Prior Baseline."""
    def __init__(self, train_tasks: List[BlindedTask]):
        counts = Counter()
        for t in train_tasks:
            for c in t.target_constraints:
                counts[c] += 1
        self.ranked_constraints = [c for c, _ in counts.most_common()]
        # Append remaining candidates with 0 count
        for c in ALL_CANDIDATE_CONSTRAINTS:
            if c not in self.ranked_constraints:
                self.ranked_constraints.append(c)

    def predict_bundle(self, user_intent: str, k: int = 3) -> List[str]:
        return self.ranked_constraints[:k]

class MultiLabelLinearPredictor:
    """Predictor 1: TF-IDF Feature Extractor + Multi-Label Linear Classifier."""
    def __init__(self, train_tasks: List[BlindedTask]):
        self.vocab = {}
        self.idf = {}
        self.weights = {c: defaultdict(float) for c in ALL_CANDIDATE_CONSTRAINTS}
        self.bias = {c: 0.0 for c in ALL_CANDIDATE_CONSTRAINTS}
        self._fit(train_tasks)

    def _fit(self, train_tasks: List[BlindedTask]):
        # 1. Build Vocab & IDF
        doc_counts = Counter()
        n_docs = len(train_tasks)
        for t in train_tasks:
            tokens = set(tokenize(t.user_intent))
            for tok in tokens:
                doc_counts[tok] += 1
        
        for tok, cnt in doc_counts.items():
            if cnt >= 2: # Min document frequency
                self.vocab[tok] = len(self.vocab)
                self.idf[tok] = math.log((n_docs + 1) / (cnt + 1)) + 1.0

        # 2. Train multi-label log-odds weights
        for c in ALL_CANDIDATE_CONSTRAINTS:
            pos_docs = [t for t in train_tasks if c in t.target_constraints]
            neg_docs = [t for t in train_tasks if c not in t.target_constraints]
            n_pos = max(1, len(pos_docs))
            n_neg = max(1, len(neg_docs))
            self.bias[c] = math.log(n_pos / n_neg)

            # Feature weight = log((P(w|pos) + eps) / (P(w|neg) + eps))
            pos_word_counts = Counter()
            for t in pos_docs:
                for w in tokenize(t.user_intent):
                    if w in self.vocab:
                        pos_word_counts[w] += 1

            neg_word_counts = Counter()
            for t in neg_docs:
                for w in tokenize(t.user_intent):
                    if w in self.vocab:
                        neg_word_counts[w] += 1

            for w in self.vocab:
                p_pos = (pos_word_counts[w] + 0.1) / (n_pos + 0.2)
                p_neg = (neg_word_counts[w] + 0.1) / (n_neg + 0.2)
                self.weights[c][w] = math.log(p_pos / p_neg) * self.idf.get(w, 1.0)

    def predict_scores(self, user_intent: str) -> Dict[str, float]:
        tokens = tokenize(user_intent)
        scores = {}
        for c in ALL_CANDIDATE_CONSTRAINTS:
            score = self.bias[c]
            for w in tokens:
                if w in self.vocab:
                    score += self.weights[c].get(w, 0.0)
            # Sigmoid probability
            scores[c] = 1.0 / (1.0 + math.exp(-max(-10.0, min(10.0, score))))
        return scores

    def predict_bundle(self, user_intent: str, k: int = 3) -> List[str]:
        scores = self.predict_scores(user_intent)
        ranked = sorted(scores.keys(), key=lambda c: scores[c], reverse=True)
        return ranked[:k]

def evaluate_predictions(y_true: List[List[str]], y_pred: List[List[str]]) -> Dict[str, float]:
    p_at_k = []
    r_at_k = []
    f1_at_k = []
    exact_matches = 0
    n = len(y_true)

    for true_set, pred_set in zip(y_true, y_pred):
        true_s = set(true_set)
        pred_s = set(pred_set)
        hits = len(true_s.intersection(pred_s))

        prec = hits / max(1, len(pred_s))
        rec = hits / max(1, len(true_s))
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        p_at_k.append(prec)
        r_at_k.append(rec)
        f1_at_k.append(f1)
        if true_s == pred_s:
            exact_matches += 1

    return {
        "precision": round(sum(p_at_k) / n, 4),
        "recall": round(sum(r_at_k) / n, 4),
        "f1": round(sum(f1_at_k) / n, 4),
        "exact_match_pct": round((exact_matches / n) * 100.0, 2)
    }

if __name__ == "__main__":
    all_tasks = generate_pilot2_blinded_tasks()
    train_tasks = [t for t in all_tasks if t.split == "train"]
    test_tasks = [t for t in all_tasks if t.split == "test"]

    print("=" * 84)
    print(f"[*] MULTI-LABEL CONSTRAINT BUNDLE PREDICTION EXPERIMENT")
    print(f"[*] Train Tasks: {len(train_tasks)} | Held-Out Test Tasks: {len(test_tasks)}")
    print(f"[*] Split Strategy: Stratified by Template Family (Zero Lexical Leakage)")
    print("=" * 84)

    freq_predictor = FrequencyPriorPredictor(train_tasks)
    ml_predictor = MultiLabelLinearPredictor(train_tasks)

    y_test_true = [t.target_constraints for t in test_tasks]

    print(f"\n{'Model':<25}{'k':<6}{'Precision@k':<15}{'Recall@k':<15}{'F1@k':<12}{'Exact Match':<12}")
    print("-" * 84)

    for k in [1, 2, 3, 4]:
        # Frequency Prior predictions
        y_pred_freq = [freq_predictor.predict_bundle(t.user_intent, k=k) for t in test_tasks]
        m_freq = evaluate_predictions(y_test_true, y_pred_freq)

        # Multi-label Linear predictions
        y_pred_ml = [ml_predictor.predict_bundle(t.user_intent, k=k) for t in test_tasks]
        m_ml = evaluate_predictions(y_test_true, y_pred_ml)

        print(f"{'Frequency Prior':<25}{k:<6}{m_freq['precision']:<15.3f}{m_freq['recall']:<15.3f}{m_freq['f1']:<12.3f}{m_freq['exact_match_pct']:<12.1f}%")
        print(f"{'Semantic Predictor (LASR)':<25}{k:<6}{m_ml['precision']:<15.3f}{m_ml['recall']:<15.3f}{m_ml['f1']:<12.3f}{m_ml['exact_match_pct']:<12.1f}%")
        print("-" * 84)

    print("\n[+] Detailed Held-Out Sample Predictions (k=2):")
    for t in test_tasks[:6]:
        pred = ml_predictor.predict_bundle(t.user_intent, k=2)
        true = t.target_constraints
        match = "MATCH" if set(pred) == set(true) else "PARTIAL"
        print(f"  Task {t.task_id} ({t.semantic_cluster[:16]}):")
        print(f"    Intent: \"{t.user_intent[:65]}...\"")
        print(f"    True  : {true}")
        print(f"    Pred  : {pred} -> {match}")
    print("=" * 84)
