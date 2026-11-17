"""Seed recon ledger before testing. Workspace-local audit utility."""
import json
from pathlib import Path

surfaces = ['GET /', 'GET /health', 'GET /me', 'GET /invoices/{invoice_id}',
            'GET /reports/{report_id}', 'GET /catalog', 'POST /orders',
            'GET /orders', 'GET /admin/export', 'GET /openapi.json']
units = []
for i, surface in enumerate(surfaces):
    units.append(dict(id=f'route-{i}-access', surface=surface,
                      boundary='caller to API resource', owasp_category='A01:2025',
                      status='planned', reviewed_paths=[], checks=[],
                      finding_fingerprints=[], unresolved=[]))
for category in range(2, 11):
    units.append(dict(id=f'application-A{category:02}', surface='Application configuration and request processing',
                      boundary='untrusted request to application state', owasp_category=f'A{category:02}:2025',
                      status='planned', reviewed_paths=[], checks=[],
                      finding_fingerprints=[], unresolved=[]))
Path('security-audit/coverage.json').write_text(json.dumps(units, indent=2))
