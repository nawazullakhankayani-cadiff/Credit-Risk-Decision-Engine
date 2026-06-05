"""Primary model: XGBoost gradient-boosted trees with SHAP explanations.

Imported lazily so the package works without xgboost/shap installed. On a machine
with the full stack (``pip install -r requirements.txt``) this is the model the
training pipeline selects automatically.
"""
from __future__ import annotations
import numpy as np
from credit_risk.models.base import PDModel


class XGBPDModel(PDModel):
    name = "xgboost"

    def __init__(self, params: dict | None = None):
        from credit_risk.config import TRAIN
        self.params = dict(params or TRAIN.xgb_params)
        self._model = None
        self._explainer = None

    @staticmethod
    def available() -> bool:
        try:
            import xgboost  # noqa: F401
            return True
        except Exception:
            return False

    def fit(self, X, y, eval_set=None) -> "XGBPDModel":
        import xgboost as xgb
        # Handle imbalance with scale_pos_weight.
        y = np.asarray(y)
        spw = float((y == 0).sum()) / max(float((y == 1).sum()), 1.0)
        params = dict(self.params)
        params["scale_pos_weight"] = spw
        self._model = xgb.XGBClassifier(**params)
        fit_kwargs = {}
        if eval_set is not None:
            fit_kwargs.update(eval_set=eval_set, verbose=False)
        self._model.fit(X, y, **fit_kwargs)
        return self

    def predict_proba(self, X) -> np.ndarray:
        return self._model.predict_proba(np.asarray(X, dtype=float))[:, 1]

    def feature_contributions(self, x) -> np.ndarray:
        import shap
        if self._explainer is None:
            self._explainer = shap.TreeExplainer(self._model)
        x = np.asarray(x, dtype=float).reshape(1, -1)
        vals = self._explainer.shap_values(x)
        if isinstance(vals, list):  # older shap returns a list per class
            vals = vals[-1]
        return np.asarray(vals).reshape(-1)

    def to_state(self) -> dict:
        import tempfile, os, base64
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        self._model.save_model(path)
        with open(path, "rb") as fh:
            blob = base64.b64encode(fh.read()).decode()
        os.unlink(path)
        return {"name": self.name, "params": self.params, "booster_b64": blob}

    @classmethod
    def from_state(cls, state: dict) -> "XGBPDModel":
        import xgboost as xgb, tempfile, os, base64
        m = cls(params=state["params"])
        m._model = xgb.XGBClassifier(**state["params"])
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        with open(path, "wb") as fh:
            fh.write(base64.b64decode(state["booster_b64"]))
        m._model.load_model(path)
        os.unlink(path)
        return m
