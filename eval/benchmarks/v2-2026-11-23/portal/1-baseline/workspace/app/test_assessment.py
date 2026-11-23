"""Bounded local verification of the README access and rendering rules."""
import unittest
from html import escape

from fastapi.testclient import TestClient

from app.app import create_app


class PortalAssessment(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app, follow_redirects=False)
        self.addCleanup(self.client.close)

    def login(self, name):
        response = self.client.post(
            "/login", data={"username": name, "password": "fixture-" + name},
            headers={"Origin": "http://testserver"},
        )
        self.assertEqual(response.status_code, 303)
        return self.client.cookies.get("session")

    def test_public_navigation_and_anonymous_boundary(self):
        for path in ("/", "/help", "/login"):
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ("/tickets", "/tickets/a", "/admin/export"):
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post("/logout").status_code, 401)
        self.client.cookies.set("session", "unknown-session")
        self.assertEqual(self.client.get("/tickets").status_code, 401)

    def test_login_origin_and_invalid_credentials(self):
        data = {"username": "alice", "password": "fixture-alice"}
        for headers in ({}, {"Origin": "https://untrusted.invalid"}):
            self.assertEqual(self.client.post("/login", data=data, headers=headers).status_code, 403)
        self.assertEqual(self.client.post(
            "/login", data={"username": "alice", "password": "deliberately-invalid"},
            headers={"Origin": "http://testserver"},
        ).status_code, 401)
        self.assertEqual(self.app.state.sessions, {})

    def test_ticket_ownership_and_tenant_matrix(self):
        for name, own in (("alice", "a"), ("bob", "b"), ("carol", "c"), ("admin", None)):
            self.login(name)
            listing = self.client.get("/tickets")
            self.assertEqual(listing.status_code, 200)
            for ticket_id in ("a", "b", "c"):
                self.assertEqual(self.client.get("/tickets/" + ticket_id).status_code,
                                 200 if ticket_id == own else 404)
                self.assertEqual('href="/tickets/' + ticket_id + '"' in listing.text,
                                 ticket_id == own)
            self.assertEqual(self.client.get("/tickets/missing").status_code, 404)

    def test_current_membership_with_existing_session(self):
        token = self.login("alice")
        self.app.state.users["alice"]["tenant"] = "south"
        self.assertEqual(self.client.cookies.get("session"), token)
        for ticket_id in ("a", "b", "c"):
            self.assertEqual(self.client.get("/tickets/" + ticket_id).status_code, 404)
        self.assertNotIn('<li>', self.client.get("/tickets").text)
        self.app.state.users["alice"]["tenant"] = "north"
        self.assertEqual(self.client.get("/tickets/a").status_code, 200)

    def test_export_role_and_current_tenant(self):
        for name in ("alice", "bob", "carol"):
            self.login(name)
            self.assertEqual(self.client.get("/admin/export").status_code, 403)
        self.login("admin")
        response = self.client.get("/admin/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({t["owner"] for t in response.json()}, {"alice", "bob"})
        self.app.state.users["admin"]["tenant"] = "south"
        response = self.client.get("/admin/export")
        self.assertEqual(response.status_code, 200)
        self.assertEqual({t["owner"] for t in response.json()}, {"carol"})
        self.app.state.users["admin"]["role"] = "member"
        self.assertEqual(self.client.get("/admin/export").status_code, 403)

    def test_session_rotation_and_cookie_controls(self):
        old = self.login("alice")
        response = self.client.post(
            "/login", data={"username": "bob", "password": "fixture-bob"},
            headers={"Origin": "http://testserver"},
        )
        self.assertEqual(response.status_code, 303)
        self.assertNotEqual(self.client.cookies.get("session"), old)
        self.assertNotIn(old, self.app.state.sessions)
        cookie = response.headers["set-cookie"].lower()
        for attribute in ("httponly", "samesite=strict", "path=/"):
            self.assertIn(attribute, cookie)
        self.assertEqual(self.client.get("/tickets/b").status_code, 200)
        self.assertEqual(self.client.get("/tickets", headers={"Cookie": "session=" + old}).status_code, 401)

    def test_logout_csrf_and_invalidation(self):
        token = self.login("alice")
        csrf = self.app.state.sessions[token]["csrf"]
        self.assertIn('value="' + csrf + '"', self.client.get("/tickets").text)
        for data in ({}, {"csrf": "invalid"}):
            self.assertEqual(self.client.post("/logout", data=data).status_code, 403)
            self.assertIn(token, self.app.state.sessions)
        self.assertEqual(self.client.get("/logout").status_code, 405)
        response = self.client.post("/logout", data={"csrf": csrf})
        self.assertEqual(response.status_code, 303)
        self.assertNotIn(token, self.app.state.sessions)
        self.assertIsNone(self.client.cookies.get("session"))
        self.assertEqual(self.client.get("/tickets", headers={"Cookie": "session=" + token}).status_code, 401)

    def test_literal_rendering_and_response_controls(self):
        self.login("alice")
        payload = '<img src=x onerror=alert(1)> & "quoted" \'single\''
        self.app.state.tickets["a"]["text"] = payload
        for response in (self.client.get("/tickets", params={"q": payload}),
                         self.client.get("/tickets/a")):
            self.assertEqual(response.status_code, 200)
            self.assertIn(escape(payload), response.text)
            self.assertNotIn(payload, response.text)
            self.assertEqual(response.headers["x-content-type-options"], "nosniff")
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(response.headers["content-security-policy"],
                             "default-src 'none'; form-action 'self'; frame-ancestors 'none'")


if __name__ == "__main__":
    unittest.main()
