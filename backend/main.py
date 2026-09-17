"""
RecoverAI - FastAPI Application
==================================
Wraps everything built in Phases 1-7 (ML model, LLM agent, LangGraph
workflow, policy engine, database) into a REST API.

Run locally:
    cd backend
    uvicorn main:app --reload --port 8000

Then browse to http://localhost:8000/docs for interactive API docs
(FastAPI generates this automatically from the Pydantic schemas below).
"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import agent_service
import analytics
from database import get_db
from models import AgentRun, Case, Customer, Policy, Prediction, RecoveryAction
from api_schemas import (
    AgentRunResponse,
    AnalyticsSummary,
    AnalyzeResponse,
    CaseCreate,
    CaseDetail,
    CaseSummary,
    ModelPerformance,
    PolicyRule,
    RecoverResponse,
    RecoveryPerformance,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("recoverai")

app = FastAPI(
    title="RecoverAI API",
    description="Agentic AI Revenue Recovery Platform — all recovery actions are simulated, never real.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/cases", response_model=CaseSummary, status_code=201)
def create_case(payload: CaseCreate, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter_by(customer_id=payload.customer_id).first()
    if not customer:
        customer = Customer(
            customer_id=payload.customer_id,
            segment=payload.customer_segment,
            tenure_months=payload.customer_tenure_months,
        )
        db.add(customer)
        db.flush()

    case = Case(
        customer_id=customer.id,
        case_type=payload.case_type,
        transaction_amount=payload.transaction_amount,
        checkout_value=payload.checkout_value if payload.checkout_value is not None else payload.transaction_amount,
        invoice_or_subscription_age_days=payload.invoice_or_subscription_age_days,
        payment_method=payload.payment_method,
        gateway=payload.gateway,
        failure_reason=payload.failure_reason,
        failure_frequency=payload.failure_frequency,
        previous_recovery_attempts=payload.previous_recovery_attempts,
        previous_recovery_success_rate=payload.previous_recovery_success_rate,
        status="NEW",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    logger.info(f"Created case {case.case_id}")
    return CaseSummary(
        case_id=case.case_id,
        case_type=case.case_type,
        transaction_amount=case.transaction_amount,
        failure_reason=case.failure_reason,
        status=case.status,
        created_at=case.created_at,
        risk_level=None,
        latest_action=None,
    )


@app.get("/cases", response_model=list[CaseSummary])
def list_cases(status: str | None = None, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    query = db.query(Case)
    if status:
        query = query.filter(Case.status == status.upper())
    cases = query.order_by(Case.id.desc()).offset(offset).limit(limit).all()

    results = []
    for c in cases:
        latest_pred = (
            db.query(Prediction).filter_by(case_id=c.id).order_by(Prediction.id.desc()).first()
        )
        latest_action = (
            db.query(RecoveryAction).filter_by(case_id=c.id).order_by(RecoveryAction.id.desc()).first()
        )
        results.append(
            CaseSummary(
                case_id=c.case_id,
                case_type=c.case_type,
                transaction_amount=c.transaction_amount,
                failure_reason=c.failure_reason,
                status=c.status,
                created_at=c.created_at,
                risk_level=latest_pred.risk_level if latest_pred else None,
                latest_action=latest_action.final_action if latest_action else None,
            )
        )
    return results


@app.get("/cases/{case_id}", response_model=CaseDetail)
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter_by(case_id=case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    latest_prediction = None
    if case.predictions:
        p = sorted(case.predictions, key=lambda p: p.id)[-1]
        latest_prediction = {
            "recoverable_probability": p.recoverable_probability,
            "risk_level": p.risk_level,
            "model_name": p.model_name,
        }

    latest_recovery_action = None
    if case.recovery_actions:
        a = sorted(case.recovery_actions, key=lambda a: a.id)[-1]
        latest_recovery_action = {
            "root_cause": a.root_cause,
            "recommended_action": a.recommended_action,
            "final_action": a.final_action,
            "policy_decision": a.policy_decision,
            "policy_rule": a.policy_rule,
            "recovery_status": a.recovery_status,
            "recovered_amount": a.recovered_amount,
        }

    return CaseDetail(
        case_id=case.case_id,
        case_type=case.case_type,
        transaction_amount=case.transaction_amount,
        checkout_value=case.checkout_value,
        payment_method=case.payment_method,
        gateway=case.gateway,
        failure_reason=case.failure_reason,
        failure_frequency=case.failure_frequency,
        previous_recovery_attempts=case.previous_recovery_attempts,
        previous_recovery_success_rate=case.previous_recovery_success_rate,
        status=case.status,
        created_at=case.created_at,
        customer_id=case.customer.customer_id if case.customer else None,
        customer_segment=case.customer.segment if case.customer else None,
        latest_prediction=latest_prediction,
        latest_recovery_action=latest_recovery_action,
    )


@app.post("/cases/{case_id}/analyze", response_model=AnalyzeResponse)
def analyze_case(case_id: str, db: Session = Depends(get_db)):
    try:
        result = agent_service.analyze_case_by_id(db, case_id)
        logger.info(f"Analyzed case {case_id}: policy={result['policy_decision']} final_action={result['final_action']}")
        return result
    except agent_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except agent_service.InvalidStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/cases/{case_id}/recover", response_model=RecoverResponse)
def recover_case(case_id: str, db: Session = Depends(get_db)):
    try:
        result = agent_service.recover_case_by_id(db, case_id)
        logger.info(f"Recovered case {case_id}: status={result['recovery_status']}")
        return result
    except agent_service.NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except agent_service.InvalidStateError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/analytics/summary", response_model=AnalyticsSummary)
def analytics_summary(db: Session = Depends(get_db)):
    return analytics.get_summary(db)


@app.get("/analytics/model-performance", response_model=ModelPerformance)
def analytics_model_performance():
    return analytics.get_model_performance()


@app.get("/analytics/recovery-performance", response_model=RecoveryPerformance)
def analytics_recovery_performance(db: Session = Depends(get_db)):
    return analytics.get_recovery_performance(db)


@app.get("/agent/runs/{case_id}", response_model=list[AgentRunResponse])
def get_agent_runs(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter_by(case_id=case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    runs = db.query(AgentRun).filter_by(case_id=case.id).order_by(AgentRun.id.asc()).all()
    return [
        AgentRunResponse(
            case_id=case.case_id,
            status=r.status,
            execution_log=r.execution_log,
            final_response=r.final_response,
            started_at=r.started_at,
            completed_at=r.completed_at,
        )
        for r in runs
    ]


@app.get("/policies", response_model=list[PolicyRule])
def list_policies(db: Session = Depends(get_db)):
    return db.query(Policy).order_by(Policy.id.asc()).all()