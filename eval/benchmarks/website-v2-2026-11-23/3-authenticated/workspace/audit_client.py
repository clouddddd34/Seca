import urllib.request, urllib.error, urllib.parse, http.cookiejar, json, re
BASE='http://127.0.0.1:10240'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None
jars={}
count=0
logins=0
secrets=set()
def redact(s):
    for v in sorted(secrets,key=len,reverse=True):
        if v: s=s.replace(v,'[REDACTED]')
    s=re.sub(r'(fixture-)(alice|bob|carol|admin)', '[REDACTED]',s)
    s=re.sub(r'(?im)^((?:set-cookie|cookie):).*$',r'\1 [REDACTED]',s)
    s=re.sub(r'(<input[^>]*name=["\'](?:csrf|csrf_token|_csrf)["\'][^>]*value=["\'])[^"\']*',r'\1[REDACTED]',s)
    return s
def request(c):
    global count,logins
    path=c['path']; assert path.startswith('/') and not path.startswith('//')
    assert urllib.parse.urlsplit(BASE+path).netloc=='127.0.0.1:10240'
    assert count<40
    who=c.get('as','anon'); jar=jars.setdefault(who,http.cookiejar.CookieJar())
    fields=c.get('fields'); headers={}
    if c.get('origin'): headers['Origin']=BASE
    if fields:
        fields=dict(fields)
        if 'password' in fields:
            assert logins<10
            logins+=1
            fields['password']='fixture-'+fields['username']
            secrets.add(fields['password'])
        if fields.get('csrf')=='AUTO': fields['csrf']=tokens[who]
    data=urllib.parse.urlencode(fields).encode() if fields is not None else None
    req=urllib.request.Request(BASE+path,data=data,headers=headers,method=c.get('method','POST' if data is not None else 'GET'))
    count+=1
    try: res=urllib.request.build_opener(NoRedirect,urllib.request.HTTPCookieProcessor(jar)).open(req,timeout=10)
    except urllib.error.HTTPError as e: res=e
    body=res.read(150000).decode('utf-8',errors='replace')
    for cookie in jar: secrets.add(cookie.value)
    for match in re.finditer(r'name=["\'](?:csrf|csrf_token|_csrf)["\'][^>]*value=["\']([^"\']*)',body):
        tokens[who]=match.group(1); secrets.add(match.group(1))
    result=redact(f'R{count:02d} {who} {req.method} {path}\nStatus: {res.code}\n'+str(res.headers)+'\n'+body)
    with open('evidence.txt','a',encoding='utf-8') as f: f.write(result+'\n\n')
    print(result,flush=True)
tokens={}
print('READY',flush=True)
while True:
    try:
        line=input()
        if line=='QUIT': break
        request(json.loads(line))
    except EOFError: break
    except Exception as e: print(type(e).__name__+': '+str(e),flush=True)
