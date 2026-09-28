"""
RecoverAI - Label Humanizer (backend)
========================================
Mirrors lib/labels.ts on the frontend: converts raw enum-style values
(RETRY_PAYMENT, card_expired, etc.) into clean, human-readable words for
use in execution_log messages and any other user-facing text generated
server-side. Underlying stored values (case_type, recommended_action,
etc.) are NEVER changed -- only the text written into log messages.
"""

from __future__ import annotations

CUSTOM_LABELS = {
    "RETRY_PAYMENT": "Retry Payment",
    "OFFER_RETRY": "Offer Retry",
    "SEND_PAYMENT_REMINDER": "Send Payment Reminder",
    "SEND_EMAIL": "Send Email",
    "ESCALATE_TO_HUMAN": "Escalate to Human",
    "NO_ACTION": "No Action",
    "failed_payment": "failed payment",
    "abandoned_checkout": "abandoned checkout",
    "failed_subscription": "failed subscription",
    "overdue_invoice": "overdue invoice",
    "card_expired": "card expired",
    "insufficient_funds": "insufficient funds",
    "card_declined_generic": "card declined",
    "bank_processing_error": "bank processing error",
    "fraud_flag": "fraud flag",
    "network_timeout": "network timeout",
    "incorrect_billing_details": "incorrect billing details",
    "subscription_cancelled_by_bank": "subscription cancelled by bank",
    "invoice_disputed": "invoice disputed",
    "customer_unresponsive": "customer unresponsive",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "SUCCESS": "successful",
    "FAILED": "unsuccessful",
    "ESCALATED": "escalated to a human",
    "BLOCKED": "blocked by policy",
    "APPROVED": "approved",
    "REJECTED": "rejected",
}


def humanize(value: str | None) -> str:
    if not value:
        return "unknown"
    if value in CUSTOM_LABELS:
        return CUSTOM_LABELS[value]
    return value.replace("_", " ")