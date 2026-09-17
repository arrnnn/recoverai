"""
RecoverAI - Run Agent & Persist
==================================
Ties Phase 5/6 (the LangGraph agent) to Phase 7 (the database): takes a
case, creates the Customer/Case rows if needed, runs the full agent
workflow, and persists the Prediction, RecoveryAction, and AgentRun rows
that result — closing the loop from "raw case data" to "queryable history."

This is exactly what the future FastAPI endpoints
(POST /cases, POST /cases/{id}/analyze, POST /cases/{id}/recover) will do
internally in Phase 8 — this script proves the persistence logic works
before it gets wrapped in an API.

Usage:
    python backend/run_and_persist.py
"""

from __future__ import annotations

import os
import sys

# --- make agent/ (and, transitively, ml/) importable ---
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT_DIR = os.path.join(_PROJECT_ROOT, "agent")
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from graph import run_case  # noqa: E402

from database import SessionLocal  # noqa: E402
from models import AgentRun, Case, Customer, Prediction, RecoveryAction  # noqa: E402


def get_or_create_customer(db, customer_id: str, segment: str, tenure_months: float) -> Customer:
    customer = db.query(Customer).filter_by(customer_id=customer_id).first()
    if customer:
        return customer
    customer = Customer(customer_id=customer_id, segment=segment, tenure_months=tenure_months)
    db.add(customer)
    db.flush()  # get customer.id without committing yet
    return customer


def run_and_persist(case_input: dict, customer_id: str = "CUST-DEMO-0001") -> str:
    """Runs the full agent workflow on `case_input` and persists the result.

    Returns the generated case_id (e.g. "CASE-XXXXXXXXXX").
    """
    db = SessionLocal()
    try:
        # 1. customer + case rows
        customer = get_or_create_customer(
            db,
            customer_id=customer_id,
            segment=case_input.get("customer_segment", "unknown"),
            tenure_months=case_input.get("customer_tenure_months", 0),
        )
        case_row = Case(
            customer_id=customer.id,
            case_type=case_input["case_type"],
            transaction_amount=case_input["transaction_amount"],
            checkout_value=case_input.get("checkout_value", case_input["transaction_amount"]),
            invoice_or_subscription_age_days=case_input.get("invoice_or_subscription_age_days", 0),
            payment_method=case_input.get("payment_method", "unknown"),
            gateway=case_input.get("gateway", "unknown"),
            failure_reason=case_input.get("failure_reason", "unknown"),
            failure_frequency=case_input.get("failure_frequency", 0.0),
            previous_recovery_attempts=case_input.get("previous_recovery_attempts", 0),
            previous_recovery_success_rate=case_input.get("previous_recovery_success_rate", 0.0),
            status="NEW",
        )
        db.add(case_row)
        db.flush()  # get case_row.id / case_row.case_id

        # 2. run the actual LangGraph agent
        final_state = run_case(case_input)

        # 3. persist prediction
        db.add(
            Prediction(
                case_id=case_row.id,
                recoverable_probability=final_state["prediction"],
                risk_level=final_state["confidence"],
                model_name="logistic_regression",
            )
        )

        # 4. persist recovery action (LLM + policy + outcome, all in one row)
        policy = final_state["policy_result"]
        recovery = final_state["recovery_result"]
        db.add(
            RecoveryAction(
                case_id=case_row.id,
                root_cause=final_state.get("root_cause"),
                recommended_action=final_state.get("recommended_action"),
                llm_reason=final_state.get("llm_reason"),
                llm_confidence=final_state.get("llm_confidence", 0.0),
                policy_decision=policy["decision"],
                policy_rule=policy.get("triggered_rule"),
                final_action=policy.get("final_action", final_state.get("recommended_action")),
                recovery_status=recovery["status"],
                recovered_amount=recovery["recovered_amount"],
            )
        )

        # 5. persist the full agent run (complete audit trail)
        db.add(
            AgentRun(
                case_id=case_row.id,
                execution_log=final_state.get("execution_log", []),
                final_response=final_state.get("final_response", {}),
                status="ERROR" if final_state.get("error") else "COMPLETED",
            )
        )

        # 6. mark the case resolved
        case_row.status = "RESOLVED"

        db.commit()
        return case_row.case_id
    finally:
        db.close()


if __name__ == "__main__":
    demo_case = {
        "case_type": "failed_payment",
        "failure_reason": "card_expired",
        "transaction_amount": 120.0,
        "customer_segment": "consumer",
        "customer_tenure_months": 36,
        "payment_method": "credit_card",
        "gateway": "stripe",
        "failure_frequency": 0.03,
        "previous_recovery_attempts": 0,
        "previous_recovery_success_rate": 0.9,
        "invoice_or_subscription_age_days": 15,
        "checkout_value": 120.0,
    }

    print("Running agent workflow and persisting to database...")
    case_id = run_and_persist(demo_case)
    print(f"\nDone. Persisted case_id: {case_id}")

    # read it all back to prove it's really there
    from database import SessionLocal
    from models import Case

    db = SessionLocal()
    case_row = db.query(Case).filter_by(case_id=case_id).first()
    print(f"\n--- Verification: reading {case_id} back from the database ---")
    print(f"Case type: {case_row.case_type} | Amount: ${case_row.transaction_amount:,.2f} | Status: {case_row.status}")
    print(f"Customer: {case_row.customer.customer_id} ({case_row.customer.segment})")
    for p in case_row.predictions:
        print(f"Prediction: probability={p.recoverable_probability}, risk={p.risk_level}")
    for a in case_row.recovery_actions:
        print(
            f"Recovery action: {a.recommended_action} -> {a.final_action} "
            f"| policy={a.policy_decision} ({a.policy_rule}) | outcome={a.recovery_status} (${a.recovered_amount})"
        )
    for r in case_row.agent_runs:
        print(f"Agent run: status={r.status}, steps={len(r.execution_log)}")
    db.close()