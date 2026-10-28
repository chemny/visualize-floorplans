"""Read-only three-case verification from explicit local manifest; never renders video.
Reports historical acceptance separately from current policy and mutation detection.
"""
import argparse,copy,json,math
from pathlib import Path
from tour_workflow import sha,metrics,markers
from plan_route import Planner
from tour_contract import inspect as contract
from tour_camera_evidence import inspect as evidence

def read(path):return json.loads(Path(path).read_text())
def audit_case(row):
    t=read(row['tour']);c=read(row['config'])
    if row.get('bundle'):b=read(row['bundle'])
    elif row.get('scene'):b=read(row['scene'])
    else:
        case=read(row['case']);b={'schemeSha256':case['sourceSchemeSha256'],'model':case['model'],'state':read(row['state'])}
    if b['schemeSha256']!=t['schemeSha256']:raise ValueError('Case geometry identity mismatch: '+row['name'])
    sources={k:{'path':str(Path(row[k]).resolve()),'sha256':sha(row[k])} for k in ('tour','config','bundle','scene','case','state') if row.get(k)}
    p=Planner(b,{'bodyRadiusMm':c.get('tourContract',{}).get('bodyRadiusMm',180),'accessPolygons':c.get('accessPolygons',[]),'gridMm':50})
    full=contract(b,t,c);base=evidence(b,t,c,p)
    m=markers(t);chapters=[]
    for ch in c['chapters']:
        a,z=m[ch['from']],m[ch['to']];fs=t['frames'][a:z+1];travel=[math.degrees(g['yawRadians']-f['yawRadians']) for f,g in zip(fs,fs[1:])]
        chapters.append({'name':ch['name'],'phase':ch.get('phase','historical_not_declared'),'roomId':ch.get('roomId'),
                         'startSeconds':a/t['fps'],'endSeconds':z/t['fps'],'positiveYawDegrees':sum(max(0,v) for v in travel),'negativeYawDegrees':sum(max(0,-v) for v in travel),
                         'lengthM':sum(math.dist(f['pointMm'],g['pointMm']) for f,g in zip(fs,fs[1:]))/1000})
    # Corrupt copies of actual sampled routes, not hand-built fixture trajectories.
    idx=next((i for i,ch in enumerate(c['chapters']) if ch.get('phase')=='observe'),0)
    bad=copy.deepcopy(c);bad['chapters'][idx].update(phase='observe',orderedViewTargets=['__missing_regression_target__'])
    unknown=evidence(b,t,bad,p)['issues']
    kink=copy.deepcopy(t);at=len(t['frames'])//2;kink['frames'][at]['yawRadians']+=.5
    kink_result=evidence(b,kink,c,p)['issues']
    reverse_t=copy.deepcopy(t);reverse_c=copy.deepcopy(c);old=reverse_c['chapters'][idx];a,z=m[old['from']],m[old['to']];cut=(a+z)//2
    # Markers use the same convention as the real source (stopFrames or visits).
    marker_key='stopFrames' if reverse_t.get('stopFrames') else 'visits';reverse_t[marker_key].append({'name':'__regression_split__','frame':cut})
    common={**old,'phase':'observe','roomId':'__same_real_window__','subjects':[],'orderedViewTargets':[]}
    reverse_c['chapters'][idx:idx+1]=[{**common,'name':'mutation-one','to':'__regression_split__'},{**common,'name':'mutation-two','from':'__regression_split__'}]
    for i in range(a,z+1):reverse_t['frames'][i]['yawRadians']=math.radians(12*(i-a)/max(1,cut-a) if i<=cut else 12-12*(i-cut)/max(1,z-cut))
    reverse_result=evidence(b,reverse_t,reverse_c,p)['issues']
    from design_homeowner_tour import clear_distance
    wall_pose=next((f for f in t['frames'] if sum(clear_distance(p,f['pointMm'],f['yawRadians']+math.radians(v),900)<900 for v in (-30,-15,0,15,30))>=4),None)
    wall_t=copy.deepcopy(t)
    if wall_pose is not None:
        for i in range(min(len(wall_t['frames']),math.ceil(2*t['fps']))):wall_t['frames'][i]=copy.deepcopy(wall_pose)
    wall_result=evidence(b,wall_t,c,p)['issues']
    legacy=copy.deepcopy(c);legacy.pop('tourContract',None);legacy_result=contract(b,t,legacy)
    mutations={'sustainedWallPoseRejected':wall_pose is not None and any(x['code']=='sustained_wall_facing' for x in wall_result),'legacyContractRejected':any(x['code']=='missing_tour_contract' for x in legacy_result['issues']),'missingTargetRejected':any(x['code']=='invalid_ordered_view_target' for x in unknown),
               'angularKinkRejected':any(x['code']=='camera_angular_acceleration' for x in kink_result),
               'wholeRoomOppositeSweepsRejected':any(x['code']=='room_wide_sweep_reversal' for x in reverse_result)}
    return {'name':row['name'],'sources':sources,'seconds':t['seconds'],'historicalAcceptance':row.get('historicalAcceptance','not_accepted'),
            'currentContract':full,'cameraEvidence':base,'chapterGeometry':chapters,'mutationChecks':mutations,
            'sourceMetadataGaps':[ch['name'] for ch in c['chapters'] if ch.get('phase')!='transit' and (not ch.get('roomId') or ch.get('singleSweepDegrees') is None)],
            'actual3DPlayback':'not_performed','acceptedMediaModified':False}

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--manifest',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Fresh report directory required')
    manifest=read(a.manifest);rows=[audit_case(row) for row in manifest['cases']];out.mkdir(parents=True)
    for i,row in enumerate(rows,1):(out/f'case-{i}.json').write_text(json.dumps(row,ensure_ascii=False,indent=2))
    result={'schema':'homeowner-tour-case-matrix/1','cases':[{'name':r['name'],'seconds':r['seconds'],'historicalAcceptance':r['historicalAcceptance'],'currentContractStatus':r['currentContract']['status'],'contractIssueCodes':sorted({x['code'] for x in r['currentContract']['issues']}),'missingObservationMetadataCount':len(r['sourceMetadataGaps']),'roomAggregationStatus':r['cameraEvidence']['roomAggregationStatus'],'cameraIssueCodes':sorted({x['code'] for x in r['cameraEvidence']['issues']}),'mutations':r['mutationChecks'],'actual3DPlayback':r['actual3DPlayback']} for r in rows],'engineSources':{name:sha(Path(__file__).with_name(name)) for name in ('tour_contract.py','tour_camera_evidence.py','design_homeowner_tour.py','route_rehearsal.py','preview_gate.mjs','h5.py','h5_browser.mjs','run_production.py','import_blender.py','audit_tour_case_matrix.py')},'allMutationsRejected':all(all(r['mutationChecks'].values()) for r in rows),'limitations':['Historical acceptance preserved; new rules do not retroactively revoke accepted media','Current source geometry and final frames checked; no browser playback or actual rendered occlusion acceptance','No scene, case or video changed']}
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
    return 0 if result['allMutationsRejected'] else 2
if __name__=='__main__':raise SystemExit(main())
