"""Stage reviewable Windows release artifacts; does not tag, push or publish."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]

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
    destination.mkdir(parents=True)
    skill=destination/'seca-skill-v0.1.0-rc.1.zip'
    with zipfile.ZipFile(skill,'w',zipfile.ZIP_DEFLATED,strict_timestamps=False) as archive:
        for path in sorted((ROOT/'security-audit').rglob('*')):
            if path.is_file():
                archive.write(path,path.relative_to(ROOT).as_posix())
        archive.write(ROOT/'LICENSE','LICENSE')
        archive.write(ROOT/'README.md','README.md')
        archive.write(ROOT/'docs/QUICKSTART.md','QUICKSTART.md')
        archive.write(notes,'RELEASE-NOTES.md')
        archive.writestr('SOURCE.txt','Source and full development documentation: https://github.com/clouddddd34/Seca\n')
    cli=destination/'seca-v0.1.0-rc.1-windows-x86_64.zip'
    with zipfile.ZipFile(cli,'w',zipfile.ZIP_DEFLATED,strict_timestamps=False) as archive:
        archive.write(binary,'seca.exe')
        archive.write(ROOT/'LICENSE','LICENSE')
        archive.write(ROOT/'security-audit/references/helpers.md','HELPERS.md')
        archive.write(notes,'RELEASE-NOTES.md')
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
