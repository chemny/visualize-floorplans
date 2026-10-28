"""Final-frame camera evidence. Horizontal proxies never approve rendered visibility."""
import math
from tour_workflow import markers

DEFAULTS={'maximumNearWallSeconds':1.0,'nearWallDistanceMm':900,
          'maximumYawAccelerationDegreesPerSecondSquared':240,
          'maximumPitchAccelerationDegreesPerSecondSquared':120,
          'minimumTargetVisibleSeconds':.25}

def target_anchor(bundle,subject):
    obj=next((o for o in bundle['state']['furniture'] if o['id']==subject),None)
    if obj is None and str(subject).startswith('opening:'):
        key=subject.split(':',1)[1]
        for wall in bundle['state']['walls']:
            for opening in wall['opens']:
                if opening.get('id')==key and not wall.get('demolished'):
                    u=(opening['at']+opening['width']/2)/math.dist(wall['a'],wall['b'])
                    return [wall['a'][i]+u*(wall['b'][i]-wall['a'][i]) for i in (0,1)]+[opening.get('sillHeight',0)+opening.get('height',2100)/2]
    if obj is None:raise ValueError('Unknown ordered viewing target: '+str(subject))
    if not all(isinstance(obj.get(k),(int,float)) and math.isfinite(obj[k]) for k in ('cx','cy')):
        raise ValueError('Ordered viewing target lacks finite position: '+str(subject))
    return [obj['cx'],obj['cy'],obj.get('h',1000)/2]

def target_samples(bundle,subject):
    centre=target_anchor(bundle,subject)
    obj=next((o for o in bundle['state']['furniture'] if o['id']==subject),None)
    if obj is not None:
        angle=math.radians(obj.get('rot',0));w=obj.get('w',0)*.4;d=obj.get('d',0)*.4
        return [centre]+[[centre[0]+u*math.cos(angle)-v*math.sin(angle),centre[1]+u*math.sin(angle)+v*math.cos(angle),centre[2]] for u,v in [(-w,-d),(-w,d),(w,-d),(w,d),(-w,0),(w,0),(0,-d),(0,d)]]
    key=str(subject).split(':',1)[-1]
    for wall in bundle['state']['walls']:
        for opening in wall['opens']:
            if opening.get('id')==key:
                length=math.dist(wall['a'],wall['b']);v=[(wall['b'][i]-wall['a'][i])/length for i in (0,1)]
                return [centre]+[[centre[i]+v[i]*opening['width']*fraction for i in (0,1)]+[centre[2]] for fraction in (-.4,.4)]
    return [centre]

def visibility_planner(bundle,planner,subject):
    # The target's own host wall/leaf is its surface, not an intervening occluder.
    obj=next((o for o in bundle['state']['furniture'] if o['id']==subject),{})
    host=obj.get('assemblyOwner',{}).get('wallId')
    if str(subject).startswith('opening:'):
        key=subject.split(':',1)[1]
        host=next((w['id'] for w in bundle['state']['walls'] if any(o.get('id')==key for o in w['opens'])),None)
    if not host:return planner
    if not hasattr(planner,'_target_planners'):planner._target_planners={}
    if host not in planner._target_planners:
        from plan_route import Planner
        b={**bundle,'state':{**bundle['state'],'walls':[w for w in bundle['state']['walls'] if w['id']!=host]}}
        planner._target_planners[host]=Planner(b,{})
    return planner._target_planners[host]

def ordered_bearings(bundle,ids,point):
    """Resolve real IDs and unwrap their bearings without an invented full revolution."""
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate ordered viewing target')
    yaws=[]
    for subject in ids:
        q=target_anchor(bundle,subject);v=math.atan2(q[1]-point[1],q[0]-point[0])
        if yaws:v=yaws[-1]+math.atan2(math.sin(v-yaws[-1]),math.cos(v-yaws[-1]))
        yaws.append(v)
    diffs=[b-a for a,b in zip(yaws,yaws[1:])]
    if any(v>1e-5 for v in diffs) and any(v< -1e-5 for v in diffs):
        raise ValueError('Ordered targets require reversing the sweep; revise targets or observation point')
    if yaws and abs(yaws[-1]-yaws[0])>math.pi:
        raise ValueError('Ordered target sweep exceeds a half turn; revise observation point')
    return yaws

