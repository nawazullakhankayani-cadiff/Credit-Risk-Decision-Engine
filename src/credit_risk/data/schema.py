"""Applicant input contract and validation.

Uses pydantic when available (the production path, also used by the FastAPI
service); otherwise falls back to a dependency-free validator so the package and
its tests run in any environment.
"""
from __future__ import annotations
from typing import Any, Dict, List, Tuple

FEATURES: List[str] = [
    "loan_amount",          # requested principal (GBP)
    "annual_income",        # gross annual income (GBP)
    "employment_length",    # years in current employment
    "debt_to_income",       # existing monthly debt / monthly income (0-1+)
    "credit_utilization",   # revolving balance / limit (0-1+)
    "num_delinquencies_2y", # count of 30+ day delinquencies in last 2 years
    "num_open_accounts",    # open credit lines
    "credit_history_length",# years since first credit line
    "num_recent_inquiries", # hard inquiries in last 6 months
    "loan_term_months",     # 36 or 60
    "interest_rate",        # offered APR (%)
    "home_ownership_code",  # 0=rent, 1=mortgage, 2=own
]

# (min, max) sanity bounds used by the dependency-free validator.
_BOUNDS: Dict[str, Tuple[float, float]] = {
    "loan_amount": (500, 100_000),
    "annual_income": (1, 5_000_000),  # strictly positive — matches Applicant(gt=0)
    "employment_length": (0, 60),
    "debt_to_income": (0, 5),
    "credit_utilization": (0, 3),
    "num_delinquencies_2y": (0, 50),
    "num_open_accounts": (0, 100),
    "credit_history_length": (0, 80),
    "num_recent_inquiries": (0, 50),
    "loan_term_months": (12, 84),
    "interest_rate": (0, 60),
    "home_ownership_code": (0, 2),
}


class ValidationError(ValueError):
    pass


def validate_record(record: Dict[str, Any]) -> Dict[str, float]:
    """Validate and coerce a single applicant record. Raises ValidationError."""
    cleaned: Dict[str, float] = {}
    missing = [f for f in FEATURES if f not in record or record[f] is None]
    if missing:
        raise ValidationError(f"missing required fields: {missing}")
    for f in FEATURES:
        try:
            v = float(record[f])
        except (TypeError, ValueError):
            raise ValidationError(f"field '{f}' must be numeric, got {record[f]!r}")
        lo, hi = _BOUNDS[f]
        if not (lo <= v <= hi):
            raise ValidationError(f"field '{f}'={v} outside plausible range [{lo}, {hi}]")
        cleaned[f] = v
    if cleaned["annual_income"] <= 0:
        raise ValidationError("annual_income must be positive")
    return cleaned


try:  # Production schema for the API layer.
    from pydantic import BaseModel, Field

    class Applicant(BaseModel):
        loan_amount: float = Field(..., ge=500, le=100_000)
        annual_income: float = Field(..., gt=0, le=5_000_000)
        employment_length: float = Field(..., ge=0, le=60)
        debt_to_income: float = Field(..., ge=0, le=5)
        credit_utilization: float = Field(..., ge=0, le=3)
        num_delinquencies_2y: int = Field(..., ge=0, le=50)
        num_open_accounts: int = Field(..., ge=0, le=100)
        credit_history_length: float = Field(..., ge=0, le=80)
        num_recent_inquiries: int = Field(..., ge=0, le=50)
        loan_term_months: int = Field(..., ge=12, le=84)
        interest_rate: float = Field(..., ge=0, le=60)
        home_ownership_code: int = Field(..., ge=0, le=2)

        def to_features(self) -> Dict[str, float]:
            return {f: float(getattr(self, f)) for f in FEATURES}

    HAS_PYDANTIC = True
except Exception:  # pragma: no cover - exercised only without pydantic
    Applicant = None  # type: ignore
    HAS_PYDANTIC = False
