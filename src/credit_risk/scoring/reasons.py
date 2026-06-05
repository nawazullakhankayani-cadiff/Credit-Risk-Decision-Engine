"""Turn model feature contributions into ranked, human-readable reason codes."""
from __future__ import annotations
import numpy as np
from typing import Dict, List
from credit_risk.features.pipeline import ALL_FEATURES

# Friendly labels + direction phrasing for adverse-action style reasons.
LABELS = {
    "debt_to_income": "debt-to-income ratio",
    "credit_utilization": "credit utilisation",
    "num_delinquencies_2y": "recent delinquencies",
    "num_recent_inquiries": "recent credit inquiries",
    "loan_to_income": "loan size relative to income",
    "payment_to_income": "estimated repayment burden",
    "monthly_payment_est": "estimated monthly payment",
    "interest_rate": "offered interest rate",
    "employment_length": "length of employment",
    "credit_history_length": "credit history length",
    "annual_income": "annual income",
    "home_ownership_code": "home ownership status",
    "loan_term_months": "loan term",
    "num_open_accounts": "number of open accounts",
    "loan_amount": "requested loan amount",
    "stress_flag": "combined high-utilisation and delinquency",
    "thin_file_flag": "limited credit file",
}


def reason_codes(contributions: np.ndarray, raw_record: Dict[str, float],
                 top_k: int = 4) -> Dict[str, List[dict]]:
    contributions = np.asarray(contributions, dtype=float)
    order = np.argsort(np.abs(contributions))[::-1]
    increases, decreases = [], []
    for i in order:
        feat = ALL_FEATURES[i]
        c = float(contributions[i])
        item = {"feature": feat, "label": LABELS.get(feat, feat),
                "impact": round(c, 4), "value": raw_record.get(feat)}
        if c > 0 and len(increases) < top_k:
            increases.append(item)        # pushes PD up (adverse)
        elif c < 0 and len(decreases) < top_k:
            decreases.append(item)        # pushes PD down (favourable)
    return {"increases_risk": increases, "reduces_risk": decreases}
