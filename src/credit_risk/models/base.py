"""Model interface so the scoring/serving layers are model-agnostic."""
from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np


class PDModel(ABC):
    """Probability-of-Default model contract."""
    name: str = "base"

    @abstractmethod
    def fit(self, X: np.ndarray, y: np.ndarray) -> "PDModel": ...

    @abstractmethod
    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return P(default) for each row, shape (n,)."""

    @abstractmethod
    def feature_contributions(self, x: np.ndarray) -> np.ndarray:
        """Per-feature additive contribution to the score for one row (for reason codes)."""

    def to_state(self) -> dict: ...
    @classmethod
    def from_state(cls, state: dict) -> "PDModel": ...
