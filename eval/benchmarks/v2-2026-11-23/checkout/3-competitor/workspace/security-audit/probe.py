"""Read-only source selection; all HTTP calls stay inside TestClient."""
import importlib.util
import json
from pathlib import Path
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location('baseline', Path('security-audit/original-app.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = {}
with TestClient(module.create_app()) as client:
    results['bare_account'] = {'status': client.get('/wallet', headers={'Authorization': 'alice'}).status_code}
with TestClient(module.create_app(), headers={'Authorization': 'Bearer fixture-alice'}) as client:
    # Two orders; four mutations total.
    for _ in range(2):
        client.post('/orders', json={'quantity': 1})
    client.post('/orders/1/pay', json={'coupon': 'WELCOME'})
    before = client.get('/wallet').json()
    response = client.post('/orders/2/pay', json={'coupon': 'WELCOME'})
    results['coupon_reuse'] = dict(status=response.status_code, before=before,
                                  after=client.get('/wallet').json(), order=client.get('/orders/2').json())
with TestClient(module.create_app(), headers={'Authorization': 'Bearer fixture-alice'}) as client:
    # One order; four mutations total.
    client.post('/orders', json={'quantity': 3})
    client.post('/orders/1/pay', json={'coupon': 'WELCOME'})
    client.post('/orders/1/refund')
    before = client.get('/wallet').json()
    response = client.post('/orders/1/refund')
    results['refund_replay'] = dict(status=response.status_code, before=before,
                                   after=client.get('/wallet').json(), order=client.get('/orders/1').json())
Path('security-audit/baseline-evidence.json').write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results, indent=2))
