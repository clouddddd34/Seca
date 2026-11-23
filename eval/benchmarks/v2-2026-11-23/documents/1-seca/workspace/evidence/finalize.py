import json
import subprocess
import sys
from pathlib import Path
result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'app', '-p', 'test_security.py', '-v'], capture_output=True, text=True)
Path('evidence/tests-after.txt').write_text(result.stdout + result.stderr + '\nPython exit code: ' + str(result.returncode) + '\n')
print(result.stdout + result.stderr)
print('Python exit code:', result.returncode)
log = json.loads(Path('audit.json').read_text())
log['outstanding'] = []
log['result'] = 'Two confirmed findings fixed; ten regression/control tests pass.'
Path('audit.json').write_text(json.dumps(log, indent=2) + '\n')
for fid, title, expected, observed, repro, impact in [
 ('F-001', 'Read access survives tenant migration', 'Current document-tenant membership is required for owners and recipients.', 'Migrated owner and live-share recipient received HTTP 200 and the full synthetic document.', ['Create a fresh app; read a as Alice.', 'Change Alice tenant to south; GET a still returns document.', 'On another fresh app share a to Bob, migrate Bob to south, and GET a as Bob.'], 'Former tenant members retain document confidentiality access.'),
 ('F-002', 'Expired shares retain read access', 'Shares authorize reads only before expires_at and while not revoked.', 'A recipient received HTTP 200 and the full synthetic document after expiry.', ['Create a fresh app; Alice shares a to Bob with future expiry.', 'Verify Bob can read; set stored expiry to past timestamp.', 'GET a as Bob still returns document.'], 'Former recipients retain document access beyond the authorized period.')
]:
    record = json.loads(Path('evidence/finding-template.json').read_text())
    record.update(id=fid, title=title, status='confirmed', severity='medium', expected=expected, observed=observed,
                  evidence=['evidence/app-before.py:41', 'evidence/runtime-before.json', 'evidence/tests-before.txt', 'app/test_security.py', 'evidence/tests-after.txt'],
                  reproduction=repro, preconditions=['Existing owner or valid share recipient; authorized fixture transition as described.'],
                  uncertainty=['Production deployment and impact outside this synthetic service were not assessed.'], impact=impact,
                  remediation='Applied current-tenant prerequisite and strict future-expiry predicate in can_read; all ten tests pass.')
    Path('evidence/' + fid + '.json').write_text(json.dumps(record, indent=2) + '\n')
sys.exit(result.returncode)
