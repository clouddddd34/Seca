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

    def request(self, method, path, who=None, **kwargs):
        headers = {} if who is None else {"Authorization": "Bearer fixture-" + who}
        return self.client.request(method, path, headers=headers, **kwargs)

    def share(self):
        response = self.request("POST", "/documents/a/shares", "alice",
                                json={"recipient": "bob", "expires_at": time() + 3600})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertEqual(self.app.state.shares[0], response.json())
        return response.json()["id"]

    def test_owner_migration_blocks_read(self):
        self.assertEqual(self.request("GET", "/documents/a", "alice").json()["id"], "a")
        self.app.state.users["alice"]["tenant"] = "south"
        self.assertEqual(self.request("GET", "/documents/a", "alice").status_code, 404)

    def test_recipient_migration_blocks_read(self):
        self.share()
        self.assertEqual(self.request("GET", "/documents/a", "bob").json()["id"], "a")
        self.app.state.users["bob"]["tenant"] = "south"
        self.assertEqual(self.request("GET", "/documents/a", "bob").status_code, 404)

    def test_expired_share_blocks_read(self):
        self.share()
        self.assertEqual(self.request("GET", "/documents/a", "bob").json()["id"], "a")
        self.app.state.shares[0]["expires_at"] = time() - 60
        self.assertEqual(self.request("GET", "/documents/a", "bob").status_code, 404)

    def test_revoke_blocks_read_and_preserves_owner_access(self):
        sid = self.share()
        self.assertEqual(self.request("GET", "/documents/a", "bob").json()["id"], "a")
        self.assertEqual(self.request("DELETE", f"/shares/{sid}", "alice").status_code, 204)
        self.assertTrue(self.app.state.shares[0]["revoked"])
        self.assertEqual(self.request("GET", "/documents/a", "bob").status_code, 404)
        self.assertEqual(self.request("GET", "/documents/a", "alice").json()["id"], "a")

    def test_unshared_documents_denied(self):
        for who in ("bob", "carol", "admin"):
            self.assertEqual(self.request("GET", "/documents/a", who).status_code, 404)
        self.assertEqual(self.request("GET", "/documents/missing", "alice").status_code, 404)

    def test_unauthenticated_routes_denied(self):
        for who in (None, "unknown"):
            for method, path, kwargs in (
                ("GET", "/documents/a", {}),
                ("GET", "/admin/inventory", {}),
                ("DELETE", "/shares/1", {}),
                ("POST", "/documents/a/shares", {"json": {"recipient": "bob", "expires_at": time() + 3600}}),
            ):
                self.assertEqual(self.request(method, path, who, **kwargs).status_code, 401)
        self.assertEqual(self.app.state.shares, [])

    def test_recipient_cannot_reshare_or_revoke(self):
        sid = self.share()
        before = deepcopy(self.app.state.shares)
        self.assertEqual(self.request("POST", "/documents/a/shares", "bob",
                         json={"recipient": "alice", "expires_at": time() + 3600}).status_code, 403)
        self.assertEqual(self.request("DELETE", f"/shares/{sid}", "bob").status_code, 403)
        self.assertEqual(self.app.state.shares, before)

    def test_invalid_share_targets_and_expiry_do_not_mutate_state(self):
        for recipient, expiry in (("carol", time() + 3600), ("missing", time() + 3600),
                                  ("bob", time() - 60)):
            self.assertEqual(self.request("POST", "/documents/a/shares", "alice",
                             json={"recipient": recipient, "expires_at": expiry}).status_code, 422)
            self.assertEqual(self.app.state.shares, [])

    def test_migrated_owner_cannot_share_or_revoke(self):
        sid = self.share()
        self.app.state.users["alice"]["tenant"] = "south"
        before = deepcopy(self.app.state.shares)
        self.assertEqual(self.request("POST", "/documents/a/shares", "alice",
                         json={"recipient": "bob", "expires_at": time() + 3600}).status_code, 403)
        self.assertEqual(self.request("DELETE", f"/shares/{sid}", "alice").status_code, 403)
        self.assertEqual(self.app.state.shares, before)

    def test_inventory_role_and_current_tenant(self):
        for who in ("alice", "bob", "carol"):
            self.assertEqual(self.request("GET", "/admin/inventory", who).status_code, 403)
        self.assertEqual({d["id"] for d in self.request("GET", "/admin/inventory", "admin").json()}, {"a", "b"})
        self.app.state.users["admin"]["tenant"] = "south"
        self.assertEqual({d["id"] for d in self.request("GET", "/admin/inventory", "admin").json()}, {"c"})


if __name__ == "__main__":
    unittest.main()
