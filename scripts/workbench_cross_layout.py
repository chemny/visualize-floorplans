"""Run isolated synthetic cross-layout checks; never read or alter a client case."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from workbench_browser_suite import selected_checks, run_process

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT/'scripts/production'))
from workbench_regression_cases import regression_cases


def summarize(rows):
    if any(r['status']=='fail' for r in rows):
        return 'fail'
    if any(r['status']=='blocked' for r in rows):
        return 'blocked'
    return 'pass' if any(r['status']=='pass' for r in rows) else 'not_applicable'


def inspect_case_result(spec, result, requested, component_report=None):
    by_name = {c['name']:c for c in result.get('checks',[])}
    missing = [name for name in requested if name not in by_name]
    if missing:
        return 'blocked', ['Checks were not reported: '+', '.join(missing)]
    if result.get('status')=='blocked':
        return 'blocked', ['Browser environment or build blocked']
    reasons = []
    for name in spec['requiredPass']:
        if name in requested and by_name.get(name,{}).get('status')!='pass':
            reasons.append('Required '+name+' did not pass on '+spec['name'])
    for name in spec.get('expectedNotApplicable',[]):
        if name in requested and by_name.get(name,{}).get('status')!='not_applicable':
            reasons.append('Absent mechanism '+name+' was not recorded as not_applicable')
    if 'components' in requested and spec.get('requiredMechanisms'):
        exercised={c['kind'] for c in (component_report or {}).get('checks',[]) if c.get('status')=='pass'}
        for kind in spec['requiredMechanisms']:
            if kind not in exercised:reasons.append('Required component mechanism was not exercised: '+kind)
    if result.get('caseUnchanged') is not True or result.get('serverStopped') is not True:
        reasons.append('Fixture preservation or server cleanup not verified')
    if reasons or result.get('status')=='fail':
        return 'fail', reasons
    return result.get('status','blocked'), reasons


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',required=True)
    p.add_argument('--node',default=shutil.which('node'))
    p.add_argument('--browser',default=os.environ.get('INTERIOR_BROWSER'))
    p.add_argument('--playwright-module',default=os.environ.get('INTERIOR_PLAYWRIGHT_MODULE'))
    p.add_argument('--checks',default='core,components,floors')
    p.add_argument('--timeout',type=int,default=180,help='Per-browser-test limit in seconds')
    args=p.parse_args(argv)
    requested=selected_checks(args.checks)
    out=Path(args.out).resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        p.error('Use a new empty evidence directory')
    out.mkdir(parents=True,exist_ok=True)
    rows=[]
    report={'schema':'interior-cross-layout-regression/1','requestedChecks':requested,
            'scope':'Independent synthetic layouts, actual generated HTML and isolated browser storage; not customer layout, ergonomic, visual, physical-device or human acceptance',
            'clientCasesRead':False,'installsPerformed':False,'cases':rows}
    try:
        for spec in regression_cases():
            case_path=out/(spec['name']+'.json')
            case_path.write_text(json.dumps(spec['case'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            case_hash=hashlib.sha256(case_path.read_bytes()).hexdigest()
            result_dir=out/spec['name']
            command=[sys.executable,str(ROOT/'scripts/workbench_browser_suite.py'),
                     '--case',str(case_path),'--out',str(result_dir),
                     '--checks',args.checks,'--timeout',str(args.timeout)]
            for option,value in [('--node',args.node),('--browser',args.browser),
                                 ('--playwright-module',args.playwright_module)]:
                if value:command.extend([option,str(value)])
            try:
                run=run_process(command,cwd=ROOT,capture_output=True,text=True,
                                timeout=max(60,args.timeout*len(requested)+30))
                (out/(spec['name']+'.log')).write_text(run.stdout+run.stderr,encoding='utf-8')
                result_file=result_dir/'result.json'
                result=json.loads(result_file.read_text()) if result_file.exists() else {}
                component_file=result_dir/'components/result.json'
                component_report=json.loads(component_file.read_text()) if component_file.exists() else None
                status,reasons=inspect_case_result(spec,result,requested,component_report)
                if run.returncode and status=='pass':status='fail';reasons.append('Suite process failed')
                if hashlib.sha256(case_path.read_bytes()).hexdigest()!=case_hash:
                    status='fail';reasons.append('Synthetic input was modified')
                row={'name':spec['name'],'status':status,'reasons':reasons,'caseSha256':case_hash,
                     'report':str(result_file.relative_to(out)),
                     'checks':{c['name']:c['status'] for c in result.get('checks',[])}}
            except subprocess.TimeoutExpired:
                row={'name':spec['name'],'status':'fail','reasons':['Matrix case timed out']}
            rows.append(row)
            print(json.dumps(row,ensure_ascii=False),flush=True)
    finally:
        report['status']=summarize(rows)
        if len(rows)!=len(regression_cases()):report['status']='blocked'
        report['notApplicable']={r['name']:[k for k,v in r.get('checks',{}).items() if v=='not_applicable'] for r in rows}
        (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(json.dumps({'status':report['status'],'report':str(out/'result.json')},ensure_ascii=False))
    return 0 if report['status']=='pass' else 2


if __name__=='__main__':
    raise SystemExit(main())
