"""Local-only regression checks; each test receives a fresh application."""
import unittest

from fastapi.testclient import TestClient
from app import create_app


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app(), follow_redirects=False)
        self.addCleanup(self.client.close)

    def request(self, method, path, actor=None, **kwargs):
        headers = {"Authorization": "Bearer fixture-" + actor} if actor else {}
        return self.client.request(method, path, headers=headers, **kwargs)

    def test_invoice_owner_matrix(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for invoice_id, owner in (("inv-a", "alice"), ("inv-b", "bob"), ("inv-c", "carol")):
                with self.subTest(actor=actor, invoice=invoice_id):
                    response = self.request("GET", "/invoices/" + invoice_id, actor)
                    self.assertEqual(response.status_code, 200 if actor == owner else 404)
                    if actor == owner:
                        self.assertEqual(response.json()["owner"], actor)
                    else:
                        self.assertEqual(response.json(), {"detail": "Not found"})

    def test_report_tenant_matrix(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for report_id, tenant in (("report-n", "north"), ("report-s", "south")):
                allowed = (actor == "carol") == (tenant == "south")
                with self.subTest(actor=actor, report=report_id):
                    response = self.request("GET", "/reports/" + report_id, actor)
                    self.assertEqual(response.status_code, 200 if allowed else 404)
                    self.assertEqual(response.json().get("tenant"), tenant if allowed else None)

    def test_authoritative_prices_and_order_isolation(self):
        self.assertEqual(self.request("GET", "/catalog", "alice").json(), {"book": 1000})
        for price, quantity in ((1, 2), (1000, 1), (2000, 5)):
            response = self.request("POST", "/orders", "alice", json={
                "sku": "book", "quantity": quantity, "unit_price_cents": price})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()["total_cents"], quantity * 1000)
        self.assertEqual(len(self.request("GET", "/orders", "alice").json()), 3)
        for actor in ("bob", "carol", "admin"):
            self.assertEqual(self.request("GET", "/orders", actor).json(), [])

    def test_authentication_and_admin_boundary(self):
        for path in ("/", "/health"):
            self.assertEqual(self.request("GET", path).status_code, 200)
        for path in ("/me", "/invoices/inv-a", "/reports/report-n", "/catalog", "/orders", "/admin/export", "/openapi.json"):
            self.assertEqual(self.request("GET", path).status_code, 401)
            self.assertEqual(self.request("GET", path, "invalid").status_code, 401)
        self.assertEqual(self.request("POST", "/orders", json={}).status_code, 401)
        for actor in ("alice", "bob", "carol"):
            self.assertEqual(self.request("GET", "/admin/export", actor).status_code, 403)
        self.assertEqual(self.request("GET", "/admin/export", "admin").json(),
                         {"export": "Synthetic administrative data"})
        self.assertEqual(self.request("GET", "/me", "alice").json()["id"], "alice")

    def test_invalid_orders_and_missing_resources(self):
        for quantity in (0, 6):
            self.assertEqual(self.request("POST", "/orders", "alice", json={
                "sku": "book", "quantity": quantity, "unit_price_cents": 1000}).status_code, 422)
        self.assertEqual(self.request("POST", "/orders", "alice", json={
            "sku": "missing", "quantity": 1, "unit_price_cents": 1000}).status_code, 404)
        self.assertEqual(self.request("GET", "/orders", "alice").json(), [])
        for path in ("/invoices/missing", "/reports/missing"):
            self.assertEqual(self.request("GET", path, "alice").status_code, 404)


if __name__ == "__main__":
    unittest.main()
