"""Bounded local authorization regressions; each test gets independent state."""
import sys
import unittest
from pathlib import Path
from time import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from app import create_app
from fastapi.testclient import TestClient


def auth(name):
    return {'Authorization': 'Bearer fixture-' + name}


class AccessTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

    def share(self, recipient='bob', doc='a', owner='alice'):
        response = self.client.post(f'/documents/{doc}/shares', headers=auth(owner),
                                    json={'recipient': recipient, 'expires_at': time() + 3600})
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['id']

    def read(self, name, doc='a'):
        return self.client.get(f'/documents/{doc}', headers=auth(name))

    def test_expired_share_denied(self):
        self.share()
        self.assertEqual(self.read('bob').status_code, 200)
        self.app.state.shares[0]['expires_at'] = time() - 1
        self.assertEqual(self.read('bob').status_code, 404)
        self.assertEqual(self.read('alice').status_code, 200)

    def test_expiry_exact_boundary_denied(self):
        self.share()
        expiry = self.app.state.shares[0]['expires_at']
        with patch('app.time', return_value=expiry):
            self.assertEqual(self.read('bob').status_code, 404)

    def test_migrated_recipient_denied_and_return_restores_live_grant(self):
        self.share()
        self.assertEqual(self.read('bob').status_code, 200)
        self.app.state.users['bob']['tenant'] = 'south'
        self.assertEqual(self.read('bob').status_code, 404)
        self.app.state.users['bob']['tenant'] = 'north'
        self.assertEqual(self.read('bob').status_code, 200)

    def test_migrated_owner_denied_and_return_restores_ownership(self):
        self.assertEqual(self.read('alice').status_code, 200)
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.read('alice').status_code, 404)
        self.app.state.users['alice']['tenant'] = 'north'
        self.assertEqual(self.read('alice').status_code, 200)

    def test_revocation_and_fresh_share(self):
        share_id = self.share()
        self.assertEqual(self.client.delete(f'/shares/{share_id}', headers=auth('bob')).status_code, 403)
        self.assertFalse(self.app.state.shares[0]['revoked'])
        self.assertEqual(self.client.delete(f'/shares/{share_id}', headers=auth('alice')).status_code, 204)
        self.assertEqual(self.read('bob').status_code, 404)
        self.share()
        self.assertEqual(self.read('bob').status_code, 200)

    def test_unrelated_grant_cannot_authorize(self):
        self.share(recipient='admin')
        self.share(recipient='alice', doc='b', owner='bob')
        self.assertEqual(self.read('bob').status_code, 404)
        self.assertEqual(self.read('admin').status_code, 200)

    def test_sharing_controls(self):
        self.share()
        for owner, recipient, expiry, status in [
            ('bob','admin',time()+3600,403),
            ('alice','carol',time()+3600,422),
            ('alice','missing',time()+3600,422),
            ('alice','bob',time()-1,422),
        ]:
            with self.subTest(owner=owner, recipient=recipient, status=status):
                r = self.client.post('/documents/a/shares', headers=auth(owner),
                                     json={'recipient':recipient,'expires_at':expiry})
                self.assertEqual(r.status_code,status)
        self.assertEqual(len(self.app.state.shares),1)

    def test_migrated_owner_cannot_mutate(self):
        share_id = self.share()
        self.app.state.users['alice']['tenant'] = 'south'
        r = self.client.post('/documents/a/shares', headers=auth('alice'),
                             json={'recipient':'carol','expires_at':time()+3600})
        self.assertEqual(r.status_code,403)
        self.assertEqual(self.client.delete(f'/shares/{share_id}',headers=auth('alice')).status_code,403)
        self.assertEqual(len(self.app.state.shares),1)
        self.assertFalse(self.app.state.shares[0]['revoked'])

    def test_inventory_tracks_current_admin_tenant(self):
        self.assertEqual(self.client.get('/admin/inventory',headers=auth('alice')).status_code,403)
        self.assertEqual({d['id'] for d in self.client.get('/admin/inventory',headers=auth('admin')).json()},{'a','b'})
        self.app.state.users['admin']['tenant']='south'
        self.assertEqual({d['id'] for d in self.client.get('/admin/inventory',headers=auth('admin')).json()},{'c'})
        self.assertEqual(self.read('admin','c').status_code,404)

    def test_no_share_cross_tenant_and_unknown_documents_denied(self):
        for name,doc in [('bob','a'),('carol','a'),('alice','c'),('alice','missing')]:
            self.assertEqual(self.read(name,doc).status_code,404)

    def test_missing_and_invalid_credentials(self):
        for headers in ({},{'Authorization':'Bearer unknown'}):
            self.assertEqual(self.client.get('/documents/a',headers=headers).status_code,401)
            self.assertEqual(self.client.get('/admin/inventory',headers=headers).status_code,401)
            self.assertEqual(self.client.post('/documents/a/shares',headers=headers,json={'recipient':'bob','expires_at':time()+3600}).status_code,401)
            self.assertEqual(self.client.delete('/shares/1',headers=headers).status_code,401)
        self.assertEqual(self.app.state.shares,[])

    def test_malformed_inputs_and_docs(self):
        self.assertEqual(self.client.post('/documents/a/shares',headers=auth('alice'),json={'recipient':'bob','expires_at':'bad'}).status_code,422)
        self.assertEqual(self.client.delete('/shares/bad',headers=auth('alice')).status_code,422)
        self.assertEqual(self.client.get('/openapi.json').status_code,200)
        self.assertEqual(self.client.get('/docs').status_code,200)
        self.assertEqual(self.app.state.shares,[])

if __name__ == '__main__':
    unittest.main(verbosity=2)
