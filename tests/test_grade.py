import unittest
from credit_risk.scoring.grade import decide, assign_grade


class TestGrade(unittest.TestCase):
    def test_low_pd_approves(self):
        d = decide(0.005)
        self.assertEqual(d["risk_grade"], "A")
        self.assertEqual(d["decision"], "APPROVE")

    def test_high_pd_declines(self):
        d = decide(0.5)
        self.assertEqual(d["decision"], "DECLINE")

    def test_boundary_forces_review(self):
        # 0.07 is the A/B->C boundary; near it should trigger human review
        d = decide(0.071)
        self.assertTrue(d["human_review"])

    def test_grade_ordering(self):
        grades = [assign_grade(p)[0] for p in [0.01, 0.05, 0.1, 0.18, 0.3, 0.6]]
        self.assertEqual(grades, ["A", "B", "C", "D", "E", "F"])


if __name__ == "__main__":
    unittest.main()
