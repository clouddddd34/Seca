"""Published evidence must retain JSONL observations while removing private values."""
import json
from pathlib import Path
import tempfile
import unittest

from eval.v2.archive import archive


class ArchiveTests(unittest.TestCase):
    def test_observations_and_failures_survive_redaction(self):
        token = 'Ab9' * 14 + 'x'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source, target = root/'source', root/'archive'
            run = source/'1-authenticated'
            work = run/'workspace'
            work.mkdir(parents=True)
            (run/'execution.json').write_text(json.dumps({'status': 'failed'}))
            failure = {'type': 'turn.failed', 'error': {'message': 'Provider blocked this assessment'}}
            (run/'events.jsonl').write_text(json.dumps(failure)+'\n')
            evidence = {'path': '/tickets/a', 'status': 200, 'session': token,
                        'local_path': 'C:\\Users\\Example User\\Temp\\evidence.jsonl'}
            (work/'evidence.jsonl').write_text(json.dumps(evidence)+'\n')
            (work/'assigned-skill').mkdir()
            (work/'assigned-skill/SKILL.md').write_text('Installed skill omitted')
            archive(source, target)
            saved = (target/'1-authenticated/workspace/evidence.jsonl').read_text()
            self.assertNotIn(token, saved)
            self.assertNotIn('Example User', saved)
            row = json.loads(saved)
            self.assertEqual((row['path'], row['status']), ('/tickets/a', 200))
            self.assertEqual(json.loads((target/'1-authenticated/failure.json').read_text()), [failure])
            self.assertFalse((target/'1-authenticated/workspace/assigned-skill').exists())


if __name__ == '__main__':
    unittest.main()
