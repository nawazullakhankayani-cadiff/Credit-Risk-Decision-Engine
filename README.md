# Credit Risk Decision Engine

**Automated, explainable, and governed credit scoring.** Upload a loan
applicant, get a calibrated probability of default, a risk grade, an
APPROVE / REFER / DECLINE decision, ranked reason codes, and an AI-written credit
memo — served behind a FastAPI API and a Streamlit app, with model versioning,
drift monitoring, and cost telemetry built in.

> **The business problem.** Lenders don't struggle to *train* a default model —
> they struggle to deploy one they can **explain, calibrate, monitor and defend
> to a regulator**. Manual underwriting is slow and inconsistent; black-box
> scores fail FCA/PRA model-risk and adverse-action expectations. This engine
> scores an applicant in milliseconds, justifies every decision, and routes
> borderline cases to a human — the deploy-and-govern gap, not another notebook.

## Results (held-out test set)
| Metric | Value | Meaning |
|--------|-------|---------|
| **AUC** | **0.795** | ranks a random defaulter above a non-defaulter ~80% of the time |
| **Gini** | **0.590** | strong rank-ordering power |
| **KS** | **0.445** | clean separation of good vs. bad |
| **Brier** | **0.187 → 0.133** | calibration cuts probability error ~29% |

*Metrics are from the built-in logistic baseline in a dependency-constrained
build; the XGBoost primary model (`pip install -r requirements.txt`) typically
adds several AUC points. Data is synthetic by default — see the Model Card.*

## What makes it production-grade (not a notebook)
- **Full web app with login:** a real multi-page site (`make web`) — sign in by
  **Employer ID or company name**, personalised dashboard (*"Welcome, &lt;you&gt;"*),
  manual scoring, upload→report, and a **login/logout session history**. Salted
  PBKDF2 passwords, server-side sessions, seeded demo accounts + self-registration.
- **Deployed:** FastAPI service (`/score`, `/score/batch`, `/health`, `/model`,
  `/monitoring/drift`) + a Streamlit UI (also login-gated) with a live monitoring dashboard.
- **Explainable:** SHAP (XGBoost) / exact linear contributions → ranked
  reason codes + an LLM **credit memo** (with a deterministic template fallback).
- **Drop-in any file:** upload **any** CSV/Excel and the engine auto-detects &
  maps columns to the schema, strips `£/$/%/,`, parses text (`"36 months"`,
  `"RENT"`), imputes missing values and clips outliers — with a full audit trail.
- **Self-contained report:** one click produces a shareable `report.html` with
  high-quality interactive charts (Plotly inlined → opens offline, **publish to
  GitHub Pages** as-is).
- **Calibrated:** isotonic (PAVA) calibration so a "5% PD" really means ~5%.
- **Governed:** versioned, content-hashed **model registry**; human-review gate;
  model card + governance docs aligned to FCA/PRA model-risk expectations.
- **Monitored:** **PSI drift** detection + latency and **LLM token-cost** logging.
- **Tested & CI'd:** 21 unit tests, GitHub Actions pipeline, Docker + compose.
- **Runs anywhere:** graceful fallback to a zero-dependency model + template memo,
  so the whole thing works even without the heavy ML stack.

## Quickstart
```bash
pip install -r requirements.txt        # full stack (XGBoost, SHAP, FastAPI, Streamlit)
make train                             # generate data + train + register a model
make test                              # run the test suite
make api                               # FastAPI scoring API at http://localhost:8000/docs
make web                               # Full website (login) at http://localhost:8080
make app                               # Streamlit at http://localhost:8501
# or: docker compose up --build
```
Minimal/offline mode (baseline model, no heavy deps):
```bash
pip install -r requirements-core.txt && make train && make test
```

### Score an applicant via the API
```bash
curl -X POST "http://localhost:8000/score?memo=true" -H "Content-Type: application/json" -d '{
  "loan_amount": 25000, "annual_income": 38000, "employment_length": 2,
  "debt_to_income": 0.55, "credit_utilization": 0.92, "num_delinquencies_2y": 2,
  "num_open_accounts": 6, "credit_history_length": 3, "num_recent_inquiries": 4,
  "loan_term_months": 60, "interest_rate": 24.5, "home_ownership_code": 0 }'
```
Returns the decision, risk grade, calibrated PD, reason codes and a credit memo.

### Auto-clean any file → one shareable HTML report
Point it at *any* applicant CSV/Excel — messy headers and all — and get a
polished, self-contained dashboard:
```bash
make report CSV=path/to/applicants.csv OUT=report.html
# or: python -m credit_risk.reporting.report applicants.csv -o report.html
```
The file auto-detects columns, cleans the data, scores every applicant, and
writes one `report.html` (Plotly inlined — no server, no internet). Open it
locally, email it, or **publish it as a website**: drop it in a repo and enable
GitHub Pages, or rename to `index.html`. The same flow is built into the
Streamlit app's **Batch scoring** tab (upload → auto-clean → charts → download
report).

### Enable real AI credit memos (optional)
```bash
export OPENAI_API_KEY=...      # or ANTHROPIC_API_KEY=...
```
Without a key, a faithful template memo is generated from the same structured facts.

## Repository layout
```
src/credit_risk/
  data/        schema (input contract) + synthetic generator + smart auto-ingest/clean
  features/    engineered features + standardisation (train/serve parity)
  models/      xgboost primary, logistic fallback, isotonic calibration, registry
  scoring/     grading & policy, reason codes, LLM credit memo
  reporting/   self-contained interactive HTML report generator (Plotly)
  monitoring/  PSI drift, AUC/Gini/KS metrics, latency + cost telemetry
  api/         FastAPI scoring service
  web/         authenticated website (FastAPI + Jinja): auth.py, app.py, templates/, static/
  predictor.py  train.py
app/           Streamlit UI (login-gated) + monitoring dashboard
tests/         21 unit tests          docs/  ARCHITECTURE · MODEL_CARD · GOVERNANCE
.github/workflows/ci.yml   Dockerfile   docker-compose.yml   Makefile
```

## How decisions are made
1. Validate input → 2. engineer features + standardise → 3. PD from the model →
4. **calibrate** the PD → 5. map to risk grade + policy decision (with a
human-review margin) → 6. generate **reason codes** → 7. write the **credit
memo**. Every call is logged for latency and cost; batches can be checked for
**PSI drift** against the training reference.

## Honest limitations
- Default dataset is **synthetic** (documented generative process) — revalidate
  on real Lending Club / book data before drawing conclusions.
- Risk-band cut-offs are illustrative and need Credit Risk Committee sign-off.
- **Fairness/disparate-impact testing** is specified in governance but not yet
  implemented — the next thing I'd add as a CI promotion gate.
- The shipped metrics are the baseline model's; XGBoost is the intended primary.

See `docs/ARCHITECTURE.md` for the system design and scaling path, and
`docs/MODEL_CARD.md` / `docs/GOVERNANCE.md` for model details and governance.

## License
MIT
