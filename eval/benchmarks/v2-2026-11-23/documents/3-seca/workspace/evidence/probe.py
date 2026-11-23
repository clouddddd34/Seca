"""Bounded read proof; output contains status and equality only, no response bodies."""
import sys
from pathlib import Path
from time import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
from app import create_app
from fastapi.testclient import TestClient

for case in ("migrated_owner", "migrated_recipient", "expired_share"):
    app = create_app()
    who = "alice" if case == "migrated_owner" else "bob"
    with TestClient(app) as client:
        if who == "bob":
            response = client.post("/documents/a/shares", headers={"Authorization": "Bearer fixture-alice"},
                                   json={"recipient": "bob", "expires_at": time()+3600})
            assert response.status_code == 201
            assert len(app.state.shares) == 1
        headers = {"Authorization": "Bearer fixture-" + who}
        before = client.get("/documents/a", headers=headers)
        assert before.json() == app.state.documents["a"]
        if case == "expired_share":
            app.state.shares[0]["expires_at"] = time()-60
        else:
            app.state.users[who]["tenant"] = "south"
        after = client.get("/documents/a", headers=headers)
        print(f"{case}: baseline={before.status_code}; after={after.status_code}; "
              f"after_body_equals_document={after.json() == app.state.documents['a']}")
