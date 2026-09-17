"""
RecoverAI - Structured LLM Output Schema
==========================================
Defines the strict Pydantic contract the LLM must fill in when analyzing a
recovery case. This is the ONLY way the LLM's opinion enters the system —
it recommends, but the schema forces the recommendation into a closed set
of allowed actions. The policy engine (Phase 6) then decides whether that
recommendation is actually allowed to execute.

The LLM NEVER directly controls execution — it only ever produces this
structured, validated object.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# The closed set of actions the agent is allowed to recommend. This list is
# intentionally identical to the ACTIONS enum used by the policy engine and
# recovery simulator (Phase 6) so nothing outside this set can ever be
# proposed, let alone executed.
RecommendedActionType = Literal[
    "RETRY_PAYMENT",
    "SEND_PAYMENT_REMINDER",
    "SEND_EMAIL",
    "OFFER_RETRY",
    "ESCALATE_TO_HUMAN",
    "NO_ACTION",
]


class RootCauseRecommendation(BaseModel):
    """Structured output the LLM must produce for every case it analyzes."""

    root_cause: str = Field(
        ...,
        description="A short (1-2 sentence) plain-language explanation of why "
        "this case likely failed, grounded in the case data provided.",
        min_length=5,
        max_length=400,
    )
    recommended_action: RecommendedActionType = Field(
        ..., description="The single best next action, chosen from the fixed action set."
    )
    reason: str = Field(
        ...,
        description="A short (1-2 sentence) justification for why this specific "
        "action was recommended over the alternatives.",
        min_length=5,
        max_length=400,
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="The model's confidence in this recommendation, from 0.0 to 1.0."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "root_cause": "The card on file expired shortly before the charge attempt.",
                "recommended_action": "RETRY_PAYMENT",
                "reason": "Card-expiry failures are transient and resolve quickly once "
                "the customer updates their payment method, so an immediate retry is "
                "low-risk and high-value.",
                "confidence": 0.91,
            }
        }
    }