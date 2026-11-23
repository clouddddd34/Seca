import unittest
from time import time
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import create_app


def auth(name):
    return {"Authorization": "Bearer fixture-" + name}


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)

    def share(self, recipient="bob"):
        response = self.client.post("/documents/a/shares", headers=auth("alice"),
                                    json={"recipient": recipient, "expires_at": time() + 3600})
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def test_owner_and_live_recipient_can_read(self):
        self.assertEqual(self.client.get("/documents/a", headers=auth("alice")).status_code, 200)
        self.share()
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 200)

    def test_expired_share_denied(self):
        self.share()
        self.app.state.shares[0]["expires_at"] = time() - 1
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 404)

    def test_expiry_boundary_denied(self):
        self.share()
        expiry = self.app.state.shares[0]["expires_at"]
        with patch("app.time", return_value=expiry):
            self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 404)

    def test_migrated_owner_denied(self):
        self.app.state.users["alice"]["tenant"] = "south"
        self.assertEqual(self.client.get("/documents/a", headers=auth("alice")).status_code, 404)

    def test_migrated_recipient_denied(self):
        self.share()
        self.app.state.users["bob"]["tenant"] = "south"
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 404)

    def test_bare_identity_is_not_bearer_authentication(self):
        for path, identity in (("/documents/a", "alice"), ("/admin/inventory", "admin")):
            with self.subTest(path=path, identity=identity):
                self.assertEqual(self.client.get(path, headers={"Authorization": identity}).status_code, 401)

    def test_missing_and_invalid_authentication(self):
        for value in ("", "Bearer fixture-unknown", "fixture-alice", "Bearer alice"):
            with self.subTest(value=value):
                self.assertEqual(self.client.get("/documents/a", headers={"Authorization": value}).status_code, 401)

    def test_unshared_and_cross_tenant_reads_denied(self):
        for name in ("bob", "carol", "admin"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get("/documents/a", headers=auth(name)).status_code, 404)

    def test_recipient_cannot_reshare_or_revoke(self):
        share_id = self.share()
        response = self.client.post("/documents/a/shares", headers=auth("bob"),
                                    json={"recipient": "admin", "expires_at": time() + 3600})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.delete(f"/shares/{share_id}", headers=auth("bob")).status_code, 403)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertFalse(self.app.state.shares[0]["revoked"])

    def test_owner_revoke_denies_recipient_but_preserves_owner(self):
        share_id = self.share()
        self.assertEqual(self.client.delete(f"/shares/{share_id}", headers=auth("alice")).status_code, 204)
        self.assertEqual(self.client.get("/documents/a", headers=auth("bob")).status_code, 404)
        self.assertEqual(self.client.get("/documents/a", headers=auth("alice")).status_code, 200)

    def test_invalid_share_targets_and_expiry(self):
        for recipient, expiry in (("carol", time() + 3600), ("unknown", time() + 3600), ("bob", time() - 1)):
            with self.subTest(recipient=recipient, expiry=expiry):
                response = self.client.post("/documents/a/shares", headers=auth("alice"),
                                            json={"recipient": recipient, "expires_at": expiry})
                self.assertEqual(response.status_code, 422)
        self.assertEqual(self.app.state.shares, [])

    def test_migrated_owner_cannot_share_or_revoke(self):
        share_id = self.share()
        self.app.state.users["alice"]["tenant"] = "south"
        self.assertEqual(self.client.post("/documents/a/shares", headers=auth("alice"),
                         json={"recipient": "bob", "expires_at": time() + 3600}).status_code, 403)
        self.assertEqual(self.client.delete(f"/shares/{share_id}", headers=auth("alice")).status_code, 403)

    def test_admin_inventory_tracks_current_tenant(self):
        response = self.client.get("/admin/inventory", headers=auth("admin"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual({d["id"] for d in response.json()}, {"a", "b"})
        self.app.state.users["admin"]["tenant"] = "south"
        self.assertEqual({d["id"] for d in self.client.get("/admin/inventory", headers=auth("admin")).json()}, {"c"})

    def test_members_cannot_list_inventory(self):
        for name in ("alice", "bob", "carol"):
            with self.subTest(name=name):
                self.assertEqual(self.client.get("/admin/inventory", headers=auth(name)).status_code, 403)

    def test_missing_resources(self):
        self.assertEqual(self.client.get("/documents/missing", headers=auth("alice")).status_code, 404)
        self.assertEqual(self.client.delete("/shares/999", headers=auth("alice")).status_code, 404)


if __name__ == "__main__":
    unittest.main()
