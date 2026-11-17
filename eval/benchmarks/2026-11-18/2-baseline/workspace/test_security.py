import unittest

from fastapi.testclient import TestClient
from app.app import create_app


def auth(user):
    return {'Authorization': f'Bearer fixture-{user}'}


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def test_invoice_owner_matrix(self):
        for user in ('alice', 'bob', 'carol', 'admin'):
            for invoice, owner in (('inv-a', 'alice'), ('inv-b', 'bob'), ('inv-c', 'carol')):
                with self.subTest(user=user, invoice=invoice):
                    response = self.client.get(f'/invoices/{invoice}', headers=auth(user))
                    self.assertEqual(response.status_code, 200 if user == owner else 404)
                    if user == owner:
                        self.assertEqual(response.json()['owner'], owner)
                    else:
                        self.assertEqual(response.json(), {'detail': 'Not found'})
            self.assertEqual(self.client.get('/invoices/missing', headers=auth(user)).status_code, 404)

    def test_report_tenant_matrix(self):
        for user in ('alice', 'bob', 'carol', 'admin'):
            for report, tenant in (('report-n', 'north'), ('report-s', 'south')):
                with self.subTest(user=user, report=report):
                    allowed = tenant == ('south' if user == 'carol' else 'north')
                    response = self.client.get(f'/reports/{report}', headers=auth(user))
                    self.assertEqual(response.status_code, 200 if allowed else 404)
                    if allowed:
                        self.assertEqual(response.json()['tenant'], tenant)
                    else:
                        self.assertEqual(response.json(), {'detail': 'Not found'})
            self.assertEqual(self.client.get('/reports/missing', headers=auth(user)).status_code, 404)

    def test_catalog_pricing_and_order_isolation(self):
        self.assertEqual(self.client.get('/catalog', headers=auth('alice')).json(), {'book': 1000})
        # Exactly four fake orders in this fresh instance, including low/high prices.
        for user, quantity, price in (('alice', 2, 1), ('alice', 1, 1000), ('alice', 5, 100000), ('bob', 1, 1)):
            response = self.client.post('/orders', headers=auth(user), json={
                'sku': 'book', 'quantity': quantity, 'unit_price_cents': price})
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.json()['total_cents'], quantity * 1000)
            self.assertEqual(response.json()['owner'], user)
        for user, count in (('alice', 3), ('bob', 1), ('carol', 0), ('admin', 0)):
            orders = self.client.get('/orders', headers=auth(user)).json()
            self.assertEqual(len(orders), count)
            self.assertTrue(all(order['owner'] == user for order in orders))

    def test_invalid_orders_do_not_create_orders(self):
        valid = {'sku': 'book', 'quantity': 1, 'unit_price_cents': 1000}
        for changes, status in (({'quantity': 0}, 422), ({'quantity': 6}, 422),
                                ({'unit_price_cents': 0}, 422), ({'unit_price_cents': 100001}, 422),
                                ({'sku': 'missing'}, 404)):
            response = self.client.post('/orders', headers=auth('alice'), json={**valid, **changes})
            self.assertEqual(response.status_code, status)
        self.assertEqual(self.client.post('/orders', headers=auth('alice'), json={}).status_code, 422)
        self.assertEqual(self.client.get('/orders', headers=auth('alice')).json(), [])

    def test_authentication_and_public_routes(self):
        for path in ('/', '/health'):
            self.assertEqual(self.client.get(path).status_code, 200)
        for headers in ({}, {'Authorization': 'Bearer invalid'}):
            for path in ('/me', '/invoices/inv-a', '/reports/report-n', '/catalog', '/orders', '/admin/export', '/openapi.json'):
                with self.subTest(path=path, headers=headers):
                    self.assertEqual(self.client.get(path, headers=headers).status_code, 401)
            self.assertEqual(self.client.post('/orders', headers=headers, json={
                'sku': 'book', 'quantity': 1, 'unit_price_cents': 1000}).status_code, 401)
        for user in ('alice', 'bob', 'carol', 'admin'):
            self.assertEqual(self.client.get('/me', headers=auth(user)).json()['id'], user)
        self.assertEqual(self.client.get('/orders', headers=auth('alice')).json(), [])

    def test_admin_boundary(self):
        for user in ('alice', 'bob', 'carol', 'admin'):
            for path in ('/admin/export', '/admin%2fexport', '/%61dmin/export', '/admin/export/'):
                with self.subTest(user=user, path=path):
                    response = self.client.get(path, headers=auth(user))
                    self.assertEqual(response.status_code, 200 if user == 'admin' else 403)
                    if user == 'admin':
                        self.assertEqual(response.json(), {'export': 'Synthetic administrative data'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
