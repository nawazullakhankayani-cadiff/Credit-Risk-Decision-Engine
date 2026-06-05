import unittest
import numpy as np
from credit_risk.monitoring import metrics as M


class TestMetrics(unittest.TestCase):
    def test_auc_perfect(self):
        y = np.array([0, 0, 1, 1])
        s = np.array([0.1, 0.2, 0.8, 0.9])
        self.assertAlmostEqual(M.roc_auc(y, s), 1.0, places=6)

    def test_auc_random_half(self):
        rng = np.random.default_rng(0)
        y = rng.integers(0, 2, 5000)
        s = rng.uniform(size=5000)
        self.assertAlmostEqual(M.roc_auc(y, s), 0.5, delta=0.05)

    def test_gini_relation(self):
        y = np.array([0, 1, 0, 1, 1, 0])
        s = np.array([0.2, 0.7, 0.3, 0.6, 0.9, 0.1])
        self.assertAlmostEqual(M.gini(y, s), 2 * M.roc_auc(y, s) - 1, places=6)


if __name__ == "__main__":
    unittest.main()
