"""
RecoverAI - Agent Tools
=========================
The concrete tool suite the agent workflow calls. These are deliberately
NOT exposed to the LLM as callable tools it can invoke freely — the LLM
only ever produces a `RootCauseRecommendation` (Phase 4). The LangGraph
nodes (Phase 5/6) call these functions directly, after the policy engine
has approved an action. This keeps a hard boundary between "the LLM's
opinion" and "code that actually runs."

Tools:
    calculate_recovery_value(case)      -> expected $ value of recovering this case
    check_policy(...)                   -> the policy engine itself (see policy.py)
    simulate_payment_retry(case)        -> simulated gateway retry outcome
    create_recovery_email(case, ...)    -> simulated email content (never actually sent)
    escalate_case(case, reason)         -> simulated human-escalation ticket

NEVER performs real financial transactions or sends real emails — everything
here is simulated and clearly labeled as such, per project requirements.
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from typing import Any

from currency import format_dual

# re-export so other modules can import policy checking from "tools" if desired
from policy import PolicyResult, check_policy  # noqa: F401


def calculate_recovery_value(case: dict[str, Any], recoverable_probability: float) -> dict[str, Any]:
    """Expected monetary value of attempting recovery on this case.

    expected_value = transaction_amount * recoverable_probability

    This is a simple expected-value calculation used for prioritization
    (e.g. "which cases should the ops team look at first") — not a
    guarantee of outcome.
    """
    amount = float(case.get("transaction_amount", 0.0))
    expected_value = round(amount * recoverable_probability, 2)
    return {
        "transaction_amount": amount,
        "transaction_amount_display": format_dual(amount),
        "recoverable_probability": recoverable_probability,
        "expected_recovery_value": expected_value,
        "expected_recovery_value_display": format_dual(expected_value),
    }


def simulate_payment_retry(case: dict[str, Any], recoverable_probability: float) -> dict[str, Any]:
    """Simulate a payment gateway retry attempt. NEVER calls a real gateway.

    Success probability is driven by the ML model's recoverable_probability
    plus a small amount of realistic noise, mirroring how the synthetic
    training data itself was generated (Phase 1) — so simulated outcomes
    stay consistent with what the model was trained to predict.
    """
    amount = float(case.get("transaction_amount", 0.0))
    noise = random.uniform(-0.05, 0.05)
    effective_prob = min(max(recoverable_probability + noise, 0.0), 1.0)
    success = random.random() < effective_prob

    result = {
        "tool": "simulate_payment_retry",
        "simulated": True,
        "status": "SUCCESS" if success else "FAILED",
        "recovered_amount": round(amount * random.uniform(0.9, 1.0), 2) if success else 0.0,
        "gateway": case.get("gateway", "unknown"),
        "attempted_at": datetime.now(timezone.utc).isoformat(),
    }
    result["recovered_amount_display"] = format_dual(result["recovered_amount"])
    return result


def create_recovery_email(case: dict[str, Any], root_cause: str) -> dict[str, Any]:
    """Simulate drafting a recovery/reminder email. NEVER actually sends anything.

    Returns the email content so it can be logged/displayed in the dashboard,
    demonstrating what *would* be sent in a real deployment.
    """
    amount = float(case.get("transaction_amount", 0.0))
    case_type_label = {
        "failed_payment": "payment",
        "abandoned_checkout": "checkout",
        "failed_subscription": "subscription renewal",
        "overdue_invoice": "invoice",
    }.get(case.get("case_type", ""), "transaction")

    subject = f"Action needed: your {case_type_label} of {format_dual(amount)} needs attention"
    body = (
        f"Hi,\n\nWe noticed an issue with your recent {case_type_label} "
        f"({format_dual(amount)}). {root_cause}\n\n"
        f"Please update your payment details or contact support to resolve this.\n\n"
        f"— RecoverAI (simulated notification, not actually sent)"
    )
    return {
        "tool": "create_recovery_email",
        "simulated": True,
        "sent": False,  # explicitly never sent — portfolio-safe by design
        "subject": subject,
        "body": body,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def escalate_case(case: dict[str, Any], reason: str) -> dict[str, Any]:
    """Simulate creating a human-review escalation ticket."""
    ticket_id = f"ESC-{uuid.uuid4().hex[:8].upper()}"
    return {
        "tool": "escalate_case",
        "simulated": True,
        "ticket_id": ticket_id,
        "status": "ESCALATED",
        "reason": reason,
        "amount_display": format_dual(float(case.get("transaction_amount", 0.0))),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }