"""
RecoverAI - Currency Utilities
================================
All amounts in the dataset and ML model are stored in USD (the platform is
currency-agnostic at its core). This module adds INR display alongside USD
wherever a dollar amount is shown to a person, since exchange rates move
constantly and portfolio/demo accuracy doesn't require live forex data.

The rate is configurable via the USD_TO_INR_RATE environment variable so it
can be kept reasonably current without touching code. It is NOT a live/API
rate — this is a display convenience for a simulated system, not a
financial instrument.
"""

from __future__ import annotations

import os

# Approximate, manually-configurable rate. Update via .env as needed.
USD_TO_INR_RATE = float(os.environ.get("USD_TO_INR_RATE", "88.0"))


def to_inr(amount_usd: float) -> float:
    return round(amount_usd * USD_TO_INR_RATE, 2)


def format_usd(amount_usd: float) -> str:
    return f"${amount_usd:,.2f}"


def format_inr(amount_usd: float) -> str:
    return f"₹{to_inr(amount_usd):,.2f}"


def format_dual(amount_usd: float) -> str:
    """The standard display format used in policy reasons, logs, and (later) the dashboard."""
    return f"{format_usd(amount_usd)} ({format_inr(amount_usd)})"