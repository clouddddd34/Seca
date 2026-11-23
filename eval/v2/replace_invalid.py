"""Preserve a failed infrastructure attempt and prepare byte-identical fresh inputs."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from eval.v2.suite import digest,hashes

def replace(root,run_id,donor_id):
    root=root.resolve()
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    runs={run['id']:run for run in manifest['runs']}
    run,donor=runs[run_id],runs[donor_id]
    if run['fixture']!=donor['fixture'] or run['arm']!=donor['arm']:
        raise ValueError('Donor must be the same fixture and arm')
    folder=(root/run_id).resolve()
    source=(root/donor_id).resolve()
    archive=(root/'invalid-attempts'/run_id.replace('/','-')).resolve()
    if any(root not in path.parents for path in (folder,source,archive)):
        raise ValueError('All resolved paths must stay inside the prepared suite')
    if archive.exists() or (source/'execution.json').exists():
        raise ValueError('Use a new archive destination and an unattempted donor')
    status=json.loads((folder/'execution.json').read_text(encoding='utf-8'))
    if status['status']!='failed' or 'You hit your spend cap' not in (folder/'events.jsonl').read_text(encoding='utf-8'):
        raise ValueError('This recovery path only classifies the observed spend-cap failure')
    if hashes(source/'workspace')!=run['inputs'] or digest(source/'prompt.txt')!=run['prompt_sha256']:
        raise ValueError('Donor differs from frozen assessed inputs')
    archive.parent.mkdir(parents=True,exist_ok=True)
    print('Preserving failed attempt:',folder,'->',archive)
    shutil.move(str(folder),str(archive))
    folder.mkdir()
    shutil.copytree(source/'workspace',folder/'workspace')
    shutil.copy2(source/'prompt.txt',folder/'prompt.txt')
    if hashes(folder/'workspace')!=run['inputs']:
        raise ValueError('Replacement verification failed; do not execute')
    record={'run_id':run_id,'donor':donor_id,'archived_attempt':archive.relative_to(root).as_posix(),
            'reason':'Provider workspace spend cap; invalid infrastructure attempt excluded from quality scores.',
            'fresh_inputs_verified':True,'manifest_unchanged':True,'model_call_made':False}
    (root/'recovery.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('run_id')
    parser.add_argument('donor_id')
    args=parser.parse_args()
    print(json.dumps(replace(args.root,args.run_id,args.donor_id),indent=2))
