"""
RecoverAI - Agent State
========================
The single shared state object that flows through every node of the
LangGraph workflow. Each node reads what it needs and adds its own piece,
so by the time the graph reaches END, `execution_log` and `final_response`
contain a complete, inspectable record of every decision the agent made
and why — this IS the audit trail shown in the "Agent Activity" dashboard
tab and returned by GET /agent/runs/{case_id}.
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    # ---- input ----
    case: dict[str, Any]  # raw case data (case_type, transaction_amount, etc.)

    # ---- ML Prediction node output ----
    prediction: float  # recoverable_probability, 0-1
    confidence: str  # risk_level: "low" | "medium" | "high"

    # ---- Root Cause Analysis node output (LLM) ----
    root_cause: str
    recommended_action: str
    llm_reason: str
    llm_confidence: float

    # ---- Policy Check node output ----
    policy_result: dict[str, Any]  # {"decision": "APPROVED"/"REJECTED", "reason": str, ...}

    # ---- Recovery Action node output ----
    recovery_result: dict[str, Any]  # {"status": "SUCCESS"/"FAILED"/"ESCALATED"/"BLOCKED", "recovered_amount": float}

    # ---- cross-cutting ----
    execution_log: list[dict[str, Any]]  # ordered trace of every node's decision
    final_response: dict[str, Any]  # assembled summary returned to the caller
    error: str | None  # set if any node hit an unrecoverable problem