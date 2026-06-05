"""Smart data ingestion: turn an arbitrary uploaded file into a clean, schema-valid
applicant table that the scorer can consume — automatically.

Pipeline:  read_any -> auto_map_columns -> clean_frame  ->  (clean df, IngestReport)

The goal is "drop in any reasonable loan-book CSV and it just works": we fuzzy-match
columns to the model's 12 features, strip currency/percent/thousands formatting,
parse text values (e.g. "36 months", "RENT"), impute missing values, clip wild
outliers into plausible ranges, and record *everything we did* in an IngestReport so
the cleaning is auditable (this is a credit-risk system — silent munging is not OK).

Dependency-light: pandas + numpy only.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from credit_risk.config import PATHS
from credit_risk.data.schema import FEATURES, _BOUNDS

# --------------------------------------------------------------------------- #
# Column synonyms — map messy real-world headers onto the model schema.
# Keys are canonical feature names; values are alternative spellings we accept.
# Matching is done on a normalised header (lowercased, alphanumerics only).
# --------------------------------------------------------------------------- #
_SYNONYMS: Dict[str, List[str]] = {
    "loan_amount": [
        "loanamount", "loanamt", "loanamnt", "fundedamount", "fundedamnt",
        "principal", "amount", "loansize", "amountrequested", "requestedamount",
    ],
    "annual_income": [
        "annualincome", "annualinc", "income", "yearlyincome", "salary",
        "grossincome", "annualsalary", "incomeannual",
    ],
    "employment_length": [
        "employmentlength", "emplength", "employmentyears", "yearsemployed",
        "jobtenure", "emplen", "employmentduration", "yearsinjob", "tenure",
    ],
    "debt_to_income": [
        "debttoincome", "dti", "debtincomeratio", "debtincome", "dtiratio",
    ],
    "credit_utilization": [
        "creditutilization", "creditutilisation", "utilization", "utilisation",
        "util", "revolutil", "creditutil", "revolvingutilization",
    ],
    "num_delinquencies_2y": [
        "numdelinquencies2y", "delinquencies", "delinq2yrs", "numdelinq",
        "delinquencycount", "pastdue", "numdelinquencies", "delinquencies2y",
        "delinq", "latepayments",
    ],
    "num_open_accounts": [
        "numopenaccounts", "openacc", "openaccounts", "numaccounts",
        "totalaccounts", "openaccts", "numtradelines", "tradelines",
    ],
    "credit_history_length": [
        "credithistorylength", "credithistory", "historylength", "creditage",
        "creditagewyears", "ageofcredit", "credithistoryyears", "yearsofcredit",
    ],
    "num_recent_inquiries": [
        "numrecentinquiries", "inquiries", "inqlast6mths", "recentinquiries",
        "numinquiries", "hardinquiries", "inq6m", "creditinquiries", "inquiries6m",
    ],
    "loan_term_months": [
        "loantermmonths", "term", "loanterm", "termmonths", "duration",
        "loandurationmonths",
    ],
    "interest_rate": [
        "interestrate", "intrate", "apr", "rate", "interest", "coupon",
    ],
    "home_ownership_code": [
        "homeownershipcode", "homeownership", "homeowner", "ownership",
        "housing", "hometype", "residencetype", "propertyownership",
    ],
}

# Features whose schema contract is integer-valued — parsed values are rounded,
# not just imputed fills, so a stray 0.7 delinquency count can't leak downstream.
INT_FEATURES = {
    "num_delinquencies_2y", "num_open_accounts", "num_recent_inquiries",
    "loan_term_months", "home_ownership_code",
}
_RATIO_FEATURES = {"debt_to_income", "credit_utilization"}

# Text -> home_ownership_code
_HOME_MAP = {
    "rent": 0, "renting": 0, "tenant": 0,
    "mortgage": 1, "mortgaged": 1, "loan": 1,
    "own": 2, "owner": 2, "owned": 2, "outright": 2,
    "other": 0, "none": 0, "any": 0,
}


def _norm(name: str) -> str:
    """Normalise a column header for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


# Reverse lookup: normalised synonym -> canonical feature.
_LOOKUP: Dict[str, str] = {}
for _canon, _alts in _SYNONYMS.items():
    _LOOKUP[_norm(_canon)] = _canon
    for _a in _alts:
        _LOOKUP[_norm(_a)] = _canon


