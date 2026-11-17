"""Bounded local regression checks; run from workspace with unittest discovery."""
import unittest

from fastapi.testclient import TestClient
from app.app import create_app


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app, follow_redirects=False)
        self.addCleanup(self.client.close)

    def headers(self, actor):
        return {"Authorization": "Bearer fixture-" + actor}

    def test_invoice_owner_matrix(self):
        owners = {"inv-a": "alice", "inv-b": "bob", "inv-c": "carol"}
        for actor in ("alice", "bob", "carol", "admin"):
            for resource, owner in owners.items():
                with self.subTest(actor=actor, resource=resource):
                    response = self.client.get("/invoices/" + resource, headers=self.headers(actor))
                    self.assertEqual(response.status_code, 200 if actor == owner else 404)
                    if actor == owner:
                        self.assertEqual(response.json()["owner"], actor)
                    else:
                        self.assertEqual(response.json(), {"detail": "Not found"})

    def test_report_tenant_matrix(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for resource in ("report-n", "report-s"):
                allowed = (actor == "carol") == (resource == "report-s")
                with self.subTest(actor=actor, resource=resource):
                    response = self.client.get("/reports/" + resource, headers=self.headers(actor))
                    self.assertEqual(response.status_code, 200 if allowed else 404)
                    if allowed:
                        self.assertEqual(response.json()["id"], resource)
                    else:
                        self.assertEqual(response.json(), {"detail": "Not found"})

    def test_catalog_pricing_and_order_isolation(self):
        catalog = self.client.get("/catalog", headers=self.headers("alice")).json()
        for actor, quantity, price in (("alice", 2, 1), ("bob", 1, 1000)):
            response = self.client.post("/orders", headers=self.headers(actor), json={
                "sku": "book", "quantity": quantity, "unit_price_cents": price})
            self.assertEqual(response.status_code, 201)
            with self.subTest(actor=actor):
                self.assertEqual(response.json()["total_cents"], quantity * catalog["book"])
        for actor, count in (("alice", 1), ("bob", 1), ("carol", 0), ("admin", 0)):
            orders = self.client.get("/orders", headers=self.headers(actor)).json()
            self.assertEqual(len(orders), count)
            self.assertTrue(all(order["owner"] == actor for order in orders))

    def test_authentication_and_admin_boundary(self):
        for path in ("/", "/health"):
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ("/me", "/catalog", "/invoices/inv-a", "/reports/report-n",
                     "/orders", "/admin/export", "/openapi.json"):
            for headers in ({}, {"Authorization": "Bearer invalid"}):
                self.assertEqual(self.client.get(path, headers=headers).status_code, 401)
        self.assertEqual(self.client.post("/orders", json={}).status_code, 401)
        self.assertEqual(self.app.state.orders, [])
        for actor in ("alice", "bob", "carol", "admin"):
            self.assertEqual(self.client.get("/me", headers=self.headers(actor)).json()["id"], actor)
            for path in ("/admin/export", "/admin%2Fexport"):
                self.assertEqual(self.client.get(path, headers=self.headers(actor)).status_code,
                                 200 if actor == "admin" else 403)

    def test_invalid_inputs_do_not_create_orders(self):
        for body in ({}, {"sku": "missing", "quantity": 1, "unit_price_cents": 1000},
                     *({"sku": "book", "quantity": q, "unit_price_cents": 1000}
                       for q in (0, 6)),
                     {"sku": "book", "quantity": 1, "unit_price_cents": 0}):
            response = self.client.post("/orders", headers=self.headers("alice"), json=body)
            self.assertIn(response.status_code, (404, 422))
        self.assertEqual(self.app.state.orders, [])
        for path in ("/invoices/missing", "/reports/missing"):
            self.assertEqual(self.client.get(path, headers=self.headers("alice")).status_code, 404)


if __name__ == "__main__":
    unittest.main()
