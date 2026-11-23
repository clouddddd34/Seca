import sys
import unittest
from pathlib import Path
from time import time

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import create_app


def auth(name):
    return {"Authorization": f"Bearer fixture-{name}"}


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def share(self):
        response = self.client.post(
            "/documents/a/shares", headers=auth("alice"),
            json={"recipient": "bob", "expires_at": time() + 3600},
        )
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def test_expired_share_denied(self):
        self.share()
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 200)
        self.app.state.shares[0]["expires_at"] = time() - 60
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 404)

    def test_migrated_owner_denied(self):
        self.app.state.users["alice"]["tenant"] = "south"
        self.assertEqual(self.client.get("/documents/a", headers=auth("alice")).status_code, 404)

    def test_migrated_recipient_denied(self):
        self.share()
        self.app.state.users["bob"]["tenant"] = "south"
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 404)

    def test_bare_identity_is_not_bearer_token(self):
        for name, path in (("alice", "/documents/a"), ("admin", "/admin/inventory")):
            with self.subTest(name=name):
                self.assertEqual(self.client.get(path, headers={"Authorization": name}).status_code, 401)

    def test_owner_share_revoke_workflow(self):
        self.assertEqual(self.client.get("/documents/a", headers=auth("alice")).status_code, 200)
        share_id = self.share()
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 200)
        self.assertEqual(self.client.delete(f"/shares/{share_id}", headers=auth("alice")).status_code, 204)
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 404)

    def test_unshared_and_cross_tenant_access_denied(self):
        for name, doc in (("bob", "a"), ("carol", "a"), ("alice", "c"), ("admin", "a")):
            with self.subTest(name=name, doc=doc):
                self.assertEqual(self.client.get(f"/documents/{doc}", headers=auth(name)).status_code, 404)

    def test_share_validation(self):
        for recipient, expiry in (("carol", time() + 3600), ("missing", time() + 3600), ("bob", time() - 60)):
            response = self.client.post("/documents/a/shares", headers=auth("alice"),
                                        json={"recipient": recipient, "expires_at": expiry})
            self.assertEqual(response.status_code, 422)
        self.assertEqual(self.app.state.shares, [])

    def test_recipient_cannot_reshare_or_revoke(self):
        share_id = self.share()
        self.assertEqual(self.client.post("/documents/a/shares", headers=auth("bob"),
                         json={"recipient": "admin", "expires_at": time() + 3600}).status_code, 403)
        self.assertEqual(self.client.delete(f"/shares/{share_id}", headers=auth("bob")).status_code, 403)
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 200)

    def test_migrated_owner_cannot_share_or_revoke(self):
        share_id = self.share()
        self.app.state.users["alice"]["tenant"] = "south"
        self.assertEqual(self.client.post("/documents/a/shares", headers=auth("alice"),
                         json={"recipient": "bob", "expires_at": time() + 3600}).status_code, 403)
        self.assertEqual(self.client.delete(f"/shares/{share_id}", headers=auth("alice")).status_code, 403)

    def test_inventory_role_and_current_tenant(self):
        self.assertEqual(self.client.get("/admin/inventory", headers=auth("alice")).status_code, 403)
        response = self.client.get("/admin/inventory", headers=auth("admin"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual({d["id"] for d in response.json()}, {"a", "b"})
        self.app.state.users["admin"]["tenant"] = "south"
        response = self.client.get("/admin/inventory", headers=auth("admin"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual({d["id"] for d in response.json()}, {"c"})

    def test_invalid_auth_and_missing_resources(self):
        for headers in ({}, auth("missing"), {"Authorization": "Basic fixture-alice"}):
            self.assertEqual(self.client.get("/documents/a", headers=headers).status_code, 401)
        self.assertEqual(self.client.get("/documents/missing", headers=auth("alice")).status_code, 404)
        self.assertEqual(self.client.delete("/shares/999", headers=auth("alice")).status_code, 404)


if __name__ == "__main__":
    unittest.main()