@dataclass
class IngestReport:
    """Auditable record of what ingestion did to the data."""
    n_rows_in: int = 0
    n_rows_out: int = 0
    source_columns: List[str] = field(default_factory=list)
    column_mapping: Dict[str, str] = field(default_factory=dict)   # source -> feature
    mapped_features: List[str] = field(default_factory=list)
    synthesized_features: List[str] = field(default_factory=list)  # not found, defaulted
    missing_filled: Dict[str, int] = field(default_factory=dict)   # feature -> #cells
    clipped: Dict[str, int] = field(default_factory=dict)          # feature -> #cells
    coerced_text: Dict[str, int] = field(default_factory=dict)     # feature -> #cells
    dropped_rows: int = 0
    duplicate_rows: int = 0
    target_column: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    @property
    def n_features_mapped(self) -> int:
        return len(self.mapped_features)

    @property
    def quality_score(self) -> float:
        """0-100 heuristic: rewards mapped columns + clean cells."""
        total_cells = max(self.n_rows_out * len(FEATURES), 1)
        touched = (sum(self.missing_filled.values()) + sum(self.clipped.values())
                   + len(self.synthesized_features) * self.n_rows_out)
        mapped_ratio = self.n_features_mapped / len(FEATURES)
        clean_ratio = 1 - min(touched / total_cells, 1.0)
        return round(100 * (0.6 * mapped_ratio + 0.4 * clean_ratio), 1)

    def to_dict(self) -> dict:
        return {
            "rows_in": self.n_rows_in,
            "rows_out": self.n_rows_out,
            "dropped_rows": self.dropped_rows,
            "duplicate_rows": self.duplicate_rows,
            "features_mapped": self.n_features_mapped,
            "features_total": len(FEATURES),
            "column_mapping": self.column_mapping,
            "synthesized_features": self.synthesized_features,
            "missing_filled": self.missing_filled,
            "clipped": self.clipped,
            "coerced_text": self.coerced_text,
            "target_column": self.target_column,
            "quality_score": self.quality_score,
            "warnings": self.warnings,
        }


# --------------------------------------------------------------------------- #
# Reading
# --------------------------------------------------------------------------- #
def read_any(source: Any) -> pd.DataFrame:
    """Read CSV/TSV/Excel from a path, bytes, or file-like buffer."""
    name = getattr(source, "name", None) or (str(source) if isinstance(source, (str, Path)) else "")
    ext = Path(name).suffix.lower()

    if ext in {".xlsx", ".xls"}:
        return pd.read_excel(source)

    # CSV/TSV: sniff the delimiter from a sample.
    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        buf = io.StringIO(raw)
        sample = raw[:5000]
    else:
        text = Path(source).read_text(encoding="utf-8", errors="replace")
        buf = io.StringIO(text)
        sample = text[:5000]

    sep = "\t" if sample.count("\t") > sample.count(",") else ","
    return pd.read_csv(buf, sep=sep)


# --------------------------------------------------------------------------- #
# Column mapping
# --------------------------------------------------------------------------- #
def auto_map_columns(df: pd.DataFrame) -> Tuple[Dict[str, str], Optional[str]]:
    """Return (source_col -> feature) mapping and a detected target column, if any."""
    mapping: Dict[str, str] = {}
    used_features: set = set()
    for col in df.columns:
        feat = _LOOKUP.get(_norm(col))
        if feat and feat not in used_features:
            mapping[col] = feat
            used_features.add(feat)

    # Detect a binary target column (default flag) for optional evaluation.
    target = None
    for col in df.columns:
        if col in mapping:
            continue
        if _norm(col) in {"default", "defaulted", "isdefault", "baddebt", "label",
                          "target", "chargedoff", "y", "outcome"}:
            target = col
            break
    return mapping, target


# --------------------------------------------------------------------------- #
# Value coercion
# --------------------------------------------------------------------------- #
_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _to_number(val: Any, ratio: bool = False) -> Optional[float]:
    """Best-effort parse of a single value into a float. Strips £$,%, words, etc.

    When ``ratio`` is True a trailing percent sign means "divide by 100" (so a
    utilisation of "92%" becomes 0.92). For non-ratio fields like interest rate the
    percent sign is just a unit and the number is kept as-is ("24.5%" -> 24.5).
    """
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (int, float, np.integer, np.floating)):
        return float(val)
    s = str(val).strip()
    if s == "" or s.lower() in {"na", "n/a", "nan", "none", "null", "-"}:
        return None
    is_pct = "%" in s
    s = s.replace(",", "").replace("£", "").replace("$", "").replace("€", "").replace("%", "")
    m = _NUM_RE.search(s)
    if not m:
        return None
    num = float(m.group())
    if ratio and is_pct:
        num /= 100.0
    return num


def _to_ratio(val: Any) -> Optional[float]:
    return _to_number(val, ratio=True)


def _parse_home_ownership(val: Any) -> Optional[float]:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    if isinstance(val, (int, float, np.integer, np.floating)) and not isinstance(val, bool):
        n = int(val)
        return float(n) if n in (0, 1, 2) else None
    key = re.sub(r"[^a-z]", "", str(val).lower())
    for k, code in _HOME_MAP.items():
        if k in key:
            return float(code)
    return None


