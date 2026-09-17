"""
RecoverAI - LangGraph Agent Workflow
======================================
Wires together everything built so far into one traceable graph:

    START
      -> analyze_case          (validate/normalize input)
      -> ml_prediction          (Phase 2 model: recoverable probability)
      -> root_cause_analysis    (Phase 4 LLM: root cause + recommended action)
      -> decision_router        (sanity-check the LLM's recommendation)
      -> policy_check           (Phase 6: real deterministic policy engine)
      -> recovery_action        (Phase 6: real simulated recovery tools)
      -> record_outcome         (append final trace entry)
      -> final_response         (assemble the summary returned to the caller)
      -> END

Every node appends a structured entry to `execution_log`, so by the end of
the run the full state is a complete audit trail: what the model predicted,
what the LLM recommended and why, what the policy engine decided (and why),
and what the simulated outcome was.

Usage:
    python agent/graph.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from langgraph.graph import END, START, StateGraph

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ML_DIR = os.path.join(_PROJECT_ROOT, "ml")
if _ML_DIR not in sys.path:
    sys.path.insert(0, _ML_DIR)

import predict as ml_predict  # noqa: E402

from currency import format_dual  # noqa: E402
from llm_client import get_recommendation  # noqa: E402
from policy import check_policy  # noqa: E402
from state import AgentState  # noqa: E402
from tools import create_recovery_email, escalate_case, simulate_payment_retry  # noqa: E402


def _log(state: AgentState, node: str, message: str, **extra) -> None:
    entry = {
        "node": node,
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **extra,
    }
    state.setdefault("execution_log", []).append(entry)


def analyze_case_node(state: AgentState) -> AgentState:
    case = state["case"]
    required = ["case_type", "transaction_amount", "failure_reason"]
    missing = [f for f in required if f not in case]
    if missing:
        state["error"] = f"Case missing required fields: {missing}"
        _log(state, "analyze_case", f"Validation FAILED: missing {missing}")
        return state
    _log(state, "analyze_case", f"Case validated: {case.get('case_type')} / {case.get('failure_reason')}")
    return state


def ml_prediction_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    result = ml_predict.predict_case(state["case"])
    state["prediction"] = result["recoverable_probability"]
    state["confidence"] = result["risk_level"]
    _log(
        state,
        "ml_prediction",
        f"Predicted recoverable_probability={result['recoverable_probability']} "
        f"(risk_level={result['risk_level']})",
        prediction=result["recoverable_probability"],
        risk_level=result["risk_level"],
    )
    return state


def root_cause_analysis_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    rec = get_recommendation(
        state["case"], ml_probability=state["prediction"], ml_risk_level=state["confidence"]
    )
    state["root_cause"] = rec.root_cause
    state["recommended_action"] = rec.recommended_action
    state["llm_reason"] = rec.reason
    state["llm_confidence"] = rec.confidence
    _log(
        state,
        "root_cause_analysis",
        f"LLM recommends {rec.recommended_action} (confidence={rec.confidence}): {rec.root_cause}",
        recommended_action=rec.recommended_action,
        llm_confidence=rec.confidence,
    )
    return state


def decision_router_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    llm_conf = state.get("llm_confidence", 0.0)
    action = state.get("recommended_action", "NO_ACTION")

    if llm_conf < 0.4 and action != "ESCALATE_TO_HUMAN":
        _log(
            state,
            "decision_router",
            f"Overriding low-confidence recommendation ({action}, conf={llm_conf}) -> ESCALATE_TO_HUMAN",
        )
        state["recommended_action"] = "ESCALATE_TO_HUMAN"
    else:
        _log(state, "decision_router", f"Routing forward with action={action} (conf={llm_conf})")
    return state


def policy_check_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    result = check_policy(
        case=state["case"],
        recommended_action=state["recommended_action"],
        llm_confidence=state.get("llm_confidence", 0.0),
    )
    state["policy_result"] = result.to_dict()
    state["recommended_action"] = result.final_action
    _log(
        state,
        "policy_check",
        f"Policy decision: {result.decision} [{result.triggered_rule}] — {result.reason}",
        decision=result.decision,
        triggered_rule=result.triggered_rule,
    )
    return state


def recovery_action_node(state: AgentState) -> AgentState:
    if state.get("error"):
        return state
    action = state["recommended_action"]
    case = state["case"]
    prob = state.get("prediction", 0.0)

    if action == "NO_ACTION":
        result = {"status": "FAILED", "recovered_amount": 0.0, "detail": "No action taken."}
    elif action == "ESCALATE_TO_HUMAN":
        esc = escalate_case(case, state["policy_result"].get("reason", "Escalated by policy/agent."))
        result = {"status": "ESCALATED", "recovered_amount": 0.0, "detail": esc}
    elif action in ("RETRY_PAYMENT", "OFFER_RETRY"):
        retry = simulate_payment_retry(case, prob)
        result = {
            "status": retry["status"],
            "recovered_amount": retry["recovered_amount"],
            "detail": retry,
        }
    elif action in ("SEND_PAYMENT_REMINDER", "SEND_EMAIL"):
        email = create_recovery_email(case, state.get("root_cause", ""))
        result = {"status": "SUCCESS", "recovered_amount": 0.0, "detail": email}
    else:
        result = {"status": "FAILED", "recovered_amount": 0.0, "detail": f"Unhandled action: {action}"}

    state["recovery_result"] = {"status": result["status"], "recovered_amount": result["recovered_amount"]}
    _log(
        state,
        "recovery_action",
        f"Simulated recovery result: {result['status']} ({format_dual(result['recovered_amount'])})",
        status=result["status"],
    )
    return state


def record_outcome_node(state: AgentState) -> AgentState:
    if state.get("error"):
        _log(state, "record_outcome", f"Run ended with error: {state['error']}")
        return state
    _log(
        state,
        "record_outcome",
        f"Outcome recorded: {state['recovery_result']['status']}",
    )
    return state


def final_response_node(state: AgentState) -> AgentState:
    if state.get("error"):
        state["final_response"] = {"status": "ERROR", "error": state["error"]}
        return state
    state["final_response"] = {
        "case_type": state["case"].get("case_type"),
        "recoverable_probability": state.get("prediction"),
        "risk_level": state.get("confidence"),
        "root_cause": state.get("root_cause"),
        "recommended_action": state.get("recommended_action"),
        "policy_decision": state["policy_result"]["decision"],
        "policy_rule": state["policy_result"].get("triggered_rule"),
        "recovery_status": state["recovery_result"]["status"],
        "recovered_amount_usd": state["recovery_result"]["recovered_amount"],
        "recovered_amount_display": format_dual(state["recovery_result"]["recovered_amount"]),
        "steps": len(state.get("execution_log", [])),
    }
    _log(state, "final_response", "Assembled final response")
    return state


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("analyze_case", analyze_case_node)
    graph.add_node("ml_prediction", ml_prediction_node)
    graph.add_node("root_cause_analysis", root_cause_analysis_node)
    graph.add_node("decision_router", decision_router_node)
    graph.add_node("policy_check", policy_check_node)
    graph.add_node("recovery_action", recovery_action_node)
    graph.add_node("record_outcome", record_outcome_node)
    graph.add_node("final_response", final_response_node)

    graph.add_edge(START, "analyze_case")
    graph.add_edge("analyze_case", "ml_prediction")
    graph.add_edge("ml_prediction", "root_cause_analysis")
    graph.add_edge("root_cause_analysis", "decision_router")
    graph.add_edge("decision_router", "policy_check")
    graph.add_edge("policy_check", "recovery_action")
    graph.add_edge("recovery_action", "record_outcome")
    graph.add_edge("record_outcome", "final_response")
    graph.add_edge("final_response", END)

    return graph.compile()


_compiled_graph = None


def get_compiled_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_case(case: dict) -> AgentState:
    app = get_compiled_graph()
    initial_state: AgentState = {"case": case, "execution_log": []}
    return app.invoke(initial_state)


if __name__ == "__main__":
    demo_case = {
        "case_type": "failed_payment",
        "failure_reason": "card_expired",
        "transaction_amount": 45000.0,
        "customer_segment": "enterprise",
        "customer_tenure_months": 60,
        "payment_method": "credit_card",
        "gateway": "stripe",
        "failure_frequency": 0.02,
        "previous_recovery_attempts": 0,
        "previous_recovery_success_rate": 0.95,
        "invoice_or_subscription_age_days": 5,
        "checkout_value": 45000.0,
    }
    final_state = run_case(demo_case)

    print("=" * 70)
    print("RecoverAI - LangGraph Agent Run")
    print("=" * 70)
    print("\nExecution log:")
    for entry in final_state["execution_log"]:
        print(f"  [{entry['node']}] {entry['message']}")
    print("\nFinal response:")
    import json

    print(json.dumps(final_state["final_response"], indent=2, ensure_ascii=False))