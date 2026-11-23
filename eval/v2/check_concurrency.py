"""Supplemental, post-freeze instrumented schedule check; not original v2 scores."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sys
import threading
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from eval.v2.check import auth, load

def evaluate(path):
    path=path.resolve()
    module=load(path)
    write_lines={i for i,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1)
                 if 'app.state.wallets[name] +=' in line or 'app.state.wallets[name] -=' in line}
    if not write_lines:
        return {'unsupported':'Review candidate state-write implementation before adapting instrumentation.'}
    results={}
    for scenario in ('payment','refund','coupon'):
        app=module.create_app()
        with TestClient(app) as control:
            first=control.post('/orders',headers=auth('alice'),json={'quantity':1}).json()['id']
            endpoint='refund' if scenario=='refund' else 'pay'
            second=first
            if scenario=='refund':
                assert control.post(f'/orders/{first}/pay',headers=auth('alice'),json={}).status_code==200
            if scenario=='coupon':
                second=control.post('/orders',headers=auth('alice'),json={'quantity':1}).json()['id']
            before=control.get('/wallet',headers=auth('alice')).json()
            start=threading.Barrier(2)
            def trace(frame,event,arg):
                if event=='line' and frame.f_code.co_filename==str(path) and frame.f_lineno in write_lines:
                    time.sleep(.1)
                return trace
            def send(order):
                with TestClient(app) as client:
                    start.wait(timeout=5)
                    return client.post(f'/orders/{order}/{endpoint}',headers=auth('alice'),
                        json={'coupon':'WELCOME'} if scenario=='coupon' else {}).status_code
            previous=threading.gettrace()
            threading.settrace(trace)
            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    futures=[pool.submit(send,order) for order in (first,second)]
                    statuses=sorted(f.result(timeout=10) for f in futures)
            finally:
                threading.settrace(previous)
            wallet=control.get('/wallet',headers=auth('alice')).json()
            orders=[control.get(f'/orders/{order}',headers=auth('alice')).json() for order in sorted({first,second})]
            expected={'payment':9000,'refund':10000,'coupon':9500}[scenario]
            results[scenario]={'statuses':statuses,'wallet_before':before,'wallet_after':wallet,
                'saved_orders':orders,'passes':statuses==[200,409] and wallet['balance']==expected}
    return results

if __name__=='__main__':
    print(json.dumps(evaluate(Path(sys.argv[1])),indent=2))
