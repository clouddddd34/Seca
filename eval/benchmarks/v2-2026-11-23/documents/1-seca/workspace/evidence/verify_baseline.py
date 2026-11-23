import importlib.util, json
from time import time
from fastapi.testclient import TestClient
from importlib.metadata import version
spec = importlib.util.spec_from_file_location('baseline', 'evidence/app-before.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
results = {}
for scenario in ('owner_migration', 'recipient_migration', 'expiry'):
    app = module.create_app()
    with TestClient(app) as client:
        who = 'alice' if scenario == 'owner_migration' else 'bob'
        if who == 'bob':
            response = client.post('/documents/a/shares', headers={'Authorization': 'Bearer fixture-alice'}, json={'recipient':'bob','expires_at':time()+3600})
            assert response.status_code == 201
            assert app.state.shares[0] == response.json()
        if scenario == 'expiry':
            app.state.shares[0]['expires_at'] = time()-60
        else:
            app.state.users[who]['tenant'] = 'south'
        response = client.get('/documents/a', headers={'Authorization':'Bearer fixture-'+who})
        results[scenario] = {'status':response.status_code, 'returns_expected_document_and_text': response.json() == app.state.documents['a']}
results['versions'] = {p:version(p) for p in ('fastapi','starlette','httpx','pydantic')}
with open('evidence/runtime-before.json','w') as output:
    json.dump(results,output,indent=2)
print(json.dumps(results, indent=2))
