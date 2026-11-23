import urllib.request, urllib.error, urllib.parse, json, re, sys
from pathlib import Path
from html.parser import HTMLParser

ORIGIN = 'http://127.0.0.1:56365'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None

def redact(s):
    s = re.sub(r'(?i)((?:password|passwd|csrf[\w-]*|token|secret|cookie|authorization)[\s\"\x27:=]+)[^\s<>\"\x27;,]+', r'\1[REDACTED]', s)
    s = re.sub(r'(?i)([\w.+-]+)@([\w.-]+\.[a-z]{2,})', '[REDACTED EMAIL]', s)
    s = re.sub(r'(?i)(value\s*=\s*)([\"\x27]).*?\2', r'\1"[REDACTED]"', s)
    return s

class Parse(HTMLParser):
    def __init__(self): super().__init__(); self.tags=[]; self.text=[]
    def handle_starttag(self, tag, attrs):
        if tag in ('a','form','input','button','script','link','iframe','img','meta'):
            self.tags.append({'tag':tag, 'attrs':{k:('[REDACTED]' if k in ('value','nonce') else redact(v or '')) for k,v in attrs}})
    def handle_data(self, d):
        if d.strip(): self.text.append(redact(d.strip()))

path = sys.argv[1]
url = urllib.parse.urljoin(ORIGIN+'/', path)
assert urllib.parse.urlsplit(url).netloc == '127.0.0.1:56365' and urllib.parse.urlsplit(url).scheme == 'http'
folder=Path('evidence'); folder.mkdir(exist_ok=True)
existing=list(folder.glob('request-*.json')); n=len(existing)+1
assert n <= 40
opener=urllib.request.build_opener(NoRedirect())
req=urllib.request.Request(url, headers={'User-Agent':'Bounded-ReadOnly-Assessment/1.0'})
try: response=opener.open(req, timeout=15)
except urllib.error.HTTPError as e: response=e
with response:
    body=response.read(262145)
    truncated=len(body)>262144
    body=body[:262144].decode('utf-8',errors='replace')
    headers={k:('[REDACTED]' if k.lower() in ('set-cookie','authorization') else redact(v)) for k,v in response.headers.items()}
    p=Parse(); p.feed(body)
    record={'request_number':n,'method':'GET','url':redact(url),'status':response.status,'headers':headers,'truncated':truncated,'elements':p.tags,'text':p.text}
    if 'text/html' not in response.headers.get('Content-Type',''): record['body']=redact(body)
    (folder/f'request-{n:02d}.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps(record,indent=2))
