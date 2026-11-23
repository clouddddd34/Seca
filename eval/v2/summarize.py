"""Combine reviewed scores and mechanical metrics without inventing missing evidence."""
import argparse
import json
from pathlib import Path
from statistics import median

def summarize(root, allow_partial=False):
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    reviews=json.loads((root/'review.json').read_text(encoding='utf-8'))
    eligible=[]
    excluded=[]
    for run in manifest['runs']:
        path=root/run['id']/'execution.json'
        execution=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'status':'not_started'}
        if execution['status'] in ('completed','timed_out'):
            eligible.append(run)
        else:
            excluded.append({'run_id':run['id'],'execution':execution})
    missing=[r['id'] for r in eligible if r['id'] not in reviews]
    if missing:
        raise ValueError('Review every run before summarizing: '+', '.join(missing))
    if excluded and not allow_partial:
        raise ValueError('Suite incomplete; use --allow-partial to explicitly report excluded attempts')
    output={'note':'Preliminary synthetic fixtures; planned root causes only. Additional findings listed per run. Dollar costs unavailable.',
            'complete':not excluded,'planned_runs':len(manifest['runs']),'scored_runs':len(eligible),
            'excluded_runs':excluded,'runs':[], 'arms':{}}
    for run in eligible:
        folder=root/run['id']
        execution=json.loads((folder/'execution.json').read_text(encoding='utf-8'))
        metrics=json.loads((folder/'metrics.json').read_text(encoding='utf-8'))
        checks=json.loads((folder/'patch-check.json').read_text(encoding='utf-8'))
        output['runs'].append(dict(run_id=run['id'],arm=run['arm'],fixture=run['fixture'],
            opportunities=0 if run['fixture']=='portal' else 2, execution=execution,
            metrics=metrics, independent_checks=checks, **reviews[run['id']]))
    for arm in ('baseline','seca','competitor'):
        runs=[r for r in output['runs'] if r['arm']==arm]
        completed=[r for r in runs if r['execution']['status']=='completed']
        known_usage=[r['metrics']['usage'] for r in runs if r['metrics']['usage'] is not None]
        output['arms'][arm]={
            'scored_runs':len(runs),
            **{key:sum(r[key] for r in runs) for key in ('opportunities','discovery','complete_runtime_proofs','false_accusations','fixes')},
            'completed':len(completed),'timed_out':sum(r['execution']['status']=='timed_out' for r in runs),
            'median_completed_seconds':median([r['execution']['elapsed_seconds'] for r in completed]) if completed else None,
            'all_checks_passed':sum(all(v is True for v in r['independent_checks'].values()) for r in runs),
            'known_usage_runs':len(known_usage), 'unknown_usage_runs':len(runs)-len(known_usage),
            'known_usage_totals':{k:sum(v.get(k,0) for v in known_usage) for k in set().union(*(v.keys() for v in known_usage))},
            'cost_usd':None,
            'secure_portal_false_accusations':sum(r['false_accusations'] for r in runs if r['fixture']=='portal'),
        }
    return output

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root',type=Path)
    parser.add_argument('--allow-partial',action='store_true',help='Report incomplete suites with explicit exclusions and observed denominators')
    args=parser.parse_args()
    result=summarize(args.root,args.allow_partial)
    (args.root/'scores.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result['arms'],indent=2))
