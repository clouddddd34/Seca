import unittest
from time import time

from fastapi.testclient import TestClient
from app import create_app


def auth(name):
    return {'Authorization': 'Bearer fixture-' + name}


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.client.__enter__()
        self.addCleanup(self.client.__exit__, None, None, None)

    def share(self, recipient='bob', owner='alice', doc='a'):
        return self.client.post('/documents/' + doc + '/shares',
                                headers=auth(owner),
                                json={'recipient': recipient, 'expires_at': time() + 3600})

    def read(self, name, doc='a'):
        return self.client.get('/documents/' + doc, headers=auth(name))

    def test_expired_share_denied(self):
        self.assertEqual(self.share().status_code, 201)
        self.app.state.shares[0]['expires_at'] = time() - 60
        self.assertEqual(self.read('bob').status_code, 404)

    def test_migrated_recipient_denied(self):
        self.assertEqual(self.share().status_code, 201)
        self.app.state.users['bob']['tenant'] = 'south'
        self.assertEqual(self.read('bob').status_code, 404)

    def test_migrated_owner_denied(self):
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.read('alice').status_code, 404)

    def test_bare_username_denied(self):
        self.assertEqual(self.client.get('/documents/c', headers={'Authorization': 'carol'}).status_code, 401)

    def test_bare_admin_denied(self):
        self.assertEqual(self.client.get('/admin/inventory', headers={'Authorization': 'admin'}).status_code, 401)

    def test_valid_bearer_scheme_is_case_insensitive(self):
        self.assertEqual(self.client.get('/documents/a', headers={'Authorization': 'bearer fixture-alice'}).status_code, 200)

    def test_live_share_and_owner_reads(self):
        self.assertEqual(self.read('alice').status_code, 200)
        self.assertEqual(self.read('bob').status_code, 404)
        self.assertEqual(self.read('carol').status_code, 404)
        self.assertEqual(self.share().status_code, 201)
        self.assertEqual(self.read('bob').json()['text'], 'Synthetic alpha')
        self.assertEqual(self.read('alice').status_code, 200)

    def test_revocation_and_no_resharing(self):
        share_id = self.share().json()['id']
        self.assertEqual(self.share(recipient='admin', owner='bob').status_code, 403)
        self.assertEqual(self.client.delete(f'/shares/{share_id}', headers=auth('bob')).status_code, 403)
        self.assertEqual(self.read('bob').status_code, 200)
        self.assertEqual(self.client.delete(f'/shares/{share_id}', headers=auth('alice')).status_code, 204)
        self.assertEqual(self.read('bob').status_code, 404)
        self.assertEqual(self.read('alice').status_code, 200)

    def test_invalid_share_targets_and_expiry(self):
        for recipient in ('carol', 'missing'):
            self.assertEqual(self.share(recipient=recipient).status_code, 422)
        self.assertEqual(self.client.post('/documents/a/shares', headers=auth('alice'),
                         json={'recipient': 'bob', 'expires_at': time() - 60}).status_code, 422)
        self.assertEqual(self.app.state.shares, [])

    def test_migrated_owner_cannot_share_or_revoke(self):
        share_id = self.share().json()['id']
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.share().status_code, 403)
        self.assertEqual(self.client.delete(f'/shares/{share_id}', headers=auth('alice')).status_code, 403)

    def test_inventory_uses_current_tenant_and_role(self):
        self.assertEqual(self.client.get('/admin/inventory', headers=auth('alice')).status_code, 403)
        self.assertEqual({d['id'] for d in self.client.get('/admin/inventory', headers=auth('admin')).json()}, {'a', 'b'})
        self.assertEqual(self.read('admin').status_code, 404)
        self.app.state.users['admin']['tenant'] = 'south'
        self.assertEqual([d['id'] for d in self.client.get('/admin/inventory', headers=auth('admin')).json()], ['c'])

    def test_authentication_and_missing_resources(self):
        for headers in ({}, {'Authorization': 'Bearer fixture-missing'},
                        {'Authorization': 'Basic fixture-alice'},
                        {'Authorization': 'Bearer alice'}):
            self.assertEqual(self.client.get('/documents/a', headers=headers).status_code, 401)
        self.assertEqual(self.read('alice', 'missing').status_code, 404)
        self.assertEqual(self.client.delete('/shares/99', headers=auth('alice')).status_code, 404)


if __name__ == '__main__':
    unittest.main()
