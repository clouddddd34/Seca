"""Bounded security verification; each test uses a fresh application."""
import sys
import unittest
from pathlib import Path
from html import escape
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'app'))
from app import create_app
from fastapi.testclient import TestClient

class PortalChecks(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = TestClient(self.app, raise_server_exceptions=False)
        self.logins = self.mutations = 0
    def tearDown(self):
        self.assertLessEqual(self.logins, 10)
        self.assertLessEqual(self.mutations, 20)
        self.client.close()
    def post(self, path, **kwargs):
        self.mutations += 1
        if path == '/login': self.logins += 1
        return self.client.post(path, follow_redirects=False, **kwargs)
    def login(self, name):
        r = self.post('/login', data={'username':name,'password':'fixture-'+name}, headers={'Origin':'http://testserver'})
        self.assertEqual(r.status_code, 303)
        return self.client.cookies.get('session')
    def test_public_and_anonymous_boundaries(self):
        for path in ['/', '/help', '/login']:
            r = self.client.get(path)
            self.assertEqual(r.status_code, 200)
            self.assertEqual(r.headers['Cache-Control'], 'no-store')
            self.assertIn("frame-ancestors 'none'", r.headers['Content-Security-Policy'])
            self.assertEqual(r.headers['X-Content-Type-Options'], 'nosniff')
        for path in ['/tickets','/tickets/a','/tickets/absent','/admin/export','/tickets%2Fa','/admin%2Fexport']:
            self.assertEqual(self.client.get(path).status_code,401,path)
        self.assertEqual(self.post('/logout',data={'csrf':'wrong'}).status_code,401)
        for path in ['/docs','/redoc','/openapi.json']:
            self.assertEqual(self.client.get(path).status_code,404)
    def test_owner_tenant_matrix(self):
        for name, own in [('alice','a'),('bob','b'),('carol','c'),('admin',None)]:
            self.login(name)
            listing=self.client.get('/tickets').text
            for key, ticket in self.app.state.tickets.items():
                allowed=key == own
                self.assertEqual(self.client.get('/tickets/'+key).status_code,200 if allowed else 404)
                self.assertEqual(ticket['text'] in listing, allowed)
            self.assertEqual(self.client.get('/tickets/missing').status_code,404)
            self.assertEqual(self.client.get('/admin/export').status_code,200 if name=='admin' else 403)
    def test_current_membership_and_export(self):
        self.login('alice')
        self.assertEqual(self.client.get('/tickets/a').status_code,200)
        self.app.state.users['alice']['tenant']='south'; self.mutations+=1
        self.assertEqual(self.client.get('/tickets/a').status_code,404)
        self.assertEqual(self.client.get('/tickets/c').status_code,404)
        self.assertNotIn('Synthetic Alice ticket',self.client.get('/tickets').text)
        self.login('admin')
        self.assertEqual({x['tenant'] for x in self.client.get('/admin/export').json()},{'north'})
        self.app.state.users['admin']['tenant']='south'; self.mutations+=1
        self.assertEqual(self.client.get('/admin/export').json(),[self.app.state.tickets['c']])
        self.app.state.users['admin']['role']='member'; self.mutations+=1
        self.assertEqual(self.client.get('/admin/export').status_code,403)
    def test_rotation_csrf_logout(self):
        old=self.login('alice'); new=self.login('alice')
        self.assertNotEqual(old,new); self.assertNotIn(old,self.app.state.sessions)
        self.assertEqual(self.client.get('/tickets',headers={'Cookie':'session='+old}).status_code,401)
        for fields in [{},{'csrf':'wrong'}]:
            self.assertEqual(self.post('/logout',data=fields).status_code,403)
            self.assertIn(new,self.app.state.sessions)
        csrf=self.app.state.sessions[new]['csrf']
        self.assertIn(csrf,self.client.get('/tickets').text)
        self.assertEqual(self.post('/logout',data={'csrf':csrf}).status_code,303)
        self.assertNotIn(new,self.app.state.sessions)
        self.assertEqual(self.client.get('/tickets',headers={'Cookie':'session='+new}).status_code,401)
    def test_origin_and_cookie_controls(self):
        for origin in [None,'https://evil.invalid','http://testserver.evil.invalid']:
            headers={} if origin is None else {'Origin':origin}
            r=self.post('/login',data={'username':'alice','password':'fixture-alice'},headers=headers)
            self.assertEqual(r.status_code,403)
        self.assertEqual(self.app.state.sessions,{})
        r=self.post('/login',data={'username':'alice','password':'fixture-alice'},headers={'Origin':'http://testserver'})
        self.assertEqual(r.status_code,303)
        for attr in ['HttpOnly','SameSite=strict','Path=/']:
            self.assertIn(attr,r.headers['set-cookie'])
        self.assertEqual(r.headers['location'],'/tickets')
    def test_literal_search(self):
        self.login('alice')
        for value in ['<script>alert(1)</script>','<img/onerror=alert(1)>','</p><svg onload=alert(1)>','"\'&<>']:
            r=self.client.get('/tickets',params={'q':value})
            self.assertEqual(r.status_code,200)
            self.assertIn('<p>Search: '+escape(value)+'</p>',r.text)
            self.assertNotIn(value,r.text)
    def test_malformed_input_is_request_local(self):
        r=self.post('/login',content=b'\xff',headers={'Origin':'http://testserver'})
        self.assertEqual(r.status_code,500)
        self.assertEqual(r.text,'Internal Server Error')
        self.assertEqual(self.app.state.sessions,{})
        token=self.login('alice')
        r=self.post('/logout',data={'csrf':'\u00e9'})
        self.assertEqual(r.status_code,500)
        self.assertIn(token,self.app.state.sessions)
        self.assertEqual(self.client.get('/tickets/a').status_code,200)

if __name__ == '__main__': unittest.main(verbosity=2)
