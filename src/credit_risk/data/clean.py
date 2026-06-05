"""Robust CSV intake & cleaning.

Takes an arbitrary applicant CSV — messy headers, currency symbols, percentages,
text categories, missing values, junk columns — and returns a tidy frame with the
exact ``schema.FEATURES`` columns, ready to score. Mirrors the in-browser cleaner
on the website so batch results match between the API and the static demo.

Steps: fuzzy-map columns by alias -> coerce values (strip £/$/%/commas, parse
"36 months", map Rent/Mortgage/Own) -> impute missing with training means
(falling back to column medians) -> clip to plausible bounds.

CLI:  python -m credit_risk.data.clean input.csv output.csv
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, Tuple
import numpy as np
import pandas as pd

from credit_risk.data.schema import FEATURES, _BOUNDS

INT_FEATURES = {"num_delinquencies_2y", "num_open_accounts", "num_recent_inquiries",
                "home_ownership_code", "loan_term_months"}

ALIASES: Dict[str, list] = {
    "loan_amount": ["loanamount", "loan", "amount", "principal", "loanamt", "loansize"],
    "annual_income": ["annualincome", "income", "grosssalary", "salary", "yearlyincome", "grossincome", "wage"],
    "employment_length": ["employmentlength", "employment", "emplength", "yearsemployed", "jobyears", "tenure", "yearsinjob"],
    "debt_to_income": ["debttoincome", "dti", "debtincome", "debtratio"],
    "credit_utilization": ["creditutilization", "creditutilisation", "utilization", "utilisation", "util", "creditutil", "revolvingutil"],
    "num_delinquencies_2y": ["numdelinquencies2y", "delinquencies", "delinq", "numdelinq", "delinquencies2y", "pastdue", "latepayments"],
    "num_open_accounts": ["numopenaccounts", "openaccounts", "openacc", "accounts", "numaccounts", "tradelines"],
    "credit_history_length": ["credithistorylength", "credithistory", "historylength", "creditage", "historyyrs", "credithistoryyrs"],
    "num_recent_inquiries": ["numrecentinquiries", "inquiries", "inq", "recentinquiries", "hardinquiries", "enquiries"],
    "loan_term_months": ["loantermmonths", "term", "loanterm", "termmonths", "duration"],
    "interest_rate": ["interestrate", "interest", "rate", "apr", "intrate"],
    "home_ownership_code": ["homeownershipcode", "homeownership", "ownership", "home", "housing", "hometype"],
}


def _norm(h: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(h).lower())


def _build_header_map(columns) -> Dict[str, str]:
    mapping, used = {}, set()
    for feat in FEATURES:
        valid = {_norm(feat), *ALIASES[feat]}
        for col in columns:
            if col in used:
                continue
            if _norm(col) in valid:
                mapping[feat] = col
                used.add(col)
                break
    return mapping


def _coerce(feat: str, raw):
    """Return (value_or_nan, was_missing). NaN signals 'impute later'."""
    if raw is None or (isinstance(raw, float) and np.isnan(raw)) or str(raw).strip() == "":
        return np.nan, True
    s = str(raw).strip()
    if feat == "home_ownership_code":
        low = s.lower()
        if "own" in low:
            return 2.0, False
        if "mort" in low:
            return 1.0, False
        if "rent" in low:
            return 0.0, False
        v = re.sub(r"[^0-9.\-]", "", low)
        return (float(v), False) if v else (np.nan, True)
    pct = "%" in s
    v = re.sub(r"[^0-9.\-]", "", s)
    if v in ("", "-", "."):
        return np.nan, True
    val = float(v)
    if feat == "credit_utilization" and (pct or val > 1.5):
        val /= 100.0
    if feat == "debt_to_income" and ((pct and val > 1.5) or val > 5):
        val /= 100.0
    return val, False


def clean_dataframe(df: pd.DataFrame, fill: Dict[str, float] | None = None
                    ) -> Tuple[pd.DataFrame, dict]:
    """Clean an arbitrary applicant frame into the canonical FEATURES schema."""
    hmap = _build_header_map(df.columns)
    report = {"rows": int(len(df)), "mapped": dict(hmap),
              "missing_columns": [f for f in FEATURES if f not in hmap],
              "ignored_columns": [c for c in df.columns if c not in hmap.values()],
              "imputed_cells": 0, "clipped_cells": 0}

    # First pass: coerce values, tracking which cells were missing.
    coerced = {f: [] for f in FEATURES}
    missing_mask = {f: [] for f in FEATURES}
    for f in FEATURES:
        src = df[hmap[f]] if f in hmap else [None] * len(df)
        for raw in src:
            v, miss = _coerce(f, raw)
            coerced[f].append(v)
            missing_mask[f].append(miss or (isinstance(v, float) and np.isnan(v)))

    out = pd.DataFrame({f: pd.Series(coerced[f], dtype="float64") for f in FEATURES})

    # Determine fill values: provided -> training means via registry -> column median -> bounds midpoint.
    if fill is None:
        fill = _registry_means()
    for f in FEATURES:
        col = out[f]
        n_missing = int(col.isna().sum())
        if n_missing:
            fv = fill.get(f) if fill else None
            if fv is None or (isinstance(fv, float) and np.isnan(fv)):
                fv = col.median()
            if pd.isna(fv):
                lo, hi = _BOUNDS[f]
                fv = (lo + hi) / 2
            out[f] = col.fillna(fv)
            report["imputed_cells"] += n_missing

    # Clip to plausible bounds; round integer features.
    for f in FEATURES:
        lo, hi = _BOUNDS[f]
        before = out[f].copy()
        out[f] = out[f].clip(lo, hi)
        if f in INT_FEATURES:
            out[f] = out[f].round().astype(int)
        report["clipped_cells"] += int((before != out[f]).sum())

    return out[FEATURES], report


def _registry_means() -> Dict[str, float] | None:
    try:
        from credit_risk.config import PATHS
        from credit_risk.models.registry import ModelRegistry
        means = ModelRegistry(PATHS.artifacts).load()["bundle"]["pipeline"]["means"]
        return {f: means[f] for f in FEATURES if f in means}
    except Exception:
        return None


def clean_csv(in_path: str | Path, out_path: str | Path) -> dict:
    df = pd.read_csv(in_path)
    clean, report = clean_dataframe(df)
    clean.to_csv(out_path, index=False)
    return report


if __name__ == "__main__":
    import sys, json
    if len(sys.argv) < 3:
        print("usage: python -m credit_risk.data.clean <input.csv> <output.csv>")
        raise SystemExit(1)
    rep = clean_csv(sys.argv[1], sys.argv[2])
    print(json.dumps(rep, indent=2))
