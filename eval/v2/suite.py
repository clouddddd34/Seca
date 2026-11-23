"""Prepare, execute and mechanically inspect v2; semantic scoring requires review."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from eval.prepare import prepare
from eval.run import agent_options, run_one

FIXTURES = ('documents','checkout','portal')

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def hashes(folder):
    return {p.relative_to(folder).as_posix():digest(p) for p in sorted(folder.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts}

def prepare_suite(output,competitor,binary):
    output = output.resolve()
    if output.exists() or output == ROOT or ROOT in output.parents:
        raise ValueError('Use a new external directory')
    manifest = {'version':2,'runs':[], 'evaluator_hashes':{name:digest(ROOT/'eval/v2'/name)
                for name in ('PROTOCOL.md','check.py','test_v2.py','suite.py')}}
    for fixture in FIXTURES:
        child = prepare(output/fixture,competitor,binary,ROOT/'eval/v2/fixtures'/fixture,ROOT/'eval/v2/task.txt')
        manifest[fixture] = child
    for repetition in range(1,4):
        for fixture in FIXTURES:
            for run in manifest[fixture]['runs']:
                if run['repetition'] == repetition:
                    identifier = fixture+'/'+run['id']
                    manifest['runs'].append(dict(run,id=identifier,fixture=fixture,
                        inputs=hashes(output/identifier/'workspace'),prompt_sha256=digest(output/identifier/'prompt.txt')))
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    shutil.copy2(ROOT/'eval/v2/PROTOCOL.md',output/'PROTOCOL.md')
    return manifest

def usage(events):
    values = []
    for line in events.read_text(encoding='utf-8').splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get('type')=='turn.completed' and event.get('usage'):
            values.append(event['usage'])
    if not values:
        return None
    return {key:sum(v.get(key,0) for v in values) for key in set().union(*(v.keys() for v in values))}

def execute(output,model,seconds):
    manifest = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
    for name,expected in manifest['evaluator_hashes'].items():
        if digest(ROOT/'eval/v2'/name)!=expected:
            raise ValueError('Frozen evaluator changed: '+name)
    executable = shutil.which('codex')
    protocol = {'model_requested':model,'seconds':seconds,'reasoning_effort':'medium',
                'cli_version':subprocess.check_output([executable,'--version'],text=True).strip(),
                'options':agent_options(model,'medium'),'manifest_sha256':digest(output/'manifest.json')}
    protocol_path = output/'protocol.json'
    if protocol_path.exists() and json.loads(protocol_path.read_text(encoding='utf-8'))!=protocol:
        raise ValueError('Protocol differs from frozen configuration')
    protocol_path.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    for run in manifest['runs']:
        folder = output/run['id']
        if (folder/'execution.json').exists():
            previous = json.loads((folder/'execution.json').read_text(encoding='utf-8'))
            if previous['status'] not in ('completed','timed_out'):
                raise ValueError('Inspect invalid/interrupted attempt before preparing a fresh suite: '+run['id'])
            continue
        if hashes(folder/'workspace')!=run['inputs'] or digest(folder/'prompt.txt')!=run['prompt_sha256']:
            raise ValueError('Frozen assessed inputs changed: '+run['id'])
        print('Starting '+run['id'],flush=True)
        status = run_one(folder,executable,model,seconds)
        metrics = {'usage':usage(folder/'events.jsonl'),'cost_usd':None,
                   'cost_note':'No authoritative billing/rate supplied; usage is not dollar cost.'}
        (folder/'metrics.json').write_text(json.dumps(metrics,indent=2),encoding='utf-8')
        # Evaluate candidate code in a child process, with a finite budget.
        try:
            checked = subprocess.run([sys.executable,str(ROOT/'eval/v2/check.py'),run['fixture'],str(folder/'workspace/app/app.py')],capture_output=True,text=True,timeout=30)
            result = json.loads(checked.stdout)
        except (subprocess.TimeoutExpired,json.JSONDecodeError) as error:
            result = {'evaluator_error':str(error)}
        (folder/'patch-check.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        print(run['id']+': '+status['status'],flush=True)
        if status['status'] not in ('completed','timed_out'):
            raise RuntimeError('Assessment infrastructure/incomplete run requires inspection; suite stopped')

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','run'))
    parser.add_argument('output',type=Path)
    parser.add_argument('--competitor',type=Path)
    parser.add_argument('--binary',type=Path,default=ROOT/'target/debug'/('seca.exe' if os.name=='nt' else 'seca'))
    parser.add_argument('--model',default='gpt-6-astra')
    parser.add_argument('--seconds',type=int,default=180)
    args=parser.parse_args()
    if args.seconds<1:
        parser.error('Positive budget required')
    if args.action=='prepare':
        if not args.competitor:
            parser.error('--competitor required')
        print(len(prepare_suite(args.output,args.competitor,args.binary)['runs']),'runs prepared')
    else:
        execute(args.output.resolve(),args.model,args.seconds)
