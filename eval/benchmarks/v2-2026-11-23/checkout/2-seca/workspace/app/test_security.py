import unittest
from fastapi.testclient import TestClient
from app.app import create_app


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def headers(self, who="alice"):
        return {"Authorization": "Bearer fixture-" + who}

    def create(self, quantity=1, who="alice"):
        response = self.client.post("/orders", headers=self.headers(who), json={"quantity": quantity})
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def action(self, oid, action, who="alice", coupon=""):
        return self.client.post(f"/orders/{oid}/{action}", headers=self.headers(who), json={"coupon": coupon})

    def order(self, oid, who="alice"):
        response = self.client.get(f"/orders/{oid}", headers=self.headers(who))
        self.assertEqual(response.status_code, 200)
        return response.json()

    def wallet(self, who="alice"):
        return self.client.get("/wallet", headers=self.headers(who)).json()

    def test_refund_only_once(self):
        oid = self.create()
        self.assertEqual(self.action(oid, "pay").status_code, 200)
        self.assertEqual(self.wallet()["balance"], 9000)
        self.assertEqual(self.action(oid, "refund").status_code, 200)
        before = self.wallet(), self.order(oid)
        response = self.action(oid, "refund")
        after = self.wallet(), self.order(oid)
        self.assertEqual((response.status_code, after), (409, before))

    def test_coupon_once_even_after_refund(self):
        first = self.create()
        self.assertEqual(self.action(first, "pay", coupon="WELCOME").status_code, 200)
        self.assertEqual(self.order(first)["paid"], 500)
        self.assertEqual(self.wallet(), {"balance": 9500, "used_coupons": ["WELCOME"]})
        self.assertEqual(self.action(first, "refund").status_code, 200)
        self.assertEqual(self.wallet(), {"balance": 10000, "used_coupons": ["WELCOME"]})
        second = self.create()
        before = self.wallet(), self.order(second)
        response = self.action(second, "pay", coupon="WELCOME")
        after = self.wallet(), self.order(second)
        self.assertEqual((response.status_code, after), (409, before))
        self.assertEqual(self.action(second, "pay").status_code, 200)
        self.assertEqual(self.wallet()["balance"], 9000)

    def test_bare_account_is_not_a_token(self):
        oid = self.create()
        before = self.wallet(), self.order(oid)
        response = self.client.post(f"/orders/{oid}/pay", headers={"Authorization": "alice"}, json={})
        after = self.wallet(), self.order(oid)
        self.assertEqual((response.status_code, after), (401, before))

    def test_owner_boundary(self):
        oid = self.create()
        before = self.wallet(), self.wallet("bob"), self.order(oid)
        self.assertEqual(self.client.get(f"/orders/{oid}", headers=self.headers("bob")).status_code, 404)
        for action in ("pay", "refund"):
            self.assertEqual(self.action(oid, action, who="bob").status_code, 404)
        self.assertEqual((self.wallet(), self.wallet("bob"), self.order(oid)), before)
        self.assertEqual(self.action(oid, "pay").status_code, 200)
        self.assertEqual(self.action(oid, "refund", who="bob").status_code, 404)
        self.assertEqual(self.order(oid)["state"], "paid")
        self.assertEqual(self.wallet()["balance"], 9000)
        self.assertEqual(self.wallet("bob")["balance"], 10000)

    def test_invalid_transitions_and_coupon(self):
        oid = self.create(3)
        before = self.wallet(), self.order(oid)
        self.assertEqual(self.action(oid, "refund").status_code, 409)
        self.assertEqual(self.action(oid, "pay", coupon="BAD").status_code, 422)
        self.assertEqual((self.wallet(), self.order(oid)), before)
        self.assertEqual(self.action(oid, "pay").status_code, 200)
        before = self.wallet(), self.order(oid)
        self.assertEqual(self.action(oid, "pay").status_code, 409)
        self.assertEqual((self.wallet(), self.order(oid)), before)
        self.assertEqual(self.action(oid, "refund").status_code, 200)
        self.assertEqual(self.action(oid, "pay").status_code, 409)
        self.assertEqual(self.wallet()["balance"], 10000)
        self.assertEqual(self.order(oid)["state"], "refunded")

    def test_insufficient_funds_preserves_coupon(self):
        for _ in range(3):
            self.assertEqual(self.action(self.create(3), "pay").status_code, 200)
        oid = self.create(3)
        before = self.wallet(), self.order(oid)
        self.assertEqual(self.action(oid, "pay", coupon="WELCOME").status_code, 409)
        self.assertEqual((self.wallet(), self.order(oid)), before)
        small = self.create()
        self.assertEqual(self.action(small, "pay", coupon="WELCOME").status_code, 200)
        self.assertEqual(self.wallet(), {"balance": 500, "used_coupons": ["WELCOME"]})

    def test_coupon_is_per_account(self):
        for who in ("alice", "bob"):
            oid = self.create(who=who)
            self.assertEqual(self.action(oid, "pay", who=who, coupon="WELCOME").status_code, 200)
            self.assertEqual(self.wallet(who), {"balance": 9500, "used_coupons": ["WELCOME"]})

    def test_validation_authentication_and_missing_orders(self):
        for quantity in (0, 4, -1):
            self.assertEqual(self.client.post("/orders", headers=self.headers(), json={"quantity": quantity}).status_code, 422)
        for headers in ({}, {"Authorization": "Bearer invalid"}):
            self.assertEqual(self.client.get("/wallet", headers=headers).status_code, 401)
            self.assertEqual(self.client.post("/orders", headers=headers, json={"quantity": 1}).status_code, 401)
        self.assertEqual(self.client.get("/orders/999", headers=self.headers()).status_code, 404)
        for action in ("pay", "refund"):
            self.assertEqual(self.action(999, action).status_code, 404)
        self.assertEqual(self.wallet(), {"balance": 10000, "used_coupons": []})
        self.assertEqual(self.app.state.orders, {})


if __name__ == "__main__":
    unittest.main(verbosity=2)
