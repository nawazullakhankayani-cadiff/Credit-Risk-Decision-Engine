"""Dependency-free L2-regularised logistic regression (numpy only).

This is the *fallback* model: it lets the whole engine train, score, explain and
pass its tests in any environment, including this one where XGBoost is not
installed. In production the primary model is gradient-boosted trees
(``xgb_model.XGBPDModel``); the serving code is identical because both implement
``PDModel``. Contributions are weight * standardised-feature, which is the exact
local explanation for a linear model (and a sane proxy for reason codes).
"""
from __future__ import annotations
import numpy as np
from credit_risk.models.base import PDModel


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -35, 35)))


class LogisticRegressionPD(PDModel):
    name = "logreg_baseline"

    def __init__(self, l2: float = 1e-3, lr: float = 0.1, epochs: int = 600):
        self.l2 = l2
        self.lr = lr
        self.epochs = epochs
        self.w: np.ndarray | None = None
        self.b: float = 0.0

    def fit(self, X: np.ndarray, y: np.ndarray) -> "LogisticRegressionPD":
        X = np.asarray(X, dtype=float)
        y = np.asarray(y, dtype=float)
        n, d = X.shape
        self.w = np.zeros(d)
        self.b = 0.0
        # Mini-batch gradient descent with class balancing via pos_weight.
        pos_w = float((y == 0).sum()) / max(float((y == 1).sum()), 1.0)
        sample_w = np.where(y == 1, pos_w, 1.0)
        rng = np.random.default_rng(0)
        idx = np.arange(n)
        bs = min(2048, n)
        for _ in range(self.epochs):
            rng.shuffle(idx)
            for start in range(0, n, bs):
                b = idx[start:start + bs]
                Xb, yb, wb = X[b], y[b], sample_w[b]
                p = _sigmoid(Xb @ self.w + self.b)
                err = (p - yb) * wb
                grad_w = Xb.T @ err / len(b) + self.l2 * self.w
                grad_b = float(err.mean())
                self.w -= self.lr * grad_w
                self.b -= self.lr * grad_b
        return self

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        X = np.asarray(X, dtype=float)
        return _sigmoid(X @ self.w + self.b)

    def feature_contributions(self, x: np.ndarray) -> np.ndarray:
        x = np.asarray(x, dtype=float)
        return self.w * x  # exact local contribution for a linear model

    def to_state(self) -> dict:
        return {"name": self.name, "w": self.w.tolist(), "b": self.b,
                "l2": self.l2, "lr": self.lr, "epochs": self.epochs}

    @classmethod
    def from_state(cls, state: dict) -> "LogisticRegressionPD":
        m = cls(l2=state["l2"], lr=state["lr"], epochs=state["epochs"])
        m.w = np.array(state["w"], dtype=float)
        m.b = float(state["b"])
        return m
