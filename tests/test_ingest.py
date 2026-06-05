"""Tests for the smart auto-ingest + cleaning pipeline."""
import io

import pandas as pd
import pytest

from credit_risk.data.ingest import (auto_map_columns, clean_frame, ingest,
                                      _to_number, _to_ratio, _parse_home_ownership)
from credit_risk.data.schema import FEATURES, _BOUNDS

MESSY = (
    "Loan Amount,Annual Income,Emp Length,DTI,Revol Util,Delinq 2yrs,Open Acc,"
    "Credit Age,Inq Last 6mths,Term,Int Rate,Home Ownership,Charged Off\n"
    '"£25,000","$38,000",2 years,55%,92%,2,6,3.0,4,36 months,24.5%,RENT,1\n'
    '"15,000","52,000",10,0.30,45%,0,8,12,1,60 months,11.2%,MORTGAGE,0\n'
    ",48000,5,0.4,0.5,1,7,,2,36,13.5,OWN,0\n"
)


def _messy_df():
    return pd.read_csv(io.StringIO(MESSY))


def test_value_parsers():
    assert _to_number("£25,000") == 25000.0
    assert _to_number("24.5%") == 24.5            # non-ratio keeps the number
    assert _to_ratio("92%") == pytest.approx(0.92)  # ratio divides by 100
    assert _to_ratio("0.30") == pytest.approx(0.30)
    assert _to_number("36 months") == 36.0
    assert _to_number("n/a") is None
    assert _parse_home_ownership("RENT") == 0
    assert _parse_home_ownership("Mortgage") == 1
    assert _parse_home_ownership("Owner") == 2


def test_auto_map_columns_handles_messy_headers():
    mapping, target = auto_map_columns(_messy_df())
    assert set(mapping.values()) == set(FEATURES)   # all 12 mapped
    assert target == "Charged Off"


def test_clean_frame_is_schema_valid_and_in_bounds():
    df_clean, rep = ingest(io.BytesIO(MESSY.encode()))
    # schema columns present and numeric
    for f in FEATURES:
        assert f in df_clean.columns
        assert df_clean[f].notna().all()
        lo, hi = _BOUNDS[f]
        assert df_clean[f].between(lo, hi).all()
    assert rep.n_rows_out == 3
    assert rep.n_features_mapped == 12
    # percent ratio handled (92% -> 0.92, not clipped to bound)
    assert df_clean.loc[0, "credit_utilization"] == pytest.approx(0.92)
    assert df_clean.loc[0, "home_ownership_code"] == 0
    # missing loan_amount imputed (was blank in row 2)
    assert df_clean.loc[2, "loan_amount"] > 0
    assert "__target__" in df_clean.columns


def test_missing_columns_are_synthesized_with_warning():
    df = pd.DataFrame({"loan_amount": [10000, 20000], "annual_income": [40000, 50000]})
    mapping, target = auto_map_columns(df)
    df_clean, rep = clean_frame(df, mapping, target)
    assert df_clean.shape[0] == 2
    assert len(rep.synthesized_features) == len(FEATURES) - 2
    assert rep.warnings  # should warn about heavy synthesis
    # still schema-valid so it can be scored
    for f in FEATURES:
        assert df_clean[f].notna().all()


def test_quality_score_in_range():
    _, rep = ingest(io.BytesIO(MESSY.encode()))
    assert 0 <= rep.quality_score <= 100
