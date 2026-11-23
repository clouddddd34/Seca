"""Incomplete assessments must never silently count as successful or zero-cost runs."""
import json
from pathlib import Path
import tempfile
import unittest

from eval.v2.summarize import summarize


class SummaryTests(unittest.TestCase):
    def test_partial_summary_excludes_failures_and_unstarted_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            runs = [dict(id=f'documents/{i}-baseline', arm='baseline', fixture='documents')
                    for i in range(1, 4)]
            (root/'manifest.json').write_text(json.dumps({'runs': runs}))
            review = dict(discovery=2, complete_runtime_proofs=1, false_accusations=0, fixes=2)
            (root/'review.json').write_text(json.dumps({runs[0]['id']: review}))
            for run, status in zip(runs, ('timed_out', 'failed')):
                folder = root/run['id']
                folder.mkdir(parents=True)
                (folder/'execution.json').write_text(json.dumps({'status': status, 'elapsed_seconds': 180}))
            first = root/runs[0]['id']
            (first/'metrics.json').write_text(json.dumps({'usage': None, 'cost_usd': None}))
            (first/'patch-check.json').write_text(json.dumps({'control': True}))
            with self.assertRaisesRegex(ValueError, 'Suite incomplete'):
                summarize(root)
            result = summarize(root, allow_partial=True)
            self.assertFalse(result['complete'])
            self.assertEqual(result['scored_runs'], 1)
            self.assertEqual([r['execution']['status'] for r in result['excluded_runs']], ['failed', 'not_started'])
            arm = result['arms']['baseline']
            self.assertEqual(arm['opportunities'], 2)
            self.assertEqual(arm['timed_out'], 1)
            self.assertEqual(arm['unknown_usage_runs'], 1)
            self.assertIsNone(arm['cost_usd'])
            self.assertIsNone(arm['median_completed_seconds'])
            (root/'review.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'Review every run'):
                summarize(root, allow_partial=True)


if __name__ == '__main__':
    unittest.main()
