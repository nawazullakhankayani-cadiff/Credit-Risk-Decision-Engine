import unittest
import pandas as pd
from credit_risk.features.pipeline import FeaturePipeline, ALL_FEATURES, ENGINEERED
from credit_risk.data.generate import generate


class TestFeatures(unittest.TestCase):
    def setUp(self):
        self.df = generate(500, seed=1)

    def test_engineered_present(self):
        pipe = FeaturePipeline().fit(self.df)
        out = pipe.transform(self.df)
        for c in ENGINEERED:
            self.assertIn(c, out.columns)
        self.assertEqual(list(out.columns), ALL_FEATURES)

    def test_standardization(self):
        pipe = FeaturePipeline().fit(self.df)
        out = pipe.transform(self.df, standardize=True)
        self.assertAlmostEqual(out["debt_to_income"].mean(), 0.0, places=5)

    def test_train_serve_parity(self):
        pipe = FeaturePipeline().fit(self.df)
        rec = self.df.iloc[0].to_dict()
        vec = pipe.transform_record({k: rec[k] for k in
              __import__('credit_risk.data.schema', fromlist=['FEATURES']).FEATURES})
        self.assertEqual(len(vec), len(ALL_FEATURES))


if __name__ == "__main__":
    unittest.main()
