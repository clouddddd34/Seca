"""Exercise actual loopback observation/cleanup without spending model calls."""
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch
import httpx
from eval.v2.website import run_one_website

class WebsiteTests(unittest.TestCase):
    def test_authenticated_observation_and_secret_minimization(self):
        def simulated_agent(folder, executable, model, seconds):
            prompt=(folder/'prompt.txt').read_text(encoding='utf-8')
            origin=re.search(r'http://127\.0\.0\.1:\d+',prompt).group()
            with httpx.Client(base_url=origin,timeout=5) as client:
                self.assertEqual(client.get('/').status_code,200)
                self.assertEqual(client.post('/login',headers={'Origin':origin},data={'username':'alice','password':'fixture-alice'}).status_code,303)
                self.assertIn('Synthetic Alice ticket',client.get('/tickets/a').text)
                self.assertEqual(client.get('/tickets/b').status_code,404)
            (folder/'events.jsonl').write_text(json.dumps({'type':'turn.completed','usage':{'input_tokens':1,'output_tokens':2}}))
            return {'status':'completed'}
        with tempfile.TemporaryDirectory() as temp, patch('eval.v2.website.run_one',side_effect=simulated_agent):
            folder=Path(temp)/'check'
            result=run_one_website(folder,True,'test-only',10)
            self.assertEqual(result['status'],'completed')
            observations=json.loads((folder/'observations.json').read_text())
            self.assertEqual(len(observations['requests']),4)
            self.assertTrue(observations['tickets_unchanged'])
            self.assertTrue(observations['server_stopped'])
            self.assertNotIn('fixture-alice',(folder/'observations.json').read_text())
            self.assertEqual(json.loads((folder/'metrics.json').read_text())['usage']['output_tokens'],2)

    def test_agent_failure_still_stops_listener(self):
        with tempfile.TemporaryDirectory() as temp, patch('eval.v2.website.run_one',side_effect=RuntimeError('simulated failure')):
            folder=Path(temp)/'failure'
            with self.assertRaisesRegex(RuntimeError,'simulated failure'):
                run_one_website(folder,False,'test-only',10)
            observations=json.loads((folder/'observations.json').read_text())
            self.assertTrue(observations['server_stopped'])
            self.assertTrue(observations['tickets_unchanged'])
            self.assertEqual(observations['requests'],[])

if __name__=='__main__':
    unittest.main()
