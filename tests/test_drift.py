import unittest
import pandas as pd
from credit_risk.data.generate import generate
from credit_risk.monitoring import drift as D


class TestDrift(unittest.TestCase):
    def setUp(self):
        self.ref = generate(3000, seed=1)
        self.cols = ["debt_to_income", "credit_utilization", "annual_income"]

    def test_no_drift_same_dist(self):
        cur = generate(3000, seed=2)
        report = D.feature_drift(self.ref, cur, self.cols)
        self.assertEqual(D.overall_status(report), D.STABLE)

    def test_detects_shift(self):
        cur = generate(3000, seed=2)
        cur["debt_to_income"] = cur["debt_to_income"] + 0.8  # inject shift
        report = D.feature_drift(self.ref, cur, self.cols)
        self.assertIn(report["debt_to_income"]["status"], (D.MODERATE, D.SIGNIFICANT))


if __name__ == "__main__":
    unittest.main()
