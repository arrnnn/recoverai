"""
RecoverAI - Seed Demo Data
============================
Populates the database with a varied set of realistic cases via the REAL
running API — not a shortcut. Each case gets a genuine ML prediction, a
genuine Groq LLM call, and a genuine policy-engine decision, exactly like
a case a recruiter creates by hand. This exists purely so a freshly
deployed instance doesn't look empty on first visit.

Usage:
    python backend/seed_demo_data.py
    python backend/seed_demo_data.py --base-url https://your-deployed-api.com

Safe to run multiple times -- it just adds more cases each time.
"""

from __future__ import annotations

import argparse
import sys
import time

import requests

CASES = [
    # low-risk, easy wins
    {
        "case_type": "failed_payment", "transaction_amount": 89.99, "payment_method": "credit_card",
        "gateway": "stripe", "failure_reason": "card_expired", "failure_frequency": 0.02,
        "previous_recovery_attempts": 0, "previous_recovery_success_rate": 0.92,
        "customer_segment": "consumer", "customer_tenure_months": 42,
    },
    {
        "case_type": "failed_subscription", "transaction_amount": 29.0, "payment_method": "digital_wallet",
        "gateway": "adyen", "failure_reason": "network_timeout", "failure_frequency": 0.04,
        "previous_recovery_attempts": 0, "previous_recovery_success_rate": 0.95,
        "customer_segment": "smb", "customer_tenure_months": 18,
    },
    {
        "case_type": "failed_payment", "transaction_amount": 215.5, "payment_method": "debit_card",
        "gateway": "stripe", "failure_reason": "bank_processing_error", "failure_frequency": 0.06,
        "previous_recovery_attempts": 0, "previous_recovery_success_rate": 0.88,
        "customer_segment": "consumer", "customer_tenure_months": 30,
    },
    # abandoned checkouts
    {
        "case_type": "abandoned_checkout", "transaction_amount": 145.0, "payment_method": "paypal",
        "gateway": "paypal_gateway", "failure_reason": "incorrect_billing_details", "failure_frequency": 0.1,
        "previous_recovery_attempts": 0, "previous_recovery_success_rate": 0.7,
        "customer_segment": "consumer", "customer_tenure_months": 6,
    },
    {
        "case_type": "abandoned_checkout", "transaction_amount": 68.25, "payment_method": "credit_card",
        "gateway": "braintree", "failure_reason": "card_declined_generic", "failure_frequency": 0.15,
        "previous_recovery_attempts": 1, "previous_recovery_success_rate": 0.55,
        "customer_segment": "startup", "customer_tenure_months": 3,
    },
    # overdue invoices, mid-size
    {
        "case_type": "overdue_invoice", "transaction_amount": 3200.0, "payment_method": "bank_transfer",
        "gateway": "worldpay", "failure_reason": "customer_unresponsive", "failure_frequency": 0.2,
        "previous_recovery_attempts": 1, "previous_recovery_success_rate": 0.5,
        "customer_segment": "smb", "customer_tenure_months": 14,
    },
    {
        "case_type": "overdue_invoice", "transaction_amount": 890.0, "payment_method": "bank_transfer",
        "gateway": "stripe", "failure_reason": "bank_processing_error", "failure_frequency": 0.08,
        "previous_recovery_attempts": 0, "previous_recovery_success_rate": 0.8,
        "customer_segment": "smb", "customer_tenure_months": 22,
    },
    # repeated failures (policy downgrade demo)
    {
        "case_type": "failed_subscription", "transaction_amount": 49.0, "payment_method": "credit_card",
        "gateway": "adyen", "failure_reason": "insufficient_funds", "failure_frequency": 0.62,
        "previous_recovery_attempts": 1, "previous_recovery_success_rate": 0.2,
        "customer_segment": "consumer", "customer_tenure_months": 8,
    },
    # excessive reminders (policy escalation demo)
    {
        "case_type": "failed_payment", "transaction_amount": 175.0, "payment_method": "digital_wallet",
        "gateway": "stripe", "failure_reason": "card_declined_generic", "failure_frequency": 0.3,
        "previous_recovery_attempts": 3, "previous_recovery_success_rate": 0.25,
        "customer_segment": "consumer", "customer_tenure_months": 11,
    },
    # retry limit exceeded
    {
        "case_type": "failed_payment", "transaction_amount": 60.0, "payment_method": "debit_card",
        "gateway": "stripe", "failure_reason": "card_declined_generic", "failure_frequency": 0.4,
        "previous_recovery_attempts": 4, "previous_recovery_success_rate": 0.1,
        "customer_segment": "consumer", "customer_tenure_months": 4,
    },
    # high-value: policy override showcase
    {
        "case_type": "overdue_invoice", "transaction_amount": 38500.0, "payment_method": "bank_transfer",
        "gateway": "worldpay", "failure_reason": "bank_processing_error", "failure_frequency": 0.03,
        "previous_recovery_attempts": 0, "previous_recovery_success_rate": 0.9,
        "customer_segment": "enterprise", "customer_tenure_months": 48,
    },
    # fraud: hard-reject showcase
    {
        "case_type": "failed_subscription", "transaction_amount": 199.0, "payment_method": "credit_card",
        "gateway": "adyen", "failure_reason": "fraud_flag", "failure_frequency": 0.4,
        "previous_recovery_attempts": 0, "previous_recovery_success_rate": 0.3,
        "customer_segment": "startup", "customer_tenure_months": 1,
    },
    # disputed invoice: hard-reject showcase
    {
        "case_type": "overdue_invoice", "transaction_amount": 1450.0, "payment_method": "bank_transfer",
        "gateway": "stripe", "failure_reason": "invoice_disputed", "failure_frequency": 0.25,
        "previous_recovery_attempts": 1, "previous_recovery_success_rate": 0.4,
        "customer_segment": "smb", "customer_tenure_months": 9,
    },
]


