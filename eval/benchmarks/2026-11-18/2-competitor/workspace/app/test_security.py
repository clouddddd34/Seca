"""Local security regressions. Each test gets a fresh application instance."""
import unittest
from fastapi.testclient import TestClient
from app.app import create_app


def auth(actor):
    return {'Authorization': f'Bearer fixture-{actor}'}


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.instance = create_app()
        self.client = TestClient(self.instance)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_invoice_owner_matrix(self):
        for actor in ['alice', 'bob', 'carol', 'admin']:
            for invoice, owner in [('inv-a', 'alice'), ('inv-b', 'bob'), ('inv-c', 'carol'), ('missing', None)]:
                with self.subTest(actor=actor, invoice=invoice):
                    r = self.client.get('/invoices/' + invoice, headers=auth(actor))
                    self.assertEqual(r.status_code, 200 if actor == owner else 404)
                    if actor != owner:
                        self.assertEqual(r.json(), {'detail': 'Not found'})

    def test_report_tenant_matrix(self):
        for actor in ['alice', 'bob', 'carol', 'admin']:
            for report, tenant in [('report-n', 'north'), ('report-s', 'south'), ('missing', None)]:
                with self.subTest(actor=actor, report=report):
                    allowed = tenant == ('south' if actor == 'carol' else 'north')
                    r = self.client.get('/reports/' + report, headers=auth(actor))
                    self.assertEqual(r.status_code, 200 if allowed else 404)
                    if not allowed:
                        self.assertEqual(r.json(), {'detail': 'Not found'})

    def test_catalog_price_and_order_isolation(self):
        self.assertEqual(self.client.get('/catalog', headers=auth('alice')).json(), {'book': 1000})
        # Exactly five orders, including low, exact and high submitted prices.
        for price, quantity, actor in [(1, 2, 'alice'), (1000, 1, 'alice'),
                                       (100000, 5, 'bob'), (999, 1, 'carol'), (1001, 1, 'admin')]:
            with self.subTest(price=price, actor=actor):
                r = self.client.post('/orders', headers=auth(actor), json={
                    'sku': 'book', 'quantity': quantity, 'unit_price_cents': price,
                    'owner': 'bob', 'total_cents': 1})
                self.assertEqual(r.status_code, 201)
                self.assertEqual(r.json()['total_cents'], quantity * 1000)
                self.assertEqual(r.json()['owner'], actor)
        for actor, count in [('alice', 2), ('bob', 1), ('carol', 1), ('admin', 1)]:
            orders = self.client.get('/orders', headers=auth(actor)).json()
            self.assertEqual(len(orders), count)
            self.assertTrue(all(o['owner'] == actor for o in orders))

    def test_invalid_orders_leave_no_state(self):
        valid = {'sku': 'book', 'quantity': 1, 'unit_price_cents': 1000}
        for patch in [{'quantity': 0}, {'quantity': 6}, {'quantity': 1.5},
                      {'unit_price_cents': 0}, {'unit_price_cents': -1},
                      {'unit_price_cents': 100001}, {'quantity': None}]:
            r = self.client.post('/orders', headers=auth('alice'), json=valid | patch)
            self.assertEqual(r.status_code, 422)
        r = self.client.post('/orders', headers=auth('alice'), json=valid | {'sku': 'missing'})
        self.assertEqual(r.status_code, 404)
        r = self.client.post(
            '/orders', headers=auth('alice') | {'Content-Type': 'application/json'}, content='{')
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.instance.state.orders, [])

    def test_authentication_and_admin(self):
        for path in ['/', '/health']:
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ['/me', '/catalog', '/invoices/inv-a', '/reports/report-n', '/orders', '/admin/export', '/openapi.json']:
            for headers in [{}, {'Authorization': 'Bearer invalid'}]:
                self.assertEqual(self.client.get(path, headers=headers).status_code, 401)
        self.assertEqual(self.client.post('/orders', json={}).status_code, 401)
        for path in ['/admin/export', '/admin/export/', '/%61dmin/export', '/admin%2fexport']:
            for actor in ['alice', 'bob', 'carol']:
                self.assertEqual(self.client.get(path, headers=auth(actor)).status_code, 403)
            self.assertEqual(self.client.get(path, headers=auth('admin')).status_code, 200)
        for actor in ['alice', 'bob', 'carol', 'admin']:
            self.assertEqual(self.client.get('/me', headers=auth(actor)).json()['id'], actor)
        self.assertEqual(self.client.get('/openapi.json', headers=auth('alice')).status_code, 200)


if __name__ == '__main__':
    unittest.main()
