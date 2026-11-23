import unittest
from time import time
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import create_app


def auth(name):
    return {"Authorization": f"Bearer fixture-{name}"}


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def share(self):
        response = self.client.post('/documents/a/shares', headers=auth('alice'),
                                    json={'recipient': 'bob', 'expires_at': time() + 3600})
        self.assertEqual(response.status_code, 201)
        return response.json()['id']

    def read(self, name, doc='a'):
        return self.client.get(f'/documents/{doc}', headers=auth(name))

    def test_expired_share(self):
        self.share()
        self.assertEqual(self.read('bob').status_code, 200)
        self.app.state.shares[0]['expires_at'] = time() - 1
        self.assertEqual(self.read('bob').status_code, 404)
        self.assertEqual(self.read('alice').status_code, 200)

    def test_exact_expiry_boundary(self):
        self.share()
        self.app.state.shares[0]['expires_at'] = 1000
        with patch('app.time', return_value=1000):
            self.assertEqual(self.read('bob').status_code, 404)

    def test_recipient_migration(self):
        self.share()
        self.app.state.users['bob']['tenant'] = 'south'
        self.assertEqual(self.read('bob').status_code, 404)
        self.app.state.users['bob']['tenant'] = 'north'
        self.assertEqual(self.read('bob').status_code, 200)

    def test_owner_migration(self):
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.read('alice').status_code, 404)
        self.app.state.users['alice']['tenant'] = 'north'
        self.assertEqual(self.read('alice').status_code, 200)

    def test_revocation_and_reshare(self):
        sid = self.share()
        self.assertEqual(self.client.delete(f'/shares/{sid}', headers=auth('bob')).status_code, 403)
        self.assertEqual(self.client.post('/documents/a/shares', headers=auth('bob'),
                         json={'recipient': 'admin', 'expires_at': time()+3600}).status_code, 403)
        self.assertEqual(self.client.delete(f'/shares/{sid}', headers=auth('alice')).status_code, 204)
        self.assertEqual(self.read('bob').status_code, 404)
        self.share()
        self.assertEqual(self.read('bob').status_code, 200)

    def test_share_validation(self):
        for recipient, expiry in [('carol', time()+3600), ('missing', time()+3600), ('bob', time()-1)]:
            self.assertEqual(self.client.post('/documents/a/shares', headers=auth('alice'),
                             json={'recipient': recipient, 'expires_at': expiry}).status_code, 422)
        self.assertEqual(self.app.state.shares, [])

    def test_migrated_owner_cannot_mutate(self):
        sid = self.share()
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.client.delete(f'/shares/{sid}', headers=auth('alice')).status_code, 403)
        self.assertEqual(self.client.post('/documents/a/shares', headers=auth('alice'),
                         json={'recipient': 'bob', 'expires_at': time()+3600}).status_code, 403)
        self.assertFalse(self.app.state.shares[0]['revoked'])
        self.assertEqual(len(self.app.state.shares), 1)

    def test_inventory(self):
        self.assertEqual(self.client.get('/admin/inventory', headers=auth('bob')).status_code, 403)
        self.assertEqual({d['id'] for d in self.client.get('/admin/inventory', headers=auth('admin')).json()}, {'a', 'b'})
        self.app.state.users['admin']['tenant'] = 'south'
        self.assertEqual({d['id'] for d in self.client.get('/admin/inventory', headers=auth('admin')).json()}, {'c'})

    def test_auth_and_unshared_reads(self):
        for method, path, kwargs in [('get', '/documents/a', {}), ('post', '/documents/a/shares',
                {'json': {'recipient': 'bob', 'expires_at': time()+3600}}),
                ('delete', '/shares/1', {}), ('get', '/admin/inventory', {})]:
            for headers in [{}, auth('unknown')]:
                self.assertEqual(getattr(self.client, method)(path, headers=headers, **kwargs).status_code, 401)
        for name in ['bob', 'carol', 'admin']:
            self.assertEqual(self.read(name).status_code, 404)
        self.assertEqual(self.read('alice', 'missing').status_code, 404)


if __name__ == '__main__':
    unittest.main()
