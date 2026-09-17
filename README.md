# RecoverAI — Agentic AI Revenue Recovery Platform

**Status: Phase 1-2 complete (synthetic data + ML model). More phases in progress.**

RecoverAI is a portfolio project that simulates an AI system for recovering
at-risk revenue from failed payments, abandoned checkouts, failed
subscriptions, and overdue invoices. **No real financial transactions are
ever performed — every recovery action is simulated.**

## Workflow (full system, in progress)

```
Business Data → ML Recoverability Prediction → Root Cause Analysis →
LangGraph Agent → Action Recommendation → Policy Validation →
Simulated Recovery → Outcome → Analytics
```

## What's built so far

### Phase 1 — Synthetic dataset (`data/generate_data.py`)
Generates 20,000 realistic revenue-recovery cases with meaningful,
explainable relationships between features and the `recoverable` label
(e.g. fraud and disputed invoices are hard to recover; transient errors
like network timeouts are easy to recover).

```bash
python data/generate_data.py --rows 20000 --seed 42 --out data/cases.csv
```

### Phase 2 — ML model (`ml/`)
- `ml/common.py` — shared feature schema + preprocessing pipeline (median
  impute + scale for numeric, most-frequent impute + one-hot for categorical).
  Explicitly excludes leakage columns (`recovery_result`, `recovered_amount`,
  the synthetic latent probability).
- `ml/train.py` — 60/20/20 stratified split; compares Logistic Regression,
  Random Forest, and Gradient Boosting on validation ROC-AUC; tunes the
  decision threshold for F1; refits the winner on train+val; evaluates once
  on the untouched test set; persists the pipeline + metrics.
- `ml/evaluate.py` — reloads the saved model and reproduces the same test
  split for an independent sanity check.
- `ml/predict.py` — single-case / batch inference used by the (future)
  FastAPI backend.

```bash
python ml/train.py
python ml/evaluate.py
python ml/predict.py
```

**Measured test-set metrics** (Logistic Regression selected, threshold 0.29):

| Metric | Value |
|---|---|
| Accuracy | 0.696 |
| Precision | 0.668 |
| Recall | 0.917 |
| F1 | 0.773 |
| ROC-AUC | 0.784 |

Full metrics are saved to `ml/artifacts/metrics.json` after each training run.

## Setup

```bash
# 1. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate data, train, evaluate, predict
python data/generate_data.py
python ml/train.py
python ml/evaluate.py
python ml/predict.py
```

## Coming next
Phase 3 (rule-based baseline), Phase 4-6 (LangChain + LangGraph agent +
policy engine), Phase 7-8 (PostgreSQL + FastAPI), Phase 9 (Next.js
dashboard), Phase 10-12 (tests, Docker, deployment).
