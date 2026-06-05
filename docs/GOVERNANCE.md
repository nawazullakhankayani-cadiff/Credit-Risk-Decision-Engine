# Model Risk Governance

This engine is built to slot into a regulated lender's model-risk framework
(aligned with the UK PRA's SS1/23 model-risk principles and FCA Consumer Duty
expectations). It is decision *support*, not an unaccountable black box.

## 1. Model inventory & versioning
Every trained model is an **immutable, content-hashed bundle** in the registry
(`models/registry/<version>/`) with a manifest recording data source, row counts,
package version, metrics and timestamp. `latest.json` is the promoted production
version. Full lineage is reproducible.

## 2. Explainability & adverse action
Each decision ships ranked **reason codes** and a plain-English **credit memo**.
Declines can therefore be explained to the customer, supporting adverse-action
notice requirements and the right to a meaningful explanation.

## 3. Human oversight
A configurable **decision margin** routes any application near a band boundary,
and all declines/REFERs, to **human review**. The LLM never makes the decision —
it only narrates the governed model's output.

## 4. Fairness (required before deployment)
No protected characteristics are used as inputs. Before production, run
**disparate-impact / proxy-bias testing** across protected groups and document
results. (Hook this into CI as a promotion gate.)

## 5. Ongoing monitoring
- **Input/score drift:** PSI per feature (stable < 0.10, investigate 0.10–0.25,
  alert/retrain ≥ 0.25).
- **Performance:** track realised AUC/KS and **calibration** as outcomes mature.
- **Operations:** latency and LLM token-cost telemetry per call.

## 6. Calibration & validation
PDs are isotonically calibrated and validated on a held-out set. Independent
validation and challenger-model benchmarking should precede each promotion.

## 7. Change management
Model promotion runs through CI with metric thresholds; the registry's hashing
and manifests provide the audit trail expected by a model-risk function.
