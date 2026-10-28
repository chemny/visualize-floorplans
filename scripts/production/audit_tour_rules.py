"""Audit existing case data without migration, preview generation, video or source mutation."""
import argparse,copy,json,hashlib
from pathlib import Path
from tour_contract import inspect as contract
from tour_rules import inspect as rules,trajectory,RULESET,review_state

def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def audit(bundle,tour,config):
    full=contract(bundle,tour,config);base=rules(tour,config)
    cases=[('height',lambda t,c:[f.update(eyeMm=c.get('cameraProfile',{}).get('eyeMm',1600)+50) for f in t['frames']],'camera_profile_frame_mismatch'),
           ('targets',lambda t,c:[ch.update(subjects=[],orderedViewTargets=[]) for ch in c['chapters'] if ch['phase']=='observe'],'missing_view_targets'),
           ('role',lambda t,c:[ch.pop('tourRole',None) for ch in c['chapters']],'missing_or_invalid_tour_role'),
           ('budgets',lambda t,c:c.pop('roomBudgetPolicy',None),'missing_room_visit_budgets'),
           ('observationLimits',lambda t,c:c.setdefault('observationPointPolicy',{}).update(maximumStillSeconds=100,maximumSecondsPerPoint=100),'unexplained_observation_limit_override')]
    trials=[]
    for name,mutate,code in cases:
        t,c=copy.deepcopy(tour),copy.deepcopy(config);mutate(t,c);r=rules(t,c)
        trials.append({'name':name,'expectedCode':code,'detected':any(i['code']==code for i in r['issues']),'alreadyPresentInSource':any(i['code']==code for i in base['issues'])})
    return {'schema':'homeowner-rules-case-audit/1','rulesetVersion':RULESET,'numericContract':full,'executionRules':base,'trajectory':trajectory(tour,config),'mutationChecks':trials,'allFiveDetected':all(x['detected'] for x in trials),'actualPlayback':'not_performed','humanAcceptance':'pending','previewModified':False,'videoGenerated':False}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('bundle','tour','config','out'):ap.add_argument('--'+key,required=True)
    ap.add_argument('--mesh-audit');ap.add_argument('--visual-feedback');a=ap.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Use a fresh audit file')
    inputs={k:{'path':str(Path(getattr(a,k)).resolve()),'sha256':sha(getattr(a,k))} for k in ('bundle','tour','config')}
    r=audit(read(a.bundle),read(a.tour),read(a.config));r['inputs']=inputs
    if a.mesh_audit:
        mesh=read(a.mesh_audit)
        if mesh.get('tourSha256')!=sha(a.tour) or mesh.get('configSha256')!=sha(a.config) or mesh.get('schemeSha256')!=read(a.tour)['schemeSha256']:raise ValueError('Stale mesh audit')
        r['screenQuality']={k:v for k,v in mesh.get('screenQuality',{}).items() if k!='samples'};r['meshAudit']={'path':str(Path(a.mesh_audit).resolve()),'sha256':sha(a.mesh_audit),'status':mesh['status']}
    if a.visual_feedback:
        visual=read(a.visual_feedback)
        if visual['tourSha256']!=sha(a.tour):raise ValueError('Stale visual feedback')
        r['knownVisualFindings']=visual['issues'];r['historicalPlaybackEvidence']=visual.get('method')
        r['currentGateState']=review_state(r['numericContract']['status'],r.get('meshAudit',{}).get('status','not_performed'),visual.get('result','pending'))
    r['sourceFilesUnchanged']=all(sha(x['path'])==x['sha256'] for x in inputs.values())
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2));print(json.dumps({'fiveMissingChecksDetected':r['allFiveDetected'],'numericStatus':r['numericContract']['status'],'issueCodes':sorted({x['code'] for x in r['numericContract']['issues']}),'sourceFilesUnchanged':r['sourceFilesUnchanged']},ensure_ascii=False))
    return 0 if r['allFiveDetected'] and r['sourceFilesUnchanged'] else 2
if __name__=='__main__':raise SystemExit(main())
