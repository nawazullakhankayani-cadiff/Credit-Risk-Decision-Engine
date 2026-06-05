"""CreditRiskScorer: load a registered model bundle and score applicants end-to-end.

Pipeline per applicant: validate -> feature transform -> model PD -> calibrate ->
grade + policy decision -> reason codes -> (optional) LLM credit memo. This is the
single object used by both the API and the Streamlit app.
"""
from __future__ import annotations
import time
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np

from credit_risk.config import PATHS
from credit_risk.data.schema import validate_record, FEATURES
from credit_risk.features.pipeline import FeaturePipeline
from credit_risk.models.baseline import LogisticRegressionPD
from credit_risk.models.calibration import IsotonicCalibrator
from credit_risk.models.registry import ModelRegistry
from credit_risk.scoring.grade import decide
from credit_risk.scoring.reasons import reason_codes
from credit_risk.scoring.memo import generate_memo


def _load_model(state: dict):
    name = state.get("name")
    if name == "xgboost":
        from credit_risk.models.xgb_model import XGBPDModel
        return XGBPDModel.from_state(state)
    return LogisticRegressionPD.from_state(state)


class CreditRiskScorer:
    def __init__(self, bundle: dict, version: str = "dev"):
        self.version = version
        self.pipeline = FeaturePipeline.from_dict(bundle["pipeline"])
        self.model = _load_model(bundle["model"])
        self.calibrator = IsotonicCalibrator.from_dict(bundle["calibrator"])
        self.cost_log_path = PATHS.data / "telemetry.jsonl"

    @classmethod
    def from_registry(cls, version: Optional[str] = None,
                      root: Optional[Path] = None) -> "CreditRiskScorer":
        reg = ModelRegistry(root or PATHS.artifacts)
        loaded = reg.load(version)
        return cls(loaded["bundle"], version=loaded["version"])

    def score(self, record: Dict, with_memo: bool = False) -> Dict:
        t0 = time.time()
        clean = validate_record(record)
        x = self.pipeline.transform_record(clean, standardize=True)
        raw_pd = float(self.model.predict_proba(x.reshape(1, -1))[0])
        pd_cal = float(self.calibrator.transform(np.array([raw_pd]))[0])
        decision = decide(pd_cal)
        contribs = self.model.feature_contributions(x)
        # Map engineered values back for display alongside reason codes.
        eng_row = self.pipeline.transform(_one_row_df(clean), standardize=False).iloc[0].to_dict()
        reasons = reason_codes(contribs, {**clean, **eng_row})
        result = {
            "model_version": self.version,
            "decision": decision,
            "reasons": reasons,
            "latency_ms": round((time.time() - t0) * 1000, 2),
        }
        from credit_risk.monitoring.cost_log import log_event
        log_event(self.cost_log_path, "score", result["latency_ms"],
                  extra={"grade": decision["risk_grade"], "decision": decision["decision"]})
        if with_memo:
            result["credit_memo"] = generate_memo(result, cost_log_path=self.cost_log_path)
        return result

    def score_batch(self, records: List[Dict], with_memo: bool = False) -> List[Dict]:
        return [self._safe_score(r, with_memo) for r in records]

    def predict_pd_frame(self, df) -> np.ndarray:
        """Vectorised calibrated PD for a whole DataFrame of applicants (fast path).

        Used for bulk analytics/reporting where per-row reason codes and memos are
        not needed — scores tens of thousands of rows in one matrix pass instead of
        a Python loop.
        """
        X = self.pipeline.transform(df[FEATURES].astype(float), standardize=True).to_numpy()
        raw = np.asarray(self.model.predict_proba(X), dtype=float).ravel()
        return np.asarray(self.calibrator.transform(raw), dtype=float).ravel()

    def _safe_score(self, r, with_memo):
        try:
            return self.score(r, with_memo=with_memo)
        except Exception as e:
            return {"error": str(e), "decision": {"decision": "REFER",
                    "human_review": True, "risk_grade": "NA"}}


def _one_row_df(clean: Dict):
    import pandas as pd
    return pd.DataFrame([{k: clean[k] for k in FEATURES}])
