"""Create the initial audit ledger, before runtime verification."""
import json
from pathlib import Path

surfaces = [
    ('home', 'GET /', 'anonymous to static HTML', 'A05'),
    ('help', 'GET /help', 'anonymous to static HTML', 'A05'),
    ('login_form', 'GET /login', 'anonymous to login form', 'A05'),
    ('login_origin', 'POST /login', 'cross-origin to session creation', 'A01'),
    ('login_session', 'POST /login', 'anonymous to authenticated session', 'A07'),
    ('tokens', 'POST /login', 'client to session secrets', 'A04'),
    ('list', 'GET /tickets', 'user to other owner or tenant', 'A01'),
    ('detail', 'GET /tickets/{ticket_id}', 'user to other owner or tenant', 'A01'),
    ('export', 'GET /admin/export', 'member to admin and tenant to other tenant', 'A01'),
    ('search', 'GET /tickets?q=', 'query to HTML', 'A05'),
    ('logout', 'POST /logout', 'cross-site to session invalidation', 'A01'),
    ('headers', 'HTTP middleware', 'client to response configuration', 'A02'),
    ('state', 'Login/logout and directory membership', 'client to trusted state', 'A06'),
    ('integrity', 'Application sinks', 'untrusted input to deserialization and side effects', 'A08'),
    ('logging', 'Login/logout', 'security events to operator', 'A09'),
    ('exceptions', 'HTTP request parsing and guards', 'invalid input to error handling', 'A10'),
    ('ssrf', 'Application sinks', 'untrusted input to outbound requests', 'A01'),
    ('advisories', 'Installed dependencies', 'dependency supply chain', 'A03'),
    ('fixtures', 'Local fixture configuration', 'local fixture to production assumptions', 'A02'),
]
units = [dict(id=f'app/app.py:{key}:{cat}', surface=surface, boundary=boundary,
              owasp_category=f'{cat}:2025', status='planned', reviewed_paths=[],
              checks=[], finding_fingerprints=[], unresolved=[])
         for key, surface, boundary, cat in surfaces]
Path('security-audit/coverage.json').write_text(json.dumps(units, indent=2)+'\n')
