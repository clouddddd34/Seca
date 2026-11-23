import sys
import unittest
from pathlib import Path
from time import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from app import create_app
from fastapi.testclient import TestClient


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def request(self, method, path, name='alice', **kwargs):
        headers = {} if name is None else {'Authorization': f'Bearer fixture-{name}'}
        return self.client.request(method, path, headers=headers, **kwargs)

    def grant(self):
        response = self.request('POST', '/documents/a/shares', json={
            'recipient': 'bob', 'expires_at': time() + 3600})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertEqual(self.app.state.shares[0]['recipient'], 'bob')
        return response.json()['id']

    def assert_read(self, name, doc='a'):
        response = self.request('GET', f'/documents/{doc}', name)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), self.app.state.documents[doc])

    def test_owner_migration_removes_read_access(self):
        self.assert_read('alice')
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.request('GET', '/documents/a').status_code, 404)

    def test_recipient_migration_removes_read_access(self):
        self.grant()
        self.assert_read('bob')
        self.app.state.users['bob']['tenant'] = 'south'
        self.assertEqual(self.request('GET', '/documents/a', 'bob').status_code, 404)

    def test_expired_share_removes_read_access(self):
        self.grant()
        self.assert_read('bob')
        self.app.state.shares[0]['expires_at'] = time() - 1
        self.assertEqual(self.request('GET', '/documents/a', 'bob').status_code, 404)
        self.assert_read('alice')

    def test_revocation_and_reshare_controls(self):
        share_id = self.grant()
        self.assert_read('bob')
        denied = self.request('POST', '/documents/a/shares', 'bob', json={
            'recipient': 'admin', 'expires_at': time() + 3600})
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertEqual(self.request('DELETE', f'/shares/{share_id}', 'bob').status_code, 403)
        self.assertFalse(self.app.state.shares[0]['revoked'])
        self.assertEqual(self.request('DELETE', f'/shares/{share_id}').status_code, 204)
        self.assertTrue(self.app.state.shares[0]['revoked'])
        self.assertEqual(self.request('GET', '/documents/a', 'bob').status_code, 404)
        self.assert_read('alice')

    def test_share_validation(self):
        for recipient, expires in [('carol', time()+3600), ('missing', time()+3600), ('bob', time()-1)]:
            response = self.request('POST', '/documents/a/shares', json={
                'recipient': recipient, 'expires_at': expires})
            self.assertEqual(response.status_code, 422)
            self.assertEqual(self.app.state.shares, [])

    def test_migrated_owner_cannot_mutate_shares(self):
        share_id = self.grant()
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.request('POST', '/documents/a/shares', json={
            'recipient': 'bob', 'expires_at': time()+3600}).status_code, 403)
        self.assertEqual(self.request('DELETE', f'/shares/{share_id}').status_code, 403)
        self.assertEqual(len(self.app.state.shares), 1)
        self.assertFalse(self.app.state.shares[0]['revoked'])

    def test_baseline_read_and_authentication(self):
        for name, doc in [('alice', 'a'), ('bob', 'b'), ('carol', 'c')]:
            self.assert_read(name, doc)
        for name in ['bob', 'carol', 'admin']:
            self.assertEqual(self.request('GET', '/documents/a', name).status_code, 404)
        for name in [None, 'unknown']:
            for method, path in [('GET', '/documents/a'), ('POST', '/documents/a/shares'),
                                 ('DELETE', '/shares/1'), ('GET', '/admin/inventory')]:
                kwargs = {'json': {'recipient': 'bob', 'expires_at': time()+3600}} if method == 'POST' else {}
                self.assertEqual(self.request(method, path, name, **kwargs).status_code, 401)
        self.assertEqual(self.app.state.shares, [])
        self.assertEqual(self.request('GET', '/documents/missing').status_code, 404)

    def test_inventory_role_and_current_tenant(self):
        for name in ['alice', 'bob', 'carol']:
            self.assertEqual(self.request('GET', '/admin/inventory', name).status_code, 403)
        response = self.request('GET', '/admin/inventory', 'admin')
        self.assertEqual(response.status_code, 200)
        self.assertEqual({d['id'] for d in response.json()}, {'a', 'b'})
        self.app.state.users['admin']['tenant'] = 'south'
        response = self.request('GET', '/admin/inventory', 'admin')
        self.assertEqual(response.status_code, 200)
        self.assertEqual({d['id'] for d in response.json()}, {'c'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
