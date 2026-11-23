import json
from pathlib import Path

units = []
for surface in ['create', 'read', 'pay', 'refund', 'wallet']:
    for category, boundary in [('A07', 'caller to account'), ('A01', 'account isolation')]:
        units.append(dict(id=f'{surface}-{category}', surface=surface, boundary=boundary,
                          owasp_category=category + ':2025', status='planned',
                          reviewed_paths=[], checks=[], finding_fingerprints=[], unresolved=[]))
for surface, category, boundary in [
    ('create', 'A05', 'input to stored quantity'),
    ('pay', 'A06', 'customer to charge and coupon policy'),
    ('refund', 'A06', 'customer to credit policy'),
    ('pay', 'A10', 'failed requests to saved state'),
    ('refund', 'A10', 'failed requests to saved state'),
    ('docs', 'A02', 'anonymous to schema'),
    ('dependencies', 'A03', 'third-party code'),
    ('credentials', 'A04', 'fixture credentials'),
    ('serialization', 'A08', 'input to executable behavior'),
    ('logging', 'A09', 'security events to monitoring'),
    ('concurrency', 'A06', 'parallel requests to shared state'),
]:
    units.append(dict(id=f'{surface}-{category}', surface=surface, boundary=boundary,
                      owasp_category=category + ':2025', status='planned',
                      reviewed_paths=[], checks=[], finding_fingerprints=[], unresolved=[]))
Path('security-audit/coverage.json').write_text(json.dumps(units, indent=2) + '\n')
