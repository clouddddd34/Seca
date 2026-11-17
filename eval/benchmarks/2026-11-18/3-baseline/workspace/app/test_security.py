"""Local-only security and behavior regressions; <= 4 orders per instance."""
import unittest

from fastapi.testclient import TestClient

from app.app import create_app


def auth(name):
    return {"Authorization": f"Bearer fixture-{name}"}


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())

    def tearDown(self):
        self.client.close()

    def test_invoice_ownership(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for invoice, owner in (("inv-a", "alice"), ("inv-b", "bob"), ("inv-c", "carol")):
                with self.subTest(actor=actor, invoice=invoice):
                    response = self.client.get(f"/invoices/{invoice}", headers=auth(actor))
                    self.assertEqual(response.status_code, 200 if actor == owner else 404)
                    if actor == owner:
                        self.assertEqual(response.json()["owner"], actor)
        self.assertEqual(self.client.get("/invoices/missing", headers=auth("alice")).status_code, 404)

    def test_report_tenant_boundary(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for report, tenant in (("report-n", "north"), ("report-s", "south")):
                with self.subTest(actor=actor, report=report):
                    response = self.client.get(f"/reports/{report}", headers=auth(actor))
                    allowed = (actor == "carol") == (tenant == "south")
                    self.assertEqual(response.status_code, 200 if allowed else 404)
                    if allowed:
                        self.assertEqual(response.json()["tenant"], tenant)
        self.assertEqual(self.client.get("/reports/missing", headers=auth("alice")).status_code, 404)

    def test_authoritative_price_and_private_orders(self):
        self.assertEqual(self.client.get("/catalog", headers=auth("alice")).json(), {"book": 1000})
        for actor, quantity, price in (("alice", 1, 1), ("alice", 5, 1000), ("bob", 2, 100000), ("carol", 1, 1000)):
            with self.subTest(actor=actor, quantity=quantity, price=price):
                response = self.client.post("/orders", headers=auth(actor), json={
                    "sku": "book", "quantity": quantity, "unit_price_cents": price})
                self.assertEqual(response.status_code, 201)
                self.assertEqual(response.json()["total_cents"], quantity * 1000)
        for actor, count in (("alice", 2), ("bob", 1), ("carol", 1), ("admin", 0)):
            orders = self.client.get("/orders", headers=auth(actor)).json()
            self.assertEqual(len(orders), count)
            self.assertTrue(all(order["owner"] == actor for order in orders))

    def test_invalid_purchases_do_not_create_orders(self):
        valid = {"sku": "book", "quantity": 1, "unit_price_cents": 1000}
        for patch, expected in (({"sku": "missing"}, 404), ({"quantity": 0}, 422),
                                ({"quantity": 6}, 422), ({"quantity": 1.5}, 422),
                                ({"unit_price_cents": 0}, 422), ({"unit_price_cents": 100001}, 422)):
            with self.subTest(patch=patch):
                response = self.client.post("/orders", headers=auth("alice"), json={**valid, **patch})
                self.assertEqual(response.status_code, expected)
        self.assertEqual(self.client.get("/orders", headers=auth("alice")).json(), [])

    def test_authentication_and_admin_boundary(self):
        for path in ("/", "/health"):
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ("/me", "/invoices/inv-a", "/reports/report-n", "/catalog", "/orders", "/admin/export", "/openapi.json"):
            for headers in ({}, {"Authorization": "Bearer invalid"}):
                with self.subTest(path=path, headers=headers):
                    self.assertEqual(self.client.get(path, headers=headers).status_code, 401)
        self.assertEqual(self.client.post("/orders", json={"sku": "book", "quantity": 1, "unit_price_cents": 1000}).status_code, 401)
        for actor in ("alice", "bob", "carol", "admin"):
            self.assertEqual(self.client.get("/me", headers=auth(actor)).json()["id"], actor)
            for path in ("/admin/export", "/admin/export/", "/%61dmin/export", "/admin%2Fexport"):
                with self.subTest(actor=actor, path=path):
                    self.assertEqual(self.client.get(path, headers=auth(actor)).status_code,
                                     200 if actor == "admin" else 403)


if __name__ == "__main__":
    unittest.main()
