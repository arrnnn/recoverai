"""
RecoverAI - Policy Engine
===========================
The deterministic guardrail layer between the LLM's recommendation and
actual execution. The LLM recommends; this engine decides what is actually
allowed to run. Nothing here uses an LLM — every rule is a plain Python
if/else so behavior is 100% predictable, auditable, and testable.

Rule precedence (first match wins — order matters when rules could
otherwise conflict, e.g. a high-value fraud case should be rejected for
fraud, not merely "approved because under the retry limit"):

    1. Restricted / fraud-flagged case          -> always REJECT
    2. High-value transaction                    -> always REJECT
    3. Retry limit exceeded                      -> REJECT
    4. Low LLM confidence                        -> REJECT
    5. Repeated-failure customer                 -> DOWNGRADE action
    6. Excessive reminders already sent          -> DOWNGRADE action
    7. Otherwise                                  -> APPROVE as recommended

Thresholds are module-level constants so they're easy to find, tune, and
reference from tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from currency import format_dual

# --------------------------------------------------------------------------
# Configurable thresholds
# --------------------------------------------------------------------------
HIGH_VALUE_THRESHOLD_USD = 10_000.0
MAX_RETRY_ATTEMPTS = 3
MIN_CONFIDENCE_TO_AUTO_EXECUTE = 0.4
HIGH_FAILURE_FREQUENCY_THRESHOLD = 0.5
MAX_REMINDER_ATTEMPTS = 2

RESTRICTED_FAILURE_REASONS = {"fraud_flag", "invoice_disputed"}

# Actions that actually "do" something and therefore need policy approval.
# NO_ACTION and ESCALATE_TO_HUMAN don't execute anything themselves.
EXECUTABLE_ACTIONS = {"RETRY_PAYMENT", "OFFER_RETRY", "SEND_PAYMENT_REMINDER", "SEND_EMAIL"}

RETRY_TYPE_ACTIONS = {"RETRY_PAYMENT", "OFFER_RETRY"}
REMINDER_TYPE_ACTIONS = {"SEND_PAYMENT_REMINDER", "SEND_EMAIL"}


@dataclass
class PolicyResult:
    decision: str  # "APPROVED" | "REJECTED" | "N/A"
    triggered_rule: str
    reason: str
    original_action: str
    final_action: str
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "triggered_rule": self.triggered_rule,
            "reason": self.reason,
            "original_action": self.original_action,
            "final_action": self.final_action,
            **self.extra,
        }


def _not_applicable(action: str) -> PolicyResult:
    return PolicyResult(
        decision="N/A",
        triggered_rule="not_executable",
        reason=f"{action} does not execute anything, so no policy approval is required.",
        original_action=action,
        final_action=action,
    )


def check_policy(
    case: dict[str, Any],
    recommended_action: str,
    llm_confidence: float,
) -> PolicyResult:
    """Run the full deterministic rule chain and return the final decision."""

    if recommended_action not in EXECUTABLE_ACTIONS:
        return _not_applicable(recommended_action)

    amount = float(case.get("transaction_amount", 0.0))
    failure_reason = case.get("failure_reason", "")
    previous_attempts = int(case.get("previous_recovery_attempts", 0))
    failure_frequency = float(case.get("failure_frequency", 0.0))

    # ---- Rule 1: restricted / fraud-flagged ----
    if failure_reason in RESTRICTED_FAILURE_REASONS:
        return PolicyResult(
            decision="REJECTED",
            triggered_rule="restricted_failure_reason",
            reason=(
                f"Failure reason '{failure_reason}' is restricted from automated action "
                f"and requires human review."
            ),
            original_action=recommended_action,
            final_action="ESCALATE_TO_HUMAN",
        )

    # ---- Rule 2: high-value transaction ----
    if recommended_action in RETRY_TYPE_ACTIONS and amount > HIGH_VALUE_THRESHOLD_USD:
        return PolicyResult(
            decision="REJECTED",
            triggered_rule="high_value_transaction",
            reason=(
                f"Transaction amount {format_dual(amount)} exceeds the "
                f"{format_dual(HIGH_VALUE_THRESHOLD_USD)} auto-approval limit; "
                f"requires human sign-off regardless of model confidence."
            ),
            original_action=recommended_action,
            final_action="ESCALATE_TO_HUMAN",
            extra={"threshold_usd": HIGH_VALUE_THRESHOLD_USD},
        )

    # ---- Rule 3: retry limit exceeded ----
    if recommended_action in RETRY_TYPE_ACTIONS and previous_attempts >= MAX_RETRY_ATTEMPTS:
        return PolicyResult(
            decision="REJECTED",
            triggered_rule="retry_limit_exceeded",
            reason=(
                f"This case has already had {previous_attempts} recovery attempts "
                f"(limit: {MAX_RETRY_ATTEMPTS}); further automated retries are blocked."
            ),
            original_action=recommended_action,
            final_action="ESCALATE_TO_HUMAN",
            extra={"previous_attempts": previous_attempts, "limit": MAX_RETRY_ATTEMPTS},
        )

    # ---- Rule 4: low LLM confidence ----
    if llm_confidence < MIN_CONFIDENCE_TO_AUTO_EXECUTE:
        return PolicyResult(
            decision="REJECTED",
            triggered_rule="low_confidence",
            reason=(
                f"LLM confidence {llm_confidence:.2f} is below the "
                f"{MIN_CONFIDENCE_TO_AUTO_EXECUTE:.2f} auto-execution threshold."
            ),
            original_action=recommended_action,
            final_action="ESCALATE_TO_HUMAN",
            extra={"llm_confidence": llm_confidence, "threshold": MIN_CONFIDENCE_TO_AUTO_EXECUTE},
        )

    # ---- Rule 5: repeated-failure customer -> downgrade retries to a reminder ----
    if recommended_action in RETRY_TYPE_ACTIONS and failure_frequency > HIGH_FAILURE_FREQUENCY_THRESHOLD:
        return PolicyResult(
            decision="APPROVED",
            triggered_rule="repeated_failure_downgrade",
            reason=(
                f"Historical failure frequency {failure_frequency:.2f} exceeds "
                f"{HIGH_FAILURE_FREQUENCY_THRESHOLD:.2f}; downgrading an automated retry "
                f"to a payment reminder instead."
            ),
            original_action=recommended_action,
            final_action="SEND_PAYMENT_REMINDER",
            extra={"failure_frequency": failure_frequency},
        )

    # ---- Rule 6: excessive reminders already sent -> escalate instead ----
    if recommended_action in REMINDER_TYPE_ACTIONS and previous_attempts >= MAX_REMINDER_ATTEMPTS:
        return PolicyResult(
            decision="APPROVED",
            triggered_rule="excessive_reminders_downgrade",
            reason=(
                f"{previous_attempts} prior attempts already made (limit: {MAX_REMINDER_ATTEMPTS} "
                f"reminders); escalating to a human instead of sending another reminder."
            ),
            original_action=recommended_action,
            final_action="ESCALATE_TO_HUMAN",
            extra={"previous_attempts": previous_attempts, "limit": MAX_REMINDER_ATTEMPTS},
        )

    # ---- Rule 7: otherwise, approve as recommended ----
    return PolicyResult(
        decision="APPROVED",
        triggered_rule="none",
        reason="No policy rule blocked this action; approved as recommended.",
        original_action=recommended_action,
        final_action=recommended_action,
    )