import urllib.request, urllib.error, urllib.parse, http.cookiejar, json, re
from html.parser import HTMLParser
from datetime import datetime, timezone

BASE='http://127.0.0.1:34947'
sessions={}
pages={}
count=0
logins=0
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None
class Forms(HTMLParser):
    def __init__(self): super().__init__(); self.forms=[]; self.current=None
    def handle_starttag(self, tag, attrs):
        d=dict(attrs)
        if tag=='form': self.current={'attrs':d,'inputs':[]}; self.forms.append(self.current)
        if tag=='input' and self.current is not None: self.current['inputs'].append(d)
    def handle_endtag(self,tag):
        if tag=='form': self.current=None
def redact(s):
    s=re.sub(r'fixture-[a-z]+','[REDACTED]',s)
    s=re.sub(r'(<input\b[^>]*\bname=[\"\'](?:csrf[^\"\']*|password)[\"\'][^>]*\bvalue=[\"\'])[^\"\']*',r'\1[REDACTED]',s,flags=re.I)
    s=re.sub(r'(?i)(csrf[\w-]*[\"\']?\s*[:=]\s*[\"\'])[^\"\']+',r'\1[REDACTED]',s)
    return s
def run(c):
    global count,logins
    who=c.get('session','anon'); path=c.get('path','/'); method='GET'; data=None
    headers={}
    if c.get('op')=='login':
        assert logins<10
        p=Forms(); p.feed(pages[who])
        f=next(f for f in p.forms if any(i.get('type')=='password' for i in f['inputs']))
        path=f['attrs'].get('action',path)
        data={i['name']:i.get('value','') for i in f['inputs'] if i.get('name')}
        data.update(username=who,password='fixture-'+who)
        data=urllib.parse.urlencode(data).encode(); method='POST'; headers['Origin']=BASE; logins+=1
    url=urllib.parse.urljoin(BASE,path)
    assert urllib.parse.urlsplit(url).netloc=='127.0.0.1:34947' and urllib.parse.urlsplit(url).scheme=='http'
    assert count<40
    if who not in sessions: sessions[who]=urllib.request.build_opener(NoRedirect(),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    count+=1
    req=urllib.request.Request(url,data=data,headers=headers,method=method)
    try: r=sessions[who].open(req,timeout=10)
    except urllib.error.HTTPError as e: r=e
    body=r.read(150000).decode('utf-8','replace'); pages[who]=body
    hs={k:('[REDACTED]' if k.lower()=='set-cookie' else redact(v)) for k,v in r.headers.items()}
    record={'request':count,'time':datetime.now(timezone.utc).isoformat(),'session':who,'method':method,'url':url,'login':c.get('op')=='login','status':r.code,'headers':hs,'body':redact(body)}
    with open('evidence.jsonl','a',encoding='utf-8') as f: f.write(json.dumps(record)+'\n')
    print(json.dumps(record),flush=True)
print('READY',flush=True)
while True:
    try:
        line=input()
        if line=='quit': break
        run(json.loads(line))
    except EOFError: break
    except Exception as e: print(type(e).__name__+': '+str(e),flush=True)
