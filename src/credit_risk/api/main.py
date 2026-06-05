"""FastAPI scoring service.

Endpoints:
  GET  /health        liveness + loaded model version
  GET  /model         model card / metrics for the live version
  POST /score         score one applicant (optional ?memo=true)
  POST /score/batch   score many applicants
  POST /monitoring/drift  PSI drift report for a batch vs. training reference

The scorer is loaded once at startup from the model registry. The service is
model-agnostic: whatever version is promoted in the registry is what serves.
"""
from __future__ import annotations
from typing import List, Optional
from pathlib import Path

try:
    from fastapi import FastAPI, HTTPException, Query
    from pydantic import BaseModel
except Exception as e:  # pragma: no cover
    raise SystemExit("FastAPI/pydantic required: pip install -r requirements.txt") from e

from credit_risk import __version__
from credit_risk.config import PATHS
from credit_risk.data.schema import Applicant
from credit_risk.predictor import CreditRiskScorer

app = FastAPI(title="Credit Risk Decision Engine", version=__version__)
_scorer: Optional[CreditRiskScorer] = None


def get_scorer() -> CreditRiskScorer:
    global _scorer
    if _scorer is None:
        _scorer = CreditRiskScorer.from_registry()
    return _scorer


@app.on_event("startup")
def _startup():
    try:
        get_scorer()
    except Exception:
        pass  # allow health checks before a model is trained


@app.get("/health")
def health():
    try:
        v = get_scorer().version
        return {"status": "ok", "model_version": v, "service_version": __version__}
    except Exception as e:
        return {"status": "degraded", "detail": str(e)}


@app.get("/model")
def model_card():
    from credit_risk.models.registry import ModelRegistry
    reg = ModelRegistry(PATHS.artifacts)
    loaded = reg.load()
    return loaded["manifest"]


@app.post("/score")
def score(applicant: Applicant, memo: bool = Query(False)):
    try:
        return get_scorer().score(applicant.to_features(), with_memo=memo)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


class BatchRequest(BaseModel):
    applicants: List[Applicant]
    memo: bool = False


@app.post("/score/batch")
def score_batch(req: BatchRequest):
    recs = [a.to_features() for a in req.applicants]
    return {"results": get_scorer().score_batch(recs, with_memo=req.memo)}


class DriftRequest(BaseModel):
    records: List[Applicant]


@app.post("/monitoring/drift")
def drift(req: DriftRequest):
    import pandas as pd
    from credit_risk.monitoring import drift as D
    from credit_risk.data.schema import FEATURES
    ref_path = PATHS.data / "reference_sample.csv"
    if not ref_path.exists():
        raise HTTPException(status_code=409, detail="no reference sample; train first")
    ref = pd.read_csv(ref_path)
    cur = pd.DataFrame([a.to_features() for a in req.records])
    report = D.feature_drift(ref, cur, [c for c in FEATURES if c in cur.columns])
    return {"overall": D.overall_status(report), "by_feature": report}
