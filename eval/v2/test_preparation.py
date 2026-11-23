"""Check input separation and tamper detection without model calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from eval.v2.suite import hashes, prepare_suite
from eval.v2.replace_invalid import replace

class PreparationTests(unittest.TestCase):
    def test_frozen_workspaces_exclude_evaluator_and_prior_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)
            competitor=base/'competitor'
            skill=competitor/'skills/owasp-audit'
            skill.mkdir(parents=True)
            (skill/'SKILL.md').write_text('Synthetic test stub; never used for assessments.')
            (competitor/'LICENSE').write_text('MIT License')
            binary=base/'seca.exe'
            binary.write_bytes(b'test-only binary placeholder')
            with patch('eval.prepare.subprocess.check_output',side_effect=lambda args,**kwargs: 'a'*40 if args[-1]=='HEAD' else ''):
                manifest=prepare_suite(base/'suite',competitor,binary)
            self.assertEqual(len(manifest['runs']),27)
            for run in manifest['runs']:
                work=base/'suite'/run['id']/'workspace'
                paths=set(hashes(work))
                self.assertEqual(hashes(work),run['inputs'])
                self.assertTrue({'app/app.py','app/README.md','tools/seca.exe'}<=paths)
                self.assertFalse(any(name in str(path) for path in paths for name in ('check.py','answer_key','scores.json','PROTOCOL.md','test_v2.py')))
                if run['arm']=='baseline':
                    self.assertEqual(paths,{'app/app.py','app/README.md','tools/seca.exe'})
            frozen=(base/'suite/manifest.json').read_bytes()
            failed=base/'suite/documents/2-seca'
            (failed/'execution.json').write_text(json.dumps({'status':'failed'}))
            (failed/'events.jsonl').write_text('You hit your spend cap')
            candidate=failed/'workspace/app/app.py'
            candidate.write_text(candidate.read_text(encoding='utf-8')+'\n# Simulated partial patch\n',encoding='utf-8')
            original_attempt=candidate.read_bytes()
            record=replace(base/'suite','documents/2-seca','documents/3-seca')
            self.assertEqual((base/'suite/manifest.json').read_bytes(),frozen)
            self.assertEqual((base/'suite'/record['archived_attempt']/'workspace/app/app.py').read_bytes(),original_attempt)
            replacement=next(r for r in manifest['runs'] if r['id']=='documents/2-seca')
            self.assertEqual(hashes(failed/'workspace'),replacement['inputs'])
            self.assertFalse((failed/'execution.json').exists())
            selected=manifest['runs'][0]
            work=base/'suite'/selected['id']/'workspace'
            (work/'unexpected-answer.txt').write_text('unintended extra input')
            self.assertNotEqual(hashes(work),selected['inputs'])
            self.assertEqual(json.loads((base/'suite/manifest.json').read_text())['runs'][0]['inputs'],selected['inputs'])

if __name__=='__main__':
    unittest.main()
