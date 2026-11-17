"""Local-only regression checks; each test gets a fresh app, at most 3 orders."""
import unittest

from fastapi.testclient import TestClient
from app.app import create_app, USERS


def headers(actor):
    token = next(token for token, user in USERS.items() if user["id"] == actor)
    return {"Authorization": "Bearer " + token}


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(), follow_redirects=False)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_invoice_owner_matrix(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for invoice, owner in (("inv-a", "alice"), ("inv-b", "bob"), ("inv-c", "carol")):
                with self.subTest(actor=actor, invoice=invoice):
                    response = self.client.get("/invoices/" + invoice, headers=headers(actor))
                    self.assertEqual(response.status_code, 200 if actor == owner else 404)
                    if actor == owner:
                        self.assertEqual(response.json()["owner"], actor)
                    else:
                        self.assertEqual(response.json(), {"detail": "Not found"})

    def test_report_tenant_matrix(self):
        for actor, tenant in (("alice", "north"), ("bob", "north"), ("carol", "south"), ("admin", "north")):
            for report, report_tenant in (("report-n", "north"), ("report-s", "south")):
                with self.subTest(actor=actor, report=report):
                    response = self.client.get("/reports/" + report, headers=headers(actor))
                    self.assertEqual(response.status_code, 200 if tenant == report_tenant else 404)
                    if tenant == report_tenant:
                        self.assertEqual(response.json()["tenant"], tenant)
                    else:
                        self.assertEqual(response.json(), {"detail": "Not found"})

    def test_authoritative_prices_and_order_isolation(self):
        self.assertEqual(self.client.get("/catalog", headers=headers("alice")).json(), {"book": 1000})
        for actor, quantity, price in (("alice", 2, 1), ("alice", 1, 1000), ("bob", 5, 2000)):
            response = self.client.post("/orders", headers=headers(actor), json={
                "sku": "book", "quantity": quantity, "unit_price_cents": price})
            self.assertEqual(response.status_code, 201)
            with self.subTest(actor=actor, price=price):
                self.assertEqual(response.json()["total_cents"], quantity * 1000)
            self.assertEqual(response.json()["owner"], actor)
        for actor, count in (("alice", 2), ("bob", 1), ("carol", 0), ("admin", 0)):
            orders = self.client.get("/orders", headers=headers(actor)).json()
            self.assertEqual(len(orders), count)
            self.assertTrue(all(order["owner"] == actor for order in orders))

    def test_authentication(self):
        for path in ("/", "/health"):
            self.assertEqual(self.client.get(path).status_code, 200)
        for auth in ({}, {"Authorization": "Bearer invalid"}):
            for path in ("/me", "/catalog", "/orders", "/invoices/inv-a", "/reports/report-n", "/admin/export", "/openapi.json"):
                with self.subTest(path=path, invalid=bool(auth)):
                    self.assertEqual(self.client.get(path, headers=auth).status_code, 401)
            self.assertEqual(self.client.post("/orders", headers=auth, json={
                "sku": "book", "quantity": 1, "unit_price_cents": 1000}).status_code, 401)
        self.assertEqual(self.client.get("/orders", headers=headers("alice")).json(), [])
        for actor in ("alice", "bob", "carol", "admin"):
            self.assertEqual(self.client.get("/me", headers=headers(actor)).json()["id"], actor)

    def test_admin_boundary(self):
        for actor in ("alice", "bob", "carol", "admin"):
            response = self.client.get("/admin/export", headers=headers(actor))
            self.assertEqual(response.status_code, 200 if actor == "admin" else 403)
            self.assertEqual(response.json(), {"export": "Synthetic administrative data"} if actor == "admin" else {"detail": "Administrator required"})
        for path in ("/admin/export/", "/%61dmin/export", "/admin%2Fexport"):
            self.assertEqual(self.client.get(path, headers=headers("alice")).status_code, 403)

    def test_invalid_inputs_and_missing_resources(self):
        for field, value in (("quantity", 0), ("quantity", 6), ("quantity", -1), ("unit_price_cents", 0), ("unit_price_cents", 100001)):
            body = {"sku": "book", "quantity": 1, "unit_price_cents": 1000}
            body[field] = value
            self.assertEqual(self.client.post("/orders", headers=headers("alice"), json=body).status_code, 422)
        self.assertEqual(self.client.post("/orders", headers=headers("alice"), json={
            "sku": "unknown", "quantity": 1, "unit_price_cents": 1000}).status_code, 404)
        for path in ("/invoices/missing", "/reports/missing"):
            self.assertEqual(self.client.get(path, headers=headers("alice")).status_code, 404)
        self.assertEqual(self.client.get("/orders", headers=headers("alice")).json(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
