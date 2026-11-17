"""Check the evaluator against known vulnerable and fixed behavior."""
from pathlib import Path
import tempfile
import unittest
from eval.check_patch import evaluate

ROOT = Path(__file__).resolve().parents[1]


class EvaluationTests(unittest.TestCase):
    def test_rejects_original_and_accepts_minimal_fixes(self):
        source = ROOT / "eval/fixture/app.py"
        original = evaluate(source)
        self.assertEqual([original[k] for k in ("ownership", "tenant", "price")], [False] * 3)
        self.assertTrue(all(original[k] for k in ("decoy_preserved", "authentication_preserved", "quantity_validation_preserved")))
        fixed = source.read_text(encoding="utf-8")
        fixed = fixed.replace('return deepcopy(item)',
            'if item["owner"] != request.state.actor["id"]:\n            raise HTTPException(404, "Not found")\n        return deepcopy(item)')
        fixed = fixed.replace('def report(report_id: str):', 'def report(report_id: str, request: Request):')
        fixed = fixed.replace('return deepcopy(REPORTS[report_id])',
            'if REPORTS[report_id]["tenant"] != request.state.actor["tenant"]:\n            raise HTTPException(404, "Not found")\n        return deepcopy(REPORTS[report_id])')
        fixed = fixed.replace('body.quantity * body.unit_price_cents', 'body.quantity * CATALOG[body.sku]')
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "app.py"
            candidate.write_text(fixed, encoding="utf-8")
            result = evaluate(candidate)
        self.assertTrue(all(result.values()), result)


if __name__ == "__main__":
    unittest.main()
