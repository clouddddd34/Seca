import unittest
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fastapi.testclient import TestClient
from app import create_app


class CheckoutSecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.addCleanup(self.client.close)
        self.mutations = 0
        self.orders = 0

    def request(self, method, path, user="alice", auth=None, **kwargs):
        if method == "POST":
            self.mutations += 1
            self.assertLessEqual(self.mutations, 20)
        headers = {"Authorization": auth if auth is not None else f"Bearer fixture-{user}"}
        response = self.client.request(method, path, headers=headers, **kwargs)
        if path == "/orders" and response.status_code == 201:
            self.orders += 1
            self.assertLessEqual(self.orders, 5)
        return response

    def create(self, quantity=1, user="alice"):
        response = self.request("POST", "/orders", user=user, json={"quantity": quantity})
        self.assertEqual(response.status_code, 201)
        return response.json()["id"]

    def pay(self, order, coupon="", user="alice"):
        return self.request("POST", f"/orders/{order}/pay", user=user, json={"coupon": coupon})

    def wallet(self, user="alice"):
        return self.request("GET", "/wallet", user=user).json()

    def order(self, order):
        return self.request("GET", f"/orders/{order}").json()

    def test_raw_account_name_is_not_a_bearer_token(self):
        order = self.create()
        for method, path, body in [
            ("GET", "/wallet", None), ("GET", f"/orders/{order}", None),
            ("POST", "/orders", {"quantity": 1}),
            ("POST", f"/orders/{order}/pay", {}),
            ("POST", f"/orders/{order}/refund", None),
        ]:
            with self.subTest(path=path):
                self.assertEqual(self.request(method, path, auth="alice", json=body).status_code, 401)
        self.assertEqual(self.wallet()["balance"], 10000)
        self.assertEqual(self.order(order)["state"], "draft")

    def test_refund_only_once_and_for_actual_charge(self):
        order = self.create(3)
        self.assertEqual(self.pay(order, "WELCOME").status_code, 200)
        self.assertEqual(self.wallet()["balance"], 7500)
        self.assertEqual(self.request("POST", f"/orders/{order}/refund").status_code, 200)
        before = self.wallet(), self.order(order)
        self.assertEqual(before[0], {"balance": 10000, "used_coupons": ["WELCOME"]})
        self.assertEqual(before[1]["paid"], 2500)
        for _ in range(2):
            self.assertEqual(self.request("POST", f"/orders/{order}/refund").status_code, 409)
            self.assertEqual((self.wallet(), self.order(order)), before)
        self.assertEqual(self.pay(order).status_code, 409)

    def test_coupon_reuse_rejected_before_and_after_refund(self):
        first, second = self.create(), self.create()
        self.assertEqual(self.pay(first, "WELCOME").status_code, 200)
        for refund in (False, True):
            if refund:
                self.assertEqual(self.request("POST", f"/orders/{first}/refund").status_code, 200)
            before = self.wallet(), self.order(second)
            self.assertEqual(self.pay(second, "WELCOME").status_code, 409)
            self.assertEqual((self.wallet(), self.order(second)), before)
        self.assertEqual(self.pay(second).status_code, 200)
        bob = self.create(user="bob")
        self.assertEqual(self.pay(bob, "WELCOME", user="bob").status_code, 200)
        self.assertEqual(self.wallet("bob")["balance"], 9500)

    def test_insufficient_funds_does_not_consume_coupon(self):
        orders = [self.create(3) for _ in range(4)]
        for order in orders[:3]:
            self.assertEqual(self.pay(order).status_code, 200)
        before = self.wallet(), self.order(orders[3])
        self.assertEqual(self.pay(orders[3], "WELCOME").status_code, 409)
        self.assertEqual((self.wallet(), self.order(orders[3])), before)
        self.assertEqual(self.request("POST", f"/orders/{orders[0]}/refund").status_code, 200)
        self.assertEqual(self.pay(orders[3], "WELCOME").status_code, 200)
        self.assertEqual(self.wallet(), {"balance": 1500, "used_coupons": ["WELCOME"]})

    def test_owner_isolation_in_each_state(self):
        order = self.create()
        for state in ("draft", "paid", "refunded"):
            if state == "paid":
                self.assertEqual(self.pay(order).status_code, 200)
            elif state == "refunded":
                self.assertEqual(self.request("POST", f"/orders/{order}/refund").status_code, 200)
            before = self.wallet(), self.wallet("bob"), self.order(order)
            for method, suffix, body in [("GET", "", None), ("POST", "/pay", {}), ("POST", "/refund", None)]:
                self.assertEqual(self.request(method, f"/orders/{order}{suffix}", user="bob", json=body).status_code, 404)
                self.assertEqual(self.request(method, f"/orders/999{suffix}", user="bob", json=body).status_code, 404)
            self.assertEqual((self.wallet(), self.wallet("bob"), self.order(order)), before)

    def test_validation_and_invalid_transitions_leave_state_unchanged(self):
        for quantity in (0, -1, 4):
            self.assertEqual(self.request("POST", "/orders", json={"quantity": quantity}).status_code, 422)
        order = self.create()
        before = self.wallet(), self.order(order)
        self.assertEqual(self.request("POST", f"/orders/{order}/refund").status_code, 409)
        self.assertEqual(self.pay(order, "UNKNOWN").status_code, 422)
        self.assertEqual((self.wallet(), self.order(order)), before)
        self.assertEqual(self.pay(order).status_code, 200)
        before = self.wallet(), self.order(order)
        self.assertEqual(self.pay(order).status_code, 409)
        self.assertEqual((self.wallet(), self.order(order)), before)

    def test_missing_and_wrong_credentials(self):
        for auth in ("", "Bearer fixture-mallory", "Bearer alice", "Basic fixture-alice"):
            self.assertEqual(self.request("GET", "/wallet", auth=auth).status_code, 401)
        self.assertEqual(self.client.get("/wallet").status_code, 401)
        self.assertEqual(self.wallet("bob"), {"balance": 10000, "used_coupons": []})

    def concurrent_posts(self, paths, body):
        # Widen a real thread scheduling window without changing application data.
        # FastAPI runs synchronous handlers in worker threads. Each worker pauses
        # immediately before wallet writes, after all business checks have run.
        source = Path(__file__).with_name("app.py")
        write_lines = {i for i, line in enumerate(source.read_text().splitlines(), 1)
                       if 'app.state.wallets[name] +=' in line or 'app.state.wallets[name] -=' in line}

        def trace(frame, event, arg):
            if event == "line" and frame.f_code.co_filename == str(source) and frame.f_lineno in write_lines:
                time.sleep(0.05)
            return trace

        start = threading.Barrier(2)

        def send(path):
            with TestClient(self.client.app) as client:
                start.wait(timeout=5)
                return client.post(path, headers={"Authorization": "Bearer fixture-alice"}, json=body).status_code

        self.mutations += 2
        self.assertLessEqual(self.mutations, 20)
        previous = threading.gettrace()
        threading.settrace(trace)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(send, path) for path in paths]
                return sorted(f.result(timeout=10) for f in futures)
        finally:
            threading.settrace(previous)

    def test_concurrent_payment_only_charges_once(self):
        order = self.create()
        self.assertEqual(self.concurrent_posts([f"/orders/{order}/pay"] * 2, {}), [200, 409])
        self.assertEqual(self.wallet()["balance"], 9000)
        self.assertEqual(self.order(order)["paid"], 1000)

    def test_concurrent_refund_only_credits_once(self):
        order = self.create()
        self.assertEqual(self.pay(order).status_code, 200)
        self.assertEqual(self.concurrent_posts([f"/orders/{order}/refund"] * 2, None), [200, 409])
        self.assertEqual(self.wallet()["balance"], 10000)

    def test_concurrent_coupon_across_orders_only_applies_once(self):
        first, second = self.create(), self.create()
        statuses = self.concurrent_posts([f"/orders/{oid}/pay" for oid in (first, second)], {"coupon": "WELCOME"})
        self.assertEqual(statuses, [200, 409])
        self.assertEqual(self.wallet()["balance"], 9500)
        self.assertEqual(sorted(self.order(oid)["state"] for oid in (first, second)), ["draft", "paid"])


if __name__ == "__main__":
    unittest.main()
