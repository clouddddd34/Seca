import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from app import create_app
from fastapi.testclient import TestClient
from importlib.metadata import version
out={'versions':{p:version(p) for p in ['fastapi','starlette','pydantic','httpx','uvicorn']},'responses':[]}
with TestClient(create_app()) as c:
 for who,path in [('alice','/invoices/inv-a'),('alice','/invoices/inv-b'),('alice','/invoices/inv-c'),('admin','/invoices/inv-a'),('alice','/reports/report-s'),('carol','/reports/report-n'),('alice','/admin/export'),('admin','/admin/export'),('alice','//admin/export'),('alice','/%61dmin/export'),('alice','/admin%2fexport')]:
  r=c.get(path,headers={'Authorization':'Bearer fixture-'+who},follow_redirects=False)
  out['responses'].append({'actor':who,'path':path,'status':r.status_code,'body':r.text})
 r=c.post('/orders',headers={'Authorization':'Bearer fixture-alice'},json={'sku':'book','quantity':2,'unit_price_cents':1})
 out['responses'].append({'actor':'alice','path':'POST /orders','input':{'sku':'book','quantity':2,'unit_price_cents':1},'status':r.status_code,'body':r.json()})
assert len(c.app.state.orders)==1
print(json.dumps(out,indent=2))
