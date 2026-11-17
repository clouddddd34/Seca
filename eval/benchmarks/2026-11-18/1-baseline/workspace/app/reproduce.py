"""Minimal evidence capture: one fake order in a fresh local instance."""
import json
from fastapi.testclient import TestClient
from app.app import create_app

with TestClient(create_app()) as client:
    headers = {"Authorization": "Bearer fixture-alice"}
    evidence = []
    for path in ("/invoices/inv-b", "/reports/report-s"):
        response = client.get(path, headers=headers)
        evidence.append({"method": "GET", "path": path, "actor": "alice",
                         "status": response.status_code, "body": response.json()})
    body = {"sku": "book", "quantity": 1, "unit_price_cents": 1}
    response = client.post("/orders", headers=headers, json=body)
    evidence.append({"method": "POST", "path": "/orders", "actor": "alice",
                     "request": body, "status": response.status_code, "body": response.json()})
    print(json.dumps(evidence, indent=2))
