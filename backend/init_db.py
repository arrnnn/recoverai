"""
RecoverAI - Initialize Database
==================================
Creates all tables defined in models.py in the database pointed to by
DATABASE_URL. Safe to run multiple times (create_all only creates tables
that don't already exist).

Usage:
    python backend/init_db.py
"""

from __future__ import annotations

from database import Base, engine
from models import AgentRun, Case, Customer, Metric, Policy, Prediction, RecoveryAction  # noqa: F401

DEFAULT_POLICIES = [
    {
        "rule_name": "restricted_failure_reason",
        "description": "Fraud-flagged or disputed cases are never auto-retried; always escalated to a human.",
        "threshold_value": "fraud_flag, invoice_disputed",
    },
    {
        "rule_name": "high_value_transaction",
        "description": "Transactions above the threshold require human sign-off regardless of AI confidence.",
        "threshold_value": "$10,000.00",
    },
    {
        "rule_name": "retry_limit_exceeded",
        "description": "Cases with too many prior recovery attempts are escalated instead of retried again.",
        "threshold_value": "3 attempts",
    },
    {
        "rule_name": "low_confidence",
        "description": "Low-confidence LLM recommendations are rejected and escalated to a human.",
        "threshold_value": "0.40",
    },
    {
        "rule_name": "repeated_failure_downgrade",
        "description": "Customers with a high historical failure rate get a reminder instead of an automated retry.",
        "threshold_value": "0.50 failure frequency",
    },
    {
        "rule_name": "excessive_reminders_downgrade",
        "description": "Cases that already received several reminders are escalated instead of reminded again.",
        "threshold_value": "2 reminders",
    },
]


def main():
    print("Creating tables (if they don't already exist)...")
    Base.metadata.create_all(bind=engine)
    print("Tables created:")
    for table in Base.metadata.sorted_tables:
        print(f"  - {table.name}")

    # seed the policies reference table so the dashboard has something to show
    from database import SessionLocal

    db = SessionLocal()
    try:
        existing = {p.rule_name for p in db.query(Policy).all()}
        added = 0
        for policy_data in DEFAULT_POLICIES:
            if policy_data["rule_name"] not in existing:
                db.add(Policy(**policy_data))
                added += 1
        db.commit()
        print(f"\nSeeded {added} policy reference rows (skipped {len(DEFAULT_POLICIES) - added} already present).")
    finally:
        db.close()

    print("\nDone.")


if __name__ == "__main__":
    main()