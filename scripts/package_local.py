"""Create a new local Skill archive with source hashes; no Git or remote actions."""
import argparse,hashlib,json,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
ROOT_FILES={'SKILL.md','README.md','README.zh.md','LICENSE','CHANGELOG.md','THIRD_PARTY_NOTICES.md','requirements.txt','.gitignore','.gitattributes'}
DIRS={'agents','assets','references','scripts'}
EXCLUDED_FILES={'assets/furniture-layout-reference/furniture-layout-linework-v9.png','assets/furniture-layout-reference/furniture-layout-linework-v9.svg'}
def files():
    for p in sorted(ROOT.rglob('*')):
        rel=p.relative_to(ROOT)
        if rel.as_posix() in EXCLUDED_FILES:continue
        if not p.is_file() or p.is_symlink() or p.name == '.DS_Store':continue
        if any(x in {'.git','__pycache__','node_modules','.pytest_cache'} for x in rel.parts) or p.suffix in {'.pyc','.skill','.zip'}:continue
        if rel.parts[0] in DIRS or (len(rel.parts)==1 and rel.name in ROOT_FILES):yield p,rel

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',required=True);args=parser.parse_args();out=Path(args.out).resolve()
    manifest=out.with_suffix('.manifest.json')
    if out.exists() or manifest.exists():raise SystemExit('Use a new archive name; existing artifacts are preserved')
    version=json.loads((ROOT/'assets/h5/version.json').read_text(encoding='utf-8'))['version']
    for name in ['SKILL.md','README.md','README.zh.md']:
        if version not in (ROOT/name).read_text(encoding='utf-8'):raise SystemExit('Version mismatch in '+name)
    records=[];out.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(out,'x',zipfile.ZIP_DEFLATED) as z:
        for p,rel in files():
            data=p.read_bytes();entry='visualize-floorplans/'+rel.as_posix();z.writestr(entry,data);records.append({'path':rel.as_posix(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)})
    with zipfile.ZipFile(out) as z:
        if z.testzip():raise SystemExit('ZIP integrity failed')
    report={'version':version,'channel':'local-beta','files':records,'archiveSha256':hashlib.sha256(out.read_bytes()).hexdigest(),'scope':'Source snapshot only, no case acceptance or platform certification','published':False}
    manifest.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps({'archive':str(out),'manifest':str(manifest),'version':version,'files':len(records)},ensure_ascii=False))
if __name__=='__main__':main()
