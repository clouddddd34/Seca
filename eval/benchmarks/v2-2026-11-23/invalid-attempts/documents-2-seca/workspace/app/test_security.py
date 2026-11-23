import unittest
from copy import deepcopy
from time import time

from fastapi.testclient import TestClient
from app import create_app


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def request(self, method, path, name=None, **kwargs):
        headers = {} if name is None else {"Authorization": "Bearer fixture-" + name}
        return self.client.request(method, path, headers=headers, follow_redirects=False, **kwargs)

    def share(self, recipient="bob"):
        response = self.request("POST", "/documents/a/shares", "alice",
                                json={"recipient": recipient, "expires_at": time() + 3600})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertEqual(self.app.state.shares[0]["recipient"], recipient)
        return response.json()["id"]

    def assert_read(self, name, doc="a", allowed=True):
        response = self.request("GET", "/documents/" + doc, name)
        if response.status_code == 200:
            self.assertEqual(response.json(), self.app.state.documents[doc])
        self.assertEqual(response.status_code, 200 if allowed else 404)
        if allowed:
            self.assertEqual(response.json(), self.app.state.documents[doc])
        else:
            self.assertNotIn("text", response.json())

    def test_owner_migration_revokes_read(self):
        self.assert_read("alice")
        self.app.state.users["alice"]["tenant"] = "south"
        self.assert_read("alice", allowed=False)

    def test_recipient_migration_revokes_read(self):
        self.share()
        self.assert_read("bob")
        self.app.state.users["bob"]["tenant"] = "south"
        self.assert_read("bob", allowed=False)

    def test_expired_share_revokes_read(self):
        self.share()
        self.assert_read("bob")
        self.app.state.shares[0]["expires_at"] = time() - 60
        self.assert_read("bob", allowed=False)

    def test_revocation_persists_and_blocks_read(self):
        share_id = self.share()
        self.assert_read("bob")
        self.assertFalse(self.app.state.shares[0]["revoked"])
        self.assertEqual(self.request("DELETE", f"/shares/{share_id}", "alice").status_code, 204)
        self.assertTrue(self.app.state.shares[0]["revoked"])
        self.assert_read("bob", allowed=False)
        self.assert_read("alice")

    def test_unshared_and_cross_tenant_reads_denied(self):
        self.assert_read("alice")
        self.assert_read("bob", allowed=False)
        self.assert_read("carol", allowed=False)
        self.assert_read("admin", allowed=False)
        self.assert_read("carol", "c")

    def test_recipient_cannot_reshare_or_revoke(self):
        share_id = self.share()
        before = deepcopy(self.app.state.shares)
        self.assertEqual(self.request("POST", "/documents/a/shares", "bob",
                         json={"recipient": "admin", "expires_at": time() + 3600}).status_code, 403)
        self.assertEqual(self.request("DELETE", f"/shares/{share_id}", "bob").status_code, 403)
        self.assertEqual(self.app.state.shares, before)
        self.assert_read("bob")

    def test_migrated_owner_cannot_share_or_revoke(self):
        share_id = self.share()
        self.app.state.users["alice"]["tenant"] = "south"
        before = deepcopy(self.app.state.shares)
        self.assertEqual(self.request("POST", "/documents/a/shares", "alice",
                         json={"recipient": "bob", "expires_at": time() + 3600}).status_code, 403)
        self.assertEqual(self.request("DELETE", f"/shares/{share_id}", "alice").status_code, 403)
        self.assertEqual(self.app.state.shares, before)

    def test_invalid_shares_leave_state_unchanged(self):
        for recipient, expiry in [("carol", time() + 3600), ("missing", time() + 3600),
                                  ("bob", time() - 60)]:
            with self.subTest(recipient=recipient, expiry=expiry):
                self.assertEqual(self.request("POST", "/documents/a/shares", "alice",
                                 json={"recipient": recipient, "expires_at": expiry}).status_code, 422)
                self.assertEqual(self.app.state.shares, [])

    def test_admin_inventory_tracks_current_tenant(self):
        response = self.request("GET", "/admin/inventory", "admin")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({d["id"] for d in response.json()}, {"a", "b"})
        self.app.state.users["admin"]["tenant"] = "south"
        response = self.request("GET", "/admin/inventory", "admin")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([d["id"] for d in response.json()], ["c"])
        self.assertEqual(self.request("GET", "/admin/inventory", "alice").status_code, 403)

    def test_anonymous_and_unknown_identity_denied(self):
        for name in (None, "unknown"):
            for method, path, kwargs in [
                ("GET", "/documents/a", {}), ("GET", "/admin/inventory", {}),
                ("DELETE", "/shares/1", {}),
                ("POST", "/documents/a/shares", {"json": {"recipient": "bob", "expires_at": time() + 3600}}),
            ]:
                self.assertEqual(self.request(method, path, name, **kwargs).status_code, 401)
        self.assertEqual(self.app.state.shares, [])

    def test_missing_resources_and_invalid_payload(self):
        self.assertEqual(self.request("GET", "/documents/missing", "alice").status_code, 404)
        self.assertEqual(self.request("DELETE", "/shares/999", "alice").status_code, 404)
        self.assertEqual(self.request("POST", "/documents/a/shares", "alice", json={}).status_code, 422)
        self.assertEqual(self.app.state.shares, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