def seed(base_url: str, run_agent: bool = True):
    print(f"Seeding {len(CASES)} demo cases against {base_url} ...\n")

    for i, case in enumerate(CASES, start=1):
        payload = {
            **case,
            "checkout_value": case["transaction_amount"],
            "invoice_or_subscription_age_days": 10,
            "customer_id": f"CUST-SEED-{i:03d}",
        }
        resp = requests.post(f"{base_url}/cases", json=payload, timeout=30)
        if resp.status_code != 201:
            print(f"  [{i}/{len(CASES)}] FAILED to create case: {resp.status_code} {resp.text}")
            continue
        case_id = resp.json()["case_id"]
        print(f"  [{i}/{len(CASES)}] Created {case_id} ({case['case_type']}, ${case['transaction_amount']:,.2f})")

        if not run_agent:
            continue

        analyze_resp = requests.post(f"{base_url}/cases/{case_id}/analyze", timeout=60)
        if analyze_resp.status_code != 200:
            print(f"      analyze FAILED: {analyze_resp.status_code} {analyze_resp.text}")
            continue
        analysis = analyze_resp.json()
        print(f"      -> {analysis['final_action']} (policy: {analysis['policy_decision']})")

        recover_resp = requests.post(f"{base_url}/cases/{case_id}/recover", timeout=30)
        if recover_resp.status_code != 200:
            print(f"      recover FAILED: {recover_resp.status_code} {recover_resp.text}")
            continue
        recovery = recover_resp.json()
        print(f"      -> {recovery['recovery_status']} ({recovery['recovered_amount_display']})")

        time.sleep(0.3)  # be gentle on the free-tier Groq rate limit

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed RecoverAI with demo cases via the live API")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--no-agent", action="store_true", help="Only create cases, skip analyze/recover")
    args = parser.parse_args()

    try:
        health = requests.get(f"{args.base_url}/health", timeout=10)
        if health.status_code != 200:
            print(f"API at {args.base_url} did not respond healthy. Aborting.")
            sys.exit(1)
    except requests.RequestException as e:
        print(f"Could not reach {args.base_url}: {e}")
        sys.exit(1)

    seed(args.base_url, run_agent=not args.no_agent)