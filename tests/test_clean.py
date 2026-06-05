import unittest
import pandas as pd
from credit_risk.data.clean import clean_dataframe
from credit_risk.data.schema import FEATURES, _BOUNDS


class TestClean(unittest.TestCase):
    def test_messy_headers_and_formats(self):
        df = pd.DataFrame({
            "Loan Amount": ["£10,000", "5000"],
            "Gross Salary": ["$40,000", ""],          # one missing -> imputed
            "Years Employed": [5, 3],
            "DTI": [0.3, 0.25],
            "Utilisation %": ["45%", "90%"],           # percent -> 0-1
            "Delinquencies": [0, 2],
            "Open Accounts": [8, 6],
            "Credit History (yrs)": [9, 4],
            "Hard Inquiries": [1, 3],
            "Term": ["36 months", "60 months"],        # parse int
            "APR": ["12.5%", "24%"],                   # stays as percent number
            "Home Ownership": ["Mortgage", "Rent"],    # text -> code
            "Notes": ["x", "y"],                        # ignored
        })
        clean, rep = clean_dataframe(df)
        self.assertEqual(list(clean.columns), FEATURES)
        self.assertEqual(rep["rows"], 2)
        self.assertEqual(len(rep["mapped"]), 12)
        self.assertAlmostEqual(clean.loc[0, "credit_utilization"], 0.45, places=3)
        self.assertAlmostEqual(clean.loc[0, "interest_rate"], 12.5, places=3)
        self.assertEqual(clean.loc[0, "loan_term_months"], 36)
        self.assertEqual(clean.loc[0, "home_ownership_code"], 1)
        self.assertEqual(clean.loc[1, "home_ownership_code"], 0)
        self.assertGreaterEqual(rep["imputed_cells"], 1)

    def test_missing_column_is_imputed(self):
        df = pd.DataFrame({"loan_amount": [10000], "annual_income": [40000]})
        clean, rep = clean_dataframe(df)
        self.assertEqual(list(clean.columns), FEATURES)
        self.assertEqual(len(clean), 1)
        for f in FEATURES:                             # everything in bounds, no NaNs
            lo, hi = _BOUNDS[f]
            self.assertFalse(clean[f].isna().any())
            self.assertTrue((clean[f] >= lo).all() and (clean[f] <= hi).all())

    def test_clipping(self):
        df = pd.DataFrame({f: [0] for f in FEATURES})
        df["interest_rate"] = [999]                    # absurd -> clipped to 60
        clean, rep = clean_dataframe(df)
        self.assertLessEqual(clean.loc[0, "interest_rate"], 60)
        self.assertGreaterEqual(rep["clipped_cells"], 1)


if __name__ == "__main__":
    unittest.main()
