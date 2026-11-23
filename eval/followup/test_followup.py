"""Validate follow-up isolation and the harmless denial fixture without model calls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from eval.followup.run import ROOT, prepare, execute
from eval.v2.suite import hashes


class FollowupTests(unittest.TestCase):
    def test_noncompleted_attempt_stops_sequence(self):
        for status in ('timed_out', 'failed', 'incomplete'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as temp:
                output = Path(temp)/'study'
                prepare(output)
                with patch('eval.followup.run.shutil.which', return_value='codex'), \
                     patch('eval.followup.run.subprocess.check_output', return_value='test-cli'), \
                     patch('eval.followup.run.run_one', return_value={'status': status}) as run, \
                     patch('eval.followup.run.usage', return_value=None):
                    with self.assertRaises(RuntimeError):
                        execute(output)
                    self.assertEqual(run.call_count, 1)

    def test_preparation_freezes_both_revisions_without_evaluator(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)/'study'
            manifest = prepare(root)
            self.assertEqual(len(manifest['runs']), 8)
            by_revision = {}
            for run in manifest['runs']:
                work = root/run['id']/'workspace'
                self.assertEqual(hashes(work), run['inputs'])
                self.assertTrue(all(name.startswith(('app/', 'assigned-skill/')) for name in run['inputs']))
                by_revision[run['revision']] = run['inputs']['assigned-skill/SKILL.md']
            self.assertNotEqual(by_revision['original'], by_revision['revised'])
            with self.assertRaises(ValueError):
                prepare(root)

    def test_denial_fixture_records_one_attempt_and_no_success(self):
        helper = ROOT/'eval/followup/fixtures/denial/verify.py'
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run([sys.executable, str(helper)], cwd=temp,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'denied')
            records = (Path(temp)/'verification-attempts.jsonl').read_text().splitlines()
            self.assertEqual(len(records), 1)
            self.assertEqual(json.loads(records[0])['result'], 'denied')
            self.assertEqual(len(list(Path(temp).iterdir())), 1)


if __name__ == '__main__':
    unittest.main()
