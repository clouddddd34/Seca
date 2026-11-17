"""Minimal proofs without storing tokens or resource bodies; one fake order."""
import json
from fastapi.testclient import TestClient
from app.app import create_app

with TestClient(create_app(), follow_redirects=False) as client:
    headers = {"Authorization": "Bearer fixture-alice"}
    invoice = client.get("/invoices/inv-b", headers=headers)
    report = client.get("/reports/report-s", headers=headers)
    order = client.post("/orders", headers=headers, json={
        "sku": "book", "quantity": 1, "unit_price_cents": 1})
    print(json.dumps({
        "invoice": {"status": invoice.status_code,
                    "other_owner_data_returned": invoice.json().get("owner") == "bob"},
        "report": {"status": report.status_code,
                   "other_tenant_data_returned": report.json().get("tenant") == "south"},
        "order": {"status": order.status_code,
                  "expected_total_cents": 1000,
                  "actual_total_cents": order.json().get("total_cents")}
    }, indent=2))
