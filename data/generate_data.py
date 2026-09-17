"""
RecoverAI - Synthetic Dataset Generator
=========================================
Generates a realistic synthetic dataset of revenue-recovery cases
(failed payments, abandoned checkouts, failed subscriptions, overdue invoices).

The generator builds *meaningful, non-trivial* relationships between
features and the `recoverable` label so that a downstream ML model has
real signal to learn from (not random noise), while still including
realistic noise so the problem isn't trivially separable.

Usage:
    python data/generate_data.py --rows 20000 --seed 42 --out data/cases.csv
"""

from __future__ import annotations

import argparse
import uuid
from dataclasses import dataclass

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Config / vocab
# --------------------------------------------------------------------------

CASE_TYPES = ["failed_payment", "abandoned_checkout", "failed_subscription", "overdue_invoice"]
CASE_TYPE_WEIGHTS = [0.35, 0.25, 0.25, 0.15]

PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "bank_transfer", "digital_wallet"]
PAYMENT_METHOD_WEIGHTS = [0.42, 0.20, 0.15, 0.13, 0.10]

GATEWAYS = ["stripe", "adyen", "braintree", "paypal_gateway", "worldpay"]

CUSTOMER_SEGMENTS = ["enterprise", "smb", "consumer", "startup"]
SEGMENT_WEIGHTS = [0.10, 0.25, 0.55, 0.10]

FAILURE_REASONS = [
    "insufficient_funds",
    "card_expired",
    "card_declined_generic",
    "bank_processing_error",
    "fraud_flag",
    "network_timeout",
    "incorrect_billing_details",
    "subscription_cancelled_by_bank",
    "invoice_disputed",
    "customer_unresponsive",
]

ACTIONS = [
    "RETRY_PAYMENT",
    "SEND_PAYMENT_REMINDER",
    "SEND_EMAIL",
    "OFFER_RETRY",
    "ESCALATE_TO_HUMAN",
    "NO_ACTION",
]

RECOVERY_RESULTS = ["SUCCESS", "FAILED", "ESCALATED", "BLOCKED"]

RNG_DEFAULT_SEED = 42


