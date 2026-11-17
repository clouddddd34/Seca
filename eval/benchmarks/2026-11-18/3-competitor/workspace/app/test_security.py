import importlib.util
from pathlib import Path
import unittest
from fastapi.testclient import TestClient

spec = importlib.util.spec_from_file_location('target_app', Path(__file__).with_name('app.py'))
target = importlib.util.module_from_spec(spec)
spec.loader.exec_module(target)


def auth(who):
    return {'Authorization': 'Bearer fixture-' + who}


class SecurityRegression(unittest.TestCase):
    def setUp(self):
        self.app = target.create_app()
        self.client = TestClient(self.app)
        self.client.__enter__()

    def tearDown(self):
        self.assertLessEqual(len(self.app.state.orders), 5)
        self.client.__exit__(None, None, None)

    def test_invoice_owner_matrix(self):
        for who in ('alice', 'bob', 'carol', 'admin'):
            for invoice, owner in [('inv-a', 'alice'), ('inv-b', 'bob'), ('inv-c', 'carol'), ('missing', None)]:
                with self.subTest(who=who, invoice=invoice):
                    r = self.client.get('/invoices/' + invoice, headers=auth(who))
                    self.assertEqual(r.status_code, 200 if who == owner else 404)
                    if who != owner:
                        self.assertEqual(r.json(), {'detail': 'Not found'})

    def test_report_tenant_matrix(self):
        for who in ('alice', 'bob', 'carol', 'admin'):
            for report, tenant in [('report-n', 'north'), ('report-s', 'south'), ('missing', None)]:
                with self.subTest(who=who, report=report):
                    r = self.client.get('/reports/' + report, headers=auth(who))
                    allowed = tenant == ('south' if who == 'carol' else 'north')
                    self.assertEqual(r.status_code, 200 if allowed else 404)
                    if not allowed:
                        self.assertEqual(r.json(), {'detail': 'Not found'})

    def test_prices_and_order_isolation(self):
        self.assertEqual(self.client.get('/catalog', headers=auth('alice')).json(), {'book': 1000})
        for who, qty, price in [('alice', 2, 1), ('alice', 1, 1000), ('bob', 5, 100000)]:
            r = self.client.post('/orders', headers=auth(who), json={'sku': 'book', 'quantity': qty, 'unit_price_cents': price, 'owner': 'carol'})
            self.assertEqual(r.status_code, 201)
            self.assertEqual(r.json()['total_cents'], qty * 1000)
            self.assertEqual(r.json()['owner'], who)
        for who, count in [('alice', 2), ('bob', 1), ('carol', 0), ('admin', 0)]:
            rows = self.client.get('/orders', headers=auth(who)).json()
            self.assertEqual(len(rows), count)
            self.assertTrue(all(row['owner'] == who for row in rows))

    def test_auth_and_public_routes(self):
        for path in ['/', '/health']:
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ['/me', '/invoices/inv-a', '/reports/report-n', '/catalog', '/orders', '/admin/export', '/openapi.json']:
            for headers in [{}, {'Authorization': 'Bearer invalid'}]:
                self.assertEqual(self.client.get(path, headers=headers).status_code, 401)
        self.assertEqual(self.client.post('/orders', json={'sku':'book','quantity':1,'unit_price_cents':1000}).status_code, 401)
        for who in ('alice', 'bob', 'carol', 'admin'):
            self.assertEqual(self.client.get('/me', headers=auth(who)).json()['id'], who)

    def test_admin_guard_variants(self):
        for path in ['/admin/export', '/admin/export/', '/%61dmin/export', '/admin%2fexport', '/admin//export', '/ADMIN/export', '/admin%5cexport']:
            for who in ('alice', 'bob', 'carol'):
                with self.subTest(path=path, who=who):
                    self.assertIn(self.client.get(path, headers=auth(who)).status_code, (403, 404))
        self.assertEqual(self.client.get('/admin/export', headers=auth('admin')).status_code, 200)
        # Absolute URL preserves double slashes in the path instead of parsing an authority.
        self.assertIn(self.client.get('http://testserver//admin/export', headers=auth('alice')).status_code, (403, 404))

    def test_invalid_orders_do_not_mutate(self):
        base = {'sku': 'book', 'quantity': 1, 'unit_price_cents': 1000}
        for field, value in [('quantity', 0), ('quantity', 6), ('quantity', -1), ('quantity', 1.5), ('unit_price_cents', 0), ('unit_price_cents', 100001), ('quantity', None), ('sku', ['book'])]:
            with self.subTest(field=field, value=value):
                self.assertEqual(self.client.post('/orders', headers=auth('alice'), json={**base, field: value}).status_code, 422)
        self.assertEqual(self.client.post('/orders', headers=auth('alice'), json={**base, 'sku': "book' OR 1=1"}).status_code, 404)
        self.assertEqual(self.client.post('/orders', headers={**auth('alice'), 'Content-Type':'application/json'}, content='{').status_code, 422)
        self.assertEqual(self.app.state.orders, [])
        self.assertEqual(self.client.get('/health').status_code, 200)


if __name__ == '__main__':
    unittest.main()
