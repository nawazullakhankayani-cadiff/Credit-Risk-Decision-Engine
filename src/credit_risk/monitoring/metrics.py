"""Discrimination & calibration metrics (numpy only): AUC, Gini, KS, Brier, PSI-ready."""
from __future__ import annotations
import numpy as np


def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y_true); s = np.asarray(scores)
    pos = s[y == 1]; neg = s[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    # Mann-Whitney U statistic == AUC (rank-based, handles ties).
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(s) + 1)
    # average ranks for ties
    _, inv, counts = np.unique(s, return_inverse=True, return_counts=True)
    csum = np.cumsum(counts)
    avg = {}
    start = 0
    for i, c in enumerate(counts):
        avg[i] = (start + 1 + start + c) / 2.0
        start += c
    ranks = np.array([avg[i] for i in inv])
    auc = (ranks[y == 1].sum() - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))
    return float(auc)


def gini(y_true, scores) -> float:
    return float(2 * roc_auc(y_true, scores) - 1)


def ks_statistic(y_true, scores) -> float:
    y = np.asarray(y_true); s = np.asarray(scores)
    order = np.argsort(s)
    y = y[order]
    cum_bad = np.cumsum(y == 1) / max((y == 1).sum(), 1)
    cum_good = np.cumsum(y == 0) / max((y == 0).sum(), 1)
    return float(np.max(np.abs(cum_bad - cum_good)))


def brier_score(y_true, p) -> float:
    y = np.asarray(y_true, dtype=float); p = np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2))


def summary(y_true, scores) -> dict:
    return {
        "auc": round(roc_auc(y_true, scores), 4),
        "gini": round(gini(y_true, scores), 4),
        "ks": round(ks_statistic(y_true, scores), 4),
        "brier": round(brier_score(y_true, scores), 4),
        "default_rate": round(float(np.mean(y_true)), 4),
        "n": int(len(y_true)),
    }
