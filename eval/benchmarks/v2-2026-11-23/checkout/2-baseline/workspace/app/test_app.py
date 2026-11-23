import unittest
from fastapi.testclient import TestClient
from app.app import create_app


class CheckoutTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.alice = {"Authorization": "Bearer fixture-alice"}
        self.bob = {"Authorization": "Bearer fixture-bob"}

    def create(self, quantity=1, headers=None):
        response = self.client.post('/orders', json={'quantity': quantity}, headers=headers or self.alice)
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def pay(self, order, coupon='', headers=None):
        return self.client.post(f'/orders/{order}/pay', json={'coupon': coupon}, headers=headers or self.alice)

    def refund(self, order, headers=None):
        return self.client.post(f'/orders/{order}/refund', headers=headers or self.alice)

    def saved(self, order, headers=None):
        headers = headers or self.alice
        return (self.client.get(f'/orders/{order}', headers=headers).json(),
                self.client.get('/wallet', headers=headers).json())

    def test_bare_account_is_not_a_bearer_token(self):
        response = self.client.post('/orders', json={'quantity': 1}, headers={'Authorization': 'alice'})
        self.assertEqual(response.status_code, 401, response.text)

    def test_repeated_refund_is_rejected_without_credit(self):
        order = self.create()
        self.assertEqual(self.pay(order, 'WELCOME').status_code, 200)
        self.assertEqual(self.saved(order)[1]['balance'], 9500)
        self.assertEqual(self.refund(order).status_code, 200)
        before = self.saved(order)
        response = self.refund(order)
        after = self.saved(order)
        self.assertEqual((response.status_code, after), (409, before))
        self.assertEqual(after[1]['balance'], 10000)

    def test_coupon_cannot_be_reused_after_refund(self):
        first = self.create()
        second = self.create()
        self.assertEqual(self.pay(first, 'WELCOME').status_code, 200)
        self.assertEqual(self.refund(first).status_code, 200)
        before = self.saved(second)
        response = self.pay(second, 'WELCOME')
        self.assertEqual((response.status_code, self.saved(second)), (409, before))
        self.assertEqual(self.pay(second).status_code, 200)
        self.assertEqual(self.saved(second)[1]['balance'], 9000)

    def test_coupon_cannot_be_reused_across_paid_orders(self):
        first, second = self.create(), self.create()
        self.assertEqual(self.pay(first, 'WELCOME').status_code, 200)
        before = self.saved(second)
        response = self.pay(second, 'WELCOME')
        self.assertEqual((response.status_code, self.saved(second)), (409, before))

    def test_owner_controls(self):
        order = self.create()
        before = self.saved(order)
        self.assertEqual(self.client.get(f'/orders/{order}', headers=self.bob).status_code, 404)
        self.assertEqual(self.pay(order, headers=self.bob).status_code, 404)
        self.assertEqual(self.refund(order, headers=self.bob).status_code, 404)
        self.assertEqual(self.saved(order), before)
        self.assertEqual(self.client.get('/wallet', headers=self.bob).json()['balance'], 10000)

    def test_transitions_and_unknown_coupon_preserve_state(self):
        order = self.create(3)
        before = self.saved(order)
        self.assertEqual(self.refund(order).status_code, 409)
        self.assertEqual(self.pay(order, 'INVALID').status_code, 422)
        self.assertEqual(self.saved(order), before)
        self.assertEqual(self.pay(order).status_code, 200)
        paid = self.saved(order)
        self.assertEqual(paid[1]['balance'], 7000)
        self.assertEqual(self.pay(order, 'WELCOME').status_code, 409)
        self.assertEqual(self.saved(order), paid)
        self.assertEqual(self.refund(order).status_code, 200)
        refunded = self.saved(order)
        self.assertEqual(refunded[1]['balance'], 10000)
        self.assertEqual(self.pay(order).status_code, 409)
        self.assertEqual(self.saved(order), refunded)

    def test_failed_payment_does_not_consume_coupon(self):
        for _ in range(3):
            self.assertEqual(self.pay(self.create(3)).status_code, 200)
        expensive = self.create(2)
        before = self.saved(expensive)
        self.assertEqual(self.pay(expensive, 'WELCOME').status_code, 409)
        self.assertEqual(self.saved(expensive), before)
        affordable = self.create()
        self.assertEqual(self.pay(affordable, 'WELCOME').status_code, 200)
        self.assertEqual(self.saved(affordable)[1], {'balance': 500, 'used_coupons': ['WELCOME']})

    def test_accounts_have_independent_coupon_eligibility(self):
        alice = self.create()
        bob = self.create(headers=self.bob)
        self.assertEqual(self.pay(alice, 'WELCOME').status_code, 200)
        self.assertEqual(self.pay(bob, 'WELCOME', self.bob).status_code, 200)
        self.assertEqual(self.saved(bob, self.bob)[1]['balance'], 9500)

    def test_validation_and_missing_credentials(self):
        for quantity in (0, 4, -1):
            self.assertEqual(self.client.post('/orders', json={'quantity': quantity}, headers=self.alice).status_code, 422)
        for headers in ({}, {'Authorization': 'Bearer fixture-unknown'}):
            self.assertEqual(self.client.get('/wallet', headers=headers).status_code, 401)
        self.assertEqual(self.client.get('/orders/999', headers=self.alice).status_code, 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
