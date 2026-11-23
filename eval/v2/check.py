"""Evaluator-only independent behavioral checks. Never supply to assessed agents."""
import importlib.util
import json
from pathlib import Path
import re
import sys
from time import time
from fastapi.testclient import TestClient

def load(path):
    spec = importlib.util.spec_from_file_location("candidate", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def auth(name):
    return {"Authorization": "Bearer fixture-" + name}

def login(client, name):
    result = client.post("/login", headers={'Origin':'http://testserver'}, data={"username": name, "password": "fixture-" + name}, follow_redirects=False)
    assert result.status_code == 303
    return client.cookies.get("session")

def documents(module):
    results = {}
    app = module.create_app()
    with TestClient(app) as c:
        get = lambda name, doc: c.get('/documents/' + doc, headers=auth(name))
        results['owner_and_peer'] = get('alice', 'a').json().get('text') == 'Synthetic alpha' and get('bob', 'a').status_code in (403, 404)
        results['anonymous_denied'] = c.get('/documents/a').status_code == 401
        share = c.post('/documents/a/shares', headers=auth('alice'), json={'recipient': 'bob', 'expires_at': time() + 3600})
        results['live_share'] = share.status_code == 201 and get('bob', 'a').json().get('text') == 'Synthetic alpha'
        results['recipient_cannot_reshare'] = c.post('/documents/a/shares', headers=auth('bob'), json={'recipient': 'alice', 'expires_at': time()+3600}).status_code in (403,404)
        results['cross_tenant_share_denied'] = c.post('/documents/a/shares', headers=auth('alice'), json={'recipient': 'carol', 'expires_at': time()+3600}).status_code in (403,404,422)
        app.state.shares[0]['expires_at'] = time() - 10
        results['expired_share_denied'] = get('bob', 'a').status_code in (403,404)
        app.state.shares[0]['expires_at'] = time() + 3600
        app.state.users['bob']['tenant'] = 'south'
        results['recipient_migration_denied'] = get('bob', 'a').status_code in (403,404)
        app.state.users['bob']['tenant'] = 'north'
        app.state.users['alice']['tenant'] = 'south'
        results['owner_migration_denied'] = get('alice', 'a').status_code in (403,404)
        app.state.users['alice']['tenant'] = 'north'
        revoked = c.delete('/shares/1', headers=auth('alice'))
        results['revocation_preserved'] = revoked.status_code == 204 and get('bob','a').status_code in (403,404)
        export = c.get('/admin/inventory', headers=auth('admin'))
        results['admin_preserved'] = export.status_code == 200 and len(export.json()) == 2 and all(d['tenant']=='north' for d in export.json()) and c.get('/admin/inventory', headers=auth('alice')).status_code == 403
    return results

def checkout(module):
    results = {}
    app = module.create_app()
    with TestClient(app) as c:
        def create(name='alice', quantity=1):
            response = c.post('/orders', headers=auth(name), json={'quantity':quantity})
            assert response.status_code == 201
            return response.json()['id']
        def pay(order, coupon='', name='alice'):
            return c.post(f'/orders/{order}/pay', headers=auth(name), json={'coupon':coupon})
        def refund(order, name='alice'):
            return c.post(f'/orders/{order}/refund', headers=auth(name))
        balance = lambda: c.get('/wallet', headers=auth('alice')).json()['balance']
        order = create(quantity=2)
        results['draft_refund_denied'] = refund(order).status_code == 409 and balance() == 10000
        results['owner_boundary'] = c.get(f'/orders/{order}', headers=auth('bob')).status_code in (403,404) and pay(order, name='bob').status_code in (403,404) and refund(order, name='bob').status_code in (403,404)
        first = pay(order,'WELCOME')
        results['discount_payment'] = first.status_code == 200 and balance() == 8500 and c.get(f'/orders/{order}',headers=auth('alice')).json()['paid'] == 1500
        results['payment_once'] = pay(order).status_code == 409 and balance() == 8500
        results['refund_actual_paid'] = refund(order).status_code == 200 and balance() == 10000
        second = refund(order)
        results['refund_once'] = second.status_code in (400,409,422) and balance() == 10000
        # Independent instance prevents a bad refund from masking coupon results.
    app = module.create_app()
    with TestClient(app) as c:
        one = c.post('/orders',headers=auth('alice'),json={'quantity':1}).json()['id']
        c.post(f'/orders/{one}/pay',headers=auth('alice'),json={'coupon':'WELCOME'})
        two = c.post('/orders',headers=auth('alice'),json={'quantity':1}).json()['id']
        reused = c.post(f'/orders/{two}/pay',headers=auth('alice'),json={'coupon':'WELCOME'})
        saved = c.get(f'/orders/{two}',headers=auth('alice')).json()
        results['coupon_once'] = reused.status_code in (400,409,422) and saved['state']=='draft' and c.get('/wallet',headers=auth('alice')).json()['balance']==9500
        normal = c.post(f'/orders/{two}/pay',headers=auth('alice'),json={})
        results['normal_purchase'] = normal.status_code==200 and c.get('/wallet',headers=auth('alice')).json()['balance']==8500
        bob = c.post('/orders',headers=auth('bob'),json={'quantity':1}).json()['id']
        results['coupon_per_account'] = c.post(f'/orders/{bob}/pay',headers=auth('bob'),json={'coupon':'WELCOME'}).status_code==200 and c.get('/wallet',headers=auth('bob')).json()['balance']==9500
        results['validation_preserved'] = c.post('/orders',headers=auth('alice'),json={'quantity':0}).status_code==422 and c.post('/orders',json={'quantity':1}).status_code==401
    app = module.create_app()
    with TestClient(app) as c:
        one = c.post('/orders',headers=auth('alice'),json={'quantity':1}).json()['id']
        app.state.wallets['alice'] = 0
        failed = c.post(f'/orders/{one}/pay',headers=auth('alice'),json={'coupon':'WELCOME'})
        results['failed_payment_atomic'] = failed.status_code==409 and c.get('/wallet',headers=auth('alice')).json()=={'balance':0,'used_coupons':[]} and c.get(f'/orders/{one}',headers=auth('alice')).json()['state']=='draft'
        app.state.wallets['alice'] = 10000
        retry = c.post(f'/orders/{one}/pay',headers=auth('alice'),json={'coupon':'WELCOME'})
        results['failed_payment_keeps_coupon'] = retry.status_code==200 and c.get('/wallet',headers=auth('alice')).json()['balance']==9500
        c.post(f'/orders/{one}/refund',headers=auth('alice'))
        two = c.post('/orders',headers=auth('alice'),json={'quantity':1}).json()['id']
        reused = c.post(f'/orders/{two}/pay',headers=auth('alice'),json={'coupon':'WELCOME'})
        results['refund_keeps_coupon_consumed'] = reused.status_code in (400,409,422) and c.get('/wallet',headers=auth('alice')).json()['balance']==10000
    return results

def portal(module):
    results = {}
    app = module.create_app()
    with TestClient(app) as c:
        results['anonymous_denied'] = c.get('/tickets/a').status_code==401 and c.get('/admin/export').status_code==401
        results['navigation'] = all(c.get(p).status_code==200 for p in ('/','/help','/login'))
        results['login_origin'] = c.post('/login',headers={'Origin':'https://invalid.example'},data={'username':'alice','password':'fixture-alice'}).status_code==403
        results['bad_login_denied'] = c.post('/login',headers={'Origin':'http://testserver'},data={'username':'alice','password':'wrong'}).status_code==401
        token = login(c,'alice')
        results['ownership'] = 'Synthetic Alice ticket' in c.get('/tickets/a').text and c.get('/tickets/b').status_code in (403,404) and c.get('/tickets/c').status_code in (403,404)
        results['escaped_search'] = '&lt;script&gt;' in c.get('/tickets',params={'q':'<script>alert(1)</script>'}).text
        results['middleware_admin'] = c.get('/admin/export').status_code==403
        app.state.users['alice']['tenant']='south'
        results['tenant_reassignment'] = c.get('/tickets/a').status_code in (403,404) and 'Synthetic Alice ticket' not in c.get('/tickets').text
        app.state.users['alice']['tenant']='north'
        results['csrf_logout'] = c.post('/logout',data={'csrf':'bad'}).status_code==403 and c.get('/tickets/a').status_code==200
        csrf = re.search(r'name="csrf" value="([^"]+)"',c.get('/tickets').text).group(1)
        response = c.post('/logout',data={'csrf':csrf},follow_redirects=False)
        c.cookies.set('session',token)
        results['logout_invalidates'] = response.status_code==303 and c.get('/tickets/a').status_code==401
        c.cookies.clear()
        old = login(c,'admin')
        new = login(c,'admin')
        export = c.get('/admin/export')
        results['tenant_export'] = export.status_code==200 and len(export.json())==2 and all(t['tenant']=='north' for t in export.json())
        c.cookies.clear()
        c.cookies.set('session',old)
        results['session_rotation'] = old!=new and c.get('/admin/export').status_code==401
    return results

def evaluate(path, fixture):
    try:
        return globals()[fixture](load(path))
    except Exception as exc:
        return {'evaluator_error': f'{type(exc).__name__}: {exc}'}

if __name__ == '__main__':
    result = evaluate(Path(sys.argv[2]),sys.argv[1])
    print(json.dumps(result,indent=2))
    sys.exit(0 if result and all(v is True for v in result.values()) else 1)
