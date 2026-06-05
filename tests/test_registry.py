import unittest, tempfile
from pathlib import Path
from credit_risk.models.registry import ModelRegistry


class TestRegistry(unittest.TestCase):
    def test_save_and_load_latest(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = ModelRegistry(Path(tmp))
            v = reg.save({"model": {"name": "demo"}}, {"auc": 0.8}, {"note": "t"})
            self.assertEqual(reg.latest_version(), v)
            loaded = reg.load()
            self.assertEqual(loaded["manifest"]["metrics"]["auc"], 0.8)
            self.assertIn(v, reg.list_versions())


if __name__ == "__main__":
    unittest.main()
