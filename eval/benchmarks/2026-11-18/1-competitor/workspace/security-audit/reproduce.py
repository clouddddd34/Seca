"""Local paired checks; creates exactly two fake orders in one fresh instance."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.app import create_app
from fastapi.testclient import TestClient

with TestClient(create_app()) as client:
    results = []
    for actor, method, path, body in [
        ('alice', 'GET', '/invoices/inv-a', None),
        ('alice', 'GET', '/invoices/inv-b', None),
        ('alice', 'GET', '/invoices/inv-c', None),
        ('alice', 'GET', '/reports/report-n', None),
        ('alice', 'GET', '/reports/report-s', None),
        ('alice', 'GET', '/admin/export', None),
        ('admin', 'GET', '/admin/export', None),
        ('alice', 'POST', '/orders', {'sku':'book','quantity':1,'unit_price_cents':1000}),
        ('alice', 'POST', '/orders', {'sku':'book','quantity':1,'unit_price_cents':1}),
    ]:
        r = client.request(method, path, headers={'Authorization': f'Bearer fixture-{actor}'}, **({'json':body} if body else {}))
        results.append(dict(actor=actor, method=method, path=path, input=body, status=r.status_code, response=r.json()))
    print(json.dumps(results, indent=2))