def inspect(bundle,tour,config,planner):
    from design_homeowner_tour import clear_distance
    policy={**DEFAULTS,**config.get('cameraEvidencePolicy',{})}
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0 for v in policy.values()):
        raise ValueError('Camera evidence thresholds must be finite and positive')
    fs=tour['frames'];fps=tour['fps'];m=markers(tour);issues=[];rows=[];rooms={}
    relaxed=[k for k,v in policy.items() if k in DEFAULTS and ((v<DEFAULTS[k]) if k=='minimumTargetVisibleSeconds' else (v>DEFAULTS[k]))]
    from tour_rules import exception
    if relaxed and not exception(config,'camera_evidence_limit_override'):
        issues.append({'code':'unjustified_camera_evidence_relaxation','thresholds':relaxed})
    fov=config.get('cameraProfile',{}).get('horizontalFovDegrees',76)
    for ch in config['chapters']:
        if ch.get('phase')!='observe' or ch.get('from') not in m or ch.get('to') not in m:continue
        a,z=m[ch['from']],m[ch['to']];room=ch.get('roomId');changes=[math.degrees(g['yawRadians']-f['yawRadians']) for f,g in zip(fs[a:z],fs[a+1:z+1])]
        entry=rooms.setdefault(room if room is not None else '__undeclared__:'+ch['name'],{'positiveDegrees':0,'negativeDegrees':0,'windows':[],'lastYaw':None})
        if entry['lastYaw'] is not None:changes.append(math.degrees(fs[a]['yawRadians']-entry['lastYaw']))
        entry['lastYaw']=fs[z]['yawRadians'];entry['windows'].append(ch['name'])
        entry['positiveDegrees']+=sum(max(0,v) for v in changes);entry['negativeDegrees']+=sum(max(0,-v) for v in changes)
        cursor=a
        explicit_order=bool(ch.get('orderedViewTargets'))
        from tour_core_targets import targets
        for subject in targets(ch):
            subject_ordered=subject in ch.get('orderedViewTargets',[])
            if not subject_ordered:cursor=a
            try:q=target_anchor(bundle,subject)
            except ValueError as e:
                issues.append({'code':'invalid_ordered_view_target','chapter':ch['name'],'subjectId':subject,'message':str(e)});continue
            target_planner=visibility_planner(bundle,planner,subject);samples=target_samples(bundle,subject)
            spans=[];start=None
            for i in range(a,z+1):
                f=fs[i]
                def sample_visible(q):
                    d=math.dist(f['pointMm'],q[:2]);bearing=math.atan2(q[1]-f['pointMm'][1],q[0]-f['pointMm'][0]);off=abs(math.atan2(math.sin(bearing-f['yawRadians']),math.cos(bearing-f['yawRadians'])))
                    return d>1 and d<=7000 and off<=math.radians(fov/2) and clear_distance(target_planner,f['pointMm'],bearing,d)>=d-60
                visible=any(sample_visible(q) for q in samples)
                if visible and start is None:start=i
                if start is not None and (not visible or i==z):
                    end=i if visible else i-1;spans.append((start,end));start=None
            need=max(1,math.ceil(policy['minimumTargetVisibleSeconds']*fps))
            match=next(((max(s,cursor),e) for s,e in spans if e-max(s,cursor)+1>=need),None)
            row={'chapter':ch['name'],'subjectId':subject,'visibleSpansFrames':spans,'orderedWindowFrames':None}
            if match:
                begin,end=match;row['orderedWindowFrames']=[begin,begin+need-1];cursor=begin+need
            else:issues.append({'code':'ordered_target_not_visible_in_sequence','chapter':ch['name'],'subjectId':subject})
            rows.append(row)
    for room,row in rooms.items():
        row.pop('lastYaw')
        if not str(room).startswith('__undeclared__:') and min(row['positiveDegrees'],row['negativeDegrees'])>1:
            issues.append({'code':'room_wide_sweep_reversal','roomId':room,**row})
    # Sample the full timeline, including exit/transit; not just chosen refinements.
    stride=max(1,round(fps/8));run=longest=total=0;wall_spans=[];run_start=None
    for i in range(0,len(fs),stride):
        f=fs[i];n=min(stride,len(fs)-i)
        wall=sum(clear_distance(planner,f['pointMm'],f['yawRadians']+math.radians(v),policy['nearWallDistanceMm'])<policy['nearWallDistanceMm'] for v in (-30,-15,0,15,30))>=4
        if wall and run_start is None:run_start=i
        if not wall and run_start is not None:wall_spans.append([run_start,i]);run_start=None
        run=run+n if wall else 0;longest=max(longest,run);total+=n if wall else 0
    if run_start is not None:wall_spans.append([run_start,len(fs)])
    if longest/fps>policy['maximumNearWallSeconds']:
        issues.append({'code':'sustained_wall_facing','longestSeconds':longest/fps})
    acceleration={};peak_frames={}
    for axis,cap in [('yawRadians','maximumYawAccelerationDegreesPerSecondSquared'),('pitchRadians','maximumPitchAccelerationDegreesPerSecondSquared')]:
        speeds=[math.degrees(g.get(axis,0)-f.get(axis,0))*fps for f,g in zip(fs,fs[1:])]
        values=[abs(y-x)*fps for x,y in zip(speeds,speeds[1:])];peak=max(values,default=0);acceleration[axis]=peak;peak_frames[axis]=values.index(peak)+1 if values else None
        if peak>policy[cap]+1e-6:issues.append({'code':'camera_angular_acceleration','axis':axis,'actual':peak,'maximum':policy[cap]})
    return {'schema':'homeowner-camera-evidence/1','issues':issues,'policy':policy,'orderedTargetWindows':rows,'roomSweeps':rooms,'roomAggregationStatus':'metadata_incomplete' if any(str(r).startswith('__undeclared__:') for r in rooms) or not rooms else 'evaluated',
            'wallFacing':{'longestSeconds':longest/fps,'totalSeconds':total/fps,'sampleStrideFrames':stride,'spansFrames':wall_spans},
            'angularAcceleration':acceleration,'angularAccelerationPeakFrames':peak_frames,'basis':'Final frames; horizontal wall/door and inset target-bound samples only. Actual mesh visibility and playback comfort remain pending.'}

