"""
RecoverAI - Shared ML utilities
================================
Central definitions for feature schema, preprocessing pipeline, and file paths
so that train.py / evaluate.py / predict.py all stay perfectly consistent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
ML_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(ML_DIR)
DATA_PATH = os.path.join(PROJECT_ROOT, "data", "cases.csv")
ARTIFACTS_DIR = os.path.join(ML_DIR, "artifacts")
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "recoverability_model.joblib")
METRICS_PATH = os.path.join(ARTIFACTS_DIR, "metrics.json")
FEATURE_META_PATH = os.path.join(ARTIFACTS_DIR, "feature_meta.json")

os.makedirs(ARTIFACTS_DIR, exist_ok=True)

# --------------------------------------------------------------------------
# Feature schema
# --------------------------------------------------------------------------
# IMPORTANT: these are the ONLY columns available *before* a recovery action
# is decided. Anything generated after the decision (actual_action,
# recovery_result, recovered_amount) or the synthetic latent probability
# (recoverable_probability_latent) would leak the label and must be excluded.

TARGET_COL = "recoverable"

NUMERIC_FEATURES = [
    "transaction_amount",
    "customer_tenure_months",
    "successful_payments_count",
    "failed_payments_count",
    "failure_frequency",
    "invoice_or_subscription_age_days",
    "checkout_value",
    "previous_recovery_attempts",
    "previous_recovery_success_rate",
]

CATEGORICAL_FEATURES = [
    "case_type",
    "payment_method",
    "gateway",
    "customer_segment",
    "failure_reason",
]

LEAKAGE_COLUMNS = [
    "recoverable_probability_latent",
    "actual_action",
    "recovery_result",
    "recovered_amount",
]

ID_COLUMNS = ["case_id", "customer_id"]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


@dataclass
class Dataset:
    X: pd.DataFrame
    y: pd.Series
    raw: pd.DataFrame


def load_dataset(path: str = DATA_PATH) -> Dataset:
    df = pd.read_csv(path)
    missing = [c for c in ALL_FEATURES + [TARGET_COL] if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing expected columns: {missing}")
    X = df[ALL_FEATURES].copy()
    y = df[TARGET_COL].copy()
    return Dataset(X=X, y=y, raw=df)


def build_preprocessor() -> ColumnTransformer:
    """Build the sklearn ColumnTransformer used ahead of any estimator.

    Numeric: median impute + standard scale.
    Categorical: most-frequent impute + one-hot encode (unknown-safe).
    """
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, NUMERIC_FEATURES),
            ("cat", categorical_pipeline, CATEGORICAL_FEATURES),
        ]
    )
    return preprocessor
