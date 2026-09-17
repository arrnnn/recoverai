"""
RecoverAI - Database Models
=============================
The 7 tables that persist everything the platform does:

    customers          - who the case belongs to
    cases               - the revenue-at-risk case itself
    predictions         - ML model output for a case
    recovery_actions    - what the agent recommended, what policy decided,
                          and what happened when it "ran" (simulated)
    policies            - reference table describing the deterministic
                          policy rules (for the dashboard/docs, not runtime logic —
                          runtime logic lives in agent/policy.py)
    agent_runs          - one row per full LangGraph execution, with the
                          complete execution_log and final_response as JSON
    metrics             - computed model-performance / business metrics,
                          snapshotted over time (so the dashboard can show trends)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return uuid.uuid4().hex


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    segment: Mapped[str] = mapped_column(String(32))
    tenure_months: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    cases: Mapped[list["Case"]] = relationship(back_populates="customer")


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, default=lambda: f"CASE-{_uuid()[:10].upper()}")
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"), nullable=True)

    case_type: Mapped[str] = mapped_column(String(32))
    transaction_amount: Mapped[float] = mapped_column(Float)
    checkout_value: Mapped[float] = mapped_column(Float, default=0.0)
    invoice_or_subscription_age_days: Mapped[int] = mapped_column(Integer, default=0)
    payment_method: Mapped[str] = mapped_column(String(32))
    gateway: Mapped[str] = mapped_column(String(32))
    failure_reason: Mapped[str] = mapped_column(String(64))
    failure_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    previous_recovery_attempts: Mapped[int] = mapped_column(Integer, default=0)
    previous_recovery_success_rate: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(32), default="NEW")  # NEW, ANALYZED, RESOLVED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    customer: Mapped["Customer | None"] = relationship(back_populates="cases")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    recovery_actions: Mapped[list["RecoveryAction"]] = relationship(back_populates="case", cascade="all, delete-orphan")
    agent_runs: Mapped[list["AgentRun"]] = relationship(back_populates="case", cascade="all, delete-orphan")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))

    recoverable_probability: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(String(16))
    model_name: Mapped[str] = mapped_column(String(64), default="logistic_regression")
    threshold_used: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    case: Mapped["Case"] = relationship(back_populates="predictions")


class RecoveryAction(Base):
    __tablename__ = "recovery_actions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))

    root_cause: Mapped[str] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[str] = mapped_column(String(32))
    llm_reason: Mapped[str] = mapped_column(Text, nullable=True)
    llm_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    policy_decision: Mapped[str] = mapped_column(String(16))  # APPROVED / REJECTED / N/A
    policy_rule: Mapped[str] = mapped_column(String(64), nullable=True)
    final_action: Mapped[str] = mapped_column(String(32))

    recovery_status: Mapped[str] = mapped_column(String(16))  # SUCCESS / FAILED / ESCALATED / BLOCKED
    recovered_amount: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    case: Mapped["Case"] = relationship(back_populates="recovery_actions")


class Policy(Base):
    """Reference/documentation table describing the deterministic rules
    enforced at runtime by agent/policy.py. Not used to evaluate policy
    decisions live — it exists so the dashboard/API can display the current
    rule set without hardcoding it in the frontend.
    """

    __tablename__ = "policies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[str] = mapped_column(Text)
    threshold_value: Mapped[str] = mapped_column(String(64), nullable=True)
    active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))

    execution_log: Mapped[list] = mapped_column(JSON)  # list of {node, message, timestamp, ...}
    final_response: Mapped[dict] = mapped_column(JSON)

    status: Mapped[str] = mapped_column(String(16), default="COMPLETED")  # COMPLETED / ERROR
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    case: Mapped["Case"] = relationship(back_populates="agent_runs")


class Metric(Base):
    """Snapshotted metrics (ML performance and business metrics) so the
    dashboard's Analytics tab can show values as-of a point in time and,
    later, trends across multiple training/evaluation runs.
    """

    __tablename__ = "metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(64))  # e.g. "roc_auc", "revenue_recovered"
    metric_value: Mapped[float] = mapped_column(Float)
    metric_type: Mapped[str] = mapped_column(String(32))  # "model_performance" | "business"
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)