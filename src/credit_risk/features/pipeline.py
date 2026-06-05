"""Feature engineering pipeline.

Pure numpy/pandas so it runs everywhere and is trivially unit-testable. Produces
a deterministic, ordered feature matrix plus engineered ratios that capture
affordability and credit-stress signals lenders care about. The pipeline is
*fit* on training data (to learn standardisation statistics) and then *applied*
to any new record, guaranteeing train/serve parity.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List
import numpy as np
import pandas as pd

from credit_risk.data.schema import FEATURES

ENGINEERED: List[str] = [
    "loan_to_income",
    "monthly_payment_est",
    "payment_to_income",
    "stress_flag",          # high utilisation AND prior delinquency
    "thin_file_flag",       # short history + few accounts
]

ALL_FEATURES: List[str] = FEATURES + ENGINEERED


def _add_engineered(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    monthly_income = out["annual_income"] / 12.0
    out["loan_to_income"] = out["loan_amount"] / out["annual_income"].clip(lower=1.0)
    # Amortised monthly payment estimate from APR + term.
    r = (out["interest_rate"] / 100.0) / 12.0
    n = out["loan_term_months"].clip(lower=1)
    factor = np.where(r > 0, r / (1 - (1 + r) ** (-n)), 1.0 / n)
    out["monthly_payment_est"] = out["loan_amount"] * factor
    out["payment_to_income"] = out["monthly_payment_est"] / monthly_income.clip(lower=1.0)
    out["stress_flag"] = ((out["credit_utilization"] > 0.8) &
                          (out["num_delinquencies_2y"] > 0)).astype(float)
    out["thin_file_flag"] = ((out["credit_history_length"] < 3) &
                             (out["num_open_accounts"] < 3)).astype(float)
    return out


@dataclass
class FeaturePipeline:
    """Fit standardisation stats on train; apply consistently at serve time."""
    means: Dict[str, float] = field(default_factory=dict)
    stds: Dict[str, float] = field(default_factory=dict)
    columns: List[str] = field(default_factory=lambda: list(ALL_FEATURES))
    fitted: bool = False

    def fit(self, df: pd.DataFrame) -> "FeaturePipeline":
        eng = _add_engineered(df)[self.columns]
        self.means = {c: float(eng[c].mean()) for c in self.columns}
        self.stds = {c: float(eng[c].std() or 1.0) for c in self.columns}
        self.fitted = True
        return self

    def transform(self, df: pd.DataFrame, standardize: bool = True) -> pd.DataFrame:
        eng = _add_engineered(df)[self.columns].astype(float)
        if standardize:
            for c in self.columns:
                eng[c] = (eng[c] - self.means.get(c, 0.0)) / (self.stds.get(c, 1.0) or 1.0)
        return eng

    def transform_record(self, record: Dict[str, float], standardize: bool = True) -> np.ndarray:
        df = pd.DataFrame([{k: record[k] for k in FEATURES}])
        return self.transform(df, standardize=standardize).to_numpy()[0]

    def to_dict(self) -> dict:
        return {"means": self.means, "stds": self.stds, "columns": self.columns,
                "fitted": self.fitted}

    @classmethod
    def from_dict(cls, d: dict) -> "FeaturePipeline":
        return cls(means=d["means"], stds=d["stds"], columns=d["columns"],
                   fitted=d.get("fitted", True))
