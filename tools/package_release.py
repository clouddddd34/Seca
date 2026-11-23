"""Stage reviewable Windows release artifacts; does not tag, push or publish."""
import argparse
import hashlib
import json
from pathlib import Path
import posixpath
import re
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]
TAG='v0.1.0-rc.1'


def packaged_markdown(path):
    """Relocated onboarding files link to the tagged source instead of absent files."""
    relative=path.relative_to(ROOT).as_posix()
    def resolve(match):
        target=match.group(2)
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target) or target.startswith('#'):
            return match.group(0)
        resolved=posixpath.normpath(posixpath.join(posixpath.dirname(relative),target))
        return match.group(1)+'https://github.com/clouddddd34/Seca/blob/'+TAG+'/'+resolved+')'
    return re.sub(r'(\[[^\]]+\]\()([^\s)]+)\)',resolve,path.read_text(encoding='utf-8'))

def package(destination):
    if destination.exists():
        raise ValueError('Use a new output directory')
    binary=ROOT/'target/release/seca.exe'
    if not binary.is_file():
        raise ValueError('Build the Windows release binary first')
    notes=ROOT/'docs/RELEASE-v0.1.0-rc.1.md'
    if not notes.is_file():
        raise ValueError('Complete release notes first')
    cargo=shutil.which('cargo') or str(Path.home()/'.cargo/bin/cargo.exe')
    metadata=json.loads(subprocess.check_output([cargo,'metadata','--locked','--offline','--filter-platform','x86_64-pc-windows-msvc','--format-version','1'],cwd=ROOT,text=True))
    provenance={'tag':TAG,'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                'source_dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()),
                'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),
                'skill_sha256':{p.relative_to(ROOT/'security-audit').as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in sorted((ROOT/'security-audit').rglob('*')) if p.is_file()}}
    destination.mkdir(parents=True)
    skill=destination/'seca-skill-v0.1.0-rc.1.zip'
    with zipfile.ZipFile(skill,'w',zipfile.ZIP_DEFLATED,strict_timestamps=False) as archive:
        for path in sorted((ROOT/'security-audit').rglob('*')):
            if path.is_file():
                archive.write(path,path.relative_to(ROOT).as_posix())
        archive.write(ROOT/'LICENSE','LICENSE')
        archive.writestr('README.md',packaged_markdown(ROOT/'README.md'))
        archive.writestr('QUICKSTART.md',packaged_markdown(ROOT/'docs/QUICKSTART.md'))
        archive.writestr('RELEASE-NOTES.md',packaged_markdown(notes))
        archive.writestr('SOURCE.json',json.dumps(provenance,indent=2))
    cli=destination/'seca-v0.1.0-rc.1-windows-x86_64.zip'
    with zipfile.ZipFile(cli,'w',zipfile.ZIP_DEFLATED,strict_timestamps=False) as archive:
        archive.write(binary,'seca.exe')
        archive.write(ROOT/'LICENSE','LICENSE')
        archive.writestr('HELPERS.md',packaged_markdown(ROOT/'security-audit/references/helpers.md'))
        archive.writestr('RELEASE-NOTES.md',packaged_markdown(notes))
        archive.writestr('SOURCE.json',json.dumps(provenance,indent=2))
        notices=[]
        for dependency in metadata['packages']:
            if dependency['name']=='seca':
                continue
            label=dependency['name']+'-'+dependency['version']
            notices.append({'package':label,'license':dependency.get('license'),'source':dependency.get('source')})
            directory=Path(dependency['manifest_path']).parent
            files={p for p in directory.iterdir() if p.is_file() and p.name.upper().startswith(('LICENSE','COPYING','NOTICE'))}
            if dependency.get('license_file'):
                files.add(directory/dependency['license_file'])
            for path in sorted(files):
                if path.is_file():
                    archive.write(path,'third-party/'+label+'/'+path.name)
        archive.writestr('third-party/packages.json',json.dumps(notices,indent=2))
    (destination/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in (skill,cli)),encoding='utf-8')
    print(destination)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    package(parser.parse_args().output.resolve())
