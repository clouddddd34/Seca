"""Archive selected reviewable evidence, excluding installed tools and skill copies."""
import argparse
import json
from pathlib import Path
import re
import shutil

def read_text(path):
    raw=path.read_bytes()
    if raw.startswith((b'\xff\xfe',b'\xfe\xff')):
        value=raw.decode('utf-16')
    else:
        try:
            value=raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            # Windows PowerShell Set-Content can emit the local ANSI code page.
            value=raw.decode('cp1252')
    return re.sub(r'\r+\n','\n',value).replace('\r','\n')

def redact(text):
    name_parts=Path.home().name.split()
    if len(name_parts)>1:
        wrapped_name=r'(?:\s|\\[rn])+'.join(re.escape(part) for part in name_parts)
        text=re.sub(wrapped_name,'<USER_NAME>',text,flags=re.I)
    text=re.sub(r'C:[/\\]+Users[/\\]+[^/\\\r\n]+', '<USER_HOME>', text, flags=re.I)
    # Long random URL-safe session/CSRF values are not needed to review observations.
    def opaque(match):
        value=match.group()
        # Preserve descriptive Python identifiers; session tokens mix character classes.
        if any(c.isupper() for c in value) and any(c.islower() for c in value) and any(c.isdigit() for c in value):
            return '<REDACTED_OPAQUE_TOKEN>'
        return value
    text=re.sub(r'(?<![A-Za-z0-9_-])[A-Za-z0-9_-]{40,48}(?![A-Za-z0-9_-])',opaque,text)
    return text

def archive(source,destination):
    if destination.exists():
        raise ValueError('Use a new archive destination')
    destination.mkdir(parents=True)
    for name in ('manifest.json','protocol.json','PROTOCOL.md','recovery.json','review.json','scores.json','supplemental-summary.json','resume-20261123.json','completion-status.json','website-review.json'):
        if (source/name).is_file():
            # Preserve frozen hashes exactly. Review documents may quote local paths.
            if name in ('manifest.json','protocol.json','PROTOCOL.md'):
                shutil.copy2(source/name,destination/name)
            else:
                (destination/name).write_text(redact(read_text(source/name)),encoding='utf-8')
    folders=sorted(p.parent for p in source.rglob('execution.json') if 'workspace' not in p.parts)
    for folder in folders:
        target=destination/folder.relative_to(source)
        target.mkdir(parents=True,exist_ok=True)
        for name in ('execution.json','metrics.json','patch-check.json','supplemental-concurrency.json','supplemental-unicode.json','observations.json','prompt.txt','last-message.txt'):
            if (folder/name).is_file():
                (target/name).write_text(redact(read_text(folder/name)),encoding='utf-8')
        commands=[]
        errors=[]
        for line in (folder/'events.jsonl').read_text(encoding='utf-8').splitlines():
            try:
                event=json.loads(line)
            except json.JSONDecodeError:
                continue
            item=event.get('item',{})
            if event.get('type') in ('error','turn.failed'):
                errors.append(event)
            if event.get('type')=='item.completed' and item.get('type') in ('command_execution','file_change'):
                commands.append(item)
        (target/'executed-actions.json').write_text(redact(json.dumps(commands,indent=2)),encoding='utf-8')
        if errors:
            (target/'failure.json').write_text(redact(json.dumps(errors,indent=2)),encoding='utf-8')
        work=folder/'workspace'
        for path in work.rglob('*'):
            relative=path.relative_to(work)
            if not path.is_file() or relative.parts[0] in ('assigned-skill','competitor','tools','.git') or '__pycache__' in relative.parts:
                continue
            if path.suffix.lower() not in ('.py','.md','.json','.jsonl','.txt','.csv','.html','.diff','.patch','.log','.yaml','.yml','.toml','.ini','.cfg','.ps1','.sh','.xml'):
                continue
            if path.stat().st_size>2_000_000:
                raise ValueError('Review oversized artifact before archiving: '+str(path))
            output=target/'workspace'/relative
            output.parent.mkdir(parents=True,exist_ok=True)
            output.write_text(redact(read_text(path)),encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    archive(args.source,args.destination)