@dataclass
class GenConfig:
    rows: int = 20_000
    seed: int = RNG_DEFAULT_SEED


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate_dataset(cfg: GenConfig) -> pd.DataFrame:
    rng = np.random.default_rng(cfg.seed)
    n = cfg.rows

    # ---------------- core categorical features ----------------
    case_type = rng.choice(CASE_TYPES, size=n, p=CASE_TYPE_WEIGHTS)
    payment_method = rng.choice(PAYMENT_METHODS, size=n, p=PAYMENT_METHOD_WEIGHTS)
    gateway = rng.choice(GATEWAYS, size=n)
    customer_segment = rng.choice(CUSTOMER_SEGMENTS, size=n, p=SEGMENT_WEIGHTS)
    failure_reason = rng.choice(FAILURE_REASONS, size=n)

    # ---------------- numeric features ----------------
    # Transaction amount: segment-dependent log-normal
    segment_base_amount = {
        "enterprise": 5000,
        "smb": 800,
        "consumer": 120,
        "startup": 350,
    }
    base_amt = np.array([segment_base_amount[s] for s in customer_segment])
    transaction_amount = np.round(
        base_amt * rng.lognormal(mean=0.0, sigma=0.6, size=n), 2
    )
    transaction_amount = np.clip(transaction_amount, 5, 250_000)

    # Customer tenure in months (0 - 120)
    customer_tenure = rng.gamma(shape=2.2, scale=10.0, size=n)
    customer_tenure = np.clip(customer_tenure, 0, 120).round(1)

    # Historical successful / failed payments — more tenure => more history
    history_len = np.clip((customer_tenure / 2.5) + rng.normal(0, 3, n), 0, 60).astype(int)
    # base failure propensity varies per-customer (latent trait)
    latent_failure_propensity = rng.beta(2, 6, size=n)  # skewed low = mostly reliable customers
    failed_payments_count = np.array(
        [rng.binomial(h, p) if h > 0 else 0 for h, p in zip(history_len, latent_failure_propensity)]
    )
    successful_payments_count = history_len - failed_payments_count

    failure_frequency = np.where(
        history_len > 0, failed_payments_count / np.maximum(history_len, 1), 0.0
    ).round(3)

    # invoice/subscription age (days) - relevant mostly for invoice/subscription case types
    invoice_or_sub_age_days = np.clip(rng.gamma(shape=2.0, scale=15.0, size=n), 0, 365).round(0)

    # checkout value (for abandoned checkouts specifically; else derived from transaction amount)
    checkout_value = np.where(
        case_type == "abandoned_checkout",
        np.round(transaction_amount * rng.uniform(0.8, 1.2, n), 2),
        np.round(transaction_amount * rng.uniform(0.95, 1.0, n), 2),
    )

    # previous recovery attempts / history
    previous_recovery_attempts = rng.poisson(lam=0.8, size=n)
    previous_recovery_attempts = np.clip(previous_recovery_attempts, 0, 8)
    # previous recovery success rate (latent trait correlated inversely with failure propensity)
    prev_recovery_success_rate = np.clip(
        1.0 - latent_failure_propensity + rng.normal(0, 0.15, n), 0, 1
    ).round(3)

    # ---------------- LATENT SCORE -> recoverable probability ----------------
    # Build a linear latent score from meaningful, interpretable drivers, then
    # squash through a sigmoid. Coefficients are intentionally chosen to create
    # realistic, explainable relationships:
    #   + higher tenure -> more recoverable
    #   + more prior successful payments -> more recoverable
    #   + higher failure_frequency -> less recoverable
    #   + very high transaction amount -> slightly less recoverable (harder to recover big amounts)
    #   + more previous recovery attempts already tried -> diminishing returns (less recoverable)
    #   + higher prev_recovery_success_rate -> more recoverable
    #   + certain failure reasons are inherently more/less recoverable
    #   + certain case types are inherently more/less recoverable
    #   + certain payment methods slightly affect recoverability (retry friction)

    failure_reason_effect = {
        "insufficient_funds": -0.3,
        "card_expired": 0.4,          # easy fix -> often recoverable via update
        "card_declined_generic": 0.0,
        "bank_processing_error": 0.6,  # transient -> often recoverable
        "fraud_flag": -1.6,            # rarely recoverable
        "network_timeout": 0.8,        # transient -> very recoverable
        "incorrect_billing_details": 0.3,
        "subscription_cancelled_by_bank": -0.8,
        "invoice_disputed": -1.0,
        "customer_unresponsive": -0.9,
    }
    case_type_effect = {
        "failed_payment": 0.3,
        "abandoned_checkout": -0.2,
        "failed_subscription": 0.0,
        "overdue_invoice": -0.1,
    }
    payment_method_effect = {
        "credit_card": 0.2,
        "debit_card": 0.0,
        "paypal": 0.1,
        "bank_transfer": -0.3,
        "digital_wallet": 0.15,
    }
    segment_effect = {
        "enterprise": 0.5,
        "smb": 0.2,
        "consumer": -0.1,
        "startup": 0.0,
    }

    fr_eff = np.array([failure_reason_effect[f] for f in failure_reason])
    ct_eff = np.array([case_type_effect[c] for c in case_type])
    pm_eff = np.array([payment_method_effect[p] for p in payment_method])
    seg_eff = np.array([segment_effect[s] for s in customer_segment])

    amount_z = (np.log1p(transaction_amount) - np.log1p(transaction_amount).mean()) / (
        np.log1p(transaction_amount).std() + 1e-6
    )

    latent_score = (
        -0.6
        + 0.015 * customer_tenure
        + 0.05 * successful_payments_count
        - 3.2 * failure_frequency
        - 0.35 * amount_z
        - 0.30 * previous_recovery_attempts
        + 1.8 * prev_recovery_success_rate
        + fr_eff
        + ct_eff
        + pm_eff
        + seg_eff
        + rng.normal(0, 0.55, n)  # irreducible noise
    )

    recoverable_prob = _sigmoid(latent_score)
    recoverable = (rng.uniform(0, 1, n) < recoverable_prob).astype(int)

    # ---------------- actual action taken (historical / simulated ops team) ----------------
    # Higher-confidence recoverable cases historically got RETRY_PAYMENT / OFFER_RETRY,
    # low-recoverable or fraud cases got ESCALATE_TO_HUMAN or NO_ACTION.
    actual_action = []
    for i in range(n):
        p = recoverable_prob[i]
        reason = failure_reason[i]
        amt = transaction_amount[i]
        if reason == "fraud_flag" or reason == "invoice_disputed":
            choice = rng.choice(["ESCALATE_TO_HUMAN", "NO_ACTION"], p=[0.75, 0.25])
        elif amt > 10_000:
            choice = rng.choice(
                ["ESCALATE_TO_HUMAN", "SEND_PAYMENT_REMINDER", "RETRY_PAYMENT"], p=[0.6, 0.25, 0.15]
            )
        elif p > 0.65:
            choice = rng.choice(
                ["RETRY_PAYMENT", "OFFER_RETRY", "SEND_EMAIL"], p=[0.55, 0.30, 0.15]
            )
        elif p > 0.35:
            choice = rng.choice(
                ["SEND_PAYMENT_REMINDER", "SEND_EMAIL", "OFFER_RETRY", "RETRY_PAYMENT"],
                p=[0.35, 0.30, 0.20, 0.15],
            )
        else:
            choice = rng.choice(["ESCALATE_TO_HUMAN", "NO_ACTION", "SEND_EMAIL"], p=[0.45, 0.35, 0.20])
        actual_action.append(choice)
    actual_action = np.array(actual_action)

    # ---------------- recovery result + recovered amount ----------------
    recovery_result = []
    recovered_amount = np.zeros(n)
    for i in range(n):
        action = actual_action[i]
        p = recoverable_prob[i]
        amt = transaction_amount[i]
        if action == "NO_ACTION":
            result = "FAILED"
        elif action == "ESCALATE_TO_HUMAN":
            # human intervention succeeds at moderate rate influenced by p
            result = "ESCALATED" if rng.uniform() < 0.5 else ("SUCCESS" if rng.uniform() < p else "FAILED")
        else:
            # automated actions succeed roughly proportional to recoverable probability,
            # with a bit of extra noise per-action-type effectiveness
            action_boost = {
                "RETRY_PAYMENT": 0.05,
                "OFFER_RETRY": 0.0,
                "SEND_PAYMENT_REMINDER": -0.05,
                "SEND_EMAIL": -0.10,
            }.get(action, 0.0)
            success_p = np.clip(p + action_boost, 0.02, 0.97)
            result = "SUCCESS" if rng.uniform() < success_p else "FAILED"
            if result == "FAILED" and rng.uniform() < 0.1:
                result = "BLOCKED"  # policy / gateway blocked retry occasionally

        recovery_result.append(result)
        if result == "SUCCESS":
            recovered_amount[i] = round(amt * rng.uniform(0.9, 1.0), 2)
        else:
            recovered_amount[i] = 0.0

    recovery_result = np.array(recovery_result)

    # ---------------- assemble dataframe ----------------
    df = pd.DataFrame(
        {
            "case_id": [f"CASE-{uuid.uuid4().hex[:10].upper()}" for _ in range(n)],
            "customer_id": [f"CUST-{rng.integers(1, n // 3):06d}" for _ in range(n)],
            "case_type": case_type,
            "transaction_amount": transaction_amount,
            "customer_tenure_months": customer_tenure,
            "successful_payments_count": successful_payments_count,
            "failed_payments_count": failed_payments_count,
            "failure_frequency": failure_frequency,
            "payment_method": payment_method,
            "gateway": gateway,
            "customer_segment": customer_segment,
            "invoice_or_subscription_age_days": invoice_or_sub_age_days.astype(int),
            "checkout_value": checkout_value,
            "previous_recovery_attempts": previous_recovery_attempts,
            "previous_recovery_success_rate": prev_recovery_success_rate,
            "failure_reason": failure_reason,
            "recoverable": recoverable,
            "recoverable_probability_latent": recoverable_prob.round(4),  # kept for analysis/debug
            "actual_action": actual_action,
            "recovery_result": recovery_result,
            "recovered_amount": recovered_amount.round(2),
        }
    )

    return df


