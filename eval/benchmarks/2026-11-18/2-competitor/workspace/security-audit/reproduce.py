"""Minimal before/after evidence; creates exactly one order in a fresh instance."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.app import create_app
from fastapi.testclient import TestClient

with TestClient(create_app()) as client:
    evidence = []
    for method, path, actor, body in [
        ('GET', '/invoices/inv-b', 'alice', None),
        ('GET', '/invoices/inv-c', 'alice', None),
        ('GET', '/reports/report-s', 'alice', None),
        ('GET', '/admin/export', 'alice', None),
        ('POST', '/orders', 'alice', {'sku': 'book', 'quantity': 2, 'unit_price_cents': 1}),
    ]:
        response = client.request(method, path, headers={'Authorization': f'Bearer fixture-{actor}'}, json=body)
        evidence.append(dict(method=method, path=path, actor=actor, input=body,
                             status=response.status_code, response=response.json()))
    print(json.dumps(evidence, indent=2))
