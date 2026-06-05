"""End-to-end training pipeline.

Steps: load (or generate) data -> stratified train/valid/test split -> fit feature
pipeline -> train PD model (XGBoost if available, else logistic baseline) -> fit
isotonic calibrator on validation -> evaluate on held-out test (AUC/Gini/KS/Brier)
-> persist a versioned, hashed bundle to the model registry with full metadata.

Run:  python -m credit_risk.train            # uses/creates data/loans.csv
"""
from __future__ import annotations
import json, platform, sys
from pathlib import Path
import numpy as np
import pandas as pd

from credit_risk import __version__
from credit_risk.config import PATHS, TRAIN
from credit_risk.data.generate import generate
from credit_risk.features.pipeline import FeaturePipeline, ALL_FEATURES
from credit_risk.models.baseline import LogisticRegressionPD
from credit_risk.models.calibration import IsotonicCalibrator
from credit_risk.models.registry import ModelRegistry
from credit_risk.monitoring import metrics as M


def _stratified_split(df, y_col, sizes, seed):
    rng = np.random.default_rng(seed)
    parts = {"train": [], "valid": [], "test": []}
    for cls in df[y_col].unique():
        idx = df.index[df[y_col] == cls].to_numpy()
        rng.shuffle(idx)
        n = len(idx)
        n_test = int(n * sizes["test"])
        n_valid = int(n * sizes["valid"])
        parts["test"].append(idx[:n_test])
        parts["valid"].append(idx[n_test:n_test + n_valid])
        parts["train"].append(idx[n_test + n_valid:])
    return {k: df.loc[np.concatenate(v)].reset_index(drop=True) for k, v in parts.items()}


def main(data_path: Path | None = None, n_rows: int = 30_000) -> dict:
    PATHS.data.mkdir(parents=True, exist_ok=True)
    data_path = data_path or (PATHS.data / "loans.csv")
    if data_path.exists():
        df = pd.read_csv(data_path)
    else:
        df = generate(n_rows)
        df.to_csv(data_path, index=False)
    print(f"[data] {len(df)} rows, default rate {df['default'].mean():.3f}")

    splits = _stratified_split(df, "default",
                               {"test": TRAIN.test_size, "valid": TRAIN.valid_size},
                               TRAIN.random_state)
    pipe = FeaturePipeline().fit(splits["train"])
    Xtr = pipe.transform(splits["train"]).to_numpy()
    Xva = pipe.transform(splits["valid"]).to_numpy()
    Xte = pipe.transform(splits["test"]).to_numpy()
    ytr = splits["train"]["default"].to_numpy()
    yva = splits["valid"]["default"].to_numpy()
    yte = splits["test"]["default"].to_numpy()

    # Select model: XGBoost primary, logistic baseline fallback.
    from credit_risk.models.xgb_model import XGBPDModel
    if XGBPDModel.available():
        print("[model] training XGBoost (primary)")
        model = XGBPDModel().fit(Xtr, ytr, eval_set=[(Xva, yva)])
    else:
        print("[model] xgboost unavailable -> training logistic baseline")
        model = LogisticRegressionPD().fit(Xtr, ytr)

    # Calibrate on validation, evaluate on test.
    raw_va = model.predict_proba(Xva)
    calib = IsotonicCalibrator().fit(raw_va, yva)
    raw_te = model.predict_proba(Xte)
    cal_te = calib.transform(raw_te)

    test_metrics = M.summary(yte, raw_te)
    test_metrics["brier_calibrated"] = round(M.brier_score(yte, cal_te), 4)
    test_metrics["brier_uncalibrated"] = test_metrics["brier"]
    print(f"[eval] {json.dumps(test_metrics)}")

    bundle = {
        "pipeline": pipe.to_dict(),
        "model": model.to_state(),
        "calibrator": calib.to_dict(),
        "features": ALL_FEATURES,
    }
    metadata = {
        "package_version": __version__,
        "model_name": model.name,
        "python": platform.python_version(),
        "rows_total": int(len(df)),
        "rows_train": int(len(splits["train"])),
        "data_source": str(data_path.name),
    }
    reg = ModelRegistry(PATHS.artifacts)
    version = reg.save(bundle, test_metrics, metadata)
    print(f"[registry] saved model version {version}")

    # Persist a reference sample for drift monitoring.
    splits["train"][ALL_FEATURES[:12]].to_csv(PATHS.data / "reference_sample.csv", index=False) \
        if False else splits["train"].to_csv(PATHS.data / "reference_sample.csv", index=False)
    return {"version": version, "metrics": test_metrics, "metadata": metadata}


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30_000
    main(n_rows=n)
