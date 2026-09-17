"""
RecoverAI - API Schemas
=========================
Pydantic models defining the request/response contracts for every
FastAPI endpoint. Kept separate from the SQLAlchemy models (models.py) so
the API shape can evolve independently of the database schema.

Named api_schemas.py (not schemas.py) to avoid colliding with
agent/schemas.py — Python caches imported modules by name, not by path,
so two same-named "schemas" modules in one process is a real collision.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    case_type: str = Field(..., examples=["failed_payment"])
    transaction_amount: float
    checkout_value: float | None = None
    invoice_or_subscription_age_days: int = 0
    payment_method: str
    gateway: str
    failure_reason: str
    failure_frequency: float = 0.0
    previous_recovery_attempts: int = 0
    previous_recovery_success_rate: float = 0.0

    customer_id: str = "CUST-UNSPECIFIED"
    customer_segment: str = "unknown"
    customer_tenure_months: float = 0.0


class CaseSummary(BaseModel):
    case_id: str
    case_type: str
    transaction_amount: float
    failure_reason: str
    status: str
    created_at: datetime
    # --- real data for Cases-page filtering, not fabricated ---
    risk_level: str | None = None
    latest_action: str | None = None

    model_config = {"from_attributes": True}


class CaseDetail(BaseModel):
    case_id: str
    case_type: str
    transaction_amount: float
    checkout_value: float
    payment_method: str
    gateway: str
    failure_reason: str
    failure_frequency: float
    previous_recovery_attempts: int
    previous_recovery_success_rate: float
    status: str
    created_at: datetime

    customer_id: str | None = None
    customer_segment: str | None = None

    latest_prediction: dict[str, Any] | None = None
    latest_recovery_action: dict[str, Any] | None = None


class AnalyzeResponse(BaseModel):
    case_id: str
    recoverable_probability: float
    risk_level: str
    root_cause: str
    llm_recommended_action: str
    llm_confidence: float
    policy_decision: str
    policy_rule: str | None
    policy_reason: str
    final_action: str  # what WILL execute if /recover is called next


class RecoverResponse(BaseModel):
    case_id: str
    final_action: str
    recovery_status: str
    recovered_amount_usd: float
    recovered_amount_display: str


class AnalyticsSummary(BaseModel):
    total_cases: int
    revenue_at_risk_usd: float
    revenue_recovered_usd: float
    recovery_rate: float
    high_risk_cases: int
    successful_recoveries: int
    escalated_cases: int


class ModelPerformance(BaseModel):
    model_selected: str
    test_metrics: dict[str, Any]
    candidate_comparison: dict[str, Any]


class RecoveryPerformance(BaseModel):
    rule_based: dict[str, Any] | None
    ml_model: dict[str, Any] | None
    by_action_type: dict[str, Any]
    by_recovery_status: dict[str, Any]


class AgentRunResponse(BaseModel):
    case_id: str
    status: str
    execution_log: list[dict[str, Any]]
    final_response: dict[str, Any]
    started_at: datetime
    completed_at: datetime

    model_config = {"from_attributes": True}


class PolicyRule(BaseModel):
    rule_name: str
    description: str
    threshold_value: str | None
    active: bool

    model_config = {"from_attributes": True}