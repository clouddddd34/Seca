"""Bounded local regression and control tests; no network transports."""
import inspect
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.app import create_app


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.mutations = 0
        self.orders = 0

    def tearDown(self):
        self.client.close()
        self.assertLessEqual(self.mutations, 20)
        self.assertLessEqual(self.orders, 5)

    def headers(self, who='alice'):
        return {'Authorization': 'Bearer fixture-' + who}

    def post(self, path, body=None, who='alice', headers=None):
        self.mutations += 1
        r = self.client.post(path, json=body, headers=self.headers(who) if headers is None else headers)
        if path == '/orders' and r.status_code == 201:
            self.orders += 1
        return r

    def order(self, quantity=1, who='alice'):
        r = self.post('/orders', {'quantity': quantity}, who)
        self.assertEqual(r.status_code, 201)
        return r.json()['id']

    def saved(self, oid, who='alice'):
        h = self.headers(who)
        return (self.client.get('/wallet', headers=h).json(),
                self.client.get(f'/orders/{oid}', headers=h).json())

    def test_auth_requires_documented_bearer_token(self):
        for value in ['', 'alice', 'bob', 'fixture-alice', 'Bearer alice', 'Bearer fixture-unknown']:
            h = {'Authorization': value}
            self.assertEqual(self.client.get('/wallet', headers=h).status_code, 401, value)
            self.assertEqual(self.post('/orders', {'quantity': 1}, headers=h).status_code, 401, value)
        for who in ['alice', 'bob']:
            self.assertEqual(self.client.get('/wallet', headers=self.headers(who)).status_code, 200)

    def test_refund_only_once_and_actual_charge(self):
        oid = self.order(3)
        self.assertEqual(self.post(f'/orders/{oid}/pay', {'coupon': 'WELCOME'}).json()['paid'], 2500)
        self.assertEqual(self.post(f'/orders/{oid}/refund').status_code, 200)
        before = self.saved(oid)
        self.assertEqual(before[0], {'balance': 10000, 'used_coupons': ['WELCOME']})
        self.assertEqual(self.post(f'/orders/{oid}/refund').status_code, 409)
        self.assertEqual(self.saved(oid), before)
        self.assertEqual(self.post(f'/orders/{oid}/pay', {}).status_code, 409)
        self.assertEqual(self.saved(oid), before)

    def test_coupon_once_across_orders_even_after_refund(self):
        first = self.order()
        self.assertEqual(self.post(f'/orders/{first}/pay', {'coupon': 'WELCOME'}).status_code, 200)
        self.assertEqual(self.post(f'/orders/{first}/refund').status_code, 200)
        second = self.order()
        before = self.saved(second)
        self.assertEqual(self.post(f'/orders/{second}/pay', {'coupon': 'WELCOME'}).status_code, 409)
        self.assertEqual(self.saved(second), before)
        self.assertEqual(self.post(f'/orders/{second}/pay', {}).status_code, 200)
        bob = self.order(who='bob')
        self.assertEqual(self.post(f'/orders/{bob}/pay', {'coupon': 'WELCOME'}, 'bob').json()['paid'], 500)

    def test_failed_payment_preserves_unused_coupon(self):
        for _ in range(3):
            oid = self.order(3)
            self.assertEqual(self.post(f'/orders/{oid}/pay', {}).status_code, 200)
        target = self.order(3)
        before = self.saved(target)
        self.assertEqual(self.post(f'/orders/{target}/pay', {'coupon': 'WELCOME'}).status_code, 409)
        self.assertEqual(self.saved(target), before)
        self.assertEqual(self.post(f'/orders/{oid}/refund').status_code, 200)
        self.assertEqual(self.post(f'/orders/{target}/pay', {'coupon': 'WELCOME'}).status_code, 200)
        self.assertEqual(self.saved(target)[0], {'balance': 1500, 'used_coupons': ['WELCOME']})

    def test_ownership_and_auth_before_order_state(self):
        oid = self.order()
        for state in ['draft', 'paid', 'refunded']:
            before = self.saved(oid)
            for other in [oid, 999]:
                self.assertEqual(self.client.get(f'/orders/{other}', headers=self.headers('bob')).status_code, 404)
                for action in ['pay', 'refund']:
                    self.assertEqual(self.post(f'/orders/{other}/{action}', {}, 'bob').status_code, 404)
            self.assertEqual(self.saved(oid), before)
            if state == 'draft':
                self.assertEqual(self.post(f'/orders/{oid}/pay', {}).status_code, 200)
            elif state == 'paid':
                self.assertEqual(self.post(f'/orders/{oid}/refund').status_code, 200)
        self.assertEqual(self.client.get('/wallet', headers=self.headers('bob')).json()['balance'], 10000)

    def test_validation_and_invalid_transitions_are_nonmutating(self):
        for quantity in [0, -1, 4, 'bad']:
            self.assertEqual(self.post('/orders', {'quantity': quantity}).status_code, 422)
        oid = self.order(2)
        before = self.saved(oid)
        for action, body, status in [('refund', None, 409), ('pay', {'coupon': 'OTHER'}, 422), ('pay', {'coupon': None}, 422)]:
            self.assertEqual(self.post(f'/orders/{oid}/{action}', body).status_code, status)
            self.assertEqual(self.saved(oid), before)
        self.assertEqual(self.post(f'/orders/{oid}/pay', {}).status_code, 200)
        before = self.saved(oid)
        self.assertEqual(before[0]['balance'], 8000)
        self.assertEqual(self.post(f'/orders/{oid}/pay', {}).status_code, 409)
        self.assertEqual(self.saved(oid), before)

    def concurrent(self, paths, body, handler, marker):
        # Pause at a real source line to force a legal scheduling interleaving.
        # The timeout permits a serialized first request to finish after the fix.
        source, start = inspect.getsourcelines(create_app)
        target = start + next(i for i, line in enumerate(source) if marker in line)
        barrier = threading.Barrier(2)
        def trace(frame, event, arg):
            if event == 'line' and frame.f_code.co_name == handler and frame.f_lineno == target:
                try:
                    barrier.wait(timeout=0.5)
                except threading.BrokenBarrierError:
                    pass
            return trace
        def send(path):
            with TestClient(self.app) as c:
                return c.post(path, json=body, headers=self.headers()).status_code
        self.mutations += 2
        threading.settrace(trace)
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                return sorted(pool.map(send, paths))
        finally:
            threading.settrace(None)

    def test_simultaneous_payment_affects_wallet_once(self):
        oid = self.order()
        results = self.concurrent([f'/orders/{oid}/pay'] * 2, {}, 'pay', 'wallets[name] -= charge')
        wallet, order = self.saved(oid)
        self.assertEqual((results, wallet['balance'], order['paid'], order['state']),
                         ([200, 409], 9000, 1000, 'paid'))

    def test_simultaneous_refund_affects_wallet_once(self):
        oid = self.order()
        self.assertEqual(self.post(f'/orders/{oid}/pay', {}).status_code, 200)
        results = self.concurrent([f'/orders/{oid}/refund'] * 2, None, 'refund', 'wallets[name] +=')
        wallet, order = self.saved(oid)
        self.assertEqual((results, wallet['balance'], order['state']), ([200, 409], 10000, 'refunded'))

    def test_simultaneous_coupon_use_across_orders(self):
        ids = [self.order(), self.order()]
        results = self.concurrent([f'/orders/{oid}/pay' for oid in ids], {'coupon': 'WELCOME'},
                                  'pay', 'wallets[name] -= charge')
        wallet, _ = self.saved(ids[0])
        states = sorted(self.saved(oid)[1]['state'] for oid in ids)
        self.assertEqual((results, wallet, states),
                         ([200, 409], {'balance': 9500, 'used_coupons': ['WELCOME']}, ['draft', 'paid']))


if __name__ == '__main__':
    unittest.main(verbosity=2)
