import json
from pathlib import Path
base = json.loads(Path('assessment/finding-template.json').read_text())
items = [
 ('F-001', 'Invoice ownership bypass', 'medium', 'Only invoice owners may read invoices.', 'Alice read Bob invoice with HTTP 200.', 'Read /invoices/inv-a then /invoices/inv-b as Alice.', 'Authenticated same-tenant non-owner with invoice ID.', 'Same-tenant invoice disclosure.', 'Applied owner and tenant checks; matrix retested.'),
 ('F-002', 'Cross-tenant report disclosure', 'medium', 'Only report tenant members may read reports.', 'Alice read south report with HTTP 200.', 'Read /reports/report-n then /reports/report-s as Alice.', 'Authenticated other-tenant user with report ID.', 'Cross-tenant report disclosure.', 'Applied tenant check; matrix retested.'),
 ('F-003', 'Client-controlled order totals', 'high', 'Total equals quantity times catalog price.', 'Independent GET showed stored total 2 instead of 2000 cents.', 'Post book quantity 2 with price 1 then GET /orders.', 'Authenticated user submitting a valid order.', 'Stored pricing integrity compromise; no actual payment.', 'Applied catalog-based pricing; independent read and regression cases retested.')
]
for fid, title, severity, expected, observed, repro, pre, impact, fix in items:
    record = dict(base, id=fid, title=title, status='confirmed', severity=severity, expected=expected + ' Source: app/README.md.', observed=observed, evidence=['assessment/evidence-before.json', 'assessment/evidence-after.json', 'assessment/before.txt', 'assessment/after.txt'], reproduction=[repro, 'Run python assessment/reproduce.py from workspace root.'], preconditions=[pre], uncertainty=['Only local synthetic application behavior demonstrated; see report.md for coverage gaps.'], impact=impact, remediation=fix)
    Path('assessment/' + fid + '.json').write_text(json.dumps(record, indent=2) + '\n')
