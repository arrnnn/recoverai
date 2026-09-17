"""
RecoverAI - Analytics Queries
===============================
Aggregates data from two sources:
  1. The database (real, live case/recovery data your agent has generated)
  2. ml/artifacts/*.json (metrics.json and baseline_comparison.json, written
     by ml/train.py and ml/rule_baseline.py — the ML model's own measured
     performance, not re-derived here)
"""

from __future__ import annotations

import json
import os

from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Case, RecoveryAction

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ML_ARTIFACTS_DIR = os.path.join(_PROJECT_ROOT, "ml", "artifacts")
_METRICS_PATH = os.path.join(_ML_ARTIFACTS_DIR, "metrics.json")
_BASELINE_COMPARISON_PATH = os.path.join(_ML_ARTIFACTS_DIR, "baseline_comparison.json")


def get_summary(db: Session) -> dict:
    total_cases = db.query(func.count(Case.id)).scalar() or 0

    revenue_at_risk = (
        db.query(func.coalesce(func.sum(Case.transaction_amount), 0.0))
        .filter(Case.status.in_(["NEW", "ANALYZED"]))
        .scalar()
    )
    revenue_recovered = (
        db.query(func.coalesce(func.sum(RecoveryAction.recovered_amount), 0.0))
        .filter(RecoveryAction.recovery_status == "SUCCESS")
        .scalar()
    )

    resolved_actions = (
        db.query(RecoveryAction)
        .filter(RecoveryAction.recovery_status.in_(["SUCCESS", "FAILED"]))
        .all()
    )
    successful = sum(1 for a in resolved_actions if a.recovery_status == "SUCCESS")
    recovery_rate = round(successful / len(resolved_actions), 4) if resolved_actions else 0.0

    high_risk_cases = (
        db.query(func.count(Case.id))
        .join(Case.predictions)
        .filter(Case.predictions.any(risk_level="high"))
        .scalar()
        or 0
    )
    escalated_cases = (
        db.query(func.count(RecoveryAction.id))
        .filter(RecoveryAction.recovery_status == "ESCALATED")
        .scalar()
        or 0
    )

    return {
        "total_cases": total_cases,
        "revenue_at_risk_usd": round(float(revenue_at_risk or 0.0), 2),
        "revenue_recovered_usd": round(float(revenue_recovered or 0.0), 2),
        "recovery_rate": recovery_rate,
        "high_risk_cases": high_risk_cases,
        "successful_recoveries": successful,
        "escalated_cases": escalated_cases,
    }


def get_model_performance() -> dict:
    if not os.path.exists(_METRICS_PATH):
        return {
            "model_selected": "unknown",
            "test_metrics": {},
            "candidate_comparison": {},
            "note": "Run `python ml/train.py` to generate metrics.json.",
        }
    with open(_METRICS_PATH) as f:
        metrics = json.load(f)
    return {
        "model_selected": metrics.get("model_selected", "unknown"),
        "test_metrics": metrics.get("test_metrics_tuned_threshold", {}),
        "candidate_comparison": metrics.get("candidate_comparison", {}),
    }


def get_recovery_performance(db: Session) -> dict:
    rule_based, ml_model = None, None
    if os.path.exists(_BASELINE_COMPARISON_PATH):
        with open(_BASELINE_COMPARISON_PATH) as f:
            comparison = json.load(f)
        rule_based = comparison.get("rule_based")
        ml_model = comparison.get("ml_model")

    by_action = (
        db.query(RecoveryAction.final_action, func.count(RecoveryAction.id))
        .group_by(RecoveryAction.final_action)
        .all()
    )
    by_status = (
        db.query(RecoveryAction.recovery_status, func.count(RecoveryAction.id))
        .group_by(RecoveryAction.recovery_status)
        .all()
    )

    return {
        "rule_based": rule_based,
        "ml_model": ml_model,
        "by_action_type": {action: count for action, count in by_action},
        "by_recovery_status": {status: count for status, count in by_status},
    }