"""Overlap short room observation with safe exitward movement; keep viewing frame counts.
A single continuous observation window is retained per input station. No video capture.
"""
import argparse,bisect,copy,json,math
from pathlib import Path
from design_homeowner_tour import navigation_gaze,entry_apron
from plan_route import Planner,inside
from tour_workflow import retime,markers,metrics,intent_check
from camera_gaze import PROFILE,delta

def dense_path(path,step=20):
    out=[path[0]]
    for a,b in zip(path,path[1:]):
        n=max(1,math.ceil(math.dist(a,b)/step));out.extend([[a[k]+(b[k]-a[k])*j/n for k in (0,1)] for j in range(1,n+1)])
    return out

def safe_path(planner,start,end):
    raw=[start]+planner.astar(start,end)+[end]
    if any(not planner.line_free(a,b) for a,b in zip(raw,raw[1:])):raise ValueError('Grid snap is not safely connected to exact endpoint')
    def checked(points):
        rounded=planner.round(points)
        if any(not planner.line_free(a,b) for a,b in zip(rounded,rounded[1:])):raise ValueError('Rounded path failed safety; replan, do not reuse sharp path')
        return rounded
    try:return checked(planner.simplify(raw))
    except ValueError as original:
        # A shortest polyline may hug a convex obstacle too closely to round.
        # Reserve more space during search, then certify with the unchanged
        # physical body. Atomic endpoints (including explicit waypoints) stay.
        for reserve in (40,80,120):
            roomy=Planner(planner.b,{**planner.cfg,'bodyRadiusMm':planner.radius+reserve})
            try:
                raw=[start]+roomy.astar(start,end)+[end]
                if any(not roomy.line_free(a,b) for a,b in zip(raw,raw[1:])):continue
                return checked(roomy.simplify(raw))
            except ValueError:continue
        raise ValueError('No safe rounded route within bounded additional search clearance') from original

def at_distance(path,d):
    for a,b in zip(path,path[1:]):
        length=math.dist(a,b)
        if d<=length:return [a[k]+(b[k]-a[k])*d/max(1e-9,length) for k in (0,1)]
        d-=length
    return path[-1][:]

