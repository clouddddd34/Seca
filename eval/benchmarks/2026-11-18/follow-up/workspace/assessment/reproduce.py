import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path
from test_security import module, headers
from fastapi.testclient import TestClient

result = {"python": platform.python_version(), "packages": {name: importlib.metadata.version(name) for name in ("fastapi", "starlette", "pydantic", "httpx", "uvicorn", "anyio")}, "source_sha256": hashlib.sha256(Path("app/app.py").read_bytes()).hexdigest(), "reads": []}
with TestClient(module.create_app(), follow_redirects=False) as client:
    for actor, path in (("alice", "/invoices/inv-a"), ("alice", "/invoices/inv-b"), ("alice", "/reports/report-n"), ("alice", "/reports/report-s")):
        response = client.get(path, headers=headers(actor))
        body = response.json()
        result["reads"].append({"actor": actor, "path": path, "status": response.status_code, "returned_id": body.get("id"), "owner_matches_actor": body.get("owner") == actor if "owner" in body else None, "tenant_matches_actor": body.get("tenant") == "north" if "tenant" in body else None})
    result["orders_before"] = len(client.get("/orders", headers=headers("alice")).json())
    response = client.post("/orders", headers=headers("alice"), json={"sku": "book", "quantity": 2, "unit_price_cents": 1})
    saved = client.get("/orders", headers=headers("alice")).json()
    result["purchase"] = {"status": response.status_code, "orders_after": len(saved), "persisted_total": saved[-1]["total_cents"], "catalog_expected_total": 2000, "read_matches_creation": saved[-1] == response.json()}
print(json.dumps(result, indent=2))
