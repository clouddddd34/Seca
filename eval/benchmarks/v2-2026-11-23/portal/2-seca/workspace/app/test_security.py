"""Bounded local security controls; each test uses an isolated application."""
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
        response = self.client.post('/login', data={
            'username': name, 'password': 'fixture-' + name,
        }, headers={'Origin': 'http://testserver'})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/tickets')
        return self.client.cookies.get('session')

    def test_anonymous_and_public_routes(self):
        for path in ('/', '/help', '/login'):
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ('/tickets', '/tickets/a', '/admin/export'):
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.post('/logout').status_code, 401)
        self.assertEqual(self.app.state.sessions, {})

    def test_ownership_and_tenant_matrix(self):
        for name, own in (('alice', 'a'), ('bob', 'b'), ('carol', 'c')):
            self.login(name)
            listing = self.client.get('/tickets')
            self.assertEqual(listing.status_code, 200)
            for key in ('a', 'b', 'c'):
                response = self.client.get('/tickets/' + key)
                self.assertEqual(response.status_code, 200 if key == own else 404)
                text = self.app.state.tickets[key]['text']
                self.assertEqual(text in listing.text, key == own)
                self.assertEqual(text in response.text, key == own)
            self.assertEqual(self.client.get('/tickets/missing').status_code, 404)
            self.assertEqual(self.client.get('/admin/export').status_code, 403)

    def test_existing_session_tracks_tenant_migration(self):
        token = self.login('alice')
        self.assertEqual(self.client.get('/tickets/a').status_code, 200)
        self.app.state.users['alice']['tenant'] = 'south'
        self.assertEqual(self.client.cookies.get('session'), token)
        self.assertNotIn('Synthetic Alice ticket', self.client.get('/tickets').text)
        self.assertEqual(self.client.get('/tickets/a').status_code, 404)
        self.assertEqual(self.client.get('/tickets/c').status_code, 404)
        self.app.state.users['alice']['tenant'] = 'north'
        self.assertEqual(self.client.get('/tickets/a').status_code, 200)

    def test_admin_export_current_tenant_and_role(self):
        self.login('admin')
        self.assertEqual(self.client.get('/admin/export').json(), [
            self.app.state.tickets['a'], self.app.state.tickets['b']])
        self.assertEqual(self.client.get('/tickets/a').status_code, 404)
        self.app.state.users['admin']['tenant'] = 'south'
        self.assertEqual(self.client.get('/admin/export').json(), [self.app.state.tickets['c']])
        self.app.state.users['admin']['role'] = 'member'
        self.assertEqual(self.client.get('/admin/export').status_code, 403)

    def test_login_origin_and_credentials_preserve_state(self):
        token = self.login('alice')
        before = {k: dict(v) for k, v in self.app.state.sessions.items()}
        for origin in (None, 'http://foreign.invalid', 'http://testserver.foreign.invalid'):
            response = self.client.post('/login', data={
                'username': 'bob', 'password': 'fixture-bob'},
                headers={} if origin is None else {'Origin': origin})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(self.app.state.sessions, before)
        response = self.client.post('/login', data={'username': 'alice', 'password': ''},
                                    headers={'Origin': 'http://testserver'})
        self.assertEqual(response.status_code, 401)
        self.assertEqual(self.app.state.sessions, before)
        self.assertEqual(self.client.cookies.get('session'), token)
        self.assertEqual(self.client.get('/tickets/a').status_code, 200)

    def test_rotation_and_cookie_controls(self):
        old = self.login('alice')
        old_csrf = self.app.state.sessions[old]['csrf']
        new = self.login('bob')
        self.assertNotEqual(old, new)
        self.assertNotIn(old, self.app.state.sessions)
        self.assertNotEqual(old_csrf, self.app.state.sessions[new]['csrf'])
        self.assertEqual(self.client.get('/tickets/b').status_code, 200)
        with TestClient(self.app, follow_redirects=False) as replay:
            self.assertEqual(replay.get('/tickets', headers={'Cookie': 'session=' + old}).status_code, 401)
        cookie = next(iter(self.client.cookies.jar))
        self.assertIn('HttpOnly', cookie._rest)
        self.assertEqual(cookie._rest['SameSite'], 'strict')
        self.assertEqual(cookie.path, '/')

    def test_logout_csrf_and_invalidation(self):
        old = self.login('bob')
        other_csrf = self.app.state.sessions[old]['csrf']
        token = self.login('alice')
        csrf = self.app.state.sessions[token]['csrf']
        self.assertIn('value="' + csrf + '"', self.client.get('/tickets').text)
        for fields in ({}, {'csrf': 'invalid'}, {'csrf': other_csrf}):
            self.assertEqual(self.client.post('/logout', data=fields).status_code, 403)
            self.assertIn(token, self.app.state.sessions)
            self.assertEqual(self.client.get('/tickets/a').status_code, 200)
        response = self.client.post('/logout', data={'csrf': csrf})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/')
        self.assertNotIn(token, self.app.state.sessions)
        self.assertIsNone(self.client.cookies.get('session'))
        self.assertEqual(self.client.get('/tickets').status_code, 401)
        self.assertEqual(self.client.get('/tickets', headers={'Cookie': 'session=' + token}).status_code, 401)

    def test_literal_search_ticket_text_and_headers(self):
        self.login('alice')
        payload = '<script>alert("synthetic")</script><img src=x onerror=alert(1)>&'
        self.app.state.tickets['a']['text'] = payload
        for response in (self.client.get('/tickets', params={'q': payload}),
                         self.client.get('/tickets/a')):
            self.assertEqual(response.status_code, 200)
            self.assertIn(escape(payload), response.text)
            self.assertNotIn(payload, response.text)
            self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertEqual(response.headers['content-security-policy'],
                             "default-src 'none'; form-action 'self'; frame-ancestors 'none'")


if __name__ == '__main__':
    unittest.main()
