"""Bounded local regression checks; each test gets independent state."""
import unittest
from fastapi.testclient import TestClient
from app import create_app


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)
        self.mutations = self.orders = 0

    def request(self, method, path, user='alice', **kwargs):
        if method == 'POST':
            self.mutations += 1
            self.assertLessEqual(self.mutations, 20)
            if path == '/orders':
                self.orders += 1
                self.assertLessEqual(self.orders, 5)
        headers = kwargs.pop('headers', {'Authorization': f'Bearer fixture-{user}'})
        return self.client.request(method, path, headers=headers, **kwargs)

    def create(self, quantity=1, user='alice'):
        response = self.request('POST', '/orders', user, json={'quantity': quantity})
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def wallet(self, user='alice'):
        return self.request('GET', '/wallet', user).json()

    def order(self, order_id):
        return self.request('GET', f'/orders/{order_id}').json()

    def pay(self, order_id, coupon=''):
        return self.request('POST', f'/orders/{order_id}/pay', json={'coupon': coupon})

    def refund(self, order_id):
        return self.request('POST', f'/orders/{order_id}/refund')

    def test_bare_account_is_not_a_credential(self):
        for user in ('alice', 'bob'):
            response = self.request('GET', '/wallet', headers={'Authorization': user})
            self.assertEqual(response.status_code, 401, response.text)

    def test_coupon_cannot_be_reused_across_orders(self):
        first, second = self.create(), self.create()
        self.assertEqual(self.pay(first, 'WELCOME').status_code, 200)
        before = self.wallet(), self.order(second)
        response = self.pay(second, 'WELCOME')
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((self.wallet(), self.order(second)), before)
        self.assertEqual(self.pay(second).status_code, 200)
        self.assertEqual(self.wallet()['balance'], 8500)

    def test_refund_is_once_and_matches_discounted_charge(self):
        order = self.create(3)
        self.assertEqual(self.pay(order, 'WELCOME').json()['paid'], 2500)
        self.assertEqual(self.wallet()['balance'], 7500)
        self.assertEqual(self.refund(order).status_code, 200)
        self.assertEqual(self.wallet()['balance'], 10000)
        before = self.wallet(), self.order(order)
        response = self.refund(order)
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual((self.wallet(), self.order(order)), before)
        self.assertEqual(self.pay(order).status_code, 409)

    def test_refund_does_not_restore_coupon_and_bob_is_independent(self):
        first = self.create()
        self.assertEqual(self.pay(first, 'WELCOME').status_code, 200)
        self.assertEqual(self.refund(first).status_code, 200)
        second = self.create()
        before = self.wallet(), self.order(second)
        self.assertEqual(self.pay(second, 'WELCOME').status_code, 409)
        self.assertEqual((self.wallet(), self.order(second)), before)
        bob = self.create(user='bob')
        self.assertEqual(self.request('POST', f'/orders/{bob}/pay', 'bob',
                                      json={'coupon': 'WELCOME'}).status_code, 200)
        self.assertEqual(self.wallet('bob')['balance'], 9500)

    def test_failed_payment_preserves_unused_coupon(self):
        orders = [self.create(3) for _ in range(4)]
        for order in orders[:3]:
            self.assertEqual(self.pay(order).status_code, 200)
        before = self.wallet(), self.order(orders[3])
        self.assertEqual(self.pay(orders[3], 'WELCOME').status_code, 409)
        self.assertEqual((self.wallet(), self.order(orders[3])), before)
        self.assertEqual(self.refund(orders[0]).status_code, 200)
        self.assertEqual(self.pay(orders[3], 'WELCOME').status_code, 200)
        self.assertEqual(self.wallet(), {'balance': 1500, 'used_coupons': ['WELCOME']})

    def test_ownership_before_state_and_mutation(self):
        order = self.create()
        before = self.wallet(), self.wallet('bob'), self.order(order)
        for target in (order, 999):
            for method, suffix, kwargs in [('GET', '', {}), ('POST', '/pay', {'json': {}}),
                                            ('POST', '/refund', {})]:
                self.assertEqual(self.request(method, f'/orders/{target}{suffix}', 'bob',
                                              **kwargs).status_code, 404)
        self.assertEqual((self.wallet(), self.wallet('bob'), self.order(order)), before)

    def test_invalid_inputs_and_transitions_preserve_state(self):
        for quantity in (0, 4, -1):
            self.assertEqual(self.request('POST', '/orders', json={'quantity': quantity}).status_code, 422)
        order = self.create()
        before = self.wallet(), self.order(order)
        self.assertEqual(self.refund(order).status_code, 409)
        self.assertEqual(self.pay(order, 'UNKNOWN').status_code, 422)
        self.assertEqual((self.wallet(), self.order(order)), before)
        self.assertEqual(self.pay(order).status_code, 200)
        before = self.wallet(), self.order(order)
        self.assertEqual(self.pay(order).status_code, 409)
        self.assertEqual((self.wallet(), self.order(order)), before)

    def test_missing_and_invalid_auth_all_routes(self):
        order = self.create()
        before = self.wallet(), self.order(order)
        for headers in ({}, {'Authorization': 'Bearer fixture-mallory'}, {'Authorization': 'alice'}):
            for method, path, kwargs in [
                ('GET', '/wallet', {}), ('GET', f'/orders/{order}', {}),
                ('POST', '/orders', {'json': {'quantity': 1}}),
                ('POST', f'/orders/{order}/pay', {'json': {}}),
                ('POST', f'/orders/{order}/refund', {})]:
                self.assertEqual(self.request(method, path, headers=headers, **kwargs).status_code, 401)
        self.assertEqual((self.wallet(), self.order(order)), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
