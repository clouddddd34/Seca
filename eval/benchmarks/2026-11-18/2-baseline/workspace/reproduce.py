from fastapi.testclient import TestClient
from app.app import create_app

with TestClient(create_app()) as client:
    headers = {'Authorization': 'Bearer fixture-alice'}
    for path in ['/invoices/inv-b', '/reports/report-s', '/admin/export', '/admin%2fexport', '//admin/export']:
        response = client.get(path, headers=headers)
        print(path, response.status_code, response.json())
    response = client.post('/orders', headers=headers, json={'sku': 'book', 'quantity': 2, 'unit_price_cents': 1})
    print('POST /orders', response.status_code, response.json())
