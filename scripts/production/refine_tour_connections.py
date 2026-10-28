"""Refine selected transit gaze with shared spatial planning, preserving all other frames.
Never captures video. Source observation frame spans remain byte-equivalent (except indices).
"""
import argparse,bisect,copy,json,math
from pathlib import Path
from design_homeowner_tour import navigation_gaze,clear_distance,entry_apron
from plan_route import Planner
from tour_workflow import retime,markers,metrics,intent_check
from camera_gaze import PROFILE

def wall_risk(frames,planner,fps):
    flags=[]
    for f in frames:
        flags.append(sum(clear_distance(planner,f['pointMm'],f['yawRadians']+math.radians(a))<900 for a in (-30,-15,0,15,30))>=4)
    run=longest=0
    for flag in flags:run=run+1 if flag else 0;longest=max(longest,run)
    return {'nearWallSeconds':sum(flags)/fps,'longestNearWallSeconds':longest/fps,'basis':'2D wall/door ray proxy; not visual playback'}

def refine(bundle,tour,config,selection,policy):
    access,_=entry_apron(bundle,{'entranceOpeningId':selection['entranceOpeningId'],'startPoint':tour['frames'][0]['pointMm'],'bodyRadiusMm':180})
    planner=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':180,'gridMm':50})
    limits=json.loads(PROFILE.read_text())['reviewLimits'];oldmarks=markers(tour);fps=tour['fps'];out=copy.deepcopy(tour);output=[copy.deepcopy(tour['frames'][0])];newmarks={0:0};rows=[];targets=set(selection['chapters']);seen=set()
    for ch in config['chapters']:
        a,z=oldmarks[ch['from']],oldmarks[ch['to']];original=tour['frames'][a:z+1];chosen=original
        if ch['name'] in targets:
            seen.add(ch['name'])
            if ch['phase']!='transit':raise ValueError('Only pure transit chapters may be refined')
            arc=[0]
            for f,g in zip(original,original[1:]):arc.append(arc[-1]+math.dist(f['pointMm'],g['pointMm']))
            distances=[arc[-1]*i/max(1,math.ceil(arc[-1]/35)) for i in range(max(1,math.ceil(arc[-1]/35))+1)]
            dense=[]
            for d in distances:
                k=max(0,min(len(arc)-2,bisect.bisect_right(arc,d)-1));u=(d-arc[k])/max(1e-9,arc[k+1]-arc[k]);dense.append([original[k]['pointMm'][j]*(1-u)+original[k+1]['pointMm'][j]*u for j in (0,1)])
            local_policy={**policy,**selection.get('chapterPolicies',{}).get(ch['name'],{})}
            yaws=navigation_gaze(planner,dense,distances,original[0]['yawRadians'],original[-1]['yawRadians'],local_policy)
            f=[]
            for i,(point,yaw) in enumerate(zip(dense,yaws)):
                u=i/(len(dense)-1);v=copy.deepcopy(original[0]);v.update(frame=i,pointMm=point,yawRadians=yaw,pitchRadians=original[0]['pitchRadians']*(1-u)+original[-1]['pitchRadians']*u);f.append(v)
            local={'fps':fps,'seconds':len(f)/fps,'frames':f,'visits':[{'name':'a','frame':0},{'name':'z','frame':len(f)-1}]}
            local_config={'chapters':[{'name':ch['name'],'from':'a','to':'z','phase':'transit'}],'cameraProfile':{'finalSmoothSeconds':0}}
            proposal=retime(local,local_config,limits)['frames']
            # Match unwrapped endpoint orientations before stitching unchanged rooms.
            winding=proposal[-1]['yawRadians']-original[-1]['yawRadians']
            if abs(winding)>1e-6:raise ValueError('Connection changes gaze winding at an unchanged room boundary')
            proposal[0]=copy.deepcopy(original[0]);proposal[-1]=copy.deepcopy(original[-1])
            before=wall_risk(original,planner,fps);after=wall_risk(proposal,planner,fps)
            mm=metrics({'frames':proposal,'fps':fps})
            collisions=[i for i,(v,w) in enumerate(zip(proposal,proposal[1:])) if planner.blocked(w['pointMm']) or not planner.line_free(v['pointMm'],w['pointMm'])]
            accepted=(len(proposal)<len(original) and not collisions and all(mm[k]<=v+1e-6 for k,v in limits.items()) and after['longestNearWallSeconds']<=before['longestNearWallSeconds']+.15)
            if accepted:chosen=proposal
            rows.append({'chapter':ch['name'],'beforeSeconds':(len(original)-1)/fps,'afterSeconds':(len(chosen)-1)/fps,'candidateSeconds':(len(proposal)-1)/fps,'applied':accepted,'beforeWallRisk':before,'candidateWallRisk':after,'motion':mm,'collisions':collisions})
        newmarks[a]=len(output)-1;output.extend(copy.deepcopy(chosen[1:]));newmarks[z]=len(output)-1
    if seen!=targets:raise ValueError('Unknown transit selection')
    for i,f in enumerate(output):f['frame']=i
    for kind in ('visits','stopFrames'):
        for v in out.get(kind,[]):
            k='frameIndex' if 'frameIndex' in v else 'frame';v[k]=newmarks[v[k]];v['seconds']=v[k]/fps
    out.update(frames=output,seconds=len(output)/fps,humanAcceptance='pending',previewOnly=True)
    for k in ('roomTimeline','roomJumpTimes','subjectAudit','qualityReview','timingMethod'):out.pop(k,None)
    out['audit']={**metrics(out),'meshAndSubjectAudit':'pending after selected transit refinement'}
    out['cameraMethod']['thresholdFailures']=[k for k,v in limits.items() if out['audit'][k]>v+1e-6]
    out['chapterReview']=intent_check(out,config)
    unchanged=[];updatedmarks=markers(out)
    for ch in config['chapters']:
        if ch['name'] in targets:continue
        old=tour['frames'][oldmarks[ch['from']]:oldmarks[ch['to']]+1];new=out['frames'][updatedmarks[ch['from']]:updatedmarks[ch['to']]+1]
        canonical=lambda xs:[{k:v for k,v in f.items() if k!='frame'} for f in xs]
        if canonical(old)!=canonical(new):raise ValueError('Unselected chapter changed')
        unchanged.append(ch['name'])
    report={'schema':'homeowner-connection-refinement/1','policy':policy,'connections':rows,'unchangedChapters':unchanged,'beforeSeconds':tour['seconds'],'afterSeconds':out['seconds'],'observationFramesPreserved':True,'visualReview':'pending','videoGenerated':False}
    from tour_contract import preserve_viewing_floors,inspect as inspect_contract
    checked_config=copy.deepcopy(config);checked_config['viewingDurationFloors']=preserve_viewing_floors(tour,config)
    report['contract']=inspect_contract(bundle,out,checked_config)
    report['status']='needs_revision' if report['contract']['issues'] else 'pending_rehearsal_checks'
    return out,report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('bundle','tour','config','selection','out'):ap.add_argument('--'+key,required=True)
    ap.add_argument('--turn-effort-weight',type=float,default=3);a=ap.parse_args();out=Path(a.out)
    if out.exists():raise ValueError('Fresh output required')
    read=lambda p:json.loads(Path(p).read_text());bundle,tour,config,selection=map(read,(a.bundle,a.tour,a.config,a.selection))
    from tour_contract import preserve_viewing_floors,inspect as inspect_contract
    config['viewingDurationFloors']=preserve_viewing_floors(tour,config)
    result,report=refine(bundle,tour,config,selection,{'forwardWeight':6,'broadWallPenalty':80,'excessTurnPerStepWeight':a.turn_effort_weight,'avoidBroadWallViews':True})
    # Rebind camera keys to the refined frame indices and gaze; never retain stale offsets.
    oldmarks=markers(tour);newmarks=markers(result);keys={}
    for key in config['cameraKeys']:
        index=oldmarks[key['atStop']]+key.get('offsetFrames',0)
        for ch in config['chapters']:
            a,z=oldmarks[ch['from']],oldmarks[ch['to']]
            if a<=index<=z:
                at=round(newmarks[ch['from']]+(index-a)/(z-a)*(newmarks[ch['to']]-newmarks[ch['from']]))
                f=result['frames'][at];keys[at]={'atStop':config['chapters'][0]['from'],'offsetFrames':at,'targetMm':[f['pointMm'][0]+1000*math.cos(f['yawRadians']),f['pointMm'][1]+1000*math.sin(f['yawRadians']),f['eyeMm']-100],'yawDegrees':math.degrees(f['yawRadians']),'pitchDegrees':math.degrees(f['pitchRadians'])};break
    config['cameraKeys']=[keys[i] for i in sorted(keys)]
    report['contract']=inspect_contract(bundle,result,config)
    report['status']='needs_revision' if report['contract']['issues'] else 'pending_rehearsal_checks'
    out.mkdir(parents=True)
    for name,value in [('tour.json',result),('camera-config.json',config),('connection-report.json',report)]: (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False))
    return 2 if report['status']=='needs_revision' else 0
if __name__=='__main__':raise SystemExit(main())