def require_actual_targets(config,tour,audit,bundle=None):
    """Bind real mesh-audit samples to the same final observation chapters and order."""
    m=markers(tour);fps=tour['fps'];policy=audit.get('policy',{});minimum=max(DEFAULTS['minimumTargetVisibleSeconds'],policy.get('minContinuousSeconds',0))
    max_gap=1.5/max(1,policy.get('sampleHz',2))+1/fps
    for ch in config['chapters']:
        if ch.get('phase')!='observe':continue
        from tour_core_targets import targets
        ordered=ch.get('orderedViewTargets',[]);ids=targets(ch);a,z=m[ch['from']]/fps,m[ch['to']]/fps;cursor=a
        for subject in ids:
            if subject not in ordered:cursor=a
            runs=[];start=last=None
            for row in audit.get('chapters',[]):
                if row.get('startSeconds',-1)<a-1/fps or row.get('endSeconds',float('inf'))>z+1/fps:continue
                start=last=None
                for sample in row.get('samples',[]):
                    tm=sample['seconds'];v=sample.get('subjects',{}).get(subject,{})
                    ok=(cursor<=tm<=z and v.get('unoccludedSamples',0)>=policy.get('minVisibleSamples',3) and v.get('unoccludedSamples',0)/max(1,v.get('totalSamples',0))>=policy.get('minVisibleFraction',.03) and v.get('screenAreaFraction',0)>=policy.get('minScreenAreaFraction',.01))
                    if not ok:start=last=None;continue
                    if start is None or tm-last>max_gap:start=tm
                    last=tm
                    if last-start+1e-6>=minimum:runs.append((start,last));break
            if not runs:raise ValueError('Actual target audit missing/occluded/out of order: '+subject+' / '+ch['name'])
            if subject in ordered:cursor=min(runs)[1]
    if bundle is not None:
        from tour_core_targets import readability
        result=readability(bundle,config,audit.get('chapters',[]),policy,fps)
        if result['issues']:raise ValueError('Actual core facility audit incomplete: '+str(result['issues']))
    return True