def _reference_medians() -> Dict[str, float]:
    """Sensible defaults for any feature a file is missing — from the training
    reference sample if present, else the midpoint of the plausible range."""
    ref_path = PATHS.data / "reference_sample.csv"
    meds: Dict[str, float] = {}
    if ref_path.exists():
        try:
            ref = pd.read_csv(ref_path)
            for f in FEATURES:
                if f in ref.columns:
                    meds[f] = float(pd.to_numeric(ref[f], errors="coerce").median())
        except Exception:
            pass
    for f in FEATURES:
        if f not in meds or not np.isfinite(meds.get(f, np.nan)):
            lo, hi = _BOUNDS[f]
            meds[f] = round((lo + hi) / 2, 2) if f != "annual_income" else 40000.0
    # Friendlier categorical/discrete defaults.
    meds["home_ownership_code"] = meds.get("home_ownership_code", 0) or 0
    meds["loan_term_months"] = 36.0
    return meds


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #
def clean_frame(df: pd.DataFrame,
                mapping: Optional[Dict[str, str]] = None,
                target: Optional[str] = None) -> Tuple[pd.DataFrame, IngestReport]:
    """Produce a clean, schema-valid DataFrame plus an audit report."""
    rep = IngestReport(n_rows_in=len(df), source_columns=list(map(str, df.columns)))

    if mapping is None:
        mapping, auto_target = auto_map_columns(df)
        target = target or auto_target
    rep.column_mapping = {str(k): v for k, v in mapping.items()}
    rep.mapped_features = sorted(set(mapping.values()))
    rep.target_column = target

    # Drop fully-empty rows and exact duplicates up front.
    df = df.dropna(how="all").copy()
    dup = int(df.duplicated().sum())
    if dup:
        df = df.drop_duplicates()
        rep.duplicate_rows = dup

    medians = _reference_medians()
    out = pd.DataFrame(index=df.index)
    inv_map = {v: k for k, v in mapping.items()}

    for feat in FEATURES:
        lo, hi = _BOUNDS[feat]
        if feat in inv_map:
            raw = df[inv_map[feat]]
            if feat == "home_ownership_code":
                parser = _parse_home_ownership
            elif feat in ("debt_to_income", "credit_utilization"):
                parser = _to_ratio
            else:
                parser = _to_number
            parsed = raw.map(parser)
            # how many needed text coercion (were non-numeric strings)?
            coerced = int(((~raw.map(lambda v: isinstance(v, (int, float, np.integer, np.floating))))
                           & parsed.notna()).sum())
            if coerced:
                rep.coerced_text[feat] = coerced
            series = pd.to_numeric(parsed, errors="coerce")
        else:
            rep.synthesized_features.append(feat)
            series = pd.Series([np.nan] * len(df), index=df.index)

        # Impute missing with the reference median (or column median if richer).
        n_missing = int(series.isna().sum())
        if n_missing:
            col_med = series.median() if series.notna().any() else np.nan
            fill = col_med if np.isfinite(col_med) else medians[feat]
            if feat in ("num_delinquencies_2y", "num_open_accounts",
                        "num_recent_inquiries", "loan_term_months", "home_ownership_code"):
                fill = round(fill)
            series = series.fillna(fill)
            rep.missing_filled[feat] = n_missing

        # Clip wild values into the plausible range and count touched cells.
        clipped_mask = (series < lo) | (series > hi)
        n_clip = int(clipped_mask.sum())
        if n_clip:
            series = series.clip(lo, hi)
            rep.clipped[feat] = n_clip

        out[feat] = series.astype(float)

    # Carry the target through (coerced to 0/1) if we found one.
    if target and target in df.columns:
        tnum = pd.to_numeric(df[target].map(_to_number), errors="coerce")
        out["__target__"] = (tnum > 0).astype("Int64")

    rep.dropped_rows = rep.n_rows_in - len(out)
    rep.n_rows_out = len(out)
    if rep.n_features_mapped == 0:
        rep.warnings.append(
            "No columns matched the applicant schema — every feature was synthesized "
            "from defaults. Results are illustrative only; check your column headers.")
    elif rep.n_features_mapped < len(FEATURES) // 2:
        rep.warnings.append(
            f"Only {rep.n_features_mapped}/{len(FEATURES)} features matched; the rest "
            "were filled with reference defaults.")
    return out, rep


def ingest(source: Any) -> Tuple[pd.DataFrame, IngestReport]:
    """One-shot: read any file -> clean schema-valid frame + audit report."""
    df = read_any(source)
    mapping, target = auto_map_columns(df)
    return clean_frame(df, mapping, target)
