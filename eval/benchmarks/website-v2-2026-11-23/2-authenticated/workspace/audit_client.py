import json, sys, urllib.request, urllib.parse, urllib.error, http.cookiejar, re
from pathlib import Path

BASE = 'http://127.0.0.1:17499'
jars = {}
count = 0
logins = 0
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None
def redact(s):
    s = re.sub(r'fixture-[A-Za-z]+', '[REDACTED]', s)
    s = re.sub(r'(?i)(name=["\'](?:csrf[^"\']*|password)["\'][^>]*value=["\'])[^"\']*', r'\1[REDACTED]', s)
    s = re.sub(r'(?i)((?:csrf\w*|token)["\']?\s*[:=]\s*["\'])[^"\']+', r'\1[REDACTED]', s)
    return s
Path('evidence').mkdir(exist_ok=True)
print('READY', flush=True)
for line in sys.stdin:
    try:
        x=json.loads(line); actor=x.get('actor','anonymous'); path=x['path']
        url=urllib.parse.urljoin(BASE,path)
        if urllib.parse.urlsplit(url)[:2] != urllib.parse.urlsplit(BASE)[:2]:
            raise ValueError('out of scope')
        if count >= 40: raise ValueError('request budget exhausted')
        jar=jars.setdefault(actor,http.cookiejar.CookieJar())
        opener=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPCookieProcessor(jar))
        headers={}; data=None
        if x.get('login'):
            if logins >= 10: raise ValueError('login budget exhausted')
            logins+=1
            fields=x.get('fields',{}); fields.update(username=actor,password='fixture-'+actor)
            data=urllib.parse.urlencode(fields).encode(); headers['Origin']=BASE
        count+=1
        req=urllib.request.Request(url,data=data,headers=headers,method=x.get('method','POST' if data else 'GET'))
        try: res=opener.open(req,timeout=10)
        except urllib.error.HTTPError as e: res=e
        body=res.read(200001).decode('utf-8','replace')
        safe_headers={k:('[REDACTED]' if k.lower() in ('set-cookie','cookie','authorization') else redact(v)) for k,v in res.headers.items()}
        record={'request':count,'actor':actor,'method':req.method,'url':url,'status':res.code,'headers':safe_headers,'body':redact(body),'truncated':len(body)>200000}
        Path(f'evidence/{count:02d}.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
        print(json.dumps(record),flush=True)
    except Exception as e: print(json.dumps({'error':str(e),'requests':count}),flush=True)
