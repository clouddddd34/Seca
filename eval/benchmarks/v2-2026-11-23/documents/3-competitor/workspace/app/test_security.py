import unittest
from time import time
from unittest.mock import patch
from fastapi.testclient import TestClient
from app import create_app

class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def headers(self, user):
        return {'Authorization': 'Bearer fixture-' + user}

    def read(self, user, doc='a'):
        return self.client.get('/documents/' + doc, headers=self.headers(user))

    def share(self, recipient='bob', user='alice', doc='a', expiry=None):
        return self.client.post('/documents/' + doc + '/shares', headers=self.headers(user),
                                json={'recipient': recipient, 'expires_at': expiry or time()+3600})

    def test_expired_share_denied(self):
        self.assertEqual(self.share().status_code, 201)
        self.assertEqual(self.read('bob').status_code, 200)
        self.app.state.shares[0]['expires_at'] = time()-1
        self.assertEqual(self.read('bob').status_code, 404)

    def test_expiry_boundary_denied(self):
        self.assertEqual(self.share().status_code, 201)
        expiry = self.app.state.shares[0]['expires_at']
        with patch('app.time', return_value=expiry):
            self.assertEqual(self.read('bob').status_code, 404)

    def test_migrated_recipient_denied(self):
        self.assertEqual(self.share().status_code, 201)
        self.assertEqual(self.read('bob').status_code, 200)
        self.app.state.users['bob']['tenant'] = 'south'
        self.assertEqual(self.read('bob').status_code, 404)

    def test_migrated_owner_denied(self):
        self.assertEqual(self.read('alice').status_code, 200)
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.read('alice').status_code, 404)

    def test_owner_and_live_share_and_revocation(self):
        self.assertEqual(self.read('alice').status_code, 200)
        self.assertEqual(self.read('bob').status_code, 404)
        self.assertEqual(self.read('carol').status_code, 404)
        self.assertEqual(self.read('admin').status_code, 404)
        share = self.share().json()
        self.assertEqual(self.read('bob').status_code, 200)
        self.assertEqual(self.client.delete('/shares/'+str(share['id']), headers=self.headers('alice')).status_code, 204)
        self.assertEqual(self.read('bob').status_code, 404)
        self.assertEqual(self.read('alice').status_code, 200)

    def test_multiple_grants_live_one_suffices(self):
        self.assertEqual(self.share().status_code, 201)
        self.app.state.shares[0]['expires_at'] = time()-1
        self.assertEqual(self.share().status_code, 201)
        self.assertEqual(self.read('bob').status_code, 200)

    def test_share_controls(self):
        for recipient in ('carol', 'missing'):
            self.assertEqual(self.share(recipient).status_code, 422)
        self.assertEqual(self.share(expiry=time()-1).status_code, 422)
        self.assertEqual(self.share().status_code, 201)
        self.assertEqual(self.share('admin', user='bob').status_code, 403)
        self.assertEqual(self.client.delete('/shares/1', headers=self.headers('bob')).status_code, 403)
        self.assertEqual(self.client.delete('/shares/1', headers=self.headers('carol')).status_code, 403)
        self.assertEqual(self.read('bob').status_code, 200)
        self.assertEqual(len(self.app.state.shares), 1)

    def test_migrated_owner_mutations_denied(self):
        self.assertEqual(self.share().status_code, 201)
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.share().status_code, 403)
        self.assertEqual(self.client.delete('/shares/1', headers=self.headers('alice')).status_code, 403)
        self.assertFalse(self.app.state.shares[0]['revoked'])

    def test_inventory_scope(self):
        self.assertEqual(self.client.get('/admin/inventory', headers=self.headers('bob')).status_code, 403)
        def ids():
            return {d['id'] for d in self.client.get('/admin/inventory', headers=self.headers('admin')).json()}
        self.assertEqual(ids(), {'a','b'})
        self.app.state.users['admin']['tenant'] = 'south'
        self.assertEqual(ids(), {'c'})

    def test_unauthenticated_and_missing(self):
        for headers in ({}, self.headers('unknown')):
            for method, url, kwargs in [('get','/documents/a',{}), ('get','/documents/missing',{}),
                ('get','/admin/inventory',{}), ('post','/documents/a/shares',{'json':{'recipient':'bob','expires_at':time()+3600}}),
                ('delete','/shares/1',{})]:
                self.assertEqual(self.client.request(method,url,headers=headers,**kwargs).status_code,401)
        self.assertEqual(self.read('alice','missing').status_code,404)
        self.assertEqual(self.client.delete('/shares/999',headers=self.headers('alice')).status_code,404)

if __name__ == '__main__':
    unittest.main(verbosity=2)
