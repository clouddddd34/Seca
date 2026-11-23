import unittest
from fastapi.testclient import TestClient
from app.app import create_app


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.headers = {"Authorization": "Bearer fixture-alice"}
        self.orders = 0
        self.mutations = 0
        self.addCleanup(self.client.close)

    def post(self, path, body=None, headers=None):
        self.mutations += 1
        self.assertLessEqual(self.mutations, 20)
        return self.client.post(path, json=body, headers=self.headers if headers is None else headers)

    def create(self, quantity=1):
        self.orders += 1
        self.assertLessEqual(self.orders, 5)
        response = self.post('/orders', {"quantity": quantity})
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def saved(self, order):
        return (self.client.get('/wallet', headers=self.headers).json(),
                self.client.get(f'/orders/{order}', headers=self.headers).json())

    def test_exact_bearer_required(self):
        for token in ('alice', 'bob', '', 'Bearer alice', 'Bearer fixture-unknown'):
            with self.subTest(token=token):
                headers = {"Authorization": token}
                self.assertEqual(self.client.get('/wallet', headers=headers).status_code, 401)
                self.assertEqual(self.post('/orders', {'quantity': 1}, headers).status_code, 401)
        self.assertEqual(self.client.get('/wallet', headers=self.headers).status_code, 200)

    def test_refund_only_once_and_net_charge(self):
        order = self.create()
        self.assertEqual(self.post(f'/orders/{order}/pay', {'coupon': 'WELCOME'}).status_code, 200)
        self.assertEqual(self.saved(order)[0]['balance'], 9500)
        self.assertEqual(self.post(f'/orders/{order}/refund').status_code, 200)
        before = self.saved(order)
        self.assertEqual(before[0], {'balance': 10000, 'used_coupons': ['WELCOME']})
        self.assertEqual(before[1]['paid'], 500)
        self.assertEqual(self.post(f'/orders/{order}/refund').status_code, 409)
        self.assertEqual(self.saved(order), before)
        self.assertEqual(self.post(f'/orders/{order}/pay', {}).status_code, 409)
        self.assertEqual(self.saved(order), before)

    def test_coupon_once_across_orders_even_after_refund(self):
        first, second = self.create(), self.create()
        self.assertEqual(self.post(f'/orders/{first}/pay', {'coupon': 'WELCOME'}).status_code, 200)
        before = self.saved(second)
        self.assertEqual(self.post(f'/orders/{second}/pay', {'coupon': 'WELCOME'}).status_code, 409)
        self.assertEqual(self.saved(second), before)
        self.assertEqual(self.post(f'/orders/{first}/refund').status_code, 200)
        before = self.saved(second)
        self.assertEqual(self.post(f'/orders/{second}/pay', {'coupon': 'WELCOME'}).status_code, 409)
        self.assertEqual(self.saved(second), before)
        self.assertEqual(self.post(f'/orders/{second}/pay', {}).status_code, 200)
        self.assertEqual(self.saved(second)[0]['balance'], 9000)
        bob = {'Authorization': 'Bearer fixture-bob'}
        third = self.post('/orders', {'quantity': 1}, bob).json()['id']
        self.assertEqual(self.post(f'/orders/{third}/pay', {'coupon': 'WELCOME'}, bob).status_code, 200)
        self.assertEqual(self.client.get('/wallet', headers=bob).json()['balance'], 9500)

    def test_owner_controls_and_missing_orders(self):
        order = self.create()
        before = self.saved(order)
        bob = {'Authorization': 'Bearer fixture-bob'}
        for target in (order, 999):
            self.assertEqual(self.client.get(f'/orders/{target}', headers=bob).status_code, 404)
            for action in ('pay', 'refund'):
                self.assertEqual(self.post(f'/orders/{target}/{action}', {}, bob).status_code, 404)
        self.assertEqual(self.saved(order), before)

    def test_validation_and_transitions(self):
        for quantity in (0, 4, -1):
            self.assertEqual(self.post('/orders', {'quantity': quantity}).status_code, 422)
        order = self.create(2)
        before = self.saved(order)
        self.assertEqual(self.post(f'/orders/{order}/refund').status_code, 409)
        self.assertEqual(self.post(f'/orders/{order}/pay', {'coupon': 'UNKNOWN'}).status_code, 422)
        self.assertEqual(self.saved(order), before)
        self.assertEqual(self.post(f'/orders/{order}/pay', {}).status_code, 200)
        before = self.saved(order)
        self.assertEqual(before[0]['balance'], 8000)
        self.assertEqual(self.post(f'/orders/{order}/pay', {}).status_code, 409)
        self.assertEqual(self.saved(order), before)

    def test_failed_payment_preserves_coupon(self):
        paid = []
        for _ in range(3):
            order = self.create(3)
            paid.append(order)
            self.assertEqual(self.post(f'/orders/{order}/pay', {}).status_code, 200)
        draft = self.create(2)
        before = self.saved(draft)
        self.assertEqual(self.post(f'/orders/{draft}/pay', {'coupon': 'WELCOME'}).status_code, 409)
        self.assertEqual(self.saved(draft), before)
        self.assertEqual(before[0], {'balance': 1000, 'used_coupons': []})
        self.assertEqual(self.post(f'/orders/{paid[0]}/refund').status_code, 200)
        self.assertEqual(self.post(f'/orders/{draft}/pay', {'coupon': 'WELCOME'}).status_code, 200)
        self.assertEqual(self.saved(draft)[0], {'balance': 2500, 'used_coupons': ['WELCOME']})


if __name__ == '__main__':
    unittest.main(verbosity=2)
