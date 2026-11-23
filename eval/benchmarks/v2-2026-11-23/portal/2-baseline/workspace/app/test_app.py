"""Bounded local checks: fresh app per test, no network services."""
import unittest
from html import escape

from fastapi.testclient import TestClient
from app.app import create_app


class PortalTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)
        self.logins = 0
        self.mutations = 0

    def login(self, name='alice', password=None, origin='http://testserver'):
        self.logins += 1
        self.mutations += 1
        self.assertLessEqual(self.logins, 10)
        self.assertLessEqual(self.mutations, 20)
        return self.client.post('/login', data={
            'username': name, 'password': password if password is not None else 'fixture-' + name
        }, headers={} if origin is None else {'Origin': origin}, follow_redirects=False)

    def logout(self, csrf=None):
        self.mutations += 1
        self.assertLessEqual(self.mutations, 20)
        return self.client.post('/logout', data={} if csrf is None else {'csrf': csrf}, follow_redirects=False)

    def migrate(self, name, tenant):
        self.mutations += 1
        self.assertLessEqual(self.mutations, 20)
        self.app.state.users[name]['tenant'] = tenant

    def test_public_and_anonymous_boundaries(self):
        for path in ['/', '/help', '/login']:
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ['/tickets', '/tickets/a', '/admin/export']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.logout().status_code, 401)
        self.client.cookies.set('session', 'unknown')
        self.assertEqual(self.client.get('/tickets').status_code, 401)

    def test_login_origin_and_invalid_credentials(self):
        for origin in [None, 'http://elsewhere.invalid']:
            self.assertEqual(self.login(origin=origin).status_code, 403)
        for password in ['', 'wrong', 'caf\u00e9', '\U0001f512']:
            self.assertEqual(self.login(password=password).status_code, 401)
        self.assertEqual(self.login(name='unknown').status_code, 401)
        self.assertEqual(self.app.state.sessions, {})
        self.assertEqual(self.login().status_code, 303)

    def test_ownership_and_tenant_matrix(self):
        for name, own in [('alice', 'a'), ('bob', 'b'), ('carol', 'c'), ('admin', None)]:
            self.assertEqual(self.login(name).status_code, 303)
            listing = self.client.get('/tickets')
            self.assertEqual(listing.status_code, 200)
            for key, ticket in self.app.state.tickets.items():
                self.assertEqual(self.client.get('/tickets/' + key).status_code, 200 if key == own else 404)
                self.assertEqual(ticket['text'] in listing.text, key == own)
            self.assertEqual(self.client.get('/tickets/missing').status_code, 404)
            self.assertEqual(self.client.get('/admin/export').status_code, 200 if name == 'admin' else 403)

    def test_membership_is_current_for_existing_session(self):
        self.login()
        token = self.client.cookies.get('session')
        self.migrate('alice', 'south')
        self.assertEqual(self.client.get('/tickets/a').status_code, 404)
        self.assertEqual(self.client.get('/tickets/c').status_code, 404)
        self.assertNotIn('Synthetic Alice ticket', self.client.get('/tickets').text)
        self.assertEqual(self.client.cookies.get('session'), token)
        self.migrate('alice', 'north')
        self.assertEqual(self.client.get('/tickets/a').status_code, 200)

    def test_admin_export_tracks_current_tenant(self):
        self.login('admin')
        self.assertEqual(self.client.get('/admin/export').json(), [self.app.state.tickets[k] for k in ['a', 'b']])
        self.migrate('admin', 'south')
        self.assertEqual(self.client.get('/admin/export').json(), [self.app.state.tickets['c']])

    def test_rotation_logout_csrf_and_replay(self):
        response = self.login()
        self.assertIn('HttpOnly', response.headers['set-cookie'])
        self.assertIn('SameSite=strict', response.headers['set-cookie'])
        old = self.client.cookies.get('session')
        old_csrf = self.app.state.sessions[old]['csrf']
        self.login()
        token = self.client.cookies.get('session')
        self.assertNotEqual(old, token)
        self.assertNotIn(old, self.app.state.sessions)
        self.assertEqual(self.client.get('/tickets', headers={'Cookie': 'session=' + old}).status_code, 401)
        for csrf in [None, '', 'wrong', 'caf\u00e9', '\U0001f512', old_csrf]:
            self.assertEqual(self.logout(csrf).status_code, 403)
            self.assertIn(token, self.app.state.sessions)
        csrf = self.app.state.sessions[token]['csrf']
        self.assertIn(csrf, self.client.get('/tickets').text)
        response = self.logout(csrf)
        self.assertEqual(response.status_code, 303)
        self.assertNotIn(token, self.app.state.sessions)
        self.assertIsNone(self.client.cookies.get('session'))
        self.assertEqual(self.client.get('/tickets', headers={'Cookie': 'session=' + token}).status_code, 401)

    def test_search_literal_and_response_controls(self):
        self.login()
        payload = '<script>alert("x")</script><img src=x onerror=alert(1)>&\''
        response = self.client.get('/tickets', params={'q': payload})
        self.assertEqual(response.status_code, 200)
        self.assertIn('<p>Search: ' + escape(payload) + '</p>', response.text)
        self.assertNotIn(payload, response.text)
        self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
        self.assertEqual(response.headers['cache-control'], 'no-store')
        self.assertEqual(response.headers['content-security-policy'], "default-src 'none'; form-action 'self'; frame-ancestors 'none'")


if __name__ == '__main__':
    unittest.main()
