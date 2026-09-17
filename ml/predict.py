"""
RecoverAI - Prediction
=======================
Loads the persisted model pipeline and produces recoverability predictions
for new case(s). This is the module the FastAPI backend will import to
score incoming cases in real time.

Usage (CLI demo):
    python ml/predict.py
"""

from __future__ import annotations

import json
from typing import Any

import joblib
import pandas as pd

from common import ALL_FEATURES, FEATURE_META_PATH, MODEL_PATH

_model = None
_threshold = 0.5


def _ensure_loaded():
    global _model, _threshold
    if _model is None:
        _model = joblib.load(MODEL_PATH)
        try:
            with open(FEATURE_META_PATH) as f:
                meta = json.load(f)
            _threshold = float(meta.get("tuned_threshold", 0.5))
        except FileNotFoundError:
            _threshold = 0.5
    return _model, _threshold


def risk_level_from_probability(p: float) -> str:
    """Map a recoverability probability to a human-readable risk-of-loss level.

    Note: higher recoverable probability => LOWER risk of permanent revenue loss.
    """
    if p >= 0.7:
        return "low"
    if p >= 0.4:
        return "medium"
    return "high"


def predict_case(case: dict[str, Any]) -> dict[str, Any]:
    """Predict recoverability for a single case dict.

    `case` must contain (at least) all keys in ALL_FEATURES. Missing keys
    are imputed by the pipeline's imputers where possible, but required
    fields should generally be supplied by the caller.
    """
    model, threshold = _ensure_loaded()
    row = {feat: case.get(feat) for feat in ALL_FEATURES}
    df = pd.DataFrame([row])
    proba = float(model.predict_proba(df)[:, 1][0])
    label = int(proba >= threshold)
    return {
        "recoverable_probability": round(proba, 4),
        "recoverable_prediction": label,
        "risk_level": risk_level_from_probability(proba),
        "threshold_used": threshold,
    }


def predict_batch(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    model, threshold = _ensure_loaded()
    df = pd.DataFrame([{feat: c.get(feat) for feat in ALL_FEATURES} for c in cases])
    probas = model.predict_proba(df)[:, 1]
    results = []
    for p in probas:
        p = float(p)
        results.append(
            {
                "recoverable_probability": round(p, 4),
                "recoverable_prediction": int(p >= threshold),
                "risk_level": risk_level_from_probability(p),
                "threshold_used": threshold,
            }
        )
    return results


def _demo():
    sample_cases = [
        {
            "case_type": "failed_payment",
            "transaction_amount": 120.0,
            "customer_tenure_months": 36.0,
            "successful_payments_count": 30,
            "failed_payments_count": 1,
            "failure_frequency": 0.03,
            "payment_method": "credit_card",
            "gateway": "stripe",
            "customer_segment": "consumer",
            "invoice_or_subscription_age_days": 15,
            "checkout_value": 120.0,
            "previous_recovery_attempts": 0,
            "previous_recovery_success_rate": 0.9,
            "failure_reason": "card_expired",
        },
        {
            "case_type": "overdue_invoice",
            "transaction_amount": 45000.0,
            "customer_tenure_months": 4.0,
            "successful_payments_count": 1,
            "failed_payments_count": 3,
            "failure_frequency": 0.75,
            "payment_method": "bank_transfer",
            "gateway": "worldpay",
            "customer_segment": "enterprise",
            "invoice_or_subscription_age_days": 90,
            "checkout_value": 45000.0,
            "previous_recovery_attempts": 4,
            "previous_recovery_success_rate": 0.15,
            "failure_reason": "invoice_disputed",
        },
        {
            "case_type": "failed_subscription",
            "transaction_amount": 19.99,
            "customer_tenure_months": 2.0,
            "successful_payments_count": 1,
            "failed_payments_count": 2,
            "failure_frequency": 0.66,
            "payment_method": "debit_card",
            "gateway": "adyen",
            "customer_segment": "startup",
            "invoice_or_subscription_age_days": 30,
            "checkout_value": 19.99,
            "previous_recovery_attempts": 1,
            "previous_recovery_success_rate": 0.4,
            "failure_reason": "fraud_flag",
        },
    ]

    print("=" * 70)
    print("RecoverAI - Prediction Demo")
    print("=" * 70)
    for i, case in enumerate(sample_cases, start=1):
        result = predict_case(case)
        print(f"\nCase {i}: {case['case_type']} | reason={case['failure_reason']} | "
              f"amount=${case['transaction_amount']:,.2f} | segment={case['customer_segment']}")
        print(f"  -> recoverable_probability = {result['recoverable_probability']}")
        print(f"  -> prediction              = {'RECOVERABLE' if result['recoverable_prediction'] else 'NOT RECOVERABLE'}")
        print(f"  -> risk_level              = {result['risk_level']}")


if __name__ == "__main__":
    _demo()
