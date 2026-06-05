"""Isotonic-style probability calibration (dependency-free).

Well-calibrated PDs matter for credit: a "5% PD" must mean ~5 in 100 default,
because downstream expected-loss and pricing depend on it. We fit a monotonic
piecewise-constant map from raw score -> empirical default rate using the
Pool-Adjacent-Violators Algorithm (PAVA), the core of sklearn's IsotonicRegression,
implemented here so it runs without sklearn.
"""
from __future__ import annotations
import numpy as np


class IsotonicCalibrator:
    def __init__(self):
        self.x_thresholds: np.ndarray | None = None
        self.y_values: np.ndarray | None = None

    def fit(self, scores: np.ndarray, y: np.ndarray) -> "IsotonicCalibrator":
        scores = np.asarray(scores, dtype=float)
        y = np.asarray(y, dtype=float)
        order = np.argsort(scores)
        xs, ys = scores[order], y[order]
        # PAVA
        vals = ys.astype(float).copy()
        wts = np.ones_like(vals)
        i = 0
        blocks = [[v, w, x] for v, w, x in zip(vals, wts, xs)]
        merged = []
        for v, w, x in blocks:
            merged.append([v, w, x])
            while len(merged) > 1 and merged[-2][0] > merged[-1][0]:
                v2, w2, x2 = merged.pop()
                v1, w1, x1 = merged.pop()
                nw = w1 + w2
                merged.append([(v1 * w1 + v2 * w2) / nw, nw, x2])
        self.x_thresholds = np.array([m[2] for m in merged])
        self.y_values = np.clip(np.array([m[0] for m in merged]), 0.005, 0.995)
        return self

    def transform(self, scores: np.ndarray) -> np.ndarray:
        scores = np.asarray(scores, dtype=float)
        idx = np.searchsorted(self.x_thresholds, scores, side="left")
        idx = np.clip(idx, 0, len(self.y_values) - 1)
        return self.y_values[idx]

    def to_dict(self) -> dict:
        return {"x": self.x_thresholds.tolist(), "y": self.y_values.tolist()}

    @classmethod
    def from_dict(cls, d: dict) -> "IsotonicCalibrator":
        c = cls()
        c.x_thresholds = np.array(d["x"]); c.y_values = np.array(d["y"])
        return c
