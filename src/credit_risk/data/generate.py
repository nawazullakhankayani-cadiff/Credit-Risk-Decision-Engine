"""Synthetic Lending-Club-style loan book generator.

Why synthetic: the real Lending Club dataset is large and licence-restricted, so
this repo ships a reproducible generator that mimics its schema and, crucially,
embeds a realistic default-generating process so models learn genuine signal.
To use the real data instead, drop a CSV with the columns in
``credit_risk.data.schema.FEATURES`` (+ a ``default`` target) into ``data/`` and
point ``train.py`` at it.

The default process is a logistic function of risk drivers with non-linearities
and interactions (so tree models add value over a linear baseline), plus label
noise to keep the problem realistic (AUC well below 1.0).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from credit_risk.data.schema import FEATURES


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def generate(n: int = 30_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    annual_income = np.clip(rng.lognormal(mean=10.5, sigma=0.5, size=n), 8_000, 500_000)
    employment_length = np.clip(rng.gamma(shape=2.0, scale=3.0, size=n), 0, 45)
    loan_amount = np.clip(rng.lognormal(mean=9.2, sigma=0.6, size=n), 500, 80_000)
    debt_to_income = np.clip(rng.beta(2.0, 5.0, size=n) * 1.4, 0, 2.5)
    credit_utilization = np.clip(rng.beta(2.0, 4.0, size=n) * 1.2, 0, 1.8)
    num_delinquencies_2y = rng.poisson(0.3, size=n)
    num_open_accounts = np.clip(rng.poisson(9, size=n), 0, 60)
    credit_history_length = np.clip(rng.gamma(3.0, 4.0, size=n), 0, 60)
    num_recent_inquiries = rng.poisson(1.1, size=n)
    loan_term_months = rng.choice([36, 60], size=n, p=[0.7, 0.3])
    home_ownership_code = rng.choice([0, 1, 2], size=n, p=[0.45, 0.42, 0.13])

    # Offered APR rises with risk drivers (mimicking a real pricing engine).
    interest_rate = np.clip(
        6.0
        + 9.0 * debt_to_income
        + 6.0 * credit_utilization
        + 1.2 * num_delinquencies_2y
        + 0.8 * num_recent_inquiries
        + rng.normal(0, 1.5, size=n),
        3.0, 35.0,
    )

    loan_to_income = loan_amount / annual_income

    # Latent log-odds of default. Coefficients chosen to be directionally sound.
    logit = (
        -4.2
        + 2.4 * debt_to_income
        + 1.9 * credit_utilization
        + 0.55 * num_delinquencies_2y
        + 0.18 * num_recent_inquiries
        + 1.3 * loan_to_income
        + 0.08 * (interest_rate - 12.0)
        - 0.04 * employment_length
        - 0.015 * credit_history_length
        - 0.35 * (home_ownership_code == 2)   # outright owners safer
        + 0.9 * (loan_term_months == 60)
        # interaction: high utilisation AND prior delinquency is disproportionately risky
        + 0.7 * (credit_utilization > 0.8) * (num_delinquencies_2y > 0)
        # non-linear income protection that saturates
        - 0.5 * np.tanh((annual_income - 40_000) / 40_000)
    )
    logit += rng.normal(0, 0.6, size=n)  # label noise -> realistic separability
    pd_true = _sigmoid(logit)
    default = (rng.uniform(size=n) < pd_true).astype(int)

    df = pd.DataFrame({
        "loan_amount": loan_amount.round(0),
        "annual_income": annual_income.round(0),
        "employment_length": employment_length.round(1),
        "debt_to_income": debt_to_income.round(4),
        "credit_utilization": credit_utilization.round(4),
        "num_delinquencies_2y": num_delinquencies_2y,
        "num_open_accounts": num_open_accounts,
        "credit_history_length": credit_history_length.round(1),
        "num_recent_inquiries": num_recent_inquiries,
        "loan_term_months": loan_term_months,
        "interest_rate": interest_rate.round(2),
        "home_ownership_code": home_ownership_code,
        "default": default,
    })
    return df[FEATURES + ["default"]]


if __name__ == "__main__":
    import sys
    from credit_risk.config import PATHS
    PATHS.data.mkdir(parents=True, exist_ok=True)
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30_000
    out = PATHS.data / "loans.csv"
    generate(n).to_csv(out, index=False)
    print(f"wrote {out} ({n} rows)")
