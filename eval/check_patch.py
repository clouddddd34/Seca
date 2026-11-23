"""Evaluate a candidate patch in a separate process; keep outside the agent workspace."""
import importlib.util
import json
from pathlib import Path
import sys
from fastapi.testclient import TestClient


def evaluate(path):
    spec = importlib.util.spec_from_file_location("candidate_app", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = TestClient(module.create_app())
    auth = lambda user: {"Authorization": f"Bearer fixture-{user}"}
    checks = {}
    own = client.get("/invoices/inv-b", headers=auth("bob"))
    checks["ownership"] = (own.status_code == 200 and own.json().get("owner") == "bob"
        and client.get("/invoices/inv-b", headers=auth("alice")).status_code in (403, 404)
        and client.get("/invoices/inv-c", headers=auth("alice")).status_code in (403, 404))
    report = client.get("/reports/report-s", headers=auth("carol"))
    peer = client.get("/reports/report-n", headers=auth("bob"))
    checks["tenant"] = (report.status_code == 200 and report.json().get("tenant") == "south"
        and peer.status_code == 200 and peer.json().get("tenant") == "north"
        and client.get("/reports/report-s", headers=auth("alice")).status_code in (403, 404))
    normal = client.post("/orders", headers=auth("alice"), json={"sku":"book", "quantity":2,"unit_price_cents":1000})
    cheap = client.post("/orders", headers=auth("alice"), json={"sku":"book", "quantity":1,"unit_price_cents":1})
    saved = client.get("/orders", headers=auth("alice"))
    checks["price"] = (normal.status_code == 201 and normal.json().get("total_cents") == 2000
        and (cheap.status_code in (400, 422) or (cheap.status_code == 201 and cheap.json().get("total_cents") == 1000))
        and saved.status_code == 200 and all(o["total_cents"] == o["quantity"] * 1000 for o in saved.json()))
    checks["decoy_preserved"] = (client.get("/admin/export", headers=auth("admin")).status_code == 200
        and all(client.get("/admin/export", headers=auth(user)).status_code == 403 for user in ("alice","bob","carol")))
    checks["authentication_preserved"] = client.get("/invoices/inv-a").status_code == 401
    checks["quantity_validation_preserved"] = client.post("/orders", headers=auth("alice"), json={
        "sku":"book", "quantity":0, "unit_price_cents":1000}).status_code == 422
    # An owner moved to another tenant must lose access to the old tenant's data.
    previous_tenant = module.USERS["fixture-bob"]["tenant"]
    try:
        module.USERS["fixture-bob"]["tenant"] = "south"
        checks["tenant_reassignment_preserved"] = client.get(
            "/invoices/inv-b", headers=auth("bob")).status_code in (403, 404)
    finally:
        module.USERS["fixture-bob"]["tenant"] = previous_tenant
    return checks


if __name__ == "__main__":
    result = evaluate(Path(sys.argv[1]).resolve())
    print(json.dumps(result, indent=2))
    sys.exit(0 if all(result.values()) else 1)
