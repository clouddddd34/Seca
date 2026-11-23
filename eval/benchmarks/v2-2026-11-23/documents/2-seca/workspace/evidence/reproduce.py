import json, sys
from time import time
from pathlib import Path
from importlib.metadata import version
sys.path.insert(0, str(Path.cwd() / 'app'))
from app import create_app
from fastapi.testclient import TestClient
results = []
for case in ['owner_migration', 'recipient_migration', 'expiry']:
    app = create_app()
    with TestClient(app) as client:
        identity = 'alice' if case == 'owner_migration' else 'bob'
        headers = {'Authorization': 'Bearer fixture-' + identity}
        if identity == 'bob':
            r = client.post('/documents/a/shares', headers={'Authorization': 'Bearer fixture-alice'}, json={'recipient': 'bob', 'expires_at': time()+3600})
            assert r.status_code == 201 and len(app.state.shares) == 1
        baseline = client.get('/documents/a', headers=headers)
        if case == 'expiry':
            app.state.shares[0]['expires_at'] = time()-1
        else:
            app.state.users[identity]['tenant'] = 'south'
        result = client.get('/documents/a', headers=headers)
        results.append({'case': case, 'baseline_status': baseline.status_code, 'after_status': result.status_code, 'document_returned': result.json() == app.state.documents['a']})
print(json.dumps({'versions': {p: version(p) for p in ['fastapi', 'starlette', 'httpx', 'pydantic']}, 'results': results}, indent=2))
