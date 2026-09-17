"""
RecoverAI - Rule-Based Baseline
=================================
A simple, fully deterministic, hand-crafted set of business rules for
predicting whether a case is recoverable. This exists so we have an
honest baseline to compare the ML model against — "is the ML model
actually earning its complexity, or would a spreadsheet of if/else rules
do just as well?"

The rules encode obvious domain heuristics an ops team might already use:
  - Known high-risk failure reasons (fraud, disputes, bank cancellation,
    unresponsive customer) => NOT recoverable
  - A customer with a high historical failure frequency => NOT recoverable
  - A customer who has already had several failed recovery attempts on
    this case => NOT recoverable (diminishing returns)
  - A very large transaction with a low prior recovery success rate =>
    NOT recoverable (too risky to keep retrying blind)
  - Otherwise => recoverable

This script:
  1. Reproduces the exact same test split used in train.py/evaluate.py
  2. Applies the rule baseline to the test set
  3. Loads the persisted ML model and scores the same test set
  4. Compares both on standard ML metrics (accuracy/precision/recall/F1/ROC-AUC*)
  5. Compares both on business metrics (dollars correctly identified as
     recoverable, dollars of recoverable revenue missed, dollars wasted
     chasing unrecoverable cases)

  * ROC-AUC needs a continuous score; the rule baseline is binary, so we
    report ROC-AUC for the ML model only and note this explicitly.

Usage:
    python ml/rule_baseline.py
"""

from __future__ import annotations

import json

import joblib
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split

from common import FEATURE_META_PATH, MODEL_PATH, load_dataset

RANDOM_STATE = 42

HIGH_RISK_FAILURE_REASONS = {
    "fraud_flag",
    "invoice_disputed",
    "subscription_cancelled_by_bank",
    "customer_unresponsive",
}

HIGH_FAILURE_FREQUENCY_THRESHOLD = 0.5
MAX_PRIOR_ATTEMPTS_BEFORE_GIVING_UP = 3
LARGE_TRANSACTION_THRESHOLD = 10_000.0
LOW_PRIOR_SUCCESS_RATE_THRESHOLD = 0.3


def rule_based_predict_row(row: pd.Series) -> int:
    """Return 1 (recoverable) or 0 (not recoverable) using deterministic rules."""
    if row["failure_reason"] in HIGH_RISK_FAILURE_REASONS:
        return 0
    if row["failure_frequency"] > HIGH_FAILURE_FREQUENCY_THRESHOLD:
        return 0
    if row["previous_recovery_attempts"] >= MAX_PRIOR_ATTEMPTS_BEFORE_GIVING_UP:
        return 0
    if (
        row["transaction_amount"] > LARGE_TRANSACTION_THRESHOLD
        and row["previous_recovery_success_rate"] < LOW_PRIOR_SUCCESS_RATE_THRESHOLD
    ):
        return 0
    return 1


def rule_based_predict(df: pd.DataFrame) -> pd.Series:
    return df.apply(rule_based_predict_row, axis=1)


def ml_metrics(y_true, y_pred, y_proba=None) -> dict:
    metrics = {
        "accuracy": round(float(accuracy_score(y_true, y_pred)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
    }
    if y_proba is not None:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_proba)), 4)
    cm = confusion_matrix(y_true, y_pred).tolist()
    metrics["confusion_matrix"] = {"labels": ["not_recoverable(0)", "recoverable(1)"], "matrix": cm}
    return metrics


def business_metrics(df_test: pd.DataFrame, y_true, y_pred, amount_col: str = "transaction_amount") -> dict:
    """Translate classification outcomes into dollar terms.

    - correctly_flagged_recoverable_value: $ the system would correctly
      prioritize for recovery action (true positives)
    - missed_recoverable_value: $ left on the table because the system
      wrongly said "not recoverable" (false negatives) — the costliest
      type of error for a revenue-recovery system
    - wasted_effort_value: $ of cases the system would chase that were
      never actually recoverable (false positives) — wasted ops/agent effort
    - correctly_skipped_value: $ correctly identified as not worth chasing
      (true negatives)
    """
    amounts = df_test[amount_col].values
    y_true = pd.Series(y_true).reset_index(drop=True)
    y_pred = pd.Series(y_pred).reset_index(drop=True)
    amounts = pd.Series(amounts).reset_index(drop=True)

    tp_mask = (y_true == 1) & (y_pred == 1)
    fn_mask = (y_true == 1) & (y_pred == 0)
    fp_mask = (y_true == 0) & (y_pred == 1)
    tn_mask = (y_true == 0) & (y_pred == 0)

    return {
        "correctly_flagged_recoverable_value": round(float(amounts[tp_mask].sum()), 2),
        "missed_recoverable_value": round(float(amounts[fn_mask].sum()), 2),
        "wasted_effort_value": round(float(amounts[fp_mask].sum()), 2),
        "correctly_skipped_value": round(float(amounts[tn_mask].sum()), 2),
        "total_test_set_value": round(float(amounts.sum()), 2),
    }


