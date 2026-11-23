import sys
import unittest
from pathlib import Path
from time import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import create_app
from fastapi.testclient import TestClient


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def request(self, method, path, who=None, **kwargs):
        headers = {} if who is None else {"Authorization": "Bearer fixture-" + who}
        return self.client.request(method, path, headers=headers, follow_redirects=False, **kwargs)

    def share(self):
        response = self.request("POST", "/documents/a/shares", "alice",
                                json={"recipient": "bob", "expires_at": time() + 3600})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertEqual(self.app.state.shares[0]["recipient"], "bob")
        self.assertFalse(self.app.state.shares[0]["revoked"])
        return response.json()["id"]

    def assert_document(self, who, doc="a"):
        response = self.request("GET", "/documents/" + doc, who)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.app.state.documents[doc])

    def test_owner_current_tenant(self):
        self.assert_document("alice")
        self.assert_document("carol", "c")

    def test_unshared_same_and_other_tenant_denied(self):
        for who in ("bob", "carol", "admin"):
            self.assertEqual(self.request("GET", "/documents/a", who).status_code, 404)

    def test_live_share_allows_read(self):
        self.share()
        self.assert_document("bob")

    def test_migrated_owner_denied(self):
        self.assert_document("alice")
        self.app.state.users["alice"]["tenant"] = "south"
        self.assertEqual(self.request("GET", "/documents/a", "alice").status_code, 404)

    def test_migrated_recipient_denied(self):
        self.share()
        self.assert_document("bob")
        self.app.state.users["bob"]["tenant"] = "south"
        self.assertEqual(self.request("GET", "/documents/a", "bob").status_code, 404)

    def test_expired_share_denied(self):
        self.share()
        self.assert_document("bob")
        self.app.state.shares[0]["expires_at"] = time() - 60
        self.assertEqual(self.request("GET", "/documents/a", "bob").status_code, 404)

    def test_revoke_blocks_read_and_preserves_owner(self):
        share_id = self.share()
        self.assert_document("bob")
        self.assertEqual(self.request("DELETE", f"/shares/{share_id}", "alice").status_code, 204)
        self.assertTrue(self.app.state.shares[0]["revoked"])
        self.assertEqual(self.request("GET", "/documents/a", "bob").status_code, 404)
        self.assert_document("alice")

    def test_recipients_cannot_reshare_or_revoke(self):
        share_id = self.share()
        self.assertEqual(self.request("POST", "/documents/a/shares", "bob",
                         json={"recipient": "alice", "expires_at": time()+3600}).status_code, 403)
        self.assertEqual(self.request("DELETE", f"/shares/{share_id}", "bob").status_code, 403)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertFalse(self.app.state.shares[0]["revoked"])
        self.assert_document("bob")

    def test_invalid_shares_do_not_persist(self):
        for recipient, expires_at in (("carol", time()+3600), ("missing", time()+3600), ("bob", time()-60)):
            self.assertEqual(self.request("POST", "/documents/a/shares", "alice",
                             json={"recipient": recipient, "expires_at": expires_at}).status_code, 422)
            self.assertEqual(self.app.state.shares, [])

    def test_migrated_owner_cannot_share_or_revoke(self):
        share_id = self.share()
        self.app.state.users["alice"]["tenant"] = "south"
        self.assertEqual(self.request("POST", "/documents/a/shares", "alice",
                         json={"recipient": "bob", "expires_at": time()+3600}).status_code, 403)
        self.assertEqual(self.request("DELETE", f"/shares/{share_id}", "alice").status_code, 403)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertFalse(self.app.state.shares[0]["revoked"])

    def test_inventory_role_and_current_tenant(self):
        for who in ("alice", "bob", "carol"):
            self.assertEqual(self.request("GET", "/admin/inventory", who).status_code, 403)
        response = self.request("GET", "/admin/inventory", "admin")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({d["id"] for d in response.json()}, {"a", "b"})
        self.app.state.users["admin"]["tenant"] = "south"
        response = self.request("GET", "/admin/inventory", "admin")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([d["id"] for d in response.json()], ["c"])

    def test_missing_and_unknown_identity_denied(self):
        for who in (None, "unknown"):
            for method, path, kwargs in (
                ("GET", "/documents/a", {}),
                ("GET", "/admin/inventory", {}),
                ("POST", "/documents/a/shares", {"json": {"recipient": "bob", "expires_at": time()+3600}}),
                ("DELETE", "/shares/1", {}),
            ):
                self.assertEqual(self.request(method, path, who, **kwargs).status_code, 401)
        self.assertEqual(self.app.state.shares, [])


if __name__ == "__main__":
    unittest.main()
