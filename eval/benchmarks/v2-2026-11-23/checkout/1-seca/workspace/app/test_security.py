"""Bounded local checks: fresh state per test, <=5 orders and <=20 mutations."""
import unittest

from fastapi.testclient import TestClient
from app.app import create_app


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.mutations = 0
        self.orders = 0

    def headers(self, who="alice"):
        return {"Authorization": "Bearer fixture-" + who}

    def post(self, path, data=None, who="alice", headers=None):
        self.mutations += 1
        self.assertLessEqual(self.mutations, 20)
        return self.client.post(path, json=data, headers=self.headers(who) if headers is None else headers)

    def create(self, quantity=1, who="alice"):
        self.orders += 1
        self.assertLessEqual(self.orders, 5)
        response = self.post("/orders", {"quantity": quantity}, who)
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def wallet(self, who="alice"):
        return self.client.get("/wallet", headers=self.headers(who)).json()

    def order(self, oid, who="alice"):
        return self.client.get(f"/orders/{oid}", headers=self.headers(who)).json()

    def pay(self, oid, coupon="", who="alice"):
        return self.post(f"/orders/{oid}/pay", {"coupon": coupon}, who)

    def refund(self, oid, who="alice"):
        return self.post(f"/orders/{oid}/refund", who=who)

    def test_bare_account_cannot_authenticate_or_mutate(self):
        oid = self.create()
        before = self.wallet(), self.order(oid)
        read = self.client.get("/wallet", headers={"Authorization": "alice"})
        write = self.post(f"/orders/{oid}/pay", {}, headers={"Authorization": "alice"})
        after = self.wallet(), self.order(oid)
        self.assertEqual((read.status_code, write.status_code, after), (401, 401, before))

    def test_refund_only_once(self):
        oid = self.create()
        self.assertEqual(self.pay(oid, "WELCOME").status_code, 200)
        self.assertEqual(self.wallet()["balance"], 9500)
        self.assertEqual(self.refund(oid).status_code, 200)
        before = self.wallet(), self.order(oid)
        self.assertEqual(before[0]["balance"], 10000)
        response = self.refund(oid)
        after = self.wallet(), self.order(oid)
        self.assertEqual((response.status_code, after), (409, before))

    def test_coupon_cannot_be_reused_across_orders(self):
        first, second = self.create(), self.create()
        self.assertEqual(self.pay(first, "WELCOME").status_code, 200)
        before = self.wallet(), self.order(second)
        response = self.pay(second, "WELCOME")
        after = self.wallet(), self.order(second)
        self.assertEqual((response.status_code, after), (409, before))
        self.assertEqual(self.pay(second).status_code, 200)
        self.assertEqual(self.wallet()["balance"], 8500)

    def test_refund_does_not_restore_coupon(self):
        first, second = self.create(), self.create()
        self.assertEqual(self.pay(first, "WELCOME").status_code, 200)
        self.assertEqual(self.refund(first).status_code, 200)
        before = self.wallet(), self.order(second)
        response = self.pay(second, "WELCOME")
        self.assertEqual((response.status_code, self.wallet(), self.order(second)), (409, *before))

    def test_ownership_and_authentication_controls(self):
        oid = self.create()
        before = self.wallet(), self.wallet("bob"), self.order(oid)
        self.assertEqual(self.client.get(f"/orders/{oid}", headers=self.headers("bob")).status_code, 404)
        self.assertEqual(self.pay(oid, who="bob").status_code, 404)
        self.assertEqual(self.refund(oid, who="bob").status_code, 404)
        for headers in ({}, {"Authorization": "Bearer invalid"}):
            self.assertEqual(self.client.get("/wallet", headers=headers).status_code, 401)
            self.assertEqual(self.post("/orders", {"quantity": 1}, headers=headers).status_code, 401)
        self.assertEqual((self.wallet(), self.wallet("bob"), self.order(oid)), before)
        self.assertEqual(self.client.get("/orders/999", headers=self.headers()).status_code, 404)

    def test_valid_workflows_and_transition_controls(self):
        oid = self.create(3)
        before = self.wallet(), self.order(oid)
        self.assertEqual(self.refund(oid).status_code, 409)
        self.assertEqual(self.pay(oid, "INVALID").status_code, 422)
        self.assertEqual((self.wallet(), self.order(oid)), before)
        self.assertEqual(self.pay(oid).status_code, 200)
        self.assertEqual(self.wallet()["balance"], 7000)
        paid = self.wallet(), self.order(oid)
        self.assertEqual(self.pay(oid).status_code, 409)
        self.assertEqual((self.wallet(), self.order(oid)), paid)
        self.assertEqual(self.refund(oid).status_code, 200)
        refunded = self.wallet(), self.order(oid)
        self.assertEqual(refunded[0]["balance"], 10000)
        self.assertEqual(self.pay(oid).status_code, 409)
        self.assertEqual((self.wallet(), self.order(oid)), refunded)

    def test_failed_payment_keeps_coupon_and_draft(self):
        for _ in range(3):
            self.assertEqual(self.pay(self.create(3)).status_code, 200)
        large, small = self.create(2), self.create(1)
        before = self.wallet(), self.order(large)
        self.assertEqual(self.pay(large, "WELCOME").status_code, 409)
        self.assertEqual((self.wallet(), self.order(large)), before)
        self.assertEqual(self.pay(small, "WELCOME").status_code, 200)
        self.assertEqual(self.wallet(), {"balance": 500, "used_coupons": ["WELCOME"]})

    def test_coupon_is_per_account(self):
        for who in ("alice", "bob"):
            oid = self.create(who=who)
            self.assertEqual(self.pay(oid, "WELCOME", who).status_code, 200)
            self.assertEqual(self.wallet(who), {"balance": 9500, "used_coupons": ["WELCOME"]})

    def test_quantity_bounds(self):
        for quantity in (0, -1, 4):
            self.assertEqual(self.post("/orders", {"quantity": quantity}).status_code, 422)
        self.assertEqual(self.wallet()["balance"], 10000)
        self.assertEqual(self.create(2), 1)

    def test_bearer_scheme_and_invalid_credentials(self):
        for value in ("bob", "Bearer alice", "Basic fixture-alice", "Bearer fixture-unknown"):
            self.assertEqual(self.client.get("/wallet", headers={"Authorization": value}).status_code, 401)
        response = self.client.get("/wallet", headers={"Authorization": "bearer fixture-alice"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["balance"], 10000)


if __name__ == "__main__":
    unittest.main()
