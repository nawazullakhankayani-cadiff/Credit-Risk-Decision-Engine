# Model Card — Credit Risk Decision Engine

## Overview
Binary classifier estimating the **probability of default (PD)** on a personal
loan, with isotonic calibration and SHAP/linear reason codes. Output drives an
A–F risk grade and an APPROVE / REFER / DECLINE policy decision.

## Intended use
- **Intended:** decision *support* for consumer-lending underwriting, with
  human review for borderline and declined cases; portfolio risk analytics.
- **Not intended:** a fully autonomous decline mechanism without human oversight,
  or use on populations unlike the training data without revalidation.

## Training data
Reproducible synthetic loan book (`data/generate.py`) modelled on the Lending
Club schema, with a documented default-generating process (affordability and
credit-stress drivers, interactions, and label noise). **Swap in real Lending
Club data** by placing a CSV with the schema columns + `default` in `data/`.
Default base rate ≈ 0.21.

## Model
- **Primary:** XGBoost (`binary:logistic`), depth 4, 400 trees, lr 0.05,
  `scale_pos_weight` for imbalance.
- **Fallback:** L2 logistic regression (numpy) with class balancing — used when
  xgboost is unavailable. Metrics below are from the **fallback** baseline in a
  dependency-constrained build; XGBoost typically improves AUC by ~3–6 points.

## Performance (held-out test, n ≈ 5,000)
| Metric | Value |
|--------|-------|
| AUC | 0.795 |
| Gini | 0.590 |
| KS | 0.445 |
| Brier (uncalibrated) | 0.187 |
| Brier (calibrated) | 0.133 |

Calibration reduces Brier by ~29%, i.e. predicted PDs align materially better
with observed default rates after isotonic calibration.

## Explainability
Per-decision reason codes from SHAP (XGBoost) or exact linear contributions
(baseline), surfaced as ranked "increases risk / reduces risk" factors and
summarised in the credit memo — supporting adverse-action explanations.

## Limitations & ethical considerations
- Synthetic data: absolute numbers are illustrative; revalidate on real data.
- No protected attributes are used, but **proxy/disparate-impact testing** is
  required before deployment (not included here).
- Risk-band cut-offs are placeholders pending Credit Risk Committee sign-off.
- PDs are floored/capped at [0.5%, 99.5%] to avoid degenerate 0/100% outputs.

## Governance
See `docs/GOVERNANCE.md` — alignment with FCA/PRA model-risk expectations,
versioning, monitoring and human oversight.
