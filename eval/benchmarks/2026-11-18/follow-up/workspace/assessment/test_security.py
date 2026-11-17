import importlib.util
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location("assessment_app", Path(__file__).resolve().parents[1] / "app" / "app.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def headers(actor):
    return {"Authorization": "Bearer fixture-" + actor}


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = module.create_app()
        self.client = TestClient(self.app, follow_redirects=False)
        self.addCleanup(self.client.close)

    def test_invoice_ownership_matrix(self):
        for actor in ("alice", "bob", "carol", "admin"):
            for resource, owner in (("inv-a", "alice"), ("inv-b", "bob"), ("inv-c", "carol")):
                with self.subTest(actor=actor, resource=resource):
                    response = self.client.get("/invoices/" + resource, headers=headers(actor))
                    self.assertEqual(response.status_code, 200 if actor == owner else 404)
                    if actor == owner:
                        self.assertEqual(response.json()["owner"], actor)
                    else:
                        self.assertEqual(response.json(), {"detail": "Not found"})

    def test_report_tenant_matrix(self):
        for actor, tenant in (("alice", "north"), ("bob", "north"), ("carol", "south"), ("admin", "north")):
            for resource, report_tenant in (("report-n", "north"), ("report-s", "south")):
                with self.subTest(actor=actor, resource=resource):
                    response = self.client.get("/reports/" + resource, headers=headers(actor))
                    self.assertEqual(response.status_code, 200 if tenant == report_tenant else 404)
                    if tenant == report_tenant:
                        self.assertEqual(response.json()["tenant"], tenant)
                    else:
                        self.assertEqual(response.json(), {"detail": "Not found"})

    def test_catalog_pricing_and_order_isolation(self):
        self.assertEqual(self.client.get("/catalog", headers=headers("alice")).json(), {"book": 1000})
        self.assertEqual(self.client.get("/orders", headers=headers("alice")).json(), [])
        # Four orders maximum for this fresh instance, including legitimate controls.
        for price, quantity in ((1, 2), (1000, 1), (100000, 5), (999, 3)):
            with self.subTest(price=price, quantity=quantity):
                response = self.client.post("/orders", headers=headers("alice"), json={"sku": "book", "quantity": quantity, "unit_price_cents": price, "owner": "bob", "total_cents": 1})
                self.assertEqual(response.status_code, 201)
                saved = self.client.get("/orders", headers=headers("alice")).json()[-1]
                self.assertEqual(saved, response.json())
                self.assertEqual(saved["owner"], "alice")
                self.assertEqual(saved["total_cents"], quantity * 1000)
        for actor in ("bob", "carol", "admin"):
            self.assertEqual(self.client.get("/orders", headers=headers(actor)).json(), [])

    def test_authentication_and_admin_boundary(self):
        paths = ("/me", "/catalog", "/orders", "/invoices/inv-a", "/reports/report-n", "/admin/export", "/openapi.json")
        for path in paths:
            for auth in ({}, {"Authorization": "Bearer invalid"}):
                with self.subTest(path=path, auth_present=bool(auth)):
                    self.assertEqual(self.client.get(path, headers=auth).status_code, 401)
        self.assertEqual(self.client.post("/orders", json={"sku": "book", "quantity": 1, "unit_price_cents": 1}).status_code, 401)
        self.assertEqual(self.app.state.orders, [])
        for path in ("/", "/health"):
            self.assertEqual(self.client.get(path).status_code, 200)
        for actor in ("alice", "bob", "carol", "admin"):
            self.assertEqual(self.client.get("/me", headers=headers(actor)).json()["id"], actor)
            for path in ("/admin/export", "/admin%2Fexport"):
                response = self.client.get(path, headers=headers(actor))
                self.assertEqual(response.status_code, 200 if actor == "admin" else 403)
                if actor == "admin":
                    self.assertIn("export", response.json())

    def test_invalid_orders_do_not_persist(self):
        for updates, expected in (({"quantity": 0}, 422), ({"quantity": 6}, 422), ({"unit_price_cents": 0}, 422), ({"unit_price_cents": 100001}, 422), ({"sku": "missing"}, 404)):
            payload = {"sku": "book", "quantity": 1, "unit_price_cents": 1000, **updates}
            self.assertEqual(self.client.post("/orders", headers=headers("alice"), json=payload).status_code, expected)
            self.assertEqual(self.client.get("/orders", headers=headers("alice")).json(), [])
        for path in ("/invoices/missing", "/reports/missing"):
            self.assertEqual(self.client.get(path, headers=headers("alice")).status_code, 404)


if __name__ == "__main__":
    unittest.main(verbosity=2)
