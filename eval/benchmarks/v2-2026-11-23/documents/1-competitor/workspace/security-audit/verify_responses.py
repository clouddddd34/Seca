import json, runpy, sys
from pathlib import Path
from time import time
from fastapi.testclient import TestClient
sys.path.insert(0, str(Path('app').resolve()))
from app import create_app
out={}
for label, factory in [('before',runpy.run_path('security-audit/original-app.py.txt')['create_app']),('after',create_app)]:
    results={}
    for scenario in ['expiry','owner_migration','recipient_migration']:
        app=factory()
        with TestClient(app) as c:
            headers=lambda n: {'Authorization':f'Bearer fixture-{n}'}
            if scenario!='owner_migration':
                assert c.post('/documents/a/shares',headers=headers('alice'),json={'recipient':'bob','expires_at':time()+3600}).status_code==201
            who='alice' if scenario=='owner_migration' else 'bob'
            if scenario=='expiry': app.state.shares[0]['expires_at']=time()-1
            else: app.state.users[who]['tenant']='south'
            r=c.get('/documents/a',headers=headers(who))
            results[scenario]={'status':r.status_code,'body':r.json()}
    out[label]=results
with TestClient(create_app()) as c:
    out['framework_routes']={p:c.get(p).status_code for p in ['/openapi.json','/docs','/redoc','/docs/oauth2-redirect']}
Path('security-audit/responses.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
