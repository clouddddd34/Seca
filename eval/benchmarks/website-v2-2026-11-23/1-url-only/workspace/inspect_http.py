import urllib.request, urllib.error, urllib.parse, re, json, sys
from pathlib import Path
from datetime import datetime, timezone

ORIGIN = 'http://127.0.0.1:17689'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def redact(s):
    s = re.sub(r'(?im)^(set-cookie|cookie|authorization):.*$', r'\1: [REDACTED]', s)
    s = re.sub(r'(?is)(<input\b[^>]*(?:csrf|token|password)[^>]*\bvalue\s*=\s*)([\x22\x27]).*?\2', r'\1"[REDACTED]"', s)
    s = re.sub(r'(?i)((?:password|passwd|csrf\w*|access_token|secret)\s*[\x22\x27]?\s*[:=]\s*[\x22\x27]?)[^\s\x22\x27<>&,;]+', r'\1[REDACTED]', s)
    return s

url = sys.argv[1]
assert urllib.parse.urlsplit(url).scheme == 'http' and urllib.parse.urlsplit(url).netloc == '127.0.0.1:17689'
folder = Path('evidence'); folder.mkdir(exist_ok=True)
logfile = folder / 'requests.json'
log = json.loads(logfile.read_text()) if logfile.exists() else []
assert len(log) < 40
n = len(log) + 1
entry = {'id': n, 'method': 'GET', 'url': url, 'time_utc': datetime.now(timezone.utc).isoformat()}
log.append(entry)
logfile.write_text(json.dumps(log, indent=2))
req = urllib.request.Request(url, headers={'User-Agent': 'Bounded-local-assessment/1.0'})
try:
    response = urllib.request.build_opener(NoRedirect).open(req, timeout=15)
except urllib.error.HTTPError as exc:
    response = exc
except Exception as exc:
    entry['error'] = str(exc)
    logfile.write_text(json.dumps(log, indent=2)); raise
with response:
    body = response.read(262145)
    entry['status'] = response.status
    entry['truncated'] = len(body) > 262144
    content = redact('GET ' + url + '\nStatus: ' + str(response.status) + '\n' + str(response.headers) + '\n' + body[:262144].decode('utf-8', errors='replace'))
    file = folder / f'{n:02d}.txt'
    file.write_text(content, encoding='utf-8')
    entry['evidence'] = str(file)
logfile.write_text(json.dumps(log, indent=2))
print(content)
