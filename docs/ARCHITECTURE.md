# Architecture

## Goal
A production-shaped credit-risk decision service that scores a loan applicant's
**probability of default (PD)**, assigns a **risk grade and policy decision**,
explains every decision with **reason codes**, narrates it as an **AI credit
memo**, and is **monitored and governed** like a regulated model would be.

## High-level flow

```mermaid
flowchart LR
    A[Applicant data\nCSV / API JSON] --> V[Schema validation\n(pydantic / dep-free)]
    V --> F[Feature pipeline\nengineered ratios + standardisation]
    F --> M[PD model\nXGBoost primary / logistic fallback]
    M --> C[Isotonic calibration\nPD means what it says]
    C --> G[Grading & policy\nA-F grade + APPROVE/REFER/DECLINE]
    M --> R[Reason codes\nSHAP / linear contributions]
    G --> Memo[LLM credit memo\nOpenAI/Anthropic + template fallback]
    R --> Memo
    G --> Out[Decision + rationale]
    Memo --> Out
    Out --> T[(Telemetry\nlatency + LLM cost)]
    F -.training reference.-> D[PSI drift monitor]
    A2[Live batch] --> D
    subgraph Registry [Model Registry: versioned + hashed + auditable]
        M & C & F
    end
```

## Components
| Layer | Module | Responsibility |
|-------|--------|----------------|
| Contract | `data/schema.py` | Validate/coerce inputs; pydantic model for the API |
| Data | `data/generate.py` | Reproducible Lending-Club-style data with real signal |
| Features | `features/pipeline.py` | Engineered ratios + standardisation; train/serve parity |
| Model | `models/xgb_model.py`, `models/baseline.py` | PD estimation behind one `PDModel` interface |
| Calibration | `models/calibration.py` | Isotonic (PAVA) so PDs are trustworthy probabilities |
| Registry | `models/registry.py` | Versioned, hashed bundles + manifest + `latest` pointer |
| Scoring | `scoring/grade.py`, `scoring/reasons.py`, `scoring/memo.py` | Decision policy, reason codes, AI memo |
| Monitoring | `monitoring/drift.py`, `monitoring/metrics.py`, `monitoring/cost_log.py` | PSI drift, AUC/Gini/KS, latency + token cost |
| Serving | `api/main.py`, `app/streamlit_app.py` | FastAPI service + Streamlit UI/dashboard |
| Orchestration | `predictor.py`, `train.py` | Score one object; train + register end-to-end |

## Key design decisions
1. **Model-agnostic serving.** Both models implement `PDModel`, so swapping
   XGBoost for the baseline (or a future model) changes nothing downstream.
2. **Graceful degradation.** No xgboost/shap → logistic baseline; no LLM key →
   template memo. The engine always runs, which keeps CI green and demos reliable.
3. **The LLM never decides.** It only narrates a decision the governed model has
   already made — essential for model-risk accountability.
4. **Calibration is first-class.** Lending economics depend on PDs being real
   probabilities, so isotonic calibration is part of the pipeline, not an extra.
5. **Everything is versioned and logged.** Immutable hashed model bundles +
   per-call telemetry give the lineage a model-risk reviewer expects.

## Scaling notes (how this goes to real production)
- Replace the file registry with **MLflow / SageMaker Model Registry**; keep the
  same `PDModel` interface.
- Run the FastAPI app behind **gunicorn/uvicorn workers** on **ECS/Kubernetes**;
  it is stateless and horizontally scalable.
- Push telemetry JSONL to **Kafka → a warehouse** and PSI jobs to a scheduler
  (**Airflow**), alerting when PSI ≥ 0.25.
- Add a **feature store** for shared, point-in-time-correct features.
- Gate promotion in CI on metric thresholds (AUC/KS) and a fairness check.