def compact(bundle,tour,config,policy):
    from tour_contract import preserve_viewing_floors
    config=copy.deepcopy(config)
    config['viewingDurationFloors']=preserve_viewing_floors(tour,config)
    tour=copy.deepcopy(tour)
    if policy.get('exteriorPoint'):
        tour['frames'][0]['pointMm']=policy['exteriorPoint'][:];tour['frames'][-1]['pointMm']=policy['exteriorPoint'][:]
    profile=json.loads(PROFILE.read_text());limits=profile['reviewLimits'];fps=tour['fps'];marks=markers(tour)
    access,_=entry_apron(bundle,{'entranceOpeningId':policy['entranceOpeningId'],'startPoint':tour['frames'][0]['pointMm'],'bodyRadiusMm':180})
    planner=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':190,'gridMm':50})
    if not 0<policy.get('observationSpeedMps',.6)<=limits['maximumSpeedMps']:raise ValueError('Observation movement must respect existing speed ceiling')
    rooms={r['id']:r['poly'] for r in bundle['model']['rooms']};chapters=copy.deepcopy(config['chapters']);windows={};rows=[]
    for i,ch in enumerate(chapters):
        if ch['phase']!='observe' or ch.get('movingView'):continue
        fs=copy.deepcopy(tour['frames'][marks[ch['from']]:marks[ch['to']]+1]);override=policy.get('observations',{}).get(ch['observationId'],{});point=override.get('point',fs[0]['pointMm']);rid=ch['roomId']
        if planner.blocked(point) or not inside(point,rooms[rid]):raise ValueError('Unsupported observation position '+ch['name'])
        nextch=chapters[i+1];destination=tour['frames'][marks[nextch['to']]]['pointMm']
        nextoverride=policy.get('observations',{}).get(next((q.get('observationId') for q in chapters[i+2:i+3]),''),{})
        destination=nextoverride.get('point',destination)
        path=safe_path(planner,point,destination);dense=dense_path(path)
        drift=[point];distance=0;maximum=override.get('driftMm',policy.get('driftMm',1100));maximum=min(maximum,(len(fs)-1)/fps*policy.get('observationSpeedMps',.6)*1000)
        for q in dense[1:]:
            d=math.dist(drift[-1],q)
            if distance+d>maximum or not inside(q,rooms[rid]):break
            if not planner.line_free(drift[-1],q):break
            drift.append(q);distance+=d
        if override.get('endPoint'):
            end=override['endPoint']
            if not inside(end,rooms[rid]) or not planner.line_free(point,end):raise ValueError('Unsafe viewing motion')
            drift=[point,end];distance=math.dist(point,end)
            if distance>maximum:raise ValueError('Viewing motion exceeds observation speed limit')
        start=math.radians(override['yawDegrees']) if 'yawDegrees' in override else fs[0]['yawRadians'];pan=math.radians(override.get('panDegrees',ch.get('singleSweepDegrees',0)))
        if override.get('reverseSweep'):start=fs[-1]['yawRadians'];pan=fs[0]['yawRadians']-start
        elif 'yawDegrees' not in override:pan=fs[-1]['yawRadians']-start
        ch['singleSweepDegrees']=math.degrees(pan)
        original_yaws=[f['yawRadians'] for f in fs]
        for j,f in enumerate(fs):
            u=j/(len(fs)-1);f['pointMm']=at_distance(drift,distance*u)
            if 'yawDegrees' in override:
                edge=.08;v=u*u/(2*edge*(1-edge)) if u<edge else 1-(1-u)**2/(2*edge*(1-edge)) if u>1-edge else (u-edge/2)/(1-edge)
                f['yawRadians']=start+pan*v
            elif override.get('reverseSweep'):f['yawRadians']=original_yaws[-1-j]
            else:f['yawRadians']=original_yaws[j]
        # Winding is aligned when stitching; angles themselves are geometric.
        windows[ch['from']]=fs;rows.append({'observationId':ch['observationId'],'roomId':rid,'seconds':(len(fs)-1)/fps,'motionMm':distance,'from':point,'to':drift[-1]})
    output=[copy.deepcopy(tour['frames'][0])];visits=[];newmarks={chapters[0]['from']:0};connection_rows=[]
    for i,ch in enumerate(chapters):
        if ch['from'] in windows:
            fs=windows[ch['from']]
            if math.dist(output[-1]['pointMm'],fs[0]['pointMm'])>.01:raise ValueError('Observation start mismatch '+ch['name']+' '+str(output[-1]['pointMm'])+' '+str(fs[0]['pointMm']))
        else:
            source=output[-1];nextwindow=windows.get(ch['to']);destination=nextwindow[0] if nextwindow else tour['frames'][marks[ch['to']]]
            path=safe_path(planner,source['pointMm'],destination['pointMm']);dense=dense_path(path);distances=[0]
            for a,b in zip(dense,dense[1:]):distances.append(distances[-1]+math.dist(a,b))
            nav={**policy.get('navigationPolicy',{}),**policy.get('connections',{}).get(ch['name'],{})}
            if distances[-1]<1:
                n=max(2,math.ceil(abs(delta(source['yawRadians'],destination['yawRadians']))*180/math.pi/32*fps))
                dense=[source['pointMm'][:] for _ in range(n+1)]
                yaws=[source['yawRadians']+delta(source['yawRadians'],destination['yawRadians'])*j/n for j in range(n+1)]
            else:yaws=navigation_gaze(planner,dense,distances,source['yawRadians'],destination['yawRadians'],nav)
            fs=[]
            for j,(q,yaw) in enumerate(zip(dense,yaws)):
                f=copy.deepcopy(source);f.update(frame=j,pointMm=q,yawRadians=yaw,pitchRadians=source['pitchRadians']+(destination['pitchRadians']-source['pitchRadians'])*j/(len(dense)-1));fs.append(f)
            local={'fps':fps,'seconds':len(fs)/fps,'frames':fs,'visits':[{'name':'a','frame':0},{'name':'z','frame':len(fs)-1}]}
            fs=retime(local,{'chapters':[{'name':ch['name'],'from':'a','to':'z','phase':ch['phase'],'minimumSeconds':(marks[ch['to']]-marks[ch['from']])/fps if ch['phase']=='observe' else 0}],'cameraProfile':{'finalSmoothSeconds':0}},limits)['frames']
            connection_rows.append({'chapter':ch['name'],'beforeSeconds':(marks[ch['to']]-marks[ch['from']])/fps,'afterSeconds':(len(fs)-1)/fps})
        shift=output[-1]['yawRadians']+delta(output[-1]['yawRadians'],fs[0]['yawRadians'])-fs[0]['yawRadians']
        for f in fs:f['yawRadians']+=shift
        output.extend(copy.deepcopy(fs[1:]));newmarks[ch['to']]=len(output)-1
    for i,f in enumerate(output):f['frame']=i
    result=copy.deepcopy(tour);result.update(frames=output,seconds=len(output)/fps,visits=[{'name':name,'frame':index,'pointMm':output[index]['pointMm'],'seconds':index/fps} for name,index in newmarks.items()],humanAcceptance='pending',previewOnly=True)
    for key in ('stopFrames','legs','roomTimeline','roomJumpTimes','timingMethod','subjectAudit','qualityReview'):result.pop(key,None)
    config=copy.deepcopy(config);config['chapters']=chapters
    config['cameraKeys']=[{'atStop':chapters[0]['from'],'offsetFrames':i,'targetMm':[f['pointMm'][0]+1000*math.cos(f['yawRadians']),f['pointMm'][1]+1000*math.sin(f['yawRadians']),f['eyeMm']-100],'yawDegrees':math.degrees(f['yawRadians']),'pitchDegrees':math.degrees(f['pitchRadians'])} for i,f in enumerate(output)]
    audit=metrics(result);result['audit']=audit;result['cameraMethod']['thresholdFailures']=[k for k,v in limits.items() if audit[k]>v+1e-6];result['chapterReview']=intent_check(result,config)
    collisions=[i for i,(a,b) in enumerate(zip(output,output[1:])) if planner.blocked(b['pointMm']) or not planner.line_free(a['pointMm'],b['pointMm'])]
    observation_counts=[]
    newmarks=markers(result)
    for ch in chapters:
        if ch['phase']=='observe':
            before=marks[ch['to']]-marks[ch['from']];after=newmarks[ch['to']]-newmarks[ch['from']]
            if after<before:raise ValueError('Viewing duration was compressed')
            observation_counts.append({'name':ch['name'],'beforeFrames':before,'afterFrames':after})
    report={'schema':'homeowner-moving-observation/1','observationFrameCounts':observation_counts,'beforeSeconds':tour['seconds'],'afterSeconds':result['seconds'],'observations':rows,'connections':connection_rows,'collisions':collisions,'motionFailures':result['cameraMethod']['thresholdFailures'],'chapterFailures':result['chapterReview']['failures'],'viewingFrameCountsPreserved':True,'visualReview':'pending','videoGenerated':False}
    from tour_contract import inspect as inspect_contract
    report['contract']=inspect_contract(bundle,result,config)
    report['chapterFailures']+=['Tour contract: '+x['code'] for x in report['contract']['issues']]
    report['status']='needs_revision' if collisions or report['motionFailures'] or report['chapterFailures'] else 'pending_rehearsal_checks'
    return result,config,report

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('bundle','tour','config','policy','out'):ap.add_argument('--'+key,required=True)
    a=ap.parse_args();read=lambda p:json.loads(Path(p).read_text());out=Path(a.out)
    if out.exists():raise ValueError('Fresh output required')
    t,c,r=compact(read(a.bundle),read(a.tour),read(a.config),read(a.policy));out.mkdir(parents=True)
    for name,value in [('tour.json',t),('camera-config.json',c),('compact-report.json',r)]: (out/name).write_text(json.dumps(value,ensure_ascii=False,indent=2))
    print(json.dumps(r,ensure_ascii=False))
    return 2 if r['status']=='needs_revision' else 0
if __name__=='__main__':raise SystemExit(main())
