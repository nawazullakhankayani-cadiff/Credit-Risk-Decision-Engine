import unittest
import numpy as np
from credit_risk.data.generate import generate
from credit_risk.features.pipeline import FeaturePipeline
from credit_risk.models.baseline import LogisticRegressionPD
from credit_risk.models.calibration import IsotonicCalibrator
from credit_risk.monitoring import metrics as M


class TestModelPipeline(unittest.TestCase):
    def setUp(self):
        df = generate(4000, seed=7)
        self.pipe = FeaturePipeline().fit(df)
        self.X = self.pipe.transform(df).to_numpy()
        self.y = df["default"].to_numpy()

    def test_model_learns_signal(self):
        m = LogisticRegressionPD(epochs=300).fit(self.X, self.y)
        p = m.predict_proba(self.X)
        self.assertGreater(M.roc_auc(self.y, p), 0.7)

    def test_proba_bounds(self):
        m = LogisticRegressionPD(epochs=100).fit(self.X, self.y)
        p = m.predict_proba(self.X)
        self.assertTrue((p >= 0).all() and (p <= 1).all())

    def test_calibration_monotonic(self):
        m = LogisticRegressionPD(epochs=100).fit(self.X, self.y)
        cal = IsotonicCalibrator().fit(m.predict_proba(self.X), self.y)
        xs = np.linspace(0, 1, 50)
        ys = cal.transform(xs)
        self.assertTrue(np.all(np.diff(ys) >= -1e-9))

    def test_serialization_roundtrip(self):
        m = LogisticRegressionPD(epochs=50).fit(self.X, self.y)
        m2 = LogisticRegressionPD.from_state(m.to_state())
        np.testing.assert_allclose(m.predict_proba(self.X[:5]),
                                   m2.predict_proba(self.X[:5]))


if __name__ == "__main__":
    unittest.main()
