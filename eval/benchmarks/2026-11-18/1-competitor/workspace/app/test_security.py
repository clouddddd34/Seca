import unittest

from fastapi.testclient import TestClient
from app.app import create_app


def auth(actor):
    return {'Authorization': f'Bearer fixture-{actor}'}


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.application = create_app()
        self.client = TestClient(self.application)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_authentication_and_public_routes(self):
        for path in ['/', '/health']:
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ['/me', '/catalog', '/invoices/inv-a', '/reports/report-n',
                     '/orders', '/admin/export', '/openapi.json']:
            for headers in [{}, {'Authorization': 'Bearer unknown'}]:
                self.assertEqual(self.client.get(path, headers=headers).status_code, 401)
        self.assertEqual(self.client.post('/orders', json={}).status_code, 401)
        self.assertEqual(self.client.get('/me', headers=auth('alice')).json()['id'], 'alice')

    def test_invoice_owner_matrix(self):
        for actor in ['alice', 'bob', 'carol', 'admin']:
            for invoice, owner in [('inv-a', 'alice'), ('inv-b', 'bob'), ('inv-c', 'carol'), ('missing', None)]:
                with self.subTest(actor=actor, invoice=invoice):
                    r = self.client.get(f'/invoices/{invoice}', headers=auth(actor))
                    self.assertEqual(r.status_code, 200 if actor == owner else 404)
                    if actor != owner:
                        self.assertEqual(r.json(), {'detail': 'Not found'})

    def test_report_tenant_matrix(self):
        for actor in ['alice', 'bob', 'carol', 'admin']:
            for report, allowed in [('report-n', actor != 'carol'), ('report-s', actor == 'carol'), ('missing', False)]:
                with self.subTest(actor=actor, report=report):
                    r = self.client.get(f'/reports/{report}', headers=auth(actor))
                    self.assertEqual(r.status_code, 200 if allowed else 404)
                    if not allowed:
                        self.assertEqual(r.json(), {'detail': 'Not found'})

    def test_admin_boundary_and_path_variants(self):
        for path in ['/admin/export', '/admin/export/', '/%61dmin/export', '/admin%2fexport']:
            self.assertEqual(self.client.get(path, headers=auth('alice')).status_code, 403)
        self.assertEqual(self.client.get('/admin/export', headers=auth('admin')).status_code, 200)

    def test_catalog_pricing_and_order_isolation(self):
        self.assertEqual(self.client.get('/catalog', headers=auth('alice')).json(), {'book': 1000})
        # Exactly five orders in this fresh instance, including upper quantity bound.
        for price, quantity in [(1, 1), (999, 2), (1000, 1), (1001, 1), (100000, 5)]:
            r = self.client.post('/orders', headers=auth('alice'), json={
                'sku': 'book', 'quantity': quantity, 'unit_price_cents': price,
                'owner': 'bob', 'total_cents': 0})
            self.assertEqual(r.status_code, 201)
            self.assertEqual(r.json()['total_cents'], quantity * 1000)
            self.assertEqual(r.json()['owner'], 'alice')
        self.assertEqual(len(self.client.get('/orders', headers=auth('alice')).json()), 5)
        for actor in ['bob', 'carol', 'admin']:
            self.assertEqual(self.client.get('/orders', headers=auth(actor)).json(), [])

    def test_invalid_orders_do_not_mutate_state(self):
        valid = {'sku': 'book', 'quantity': 1, 'unit_price_cents': 1000}
        for field, value in [('quantity', 0), ('quantity', 6), ('quantity', -1),
                             ('unit_price_cents', 0), ('unit_price_cents', 100001),
                             ('quantity', 'bad'), ('sku', None)]:
            r = self.client.post('/orders', headers=auth('alice'), json={**valid, field: value})
            self.assertEqual(r.status_code, 422)
        self.assertEqual(self.client.post('/orders', headers=auth('alice'), json={**valid, 'sku': 'missing'}).status_code, 404)
        r = self.client.post('/orders', headers={**auth('alice'), 'Content-Type': 'application/json'}, content='{')
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.application.state.orders, [])


if __name__ == '__main__':
    unittest.main()
