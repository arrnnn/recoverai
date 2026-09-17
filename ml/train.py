"""
RecoverAI - Model Training
===========================
Trains a recoverability classifier (probability that a failed-payment /
abandoned-checkout / failed-subscription / overdue-invoice case can be
recovered).

Pipeline:
    1. Load synthetic dataset (data/cases.csv)
    2. Split train / validation / test (60/20/20), stratified on target
    3. Fit preprocessing + Logistic Regression (primary/interpretable model)
    4. Fit Random Forest and Gradient Boosting as comparison candidates
    5. Select the best model on validation ROC-AUC
    6. Tune the decision threshold on validation set (maximize F1)
    7. Final evaluation on the held-out test set
    8. Persist: model pipeline (.joblib), metrics.json, feature_meta.json

Usage:
    python ml/train.py
"""

from __future__ import annotations

import json
import time

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from common import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    FEATURE_META_PATH,
    METRICS_PATH,
    MODEL_PATH,
    NUMERIC_FEATURES,
    build_preprocessor,
    load_dataset,
)

RANDOM_STATE = 42


def make_candidates() -> dict:
    return {
        "logistic_regression": LogisticRegression(
            max_iter=2000, class_weight="balanced", random_state=RANDOM_STATE
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=300,
            max_depth=10,
            min_samples_leaf=5,
            class_weight="balanced",
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "gradient_boosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=3, learning_rate=0.08, random_state=RANDOM_STATE
        ),
    }


def find_best_threshold(y_true, y_proba) -> tuple[float, float]:
    """Scan thresholds and return the one maximizing F1 (and that F1)."""
    best_t, best_f1 = 0.5, -1.0
    for t in np.arange(0.05, 0.96, 0.01):
        preds = (y_proba >= t).astype(int)
        f1 = f1_score(y_true, preds, zero_division=0)
        if f1 > best_f1:
            best_f1, best_t = f1, t
    return round(float(best_t), 2), round(float(best_f1), 4)


def evaluate_at_threshold(y_true, y_proba, threshold: float) -> dict:
    preds = (y_proba >= threshold).astype(int)
    cm = confusion_matrix(y_true, preds).tolist()
    return {
        "threshold": threshold,
        "accuracy": round(float(accuracy_score(y_true, preds)), 4),
        "precision": round(float(precision_score(y_true, preds, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, preds, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, preds, zero_division=0)), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_proba)), 4),
        "confusion_matrix": {
            "labels": ["not_recoverable(0)", "recoverable(1)"],
            "matrix": cm,  # rows = true, cols = predicted
        },
    }


def main():
    print("=" * 70)
    print("RecoverAI - Model Training")
    print("=" * 70)

    ds = load_dataset()
    X, y = ds.X, ds.y
    print(f"Loaded dataset: {X.shape[0]:,} rows, {X.shape[1]} features")
    print(f"Target balance -> recoverable=1: {y.mean():.3f}, recoverable=0: {1 - y.mean():.3f}")

    # 60 / 20 / 20 stratified split
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.4, stratify=y, random_state=RANDOM_STATE
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=RANDOM_STATE
    )
    print(f"Split -> train: {len(X_train):,} | val: {len(X_val):,} | test: {len(X_test):,}")

    preprocessor = build_preprocessor()
    candidates = make_candidates()

    results = {}
    fitted_pipelines = {}

    for name, estimator in candidates.items():
        t0 = time.time()
        pipe = Pipeline(steps=[("preprocessor", preprocessor), ("classifier", estimator)])
        pipe.fit(X_train, y_train)
        val_proba = pipe.predict_proba(X_val)[:, 1]
        val_auc = roc_auc_score(y_val, val_proba)
        elapsed = time.time() - t0
        results[name] = {"val_roc_auc": round(float(val_auc), 4), "train_seconds": round(elapsed, 2)}
        fitted_pipelines[name] = pipe
        print(f"  [{name}] val ROC-AUC = {val_auc:.4f}  (fit in {elapsed:.2f}s)")

        # IMPORTANT: rebuild a fresh (unfitted) preprocessor per model so pipelines
        # don't share fitted transformer state across candidates.
        preprocessor = build_preprocessor()

    best_name = max(results, key=lambda k: results[k]["val_roc_auc"])
    best_pipe = fitted_pipelines[best_name]
    print(f"\nBest candidate by validation ROC-AUC: {best_name}")

    # threshold tuning on validation set using the best model
    val_proba_best = best_pipe.predict_proba(X_val)[:, 1]
    best_threshold, best_val_f1 = find_best_threshold(y_val, val_proba_best)
    print(f"Tuned decision threshold (max F1 on val): {best_threshold} (val F1={best_val_f1})")

    # refit best model on train+val for the final artifact (common practice:
    # test set remains untouched for the final unbiased evaluation)
    X_trainval = np.vstack([X_train.values, X_val.values]) if False else None  # keep pandas types
    import pandas as pd  # local import to avoid top clutter

    X_trainval = pd.concat([X_train, X_val], axis=0)
    y_trainval = pd.concat([y_train, y_val], axis=0)

    final_preprocessor = build_preprocessor()
    final_estimator = make_candidates()[best_name]
    final_pipe = Pipeline(steps=[("preprocessor", final_preprocessor), ("classifier", final_estimator)])
    final_pipe.fit(X_trainval, y_trainval)

    # final unbiased evaluation on the held-out test set
    test_proba = final_pipe.predict_proba(X_test)[:, 1]
    test_metrics = evaluate_at_threshold(y_test, test_proba, best_threshold)
    print("\nFinal TEST SET metrics (best model, tuned threshold):")
    for k, v in test_metrics.items():
        if k != "confusion_matrix":
            print(f"  {k}: {v}")
    print(f"  confusion_matrix: {test_metrics['confusion_matrix']}")

    # also report metrics at default 0.5 threshold for transparency
    test_metrics_default = evaluate_at_threshold(y_test, test_proba, 0.5)

    # persist model
    joblib.dump(final_pipe, MODEL_PATH)
    print(f"\nSaved model pipeline -> {MODEL_PATH}")

    metrics_payload = {
        "model_selected": best_name,
        "candidate_comparison": results,
        "tuned_threshold": best_threshold,
        "val_f1_at_tuned_threshold": best_val_f1,
        "test_metrics_tuned_threshold": test_metrics,
        "test_metrics_default_threshold_0.5": test_metrics_default,
        "train_rows": int(len(X_train)),
        "val_rows": int(len(X_val)),
        "test_rows": int(len(X_test)),
        "trained_on_rows_final_fit": int(len(X_trainval)),
        "random_state": RANDOM_STATE,
    }
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics_payload, f, indent=2)
    print(f"Saved metrics -> {METRICS_PATH}")

    feature_meta = {
        "numeric_features": NUMERIC_FEATURES,
        "categorical_features": CATEGORICAL_FEATURES,
        "all_features": ALL_FEATURES,
        "target": "recoverable",
        "tuned_threshold": best_threshold,
    }
    with open(FEATURE_META_PATH, "w") as f:
        json.dump(feature_meta, f, indent=2)
    print(f"Saved feature metadata -> {FEATURE_META_PATH}")

    print("\nDone.")


if __name__ == "__main__":
    main()
