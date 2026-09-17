"""
RecoverAI - Agent Service
===========================
Bridges the FastAPI layer to the LangGraph agent (agent/graph.py) and the
database. Unlike backend/run_and_persist.py (Phase 7, which runs the full
workflow in one shot), this module splits the workflow into the two steps
the API contract requires:

    analyze_case_by_id(case_id)   -> runs analyze_case, ml_prediction,
                                      root_cause_analysis, decision_router,
                                      and policy_check; persists Prediction
                                      + a PENDING RecoveryAction + a partial
                                      AgentRun; does NOT execute anything yet.

    recover_case_by_id(case_id)   -> resumes from the persisted PENDING
                                      state, runs recovery_action,
                                      record_outcome, and final_response;
                                      updates the RecoveryAction row with
                                      the real outcome and completes the
                                      AgentRun.

This mirrors how a real system would work: "analyze" tells you what WOULD
happen; "recover" is a separate, deliberate step that actually does it.
"""

from __future__ import annotations

import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_AGENT_DIR = os.path.join(_PROJECT_ROOT, "agent")
if _AGENT_DIR not in sys.path:
    sys.path.insert(0, _AGENT_DIR)

from graph import (  # noqa: E402
    analyze_case_node,
    decision_router_node,
    ml_prediction_node,
    policy_check_node,
    recovery_action_node,
    record_outcome_node,
    final_response_node,
    root_cause_analysis_node,
)

from sqlalchemy.orm import Session  # noqa: E402

from models import AgentRun, Case, Prediction, RecoveryAction  # noqa: E402


class NotFoundError(Exception):
    pass


class InvalidStateError(Exception):
    pass


def _case_to_input_dict(case: Case) -> dict:
    return {
        "case_type": case.case_type,
        "transaction_amount": case.transaction_amount,
        "checkout_value": case.checkout_value,
        "invoice_or_subscription_age_days": case.invoice_or_subscription_age_days,
        "payment_method": case.payment_method,
        "gateway": case.gateway,
        "failure_reason": case.failure_reason,
        "failure_frequency": case.failure_frequency,
        "previous_recovery_attempts": case.previous_recovery_attempts,
        "previous_recovery_success_rate": case.previous_recovery_success_rate,
        "customer_segment": case.customer.segment if case.customer else "unknown",
        "customer_tenure_months": case.customer.tenure_months if case.customer else 0,
    }


def analyze_case_by_id(db: Session, case_id: str) -> dict:
    case = db.query(Case).filter_by(case_id=case_id).first()
    if not case:
        raise NotFoundError(f"Case {case_id} not found")

    case_input = _case_to_input_dict(case)
    state = {"case": case_input, "execution_log": []}

    state = analyze_case_node(state)
    state = ml_prediction_node(state)
    state = root_cause_analysis_node(state)
    llm_original_action = state.get("recommended_action")  # capture before it can be overridden
    state = decision_router_node(state)
    state = policy_check_node(state)

    if state.get("error"):
        raise InvalidStateError(state["error"])

    # persist Prediction
    db.add(
        Prediction(
            case_id=case.id,
            recoverable_probability=state["prediction"],
            risk_level=state["confidence"],
            model_name="logistic_regression",
        )
    )

    # persist a PENDING recovery action — nothing has executed yet
    policy = state["policy_result"]
    recovery_action_row = RecoveryAction(
        case_id=case.id,
        root_cause=state.get("root_cause"),
        recommended_action=state.get("recommended_action"),
        llm_reason=state.get("llm_reason"),
        llm_confidence=state.get("llm_confidence", 0.0),
        policy_decision=policy["decision"],
        policy_rule=policy.get("triggered_rule"),
        final_action=policy.get("final_action", state.get("recommended_action")),
        recovery_status="PENDING",
        recovered_amount=0.0,
    )
    db.add(recovery_action_row)

    # persist a partial agent run (analysis steps only so far)
    agent_run_row = AgentRun(
        case_id=case.id,
        execution_log=state.get("execution_log", []),
        final_response={},
        status="ANALYZED",
    )
    db.add(agent_run_row)

    case.status = "ANALYZED"
    db.commit()

    return {
        "case_id": case.case_id,
        "recoverable_probability": state["prediction"],
        "risk_level": state["confidence"],
        "root_cause": state.get("root_cause", ""),
        "llm_recommended_action": llm_original_action,
        "llm_confidence": state.get("llm_confidence", 0.0),
        "policy_decision": policy["decision"],
        "policy_rule": policy.get("triggered_rule"),
        "policy_reason": policy.get("reason", ""),
        "final_action": policy.get("final_action", state["recommended_action"]),
    }


def recover_case_by_id(db: Session, case_id: str) -> dict:
    case = db.query(Case).filter_by(case_id=case_id).first()
    if not case:
        raise NotFoundError(f"Case {case_id} not found")
    if case.status != "ANALYZED":
        raise InvalidStateError(
            f"Case {case_id} is in status '{case.status}'; call /analyze before /recover."
        )

    recovery_action_row = (
        db.query(RecoveryAction)
        .filter_by(case_id=case.id, recovery_status="PENDING")
        .order_by(RecoveryAction.id.desc())
        .first()
    )
    prediction_row = (
        db.query(Prediction).filter_by(case_id=case.id).order_by(Prediction.id.desc()).first()
    )
    agent_run_row = (
        db.query(AgentRun).filter_by(case_id=case.id).order_by(AgentRun.id.desc()).first()
    )
    if not recovery_action_row or not prediction_row or not agent_run_row:
        raise InvalidStateError(f"Case {case_id} is missing analysis data; re-run /analyze.")

    case_input = _case_to_input_dict(case)
    state = {
        "case": case_input,
        "prediction": prediction_row.recoverable_probability,
        "confidence": prediction_row.risk_level,
        "root_cause": recovery_action_row.root_cause,
        "recommended_action": recovery_action_row.final_action,  # policy-adjusted action
        "policy_result": {
            "decision": recovery_action_row.policy_decision,
            "triggered_rule": recovery_action_row.policy_rule,
            "final_action": recovery_action_row.final_action,
        },
        "execution_log": list(agent_run_row.execution_log),  # continue from where analyze left off
    }

    state = recovery_action_node(state)
    state = record_outcome_node(state)
    state = final_response_node(state)

    recovery_action_row.recovery_status = state["recovery_result"]["status"]
    recovery_action_row.recovered_amount = state["recovery_result"]["recovered_amount"]

    agent_run_row.execution_log = state["execution_log"]
    agent_run_row.final_response = state["final_response"]
    agent_run_row.status = "COMPLETED"

    case.status = "RESOLVED"
    db.commit()

    from currency import format_dual

    return {
        "case_id": case.case_id,
        "final_action": recovery_action_row.final_action,
        "recovery_status": recovery_action_row.recovery_status,
        "recovered_amount_usd": recovery_action_row.recovered_amount,
        "recovered_amount_display": format_dual(recovery_action_row.recovered_amount),
    }