def print_metrics_block(title: str, ml: dict, biz: dict):
    print(f"\n--- {title} ---")
    print(f"  Accuracy:  {ml['accuracy']}")
    print(f"  Precision: {ml['precision']}")
    print(f"  Recall:    {ml['recall']}")
    print(f"  F1:        {ml['f1']}")
    if "roc_auc" in ml:
        print(f"  ROC-AUC:   {ml['roc_auc']}")
    cm = ml["confusion_matrix"]["matrix"]
    print(f"  Confusion matrix (rows=true, cols=pred): {cm}")
    print(f"  Business impact ($ of test-set transaction value):")
    print(f"    Correctly flagged recoverable (true positives):  ${biz['correctly_flagged_recoverable_value']:,.2f}")
    print(f"    Missed recoverable revenue (false negatives):    ${biz['missed_recoverable_value']:,.2f}")
    print(f"    Wasted effort on unrecoverable (false positives):${biz['wasted_effort_value']:,.2f}")
    print(f"    Correctly skipped (true negatives):              ${biz['correctly_skipped_value']:,.2f}")


def main():
    print("=" * 70)
    print("RecoverAI - Rule-Based Baseline vs ML Model")
    print("=" * 70)

    ds = load_dataset()
    X, y = ds.X, ds.y
    raw = ds.raw

    # reproduce the identical split used in train.py / evaluate.py
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.4, stratify=y, random_state=RANDOM_STATE
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, stratify=y_temp, random_state=RANDOM_STATE
    )
    # transaction_amount for business metrics, aligned to the same test rows
    test_amounts = raw.loc[X_test.index, ["transaction_amount"]]

    print(f"Test set: {len(X_test):,} cases | total value at risk: ${test_amounts['transaction_amount'].sum():,.2f}\n")

    # ---------------- rule-based baseline ----------------
    rule_preds = rule_based_predict(X_test)
    rule_ml_metrics = ml_metrics(y_test, rule_preds)  # no proba -> no ROC-AUC
    rule_biz_metrics = business_metrics(test_amounts, y_test, rule_preds)
    print_metrics_block("RULE-BASED BASELINE", rule_ml_metrics, rule_biz_metrics)

    # ---------------- ML model ----------------
    try:
        pipe = joblib.load(MODEL_PATH)
    except FileNotFoundError:
        print(f"\nNo trained model found at {MODEL_PATH}. Run `python ml/train.py` first.")
        return

    with open(FEATURE_META_PATH) as f:
        feature_meta = json.load(f)
    threshold = feature_meta.get("tuned_threshold", 0.5)

    ml_proba = pipe.predict_proba(X_test)[:, 1]
    ml_preds = (ml_proba >= threshold).astype(int)
    ml_metrics_result = ml_metrics(y_test, ml_preds, ml_proba)
    ml_biz_metrics = business_metrics(test_amounts, y_test, ml_preds)
    print_metrics_block(f"ML MODEL (threshold={threshold})", ml_metrics_result, ml_biz_metrics)

    # ---------------- head-to-head summary ----------------
    print("\n" + "=" * 70)
    print("HEAD-TO-HEAD SUMMARY")
    print("=" * 70)
    print(f"{'Metric':<40}{'Rule Baseline':>15}{'ML Model':>15}")
    for key, label in [
        ("accuracy", "Accuracy"),
        ("precision", "Precision"),
        ("recall", "Recall"),
        ("f1", "F1"),
    ]:
        print(f"{label:<40}{rule_ml_metrics[key]:>15}{ml_metrics_result[key]:>15}")
    print(f"{'ROC-AUC (ML only, needs probability)':<40}{'n/a':>15}{ml_metrics_result['roc_auc']:>15}")

    print()
    delta_missed = rule_biz_metrics["missed_recoverable_value"] - ml_biz_metrics["missed_recoverable_value"]
    delta_wasted = rule_biz_metrics["wasted_effort_value"] - ml_biz_metrics["wasted_effort_value"]
    print(f"{'Missed recoverable revenue ($)':<40}{rule_biz_metrics['missed_recoverable_value']:>15,.2f}{ml_biz_metrics['missed_recoverable_value']:>15,.2f}")
    print(f"{'Wasted effort value ($)':<40}{rule_biz_metrics['wasted_effort_value']:>15,.2f}{ml_biz_metrics['wasted_effort_value']:>15,.2f}")
    print()
    if delta_missed > 0:
        print(f"-> ML model recovers ${delta_missed:,.2f} more in previously-missed revenue than the rule baseline.")
    elif delta_missed < 0:
        print(f"-> Rule baseline recovers ${-delta_missed:,.2f} more in previously-missed revenue than the ML model.")
    else:
        print("-> Both approaches miss the same amount of recoverable revenue.")

    if delta_wasted > 0:
        print(f"-> ML model wastes ${delta_wasted:,.2f} LESS effort chasing unrecoverable cases than the rule baseline.")
    elif delta_wasted < 0:
        print(f"-> ML model wastes ${-delta_wasted:,.2f} MORE effort chasing unrecoverable cases than the rule baseline.")
    else:
        print("-> Both approaches waste the same amount of effort.")

    # persist comparison for the analytics API / dashboard to consume later
    comparison_payload = {
        "test_rows": int(len(X_test)),
        "test_set_total_value": round(float(test_amounts["transaction_amount"].sum()), 2),
        "rule_based": {"metrics": rule_ml_metrics, "business": rule_biz_metrics},
        "ml_model": {
            "threshold": threshold,
            "metrics": ml_metrics_result,
            "business": ml_biz_metrics,
        },
    }
    from common import ARTIFACTS_DIR
    import os

    out_path = os.path.join(ARTIFACTS_DIR, "baseline_comparison.json")
    with open(out_path, "w") as f:
        json.dump(comparison_payload, f, indent=2)
    print(f"\nSaved comparison payload -> {out_path}")


if __name__ == "__main__":
    main()