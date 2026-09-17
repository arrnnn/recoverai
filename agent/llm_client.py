"""
RecoverAI - LLM Client (Root Cause + Action Recommendation)
=============================================================
Wraps Groq's free-tier cloud API (no cost, no laptop compute required — the
model runs on Groq's servers) to analyze a recovery case and produce a
structured recommendation that strictly conforms to
`schemas.RootCauseRecommendation`.

Design notes:
  - The LLM only ever RECOMMENDS. It has no tool access and no ability to
    execute anything. Its entire output surface is the validated Pydantic
    schema below, which the policy engine then approves/rejects.
  - We use Groq's JSON mode + a Pydantic output parser (rather than relying
    solely on tool-calling) so this works reliably even with lightweight
    open models.
  - If the model returns invalid/unparseable JSON, we retry once with the
    validation error fed back into the prompt, then fall back to a safe
    ESCALATE_TO_HUMAN recommendation rather than crashing the pipeline —
    a malformed LLM response should never take down the agent.

Getting a free API key:
  1. Sign up at https://console.groq.com (free, no credit card required)
  2. Create an API key
  3. Put it in your local .env file as GROQ_API_KEY=...  (never commit this)

Environment variables (see .env.example):
  GROQ_API_KEY      required — your free Groq API key
  GROQ_MODEL        default: llama-3.1-8b-instant
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

load_dotenv()  # reads .env in the project root if present, so GROQ_API_KEY
                # doesn't need to be manually exported every terminal session

from langchain_core.exceptions import OutputParserException
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import ValidationError

from schemas import RootCauseRecommendation

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

_parser = PydanticOutputParser(pydantic_object=RootCauseRecommendation)

_SYSTEM_PROMPT = """You are a revenue-recovery analyst for a payments platform.
You analyze a single failed-payment / abandoned-checkout / failed-subscription /
overdue-invoice case and recommend ONE next action from a fixed list.

Rules:
- You may ONLY recommend one of these exact actions: RETRY_PAYMENT, SEND_PAYMENT_REMINDER,
  SEND_EMAIL, OFFER_RETRY, ESCALATE_TO_HUMAN, NO_ACTION.
- You never guarantee outcomes; you only recommend the most sensible next step.
- If the case looks risky (fraud, dispute, high value with prior failures), prefer
  ESCALATE_TO_HUMAN over an automated retry.
- Respond with ONLY a single valid JSON object matching the schema. No prose,
  no markdown fences, no extra commentary.

{format_instructions}
"""

_HUMAN_PROMPT = """Case details:
- Case type: {case_type}
- Failure reason: {failure_reason}
- Transaction amount: ${transaction_amount:,.2f}
- Customer segment: {customer_segment}
- Customer tenure (months): {customer_tenure_months}
- Payment method: {payment_method}
- Historical failure frequency: {failure_frequency}
- Previous recovery attempts on this case: {previous_recovery_attempts}
- Previous recovery success rate: {previous_recovery_success_rate}

ML model prediction:
- Recoverable probability: {ml_probability}
- Risk level: {ml_risk_level}

Analyze this case and provide your structured recommendation now.
"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", _SYSTEM_PROMPT),
        ("human", _HUMAN_PROMPT),
    ]
).partial(format_instructions=_parser.get_format_instructions())


def _get_llm() -> ChatGroq:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at https://console.groq.com "
            "and put it in your .env file."
        )
    return ChatGroq(
        model=GROQ_MODEL,
        api_key=GROQ_API_KEY,
        temperature=0.1,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def _fallback_recommendation(reason: str) -> RootCauseRecommendation:
    """A safe, deterministic fallback used when the LLM is unreachable or
    returns something that can't be validated. Always escalates to a human
    rather than guessing, since that's the safest default for revenue-impacting
    decisions.
    """
    return RootCauseRecommendation(
        root_cause="Unable to determine root cause automatically.",
        recommended_action="ESCALATE_TO_HUMAN",
        reason=f"Falling back to human review because: {reason}",
        confidence=0.0,
    )


def get_recommendation(case: dict, ml_probability: float, ml_risk_level: str) -> RootCauseRecommendation:
    """Analyze a case and return a validated RootCauseRecommendation.

    Never raises: on any LLM/parsing failure this returns a safe
    ESCALATE_TO_HUMAN fallback so the agent pipeline can always continue.
    """
    messages = _prompt.format_messages(
        case_type=case.get("case_type", "unknown"),
        failure_reason=case.get("failure_reason", "unknown"),
        transaction_amount=float(case.get("transaction_amount", 0.0)),
        customer_segment=case.get("customer_segment", "unknown"),
        customer_tenure_months=case.get("customer_tenure_months", 0),
        payment_method=case.get("payment_method", "unknown"),
        failure_frequency=case.get("failure_frequency", 0),
        previous_recovery_attempts=case.get("previous_recovery_attempts", 0),
        previous_recovery_success_rate=case.get("previous_recovery_success_rate", 0),
        ml_probability=ml_probability,
        ml_risk_level=ml_risk_level,
    )

    last_error = None
    for attempt in range(2):  # try once, retry once with error feedback
        try:
            llm = _get_llm()
            response = llm.invoke(messages)
            content = response.content if hasattr(response, "content") else str(response)
            return _parser.parse(content)
        except (OutputParserException, ValidationError, json.JSONDecodeError) as e:
            last_error = e
            # feed the error back in for the retry attempt
            messages = messages + [
                (
                    "human",
                    f"Your previous response was invalid: {e}. "
                    "Return ONLY a corrected JSON object matching the schema.",
                )
            ]
            continue
        except Exception as e:  # connection errors, model not found, etc.
            last_error = e
            break

    return _fallback_recommendation(str(last_error))


if __name__ == "__main__":
    demo_case = {
        "case_type": "failed_payment",
        "failure_reason": "card_expired",
        "transaction_amount": 120.0,
        "customer_segment": "consumer",
        "customer_tenure_months": 36,
        "payment_method": "credit_card",
        "failure_frequency": 0.03,
        "previous_recovery_attempts": 0,
        "previous_recovery_success_rate": 0.9,
    }
    result = get_recommendation(demo_case, ml_probability=0.977, ml_risk_level="low")
    print(result.model_dump_json(indent=2))