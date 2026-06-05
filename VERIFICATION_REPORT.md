# Verification & Data-Cleaning Report

_Generated after a full read-through of every file, a clean run of the test suite,
and an end-to-end clean + score of the sample data._

## 1. Health check — all green
- **Python compiles:** every module in `src/`, `app/`, `tests/` byte-compiles with no errors.
- **Unit tests:** **24 / 24 pass** (21 original + 3 new for the CSV cleaner).
- **Model trains & loads:** held-out test metrics below.
- **Website JS:** syntax-checked; scoring matches the Python engine exactly.

### Live model metrics (held-out test, n ≈ 5,000)
| AUC | Gini | KS | Brier (uncal.) | Brier (cal.) | Default rate |
|-----|------|----|----------------|--------------|--------------|
| 0.795 | 0.590 | 0.445 | 0.187 | 0.133 | 0.215 |

## 2. CSV cleaning — what was fixed
The new module `src/credit_risk/data/clean.py` was run on the messy sample
(`site/samples/messy_applicants.csv`, 120 rows of deliberately broken data):

```json
{
  "rows": 120,
  "columns_mapped": "12 / 12",
  "imputed_cells": 97,
  "clipped_cells": 37,
  "ignored_columns": ["Applicant ID", "Notes"]
}
```

**Column auto-mapping** (messy header → model feature): Loan Amount→loan_amount,
Gross Salary→annual_income, Years Employed→employment_length, DTI→debt_to_income,
Utilisation %→credit_utilization, Delinquencies→num_delinquencies_2y,
Open Accounts→num_open_accounts, Credit History (yrs)→credit_history_length,
Hard Inquiries→num_recent_inquiries, Term→loan_term_months, APR→interest_rate,
Home Ownership→home_ownership_code.

**Value fixes applied:** stripped `£ $ % ,`; `"36 months"`→`36`;
`Mortgage/Rent/Own`→`1/0/2`; `45%` utilisation→`0.45` (but `APR 12.5%`→`12.5`,
not divided); blanks → imputed with training means; out-of-range → clipped to bounds.

### Cleaned output (`data/cleaned_applicants.csv`, first rows)
```
loan_amount,annual_income,employment_length,debt_to_income,credit_utilization,num_delinquencies_2y,num_open_accounts,credit_history_length,num_recent_inquiries,loan_term_months,interest_rate,home_ownership_code
10234.0,36338.0,5.4,0.539,0.405,0,4,24.5,1,36,17.01,1
3599.0,42166.0,6.02980269297427,0.132,0.478,0,8,1.1,0,36,10.13,0
```

### Scored output (`data/scored_applicants.csv`, first rows)
```
 loan_amount  annual_income  debt_to_income  credit_utilization  interest_rate     pd risk_grade decision
     10234.0   36338.000000           0.539               0.405          17.01 0.1437          D    REFER
      3599.0   42166.000000           0.132               0.478          10.13 0.0707          C    REFER
     12491.0   31664.000000           0.213               0.068           9.83 0.1437          D    REFER
      3078.0   23265.000000           0.264               0.286          12.27 0.3697          F    REFER
      4250.0   28931.000000           0.061               0.205           6.82 0.0308          B    REFER
     16528.0   41520.142781           0.589               0.363          13.42 0.1437          D    REFER
```
Decision counts across all 120: `{'REFER': 78, 'DECLINE': 39, 'APPROVE': 3}`

Regenerate any time with:
```
make clean-csv IN=site/samples/messy_applicants.csv OUT=data/cleaned_applicants.csv
```

## 3. Every file — purpose & status
| File | Purpose | Status |
|------|---------|--------|
| src/credit_risk/config.py | Central config: paths, risk bands, hyper-params | OK |
| src/credit_risk/data/schema.py | Input contract + validation (pydantic + fallback) | OK |
| src/credit_risk/data/generate.py | Synthetic Lending-Club-style data generator | OK |
| src/credit_risk/data/clean.py | **NEW** — robust CSV intake/cleaning | OK (3 tests) |
| src/credit_risk/features/pipeline.py | Feature engineering + standardisation | OK |
| src/credit_risk/models/base.py | PDModel interface | OK |
| src/credit_risk/models/baseline.py | numpy logistic regression (fallback) | OK |
| src/credit_risk/models/xgb_model.py | XGBoost + SHAP (primary) | OK |
| src/credit_risk/models/calibration.py | Isotonic (PAVA) calibration | OK |
| src/credit_risk/models/registry.py | Versioned, hashed model registry | OK |
| src/credit_risk/scoring/grade.py | PD → grade + policy decision | OK |
| src/credit_risk/scoring/reasons.py | Ranked reason codes | OK |
| src/credit_risk/scoring/memo.py | LLM credit memo + template fallback | OK |
| src/credit_risk/monitoring/metrics.py | AUC / Gini / KS / Brier | OK |
| src/credit_risk/monitoring/drift.py | PSI drift detection | OK |
| src/credit_risk/monitoring/cost_log.py | Latency + token-cost telemetry | OK |
| src/credit_risk/predictor.py | End-to-end scorer used by API + app | OK |
| src/credit_risk/train.py | Training pipeline → registry | OK |
| src/credit_risk/api/main.py | FastAPI service | OK |
| app/streamlit_app.py | Streamlit UI + monitoring dashboard | OK |
| site/index.html | Static website: scorer, batch, charts, PDF, letters | OK |
| tests/*.py | 24 unit tests | All pass |
| docs/ARCHITECTURE.md, MODEL_CARD.md, GOVERNANCE.md | Design + governance | OK |
| Dockerfile, docker-compose.yml, .github/workflows/ci.yml, Makefile | Infra/CI | OK |

## 4. Notes
- Data is synthetic by design; swap in a real Lending Club CSV in `data/` to use real figures.
- Many cleaned rows land on REFER because the human-review margin is intentionally
  wide relative to the band widths — a conservative, governance-friendly default that
  the Credit Risk Committee would tune in production.
