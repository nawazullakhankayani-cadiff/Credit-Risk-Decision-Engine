"""Population Stability Index (PSI) drift detection.

PSI is the standard credit-industry measure for input/score drift. We bin the
reference (training) distribution into deciles and compare the live distribution.
Rule of thumb: PSI < 0.1 stable, 0.1-0.25 moderate shift (investigate),
>= 0.25 significant shift (retrain / alert).
"""
from __future__ import annotations
import numpy as np
from typing import Dict

STABLE, MODERATE, SIGNIFICANT = "stable", "moderate", "significant"


def _psi(ref: np.ndarray, cur: np.ndarray, bins: int = 10) -> float:
    ref = np.asarray(ref, dtype=float); cur = np.asarray(cur, dtype=float)
    quantiles = np.unique(np.quantile(ref, np.linspace(0, 1, bins + 1)))
    if len(quantiles) < 3:
        return 0.0
    quantiles[0], quantiles[-1] = -np.inf, np.inf
    ref_pct = np.histogram(ref, bins=quantiles)[0] / max(len(ref), 1)
    cur_pct = np.histogram(cur, bins=quantiles)[0] / max(len(cur), 1)
    eps = 1e-6
    ref_pct = np.clip(ref_pct, eps, None)
    cur_pct = np.clip(cur_pct, eps, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def classify(psi: float) -> str:
    if psi < 0.1:
        return STABLE
    if psi < 0.25:
        return MODERATE
    return SIGNIFICANT


def feature_drift(reference, current, columns) -> Dict[str, dict]:
    report = {}
    for c in columns:
        val = _psi(reference[c].to_numpy(), current[c].to_numpy())
        report[c] = {"psi": round(val, 4), "status": classify(val)}
    return report


def overall_status(report: Dict[str, dict]) -> str:
    statuses = [v["status"] for v in report.values()]
    if SIGNIFICANT in statuses:
        return SIGNIFICANT
    if MODERATE in statuses:
        return MODERATE
    return STABLE