def main():
    parser = argparse.ArgumentParser(description="Generate RecoverAI synthetic dataset")
    parser.add_argument("--rows", type=int, default=20_000, help="Number of cases to generate")
    parser.add_argument("--seed", type=int, default=RNG_DEFAULT_SEED, help="Random seed")
    parser.add_argument("--out", type=str, default="data/cases.csv", help="Output CSV path")
    args = parser.parse_args()

    cfg = GenConfig(rows=args.rows, seed=args.seed)
    df = generate_dataset(cfg)
    df.to_csv(args.out, index=False)

    # ---- sanity print summary (helps verify realistic relationships) ----
    print(f"Generated {len(df):,} rows -> {args.out}")
    print(f"Recoverable rate overall: {df['recoverable'].mean():.3f}")
    print("\nRecoverable rate by failure_reason:")
    print(df.groupby("failure_reason")["recoverable"].mean().sort_values(ascending=False).round(3))
    print("\nRecoverable rate by customer_segment:")
    print(df.groupby("customer_segment")["recoverable"].mean().sort_values(ascending=False).round(3))
    print("\nRecovery result distribution:")
    print(df["recovery_result"].value_counts(normalize=True).round(3))
    print(f"\nTotal transaction value at risk: ${df['transaction_amount'].sum():,.2f}")
    print(f"Total recovered (simulated): ${df['recovered_amount'].sum():,.2f}")


if __name__ == "__main__":
    main()
