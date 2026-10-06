"""Cross-platform local release checks; no installs, network calls or approvals."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,help='New empty evidence directory')
    parser.add_argument('--node',help='Existing Node executable; required for subject checks')
    args=parser.parse_args();root=Path(__file__).resolve().parent.parent;out=Path(args.out).resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):raise SystemExit('Use a new empty evidence directory')
    out.mkdir(parents=True,exist_ok=True);node=args.node or shutil.which('node')
    env={**os.environ,'PYTHONUTF8':'1'};commands=[('doctor',[sys.executable,str(root/'scripts/production/h5.py'),'doctor']),('python-regression',[sys.executable,'-m','unittest','discover','-s',str(root/'scripts'),'-p','test_*.py'])]
    if node:
        commands.append(('subject-regression',[node,str(root/'scripts/production/test_subject_quality.mjs')]))
        commands.append(('interaction-regression',[node,str(root/'scripts/production/test_interaction_modules.mjs')]))
    results=[]
    for name,command in commands:
        run=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
        (out/(name+'.txt')).write_text(run.stdout+run.stderr,encoding='utf-8');results.append({'name':name,'exitCode':run.returncode,'evidence':name+'.txt'})
    if not node:results.append({'name':'subject-regression','exitCode':None,'reason':'Existing Node executable missing; no automatic install'})
    report={'platform':sys.platform,'python':sys.version.split()[0],'node':node,'checks':results,'status':'pass' if all(r['exitCode']==0 for r in results) else 'fail','scope':'Installed source/regression execution only; not host-agent discovery, real UI/video, another floorplan or human acceptance','installsPerformed':False,'networkCalls':False}
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True));return 0 if report['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
