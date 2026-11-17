"""Bounded local reproduction; stores selected fields, never auth headers."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "app"))
from app import create_app
from fastapi.testclient import TestClient

output = {"source_sha256": hashlib.sha256(Path("app/app.py").read_bytes()).hexdigest(),
          "versions": {name: importlib.metadata.version(name) for name in
                       ("fastapi", "starlette", "pydantic", "httpx", "uvicorn")},
          "observations": []}
with TestClient(create_app(), follow_redirects=False) as client:
    for path, actor, field in (("/invoices/inv-b", "bob", "owner"),
                               ("/invoices/inv-b", "alice", "owner"),
                               ("/reports/report-s", "carol", "tenant"),
                               ("/reports/report-s", "alice", "tenant")):
        response = client.get(path, headers={"Authorization": "Bearer fixture-" + actor})
        output["observations"].append({"actor": actor, "path": path,
            "status": response.status_code, field: response.json().get(field)})
    response = client.post("/orders", headers={"Authorization": "Bearer fixture-alice"},
        json={"sku": "book", "quantity": 2, "unit_price_cents": 1})
    output["observations"].append({"actor": "alice", "path": "/orders", "quantity": 2,
        "submitted_price": 1, "expected_total": 2000, "status": response.status_code,
        "actual_total": response.json().get("total_cents")})
Path(sys.argv[1]).write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
