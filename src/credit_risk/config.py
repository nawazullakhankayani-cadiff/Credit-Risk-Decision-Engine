"""Central configuration. Values can be overridden via config/config.yaml or env vars."""
from __future__ import annotations
import os
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Paths:
    root: Path = ROOT
    data: Path = ROOT / "data"
    models: Path = ROOT / "models"
    artifacts: Path = ROOT / "models" / "registry"


# Risk grading bands map a calibrated probability-of-default (PD) to a letter grade
# and a default policy decision. Cut-offs are illustrative and must be set by a
# Credit Risk Committee against the firm's risk appetite (see docs/GOVERNANCE.md).
RISK_BANDS = [
    # (grade, pd_upper_bound_exclusive, decision)
    ("A", 0.03, "APPROVE"),
    ("B", 0.07, "APPROVE"),
    ("C", 0.13, "REFER"),
    ("D", 0.22, "REFER"),
    ("E", 0.35, "DECLINE"),
    ("F", 1.01, "DECLINE"),
]

# Confidence band (in PD units) around a decision boundary that forces a human REFER.
DECISION_MARGIN = 0.02


@dataclass(frozen=True)
class TrainConfig:
    target: str = "default"
    test_size: float = 0.2
    valid_size: float = 0.2
    random_state: int = 42
    # XGBoost hyper-parameters (primary model)
    xgb_params: Dict = field(default_factory=lambda: {
        "n_estimators": 400,
        "max_depth": 4,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "reg_lambda": 1.0,
        "min_child_weight": 5,
        "objective": "binary:logistic",
        "eval_metric": "auc",
        "n_jobs": 4,
    })


@dataclass(frozen=True)
class LLMConfig:
    provider: str = os.getenv("CREDIT_LLM_PROVIDER", "auto")  # auto|openai|anthropic|template
    model: str = os.getenv("CREDIT_LLM_MODEL", "gpt-4o-mini")
    max_tokens: int = 600
    temperature: float = 0.2


PATHS = Paths()
TRAIN = TrainConfig()
LLM = LLMConfig()


def as_dict() -> dict:
    return {"train": asdict(TRAIN), "llm": asdict(LLM), "risk_bands": RISK_BANDS}
