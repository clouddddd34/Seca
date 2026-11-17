"""Local-only security regressions; each test gets fresh in-memory state."""
import unittest

from fastapi.testclient import TestClient
from app.app import create_app


def auth(name):
    return {"Authorization": "Bearer fixture-" + name}


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_invoice_owner_matrix(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for suffix, owner in (("a", "alice"), ("b", "bob"), ("c", "carol")):
                with self.subTest(actor=actor, owner=owner):
                    response = self.client.get("/invoices/inv-" + suffix, headers=auth(actor))
                    self.assertEqual(response.status_code, 200 if actor == owner else 404)
                    if actor == owner:
                        self.assertEqual(response.json()["owner"], actor)

    def test_report_tenant_matrix(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for suffix in ("n", "s"):
                with self.subTest(actor=actor, report=suffix):
                    response = self.client.get("/reports/report-" + suffix, headers=auth(actor))
                    allowed = (actor == "carol") == (suffix == "s")
                    self.assertEqual(response.status_code, 200 if allowed else 404)

    def test_authoritative_price(self):
        # Three orders on this fresh instance, including both quantity bounds.
        for quantity, supplied_price in ((1, 1), (5, 1000), (2, 100000)):
            with self.subTest(quantity=quantity, supplied_price=supplied_price):
                response = self.client.post("/orders", headers=auth("alice"), json={
                    "sku": "book", "quantity": quantity, "unit_price_cents": supplied_price})
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["total_cents"], quantity * 1000)

    def test_authentication_boundary(self):
        for path in ("/", "/health"):
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ("/me", "/invoices/inv-a", "/reports/report-n", "/catalog",
                     "/orders", "/admin/export", "/openapi.json"):
            for headers in ({}, {"Authorization": "Bearer invalid"}):
                with self.subTest(path=path, headers=headers):
                    self.assertEqual(self.client.get(path, headers=headers).status_code, 401)
        self.assertEqual(self.client.post("/orders", json={}).status_code, 401)

    def test_admin_boundary(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for path in ("/admin/export", "/admin/export/", "/%61dmin/export", "/admin%2Fexport"):
                with self.subTest(actor=actor, path=path):
                    self.assertEqual(self.client.get(path, headers=auth(actor)).status_code,
                                     200 if actor == "admin" else 403)

    def test_order_ownership(self):
        for actor in ("alice", "bob", "carol"):
            response = self.client.post("/orders", headers=auth(actor), json={
                "sku": "book", "quantity": 1, "unit_price_cents": 1000,
                "owner": "admin", "total_cents": 1})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["owner"], actor)
        for actor in ("alice", "bob", "carol", "admin"):
            items = self.client.get("/orders", headers=auth(actor)).json()
            self.assertEqual(len(items), 0 if actor == "admin" else 1)
            self.assertTrue(all(item["owner"] == actor for item in items))

    def test_invalid_orders(self):
        base = {"sku": "book", "quantity": 1, "unit_price_cents": 1000}
        for field, value, status in (("quantity", 0, 422), ("quantity", 6, 422),
                                     ("unit_price_cents", 0, 422),
                                     ("unit_price_cents", 100001, 422),
                                     ("sku", "missing", 404)):
            with self.subTest(field=field, value=value):
                response = self.client.post("/orders", headers=auth("alice"),
                                            json={**base, field: value})
                self.assertEqual(response.status_code, status)
        self.assertEqual(self.client.get("/orders", headers=auth("alice")).json(), [])

    def test_missing_resources_and_profile(self):
        for path in ("/invoices/missing", "/reports/missing"):
            self.assertEqual(self.client.get(path, headers=auth("alice")).status_code, 404)
        self.assertEqual(self.client.get("/me", headers=auth("alice")).json(),
                         {"id": "alice", "tenant": "north", "role": "member"})
        self.assertEqual(self.client.get("/catalog", headers=auth("alice")).json(), {"book": 1000})


if __name__ == "__main__":
    unittest.main()
