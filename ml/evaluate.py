
"""
RecoverAI - Model Evaluation
=============================
Reloads the persisted model pipeline, reproduces the exact same
train/val/test split used at training time (same random_state), and
reports full evaluation metrics on the held-out test set.

This script is intentionally independent from train.py so it can be run
any time to sanity-check a saved artifact without retraining.

Usage:
    python ml/evaluate.py
"""

from __future__ import annotations

import json

import joblib
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from common import FEATURE_META_PATH, METRICS_PATH, MODEL_PATH, load_dataset

RANDOM_STATE = 42


def main():
    print("=" * 70)
    print("RecoverAI - Model Evaluation")
    print("=" * 70)

    ds = load_dataset()
    X, y = ds.X, ds.y

    # reproduce the identical split used in train.py
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.4, stratify=y, random_state=RANDOM_STATE
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=RANDOM_STATE
    )

    try:
        pipe = joblib.load(MODEL_PATH)
    except FileNotFoundError:
        print(f"No trained model found at {MODEL_PATH}. Run `python ml/train.py` first.")
        return

    with open(FEATURE_META_PATH) as f:
        feature_meta = json.load(f)
    threshold = feature_meta.get("tuned_threshold", 0.5)

    test_proba = pipe.predict_proba(X_test)[:, 1]
    test_preds = (test_proba >= threshold).astype(int)

    print(f"Evaluating on held-out test set: {len(X_test):,} rows (threshold={threshold})\n")
    print("Classification report:")
    print(classification_report(y_test, test_preds, target_names=["not_recoverable", "recoverable"]))

    cm = confusion_matrix(y_test, test_preds)
    print("Confusion matrix (rows=true, cols=predicted):")
    print(f"                 pred_0   pred_1")
    print(f"  true_0(not rec)  {cm[0][0]:>6}   {cm[0][1]:>6}")
    print(f"  true_1(recover)  {cm[1][0]:>6}   {cm[1][1]:>6}")

    metrics = {
        "threshold": threshold,
        "accuracy": round(float(accuracy_score(y_test, test_preds)), 4),
        "precision": round(float(precision_score(y_test, test_preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, test_preds, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, test_preds, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_test, test_proba)), 4),
    }
    print("\nSummary metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    print(f"\n(Reference) metrics.json saved at train time -> {METRICS_PATH}")


if __name__ == "__main__":
    main()
