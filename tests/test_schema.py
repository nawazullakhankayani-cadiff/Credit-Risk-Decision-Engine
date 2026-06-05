import unittest
from credit_risk.data.schema import validate_record, ValidationError, FEATURES

BASE = {f: 1 for f in FEATURES}
BASE.update(dict(loan_amount=10000, annual_income=40000, employment_length=3,
                 debt_to_income=0.3, credit_utilization=0.4, num_delinquencies_2y=0,
                 num_open_accounts=5, credit_history_length=6, num_recent_inquiries=1,
                 loan_term_months=36, interest_rate=10, home_ownership_code=1))


class TestSchema(unittest.TestCase):
    def test_valid(self):
        out = validate_record(BASE)
        self.assertEqual(set(out), set(FEATURES))

    def test_missing_field(self):
        bad = dict(BASE); bad.pop("loan_amount")
        with self.assertRaises(ValidationError):
            validate_record(bad)

    def test_out_of_range(self):
        bad = dict(BASE); bad["debt_to_income"] = 99
        with self.assertRaises(ValidationError):
            validate_record(bad)

    def test_non_numeric(self):
        bad = dict(BASE); bad["interest_rate"] = "abc"
        with self.assertRaises(ValidationError):
            validate_record(bad)


if __name__ == "__main__":
    unittest.main()
