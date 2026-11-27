"""Reproducible, local synthetic-only Isolation Forest for demo review flags."""
from collections import deque
from functools import lru_cache
from math import log1p, log2
from statistics import median

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.metrics import precision_recall_fscore_support, roc_auc_score, confusion_matrix

MODEL_VERSION = "isolation-forest-demo-v1"
FEATURE_NAMES = ("log2_amount_to_history", "log1p_amount_rupees", "prior_hour_count")
MIN_HISTORY = 4
MAX_HISTORY = 30
MAX_FLAGS = 10

def vector(amount_minor, median_minor, prior_hour_count):
    if amount_minor <= 0 or median_minor <= 0 or prior_hour_count < 0:
        raise ValueError("Positive expense amounts and nonnegative counts required")
    return (log2(amount_minor / median_minor), log1p(amount_minor / 100),
            min(prior_hour_count, 100))

def synthetic(seed, normal_count, anomalous_count=0):
    """Independent synthetic examples, not real or labeled fraud data.

    Normal purchases vary by typical spend and frequency. Injected scenarios
    include unusually large purchases, bursts and a combination. Distributions
    overlap; labels describe the generator, not real fraud.
    """
    rng = np.random.default_rng(seed)
    x, y = [], []
    for i in range(normal_count + anomalous_count):
        anomalous = i >= normal_count
        baseline = max(100, int(rng.lognormal(np.log(35000), .8)))
        ratio = rng.lognormal(0, .55)
        count = int(rng.poisson(1.8))
        if anomalous:
            scenario = i % 3
            if scenario in (0, 2):
                ratio *= rng.uniform(3, 10)
            if scenario in (1, 2):
                count += int(rng.integers(5, 15))
        amount = max(1, round(baseline * ratio))
        x.append(vector(amount, baseline, count))
        y.append(int(anomalous))
    return np.asarray(x, dtype=float), np.asarray(y, dtype=int)

@lru_cache(maxsize=1)
def trained_model():
    features, _ = synthetic(1701, 2400)
    return IsolationForest(n_estimators=96, max_samples=256, contamination=.05,
                           random_state=1701, n_jobs=1).fit(features)

def evaluate():
    # A different seed and independent generated observations, never training rows.
    features, truth = synthetic(2701, 900, 150)
    model = trained_model()
    score = -model.decision_function(features)
    predicted = (score > 0).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        truth, predicted, average="binary", zero_division=0)
    tn, fp, fn, tp = confusion_matrix(truth, predicted, labels=[0, 1]).ravel()
    return {"model_version": MODEL_VERSION, "training_normal_examples": 2400,
            "evaluation_normal_examples": 900, "evaluation_injected_examples": 150,
            "precision": round(float(precision), 4), "recall": round(float(recall), 4),
            "f1": round(float(f1), 4), "roc_auc": round(float(roc_auc_score(truth, score)), 4),
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
            "synthetic_only": True}

def feature_rows(expenses):
    """Chronological outgoing expenses from one owner, with no future leakage.

    Entries sharing a timestamp are scored against the same strictly earlier
    history. The stable input order determines which older entries survive the
    rolling 30-entry baseline. A one-hour deque counts strictly earlier entries.
    """
    history = deque(maxlen=MAX_HISTORY)
    recent = deque()
    batch = []
    timestamp = None

    def process():
        if not batch:
            return []
        while recent and recent[0] < timestamp-3600:
            recent.popleft()
        result = []
        if len(history) >= MIN_HISTORY:
            typical = median(history)
            for row in batch:
                amount = row["amount_minor"]
                result.append((row, vector(amount, typical, len(recent)),
                               amount/typical, len(recent)))
        for row in batch:
            history.append(row["amount_minor"])
            recent.append(timestamp)
        return result

    for row in expenses:
        current = row["created_at"]
        if timestamp is not None and current < timestamp:
            raise ValueError("Expense history must be chronological")
        if timestamp is not None and current != timestamp:
            yield from process()
            batch.clear()
        timestamp = current
        batch.append(row)
    yield from process()

def review(expenses):
    model = None
    flags = deque(maxlen=MAX_FLAGS)
    evaluated = total_flags = 0
    batch = []

    def score_batch():
        nonlocal model, evaluated, total_flags
        if not batch:
            return
        if model is None:
            model = trained_model()
        scores = -model.decision_function([entry[1] for entry in batch])
        for (row, _, ratio, count), score in zip(batch, scores):
            evaluated += 1
            if score <= 0:
                continue
            total_flags += 1
            flags.append({"transaction_id": row["id"], "amount_minor": row["amount_minor"],
                          "model_version": MODEL_VERSION, "method": "isolation-forest",
                          "anomaly_score": round(float(score), 6),
                          "amount_to_prior_median": round(ratio, 2),
                          "prior_hour_expense_count": count,
                          "reason": "Unusual combination of amount and recent expense frequency",
                          "fraud_confirmed": False})
        batch.clear()

    for entry in feature_rows(expenses):
        batch.append(entry)
        if len(batch) >= 256:
            score_batch()
    score_batch()
    return {"model_version": MODEL_VERSION, "training_data": "synthetic",
            "status": "evaluated" if evaluated else "insufficient_history",
            "evaluated_count": evaluated, "flagged_count": total_flags,
            "flags": list(reversed(flags)),
            "note": "Review only. Scores are not fraud probabilities or proof of fraud."}
