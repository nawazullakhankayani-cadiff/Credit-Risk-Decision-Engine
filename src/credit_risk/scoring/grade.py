"""Map calibrated PD -> risk grade and a policy decision with a confidence margin."""
from __future__ import annotations
from credit_risk.config import RISK_BANDS, DECISION_MARGIN


def assign_grade(pd_value: float):
    for grade, upper, decision in RISK_BANDS:
        if pd_value < upper:
            return grade, decision
    return RISK_BANDS[-1][0], RISK_BANDS[-1][2]


def _boundaries():
    return [b[1] for b in RISK_BANDS[:-1]]


def decide(pd_value: float) -> dict:
    """Return grade, decision and confidence. Near a band boundary -> force human REFER."""
    grade, decision = assign_grade(pd_value)
    near_boundary = any(abs(pd_value - b) <= DECISION_MARGIN for b in _boundaries())
    final = "REFER" if (near_boundary and decision != "REFER") else decision
    # Confidence: distance from nearest decision boundary, scaled.
    nearest = min((abs(pd_value - b) for b in _boundaries()), default=0.5)
    confidence = round(min(1.0, nearest / max(DECISION_MARGIN * 3, 1e-6)), 3)
    return {
        "pd": round(float(pd_value), 4),
        "risk_grade": grade,
        "decision": final,
        "auto_decision": decision,
        "human_review": near_boundary or final == "REFER",
        "confidence": confidence,
    }
