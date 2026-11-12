"""Seconds-long camera draft: design, gaze smoothing, numeric contract, per-chapter diagnostics.

Optional real mesh audit when a runtime is given. Skips the 10-minute candidate search, so use it
to iterate on a brief and let plan-tour confirm. Output is never for confirmation.
"""
import argparse,json,math,shutil,subprocess,time
from collections import Counter
from pathlib import Path
from plan_route import Planner
from tour_stage_gate import read

SCHEMA='homeowner-tour-draft/1'

def draft(bundle_path,brief_path,out,runtime=None,node=None,write=True):
    from design_homeowner_tour import design,entry_apron
    from tour_pipeline import finalize_gaze
    from tour_contract import inspect as contract
    from tour_choreography import inspect as choreography
    from tour_camera_diagnostics import build as diagnostics
    started=time.monotonic();bundle=read(bundle_path);brief=read(brief_path)
    tour,config,_=design(bundle,brief);final=finalize_gaze(tour,config,.2);report=contract(bundle,final,config);turns=choreography(final,config)
    access,_=entry_apron(bundle,brief);planner=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':brief.get('bodyRadiusMm',180),'gridMm':50})
    out=Path(out);audit=None
    if write:
        if out.exists():raise ValueError('Use a new draft directory')
        out.mkdir(parents=True)
        for name,value in (('tour.json',final),('camera-config.json',config)):(out/name).write_text(json.dumps(value,ensure_ascii=False))
        if runtime:
            node=node or shutil.which('node')
            if not node:raise ValueError('Existing Node.js required for the mesh audit')
            done=subprocess.run([node,str(Path(__file__).with_name('tour_mesh_preflight.mjs')),'--runtime',str(runtime),'--tour',str(out/'tour.json'),'--config',str(out/'camera-config.json'),'--out',str(out/'mesh-subject-audit.json')],capture_output=True,text=True)
            if done.returncode:raise ValueError('Mesh audit failed: '+(done.stderr or done.stdout)[-300:])
            audit=read(out/'mesh-subject-audit.json')
    diag=diagnostics(bundle,final,config,planner,audit)
    transit=[row['yawTravelDegrees'] for row in diag['chapters'] if row['phase']=='transit']
    summary={'schema':SCHEMA,'status':'draft_not_for_confirmation','elapsedSeconds':round(time.monotonic()-started,1),'totalSeconds':final['seconds'],'transitFraction':diag['transitFraction'],
             'stations':len([r for r in diag['chapters'] if r['phase']=='observe']),'maxTransitTurnDegrees':round(max(transit,default=0)),
             'contractIssues':dict(Counter(x['code'] for x in report['issues'])),'meshIssues':dict(Counter(x['code'] for x in (audit or {}).get('screenQuality',{}).get('issues',[]))) if audit else None,
             'meshChecked':audit is not None,'approvalGranted':False,'videoGenerated':False}
    if write:
        for name,value in (('contract-report.json',report),('camera-diagnostics.json',diag),('draft-summary.json',summary)):(out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2))
    return summary,diag,report

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--bundle',required=True);a.add_argument('--brief',required=True);a.add_argument('--out',required=True);a.add_argument('--runtime');a.add_argument('--node')
    v=a.parse_args();summary,_,_=draft(v.bundle,v.brief,v.out,v.runtime,v.node);print(json.dumps(summary,ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError) as e:raise SystemExit(str(e))
