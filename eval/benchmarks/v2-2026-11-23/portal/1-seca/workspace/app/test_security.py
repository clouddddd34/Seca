"""Bounded local control checks; no live server or external requests."""
import unittest
from html import escape

from fastapi.testclient import TestClient
from app.app import create_app


class SecurityControls(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app, follow_redirects=False)
        self.addCleanup(self.client.close)

    def login(self, name):
        response = self.client.post('/login', headers={'Origin': 'http://testserver'},
                                    data={'username': name, 'password': 'fixture-' + name})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/tickets')
        return self.client.cookies['session']

    def test_anonymous_and_public_routes(self):
        for path in ['/', '/help', '/login']:
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ['/tickets', '/tickets/a', '/admin/export']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post('/logout').status_code, 401)

    def test_ticket_ownership_and_tenant_matrix(self):
        for name, own in [('alice', 'a'), ('bob', 'b'), ('carol', 'c')]:
            self.login(name)
            listing = self.client.get('/tickets')
            self.assertEqual(listing.status_code, 200)
            for key in ['a', 'b', 'c']:
                item = self.app.state.tickets[key]
                response = self.client.get('/tickets/' + key)
                self.assertEqual(response.status_code, 200 if key == own else 404)
                self.assertEqual(item['text'] in listing.text, key == own)
                self.assertEqual(item['text'] in response.text, key == own)
            self.assertEqual(self.client.get('/tickets/missing').status_code, 404)
            self.assertEqual(self.client.get('/admin/export').status_code, 403)

    def test_current_membership_after_migration(self):
        self.login('alice')
        original = dict(self.app.state.tickets['a'])
        self.assertEqual(self.client.get('/tickets/a').status_code, 200)
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertNotIn(original['text'], self.client.get('/tickets').text)
        for key in ['a', 'c']:
            self.assertEqual(self.client.get('/tickets/' + key).status_code, 404)
        self.assertEqual(self.app.state.tickets['a'], original)
        self.app.state.users['alice']['tenant'] = 'north'
        self.assertIn(original['text'], self.client.get('/tickets/a').text)

    def test_admin_export_current_tenant_and_role(self):
        self.login('admin')
        self.assertEqual(self.client.get('/admin/export').json(),
                         [self.app.state.tickets[k] for k in ['a', 'b']])
        self.assertEqual(self.client.get('/tickets/a').status_code, 404)
        self.app.state.users['admin']['tenant'] = 'south'
        self.assertEqual(self.client.get('/admin/export').json(), [self.app.state.tickets['c']])
        self.app.state.users['admin']['role'] = 'member'
        self.assertEqual(self.client.get('/admin/export').status_code, 403)

    def test_login_origin_and_rotation(self):
        for origin in [None, 'http://untrusted.invalid']:
            headers = {} if origin is None else {'Origin': origin}
            response = self.client.post('/login', headers=headers,
                                        data={'username': 'alice', 'password': 'fixture-alice'})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(self.app.state.sessions, {})
        old = self.login('alice')
        new = self.login('alice')
        self.assertNotEqual(old, new)
        self.assertNotIn(old, self.app.state.sessions)
        self.assertEqual(len(self.app.state.sessions), 1)
        self.assertEqual(self.client.get('/tickets').status_code, 200)
        self.client.cookies.set('session', old, domain='testserver.local', path='/')
        self.assertEqual(self.client.get('/tickets').status_code, 401)

    def test_logout_csrf_and_invalidation(self):
        token = self.login('alice')
        csrf = self.app.state.sessions[token]['csrf']
        self.assertIn(csrf, self.client.get('/tickets').text)
        for data in [{}, {'csrf': 'incorrect'}]:
            self.assertEqual(self.client.post('/logout', data=data).status_code, 403)
            self.assertIn(token, self.app.state.sessions)
            self.assertEqual(self.client.get('/tickets/a').status_code, 200)
        self.assertEqual(self.client.get('/logout').status_code, 405)
        self.assertIn(token, self.app.state.sessions)
        response = self.client.post('/logout', data={'csrf': csrf})
        self.assertEqual(response.status_code, 303)
        self.assertNotIn(token, self.app.state.sessions)
        self.assertNotIn('session', self.client.cookies)
        self.client.cookies.set('session', token, domain='testserver.local', path='/')
        self.assertEqual(self.client.get('/tickets/a').status_code, 401)

    def test_escaping_cookie_and_headers(self):
        response = self.client.post('/login', headers={'Origin': 'http://testserver'},
                                    data={'username': 'alice', 'password': 'fixture-alice'})
        self.assertEqual(response.status_code, 303)
        cookie = response.headers['set-cookie'].lower()
        self.assertIn('httponly', cookie)
        self.assertIn('samesite=strict', cookie)
        payload = '<script>alert("synthetic")</script>&'
        self.app.state.tickets['a']['text'] = payload
        for response in [self.client.get('/tickets', params={'q': payload}),
                         self.client.get('/tickets/a')]:
            self.assertEqual(response.status_code, 200)
            self.assertNotIn(payload, response.text)
            self.assertIn(escape(payload), response.text)
            self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertIn("default-src 'none'", response.headers['content-security-policy'])


if __name__ == '__main__':
    unittest.main()
