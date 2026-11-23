"""Bounded evidence collection: two fresh instances, <=2 orders/7 mutations each."""
import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from app import create_app


results = {}
headers = {"Authorization": "Bearer fixture-alice"}
with TestClient(create_app()) as c:
    results["bare_account_auth"] = {
        "status": (r := c.get("/wallet", headers={"Authorization": "alice"})).status_code,
        "body": r.json(),
    }
    first = c.post("/orders", headers=headers, json={"quantity": 1}).json()["id"]
    second = c.post("/orders", headers=headers, json={"quantity": 1}).json()["id"]
    results["coupon_pay_statuses"] = [
        c.post(f"/orders/{oid}/pay", headers=headers, json={"coupon": "WELCOME"}).status_code
        for oid in (first, second)
    ]
    results["coupon_wallet"] = c.get("/wallet", headers=headers).json()
    results["second_order"] = c.get(f"/orders/{second}", headers=headers).json()
with TestClient(create_app()) as c:
    oid = c.post("/orders", headers=headers, json={"quantity": 3}).json()["id"]
    c.post(f"/orders/{oid}/pay", headers=headers, json={"coupon": "WELCOME"})
    results["refunds"] = []
    for _ in range(2):
        status = c.post(f"/orders/{oid}/refund", headers=headers).status_code
        results["refunds"].append({
            "status": status, "wallet": c.get("/wallet", headers=headers).json(),
            "order": c.get(f"/orders/{oid}", headers=headers).json(),
        })
print(json.dumps(results, indent=2))
