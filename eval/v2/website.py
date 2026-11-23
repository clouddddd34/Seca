"""Separate HTML/form website coverage experiment without source access."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import shutil
import socket
import sys
import threading
import time
import uvicorn

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from eval.run import run_one
from eval.v2.fixtures.portal.app import create_app
from eval.v2.suite import digest, hashes, usage

def run_one_website(folder, authenticated, model, seconds):
    folder = folder.resolve()
    if folder.exists() or folder == ROOT or ROOT in folder.parents:
        raise ValueError('Use a new external directory')
    work=folder/'workspace'
    work.mkdir(parents=True)
    shutil.copytree(ROOT/'security-audit',work/'assigned-skill')
    app=create_app()
    initial=deepcopy(app.state.tickets)
    requests=[]

    @app.middleware('http')
    async def observe(request,call_next):
        response=await call_next(request)
        requests.append({'method':request.method,'path':request.url.path,'status':response.status_code})
        return response

    listener=socket.socket()
    listener.bind(('127.0.0.1',0))
    origin=f'http://127.0.0.1:{listener.getsockname()[1]}'
    server=uvicorn.Server(uvicorn.Config(app,log_level='critical',access_log=False,ws='none'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True)
    prompt=f'''Read assigned-skill/SKILL.md. Assess my local synthetic website at {origin}/.
Only this origin and its linked first-party resources are authorized. Inspect navigation,
HTML, forms and observable access controls using bounded sequential HTTP requests.
Do not read outside this workspace, seek source files, guess routes or credentials,
install packages, delegate, scan ports, contact external services or run load tests.
Plain loopback HTTP, fixed fake passwords, no rate limiting/persistence and absent
production deployment infrastructure are intentional fixture conditions, not findings.
There may be zero or multiple issues. Write report.md with actual evidence, confirmed
findings, protected controls, coverage limits and requested additional access if needed.
Redact credentials, cookies and CSRF values in saved evidence. At most 40 requests.
'''
    if authenticated:
        prompt+='''You may log in/out using these synthetic users: alice, bob, carol, admin;
passwords are fixture- followed by the username. Alice/Bob/admin belong to north;
Carol belongs to south; only admin has the admin role. Tickets require BOTH ownership
and current tenant membership; admin exports only its current tenant. Use navigation
to discover tickets under each account; bounded cross-account replay and HTML-escaping
tests are authorized. Login requires this site's Origin header. At most ten logins.
Logout and login are the only authorized state-changing actions. Do not alter tickets.
'''
    else:
        prompt+='''No accounts, source or private access rules are supplied. Only linked,
non-mutating GET requests are permitted. Do not submit forms, log in/out or change state.
Complete independent checks and mark authenticated/internal checks untested.
'''
    (folder/'prompt.txt').write_text(prompt,encoding='utf-8')
    metadata={'mode':'authenticated' if authenticated else 'url-only','source_supplied':False,
              'accounts_supplied':authenticated,'origin':origin,'model_requested':model,
              'seconds':seconds,'skill_sha256':hashes(work/'assigned-skill'),
              'cli_version':__import__('subprocess').check_output([shutil.which('codex'),'--version'],text=True).strip()}
    thread.start()
    try:
        deadline=time.monotonic()+5
        while not server.started and thread.is_alive() and time.monotonic()<deadline:
            time.sleep(.02)
        if not server.started:
            raise RuntimeError('Local server did not start')
        result=run_one(folder,shutil.which('codex'),model,seconds)
        (folder/'metrics.json').write_text(json.dumps({'usage':usage(folder/'events.jsonl'),'cost_usd':None},indent=2),encoding='utf-8')
        return result
    finally:
        server.should_exit=True
        thread.join(timeout=5)
        listener.close()
        metadata.update(requests=requests,tickets_unchanged=initial==app.state.tickets,
            remaining_sessions=len(app.state.sessions),server_stopped=not thread.is_alive())
        (folder/'observations.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    parser.add_argument('--model',default='gpt-6-astra')
    parser.add_argument('--seconds',type=int,default=180)
    args=parser.parse_args()
    if args.seconds<1:
        parser.error('Positive budget required')
    args.output=args.output.resolve()
    if args.output.exists() or args.output==ROOT or ROOT in args.output.parents:
        parser.error('Use a new external output directory')
    frozen={'model_requested':args.model,'seconds':args.seconds,'reasoning_effort':'medium',
            'skill_sha256':hashes(ROOT/'security-audit'),
            'source_sha256':{name:digest(ROOT/'eval/v2'/name) for name in ('website.py','fixtures/portal/app.py','PROTOCOL.md')}}
    args.output.mkdir(parents=True)
    (args.output/'protocol.json').write_text(json.dumps(frozen,indent=2),encoding='utf-8')
    for repetition in range(1,4):
        for mode in ('url-only','authenticated') if repetition%2 else ('authenticated','url-only'):
            if hashes(ROOT/'security-audit')!=frozen['skill_sha256'] or any(digest(ROOT/'eval/v2'/name)!=expected for name,expected in frozen['source_sha256'].items()):
                raise ValueError('Frozen website experiment inputs changed')
            folder=args.output/f'{repetition}-{mode}'
            if folder.exists():
                raise ValueError('Do not reuse previous website runs')
            result=run_one_website(folder,mode=='authenticated',args.model,args.seconds)
            print(folder.name,result,flush=True)
            if result['status'] not in ('completed','timed_out'):
                raise RuntimeError('Website assessment stopped; inspect the failed attempt before scheduling further runs')
