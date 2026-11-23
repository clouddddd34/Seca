"""Bounded in-process audit checks; no external services or guessed credentials."""
import re
import unittest
from html import escape

from fastapi.testclient import TestClient
from app import create_app


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app)
        self.logins = self.mutations = 0

    def tearDown(self):
        self.client.close()
        self.assertLessEqual(self.logins, 10)
        self.assertLessEqual(self.mutations, 20)

    def post(self, path, **kwargs):
        self.mutations += 1
        if path == '/login':
            self.logins += 1
        return self.client.post(path, follow_redirects=False, **kwargs)

    def login(self, name):
        response = self.post('/login', data={'username': name, 'password': f'fixture-{name}'},
                             headers={'Origin': 'http://testserver'})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/tickets')
        return response

    def migrate(self, name, tenant):
        self.mutations += 1
        self.app.state.users[name]['tenant'] = tenant

    def test_public_and_anonymous_boundaries(self):
        for path in ['/', '/help', '/login']:
            self.assertEqual(self.client.get(path).status_code, 200)
        for path in ['/tickets', '/tickets/a', '/tickets/unknown', '/admin/export']:
            self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.post('/logout', data={'csrf': 'invalid'}).status_code, 401)
        for path in ['/docs', '/redoc', '/openapi.json']:
            self.assertEqual(self.client.get(path).status_code, 404)
        self.client.cookies.set('session', 'unrecognized')
        self.assertEqual(self.client.get('/tickets').status_code, 401)

    def test_owner_and_tenant_matrix(self):
        for name, own in [('alice', 'a'), ('bob', 'b'), ('carol', 'c'), ('admin', None)]:
            self.login(name)
            listing = self.client.get('/tickets')
            self.assertEqual(listing.status_code, 200)
            for key in ['a', 'b', 'c', 'unknown']:
                response = self.client.get('/tickets/' + key)
                self.assertEqual(response.status_code, 200 if key == own else 404)
                if key in ['a', 'b', 'c']:
                    self.assertEqual(f'href="/tickets/{key}"' in listing.text, key == own)
            if name != 'admin':
                self.assertEqual(self.client.get('/admin/export').status_code, 403)

    def test_membership_changes_apply_to_existing_session(self):
        self.login('alice')
        session = self.client.cookies.get('session')
        self.assertEqual(self.client.get('/tickets/a').status_code, 200)
        self.migrate('alice', 'south')
        listing = self.client.get('/tickets').text
        for key in ['a', 'b', 'c']:
            self.assertNotIn(f'href="/tickets/{key}"', listing)
            self.assertEqual(self.client.get('/tickets/' + key).status_code, 404)
        self.assertEqual(self.client.cookies.get('session'), session)
        self.migrate('alice', 'north')
        self.assertEqual(self.client.get('/tickets/a').status_code, 200)

    def test_admin_export_uses_current_tenant_and_role(self):
        self.login('admin')
        response = self.client.get('/admin/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual({t['owner'] for t in response.json()}, {'alice', 'bob'})
        self.migrate('admin', 'south')
        self.assertEqual({t['owner'] for t in self.client.get('/admin/export').json()}, {'carol'})
        self.assertEqual(self.client.get('/tickets/c').status_code, 404)
        self.app.state.users['admin']['role'] = 'member'
        self.mutations += 1
        self.assertEqual(self.client.get('/admin/export').status_code, 403)

    def test_login_origin_rotation_and_cookie_controls(self):
        fields = {'username': 'alice', 'password': 'fixture-alice'}
        for headers in [{}, {'Origin': 'http://untrusted.invalid'}]:
            self.assertEqual(self.post('/login', data=fields, headers=headers).status_code, 403)
            self.assertEqual(self.app.state.sessions, {})
        response = self.login('alice')
        cookie = response.headers['set-cookie'].lower()
        self.assertIn('httponly', cookie)
        self.assertIn('samesite=strict', cookie)
        old = self.client.cookies.get('session')
        old_csrf = self.app.state.sessions[old]['csrf']
        self.login('alice')
        new = self.client.cookies.get('session')
        self.assertNotEqual(old, new)
        self.assertNotEqual(old_csrf, self.app.state.sessions[new]['csrf'])
        self.assertNotIn(old, self.app.state.sessions)
        with TestClient(self.app) as replay:
            self.assertEqual(replay.get('/tickets', headers={'Cookie': f'session={old}'}).status_code, 401)

    def test_logout_csrf_and_replay(self):
        self.login('alice')
        token = self.client.cookies.get('session')
        html = self.client.get('/tickets').text
        csrf = re.search(r'name="csrf" value="([^"]+)"', html).group(1)
        for data in [{}, {'csrf': 'invalid'}]:
            self.assertEqual(self.post('/logout', data=data).status_code, 403)
            self.assertIn(token, self.app.state.sessions)
        self.assertEqual(self.client.get('/logout').status_code, 405)
        response = self.post('/logout', data={'csrf': csrf})
        self.assertEqual(response.status_code, 303)
        self.assertEqual(response.headers['location'], '/')
        self.assertNotIn(token, self.app.state.sessions)
        self.assertIsNone(self.client.cookies.get('session'))
        self.assertEqual(self.client.get('/tickets').status_code, 401)
        self.assertEqual(self.post('/logout', data={'csrf': csrf},
                                  headers={'Cookie': f'session={token}'}).status_code, 401)

    def test_literal_search_and_headers(self):
        self.login('alice')
        for payload in ['<script>alert(1)</script>', '<img/onerror=alert(1) src=x>',
                        '</p><svg onload=alert(1)>', '"\'&<>', '&lt;script&gt;', '普通文字']:
            response = self.client.get('/tickets', params={'q': payload})
            self.assertEqual(response.status_code, 200)
            self.assertIn('<p>Search: ' + escape(payload) + '</p>', response.text)
            self.assertNotIn('<script>', response.text)
            self.assertNotIn('<svg ', response.text)
            self.assertNotIn('<img/', response.text)
        for path in ['/', '/help', '/login', '/tickets', '/tickets/a']:
            response = self.client.get(path)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertEqual(response.headers['x-content-type-options'], 'nosniff')
            self.assertIn("default-src 'none'", response.headers['content-security-policy'])
            self.assertIn("frame-ancestors 'none'", response.headers['content-security-policy'])


if __name__ == '__main__':
    unittest.main()
