"""Bounded local evidence: selected synthetic fields, no headers or tokens saved."""
import hashlib
import importlib.metadata
import json
import platform
from pathlib import Path

from fastapi.testclient import TestClient
from app.app import create_app
from test_security import headers


result = {
    "source_sha256": hashlib.sha256(Path("app/app.py").read_bytes()).hexdigest(),
    "python": platform.python_version(),
    "packages": {name: importlib.metadata.version(name) for name in
                 ("fastapi", "starlette", "pydantic", "uvicorn", "httpx", "anyio")},
    "observations": [],
}
with TestClient(create_app(), follow_redirects=False) as client:
    for path, field in (("/invoices/inv-a", "owner"), ("/invoices/inv-b", "owner"),
                        ("/reports/report-n", "tenant"), ("/reports/report-s", "tenant")):
        response = client.get(path, headers=headers("alice"))
        result["observations"].append({"actor": "alice", "method": "GET", "path": path,
                                       "status": response.status_code, field: response.json().get(field)})
    response = client.post("/orders", headers=headers("alice"), json={
        "sku": "book", "quantity": 2, "unit_price_cents": 1})
    result["observations"].append({"actor": "alice", "method": "POST", "path": "/orders",
                                   "quantity": 2, "submitted_unit_price": 1,
                                   "status": response.status_code,
                                   "total_cents": response.json().get("total_cents")})
print(json.dumps(result, indent=2))
