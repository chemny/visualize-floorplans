"""One local planning job -> joint candidates -> bounded repairs -> synchronized rehearsal.
No video, no auto-approval, no policy relaxation. Local deterministic planner.
"""
import argparse,copy,json,math,shutil,time,subprocess
from pathlib import Path
from plan_route import Planner,inside
from camera_gaze import PROFILE,delta,smooth
from tour_workflow import markers,metrics,sha,chapter_limits,edge_limits
from tour_contract import inspect as contract,preserve_viewing_floors
from compact_tour_visits import safe_path,at_distance,dense_path
from design_homeowner_tour import entry_apron,navigation_gaze,opening_candidates,clear_distance
from tour_camera_evidence import target_anchor,ordered_bearings,visibility_planner,target_samples
from tour_candidate_quality import (attach_screen_evidence,segment_effort,resample_segment,
    framing_cost,pitch_candidates,smooth_position_seams,protect_satisfied_constraints,connection_effort)
from tour_speed_profile import profile as speed_profile,sample as speed_sample,coupled_clock,spatial_time


def read(p):return json.loads(Path(p).read_text())
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2))
def length(p):return sum(math.dist(a,b) for a,b in zip(p,p[1:]))

def revision_scope(tour,config,value):
    """Resolve explicitly authorized transit chapters to immutable frame masks."""
    if value is None:return None
    if not isinstance(value,dict):raise ValueError('Revision scope must be an object')
    names=value.get('chapters');axes=value.get('axes',['pointMm','yawRadians'])
    if not isinstance(names,list) or not names or len(names)!=len(set(names)):raise ValueError('Explicit unique revision chapters required')
    if not isinstance(axes,list) or not axes or len(axes)!=len(set(axes)) or any(a not in ('pointMm','yawRadians','pitchRadians') for a in axes):raise ValueError('Explicit revision axes required')
    by_name={ch['name']:ch for ch in config['chapters']};marks=markers(tour);last=len(tour['frames'])-1
    allowed={a:[] for a in axes}
    for name in names:
        ch=by_name.get(name)
        if not ch or ch['phase']!='transit':raise ValueError('Scoped native repair accepts actual transit chapters only')
        a,z=marks[ch['from']],marks[ch['to']]
        for axis in axes:
            end=z if z==last and axis!='pointMm' else z-1
            if end>=a+1:allowed[axis].append([a+1,end])
    if value.get('preserveViewingWindows',True) is not True:raise ValueError('Scoped repair must preserve viewing windows')
    return {'chapters':names[:],'allowedChanges':allowed,'preserveViewingWindows':True,'preserveTiming':True,'baselineConfig':copy.deepcopy(config)}

def scope_check(baseline,tour,config,scope):
    if scope is None:return {'status':'not_requested','issues':[]}
    issues=[];a,b=baseline['frames'],tour['frames']
    if len(a)!=len(b) or baseline['fps']!=tour['fps'] or baseline['seconds']!=tour['seconds'] or baseline.get('visits')!=tour.get('visits'):
        issues.append({'code':'revision_scope_changed','field':'timebase_or_visits'})
    allowed=scope['allowedChanges'];violations=[]
    for i,(one,two) in enumerate(zip(a,b)):
        for key in one.keys()|two.keys():
            if one.get(key)!=two.get(key) and not any(lo<=i<=hi for lo,hi in allowed.get(key,[])):
                if len(violations)<8:violations.append({'frame':i,'field':key})
    if violations:issues.append({'code':'revision_scope_changed','samples':violations})
    if config!=scope.get('baselineConfig',config):issues.append({'code':'revision_scope_changed','field':'config'})
    return {'status':'pass' if not issues else 'failed','issues':issues}

def attach_doorway_evidence(bundle,tour,config,report):
    from tour_doorway import doorway_report
    report=copy.deepcopy(report)
    report.setdefault('checks',{})['doorwayComposition']=doorway_report(bundle,tour,config)
    return report
def attach_spatial_evidence(report,spatial,tour):
    """A candidate leaving the approved route never wins; it returns to route confirmation."""
    if not spatial:return report
    from tour_spatial_plan import conformance
    result=conformance(spatial['value'],tour)
    report.setdefault('checks',{})['spatialRoute']=result
    report['issues']+=[{**i,'message':'Candidate leaves the approved spatial route'} for i in result['issues']]
    if result['issues']:report['status']='needs_revision'
    return report
def apply_timing_locks(tour,config,preserve_connection_clock=False):
    """Allocate only connection slack; never shorten a locked viewing window.
    This does not relax motion limits: the final contract still rejects unsafe
    resampling. If the minimum connection work cannot fit, reject the candidate.
    """
    locks=config.get('timingLocks',{})
    if not locks:return tour
    fps=tour['fps'];m=markers(tour);chapters=config['chapters']
    if locks.get('fps',fps)!=fps:raise ValueError('Locked fps differs')
    counts=[m[c['to']]-m[c['from']] for c in chapters]
    fixed={i:locks.get('viewingFrames',{}).get(c['name'],counts[i]) for i,c in enumerate(chapters) if c['phase']=='observe'}
    if any(counts[i]!=n for i,n in fixed.items()):raise ValueError('Locked observation changed during rebuilding: '+str({chapters[i]['name']:{'actualFrames':counts[i],'lockedFrames':n} for i,n in fixed.items() if counts[i]!=n}))
    if 'totalFrames' not in locks:return tour
    free=[i for i,c in enumerate(chapters) if c['phase']!='observe']
    available=locks['totalFrames']-1-sum(fixed.values())
    limits={**read(PROFILE)['reviewLimits'],**config.get('motionReviewLimits',{})}
    work={i:segment_effort(tour['frames'][m[chapters[i]['from']]:m[chapters[i]['to']]+1],chapter_limits(limits,chapters[i])) for i in free}
    minimum={i:max(1,math.ceil(sum(work[i])*fps-1e-8)) for i in free}
    if preserve_connection_clock:minimum={i:max(minimum[i],counts[i]) for i in free}
    if available<sum(minimum.values()):raise ValueError(f'Connections cannot fit locked total time without exceeding minimum effort: required {sum(minimum.values())}, available {available} frames')
    slack=available-sum(minimum.values())
    if not free and slack:raise ValueError('No connection available for locked timing slack')
    weights={i:max(0,counts[i]-minimum[i]) for i in free}
    if not sum(weights.values()):weights={i:1 for i in free}
    denominator=sum(weights.values()) or 1
    additions={i:slack*weights[i]/denominator for i in free}
    allocation={i:minimum[i]+int(additions[i]) for i in free}
    for i in sorted(free,key=lambda i:additions[i]-int(additions[i]),reverse=True)[:available-sum(allocation.values())]:allocation[i]+=1
    allocation.update(fixed)
    frames=[copy.deepcopy(tour['frames'][0])];visits=[{'name':chapters[0]['from'],'frame':0}]
    for i,c in enumerate(chapters):
        source=tour['frames'][m[c['from']]:m[c['to']]+1];n=allocation[i]
        if n==len(source)-1:chunk=copy.deepcopy(source)
        else:chunk=resample_segment(source,n,None if preserve_connection_clock else work.get(i))
        frames.extend(chunk[1:]);visits.append({'name':c['to'],'frame':len(frames)-1})
    for i,f in enumerate(frames):f['frame']=i
    return {**tour,'frames':frames,'visits':visits,'seconds':len(frames)/fps}
def unwrap(values):
    out=[values[0]]
    for v in values[1:]:out.append(out[-1]+delta(out[-1],v))
    return out

def project_monotone(values,sign):
    if not sign:return values[:]
    blocks=[]
    for value in values:
        blocks.append([value*sign,1])
        while len(blocks)>1 and blocks[-2][0]>blocks[-1][0]:
            b=blocks.pop();a=blocks.pop();n=a[1]+b[1];blocks.append([(a[0]*a[1]+b[0]*b[1])/n,n])
    return [v*sign for v,n in blocks for _ in range(n)]

def constrained_angles(target,config,tour,axis):
    """Project a soft gaze curve onto shared speed, acceleration and scan constraints.
    Hildreth projections solve sparse linear inequalities; no optional solver dependency.
    """
    n=len(target);fps=tour['fps'];x=[math.degrees(v) for v in target];constraints=[];duals=[]
    limits={**read(PROFILE)['reviewLimits'],**config.get('motionReviewLimits',{})}
    from tour_camera_evidence import DEFAULTS
    policy={**DEFAULTS,**config.get('cameraEvidencePolicy',{})}
    speed=[v*.999/fps for v in edge_limits(tour,config,'maxYawDegreesPerSecond' if axis=='yawRadians' else 'maxPitchDegreesPerSecond',limits)]
    accel=policy['maximumYawAccelerationDegreesPerSecondSquared' if axis=='yawRadians' else 'maximumPitchAccelerationDegreesPerSecondSquared']*.98/fps**2
    signs={}
    if axis=='yawRadians':
        m=markers(tour)
        for ch in config['chapters']:
            if ch['phase']!='observe':continue
            pan=ch.get('singleSweepDegrees',0);sign=1 if pan>0 else -1 if pan<0 else 0
            for i in range(m[ch['from']],m[ch['to']]):signs[i]=sign
    try:
        import numpy
    except ImportError:pass
    else:
        from tour_connection_motion import project_gaze_numpy
        return [math.radians(v) for v in project_gaze_numpy(x,fps,speed,accel,signs)]
    def add(indices,values,bound):constraints.append((indices,values,bound,sum(v*v for v in values)));duals.append(0.)
    for i in range(n-1):
        sign=signs.get(i)
        add((i,i+1),(-1.,1.),0. if sign in (-1,0) else speed[i])
        add((i,i+1),(1.,-1.),0. if sign in (1,0) else speed[i])
    for i in range(n-2):
        add((i,i+1,i+2),(1.,-2.,1.),accel);add((i,i+1,i+2),(-1.,2.,-1.),accel)
    for iteration in range(16000):
        largest=0
        for k,(indices,values,bound,norm) in enumerate(constraints):
            residual=sum(x[i]*v for i,v in zip(indices,values))-bound
            update=max(0.,duals[k]+residual/norm)-duals[k]
            if abs(update)>1e-12:
                duals[k]+=update
                for i,v in zip(indices,values):x[i]-=update*v
            largest=max(largest,max(0.,residual))
        if largest<1e-7:break
    # A sweep can temporarily re-violate an earlier neighbour constraint.
    # Certify the completed vector, not the last visited inequality or an
    # iteration count; never pass a residual speed/acceleration violation on.
    residual=max((sum(x[i]*v for i,v in zip(indices,values))-bound
                  for indices,values,bound,norm in constraints),default=0.)
    if residual>1e-6:
        raise ValueError(f'Gaze projection did not converge for {axis}: residual {residual:.9g} degrees')
    return [math.radians(v) for v in x]

def finalize_gaze(tour,config,seconds):
    """Regularize final sampled gaze with hard derivative and room scan constraints."""
    out=copy.deepcopy(tour);fs=out['frames'];fps=out['fps']
    for axis in ('yawRadians','pitchRadians'):
        values=[f[axis] for f in fs]
        if axis=='yawRadians':values=unwrap(values)
        values=constrained_angles(smooth(values,seconds,fps),config,out,axis)
        for f,v in zip(fs,values):f[axis]=v
    out['audit']=metrics(out);out['humanAcceptance']='pending';out['previewOnly']=True
    for key in ('subjectAudit','qualityReview','roomTimeline','roomJumpTimes'):out.pop(key,None)
    return out

class JointPlanner:
    def __init__(self,bundle,tour,config,search):
        from tour_core_targets import bind
        config=bind(bundle,config)
        self.b=bundle;self.t=tour;self.c=copy.deepcopy(config);self.search=search
        self.new_plan=search.get('_planningMode')=='new'
        # A generated seed is a proposal, not an approved viewing-time floor.
        # Explicit floors/locks still apply to both modes. Seed-based revisions
        # retain the previous behavior unless the job explicitly requests new planning.
        self.c['viewingDurationFloors']=(copy.deepcopy(config.get('viewingDurationFloors',{}))
            if self.new_plan else preserve_viewing_floors(tour,config))
        if self.new_plan:
            for ch in config['chapters']:
                if ch['phase']=='observe' and not ch.get('movingView'):
                    floors=self.c['viewingDurationFloors']
                    floors[ch['name']]=max(floors.get(ch['name'],0),ch.get('minimumSeconds',0))
        self.m=markers(tour);self.fps=tour['fps'];self.limits={**read(PROFILE)['reviewLimits'],**config.get('motionReviewLimits',{})}
        radius=config['tourContract']['bodyRadiusMm'];access,_=entry_apron(bundle,{'entranceOpeningId':config['tourContract']['entranceOpeningId'],'startPoint':tour['frames'][0]['pointMm'],'bodyRadiusMm':radius}) if config['tourContract'].get('tourMode')=='full_tour' else ([],None)
        self.p=Planner(bundle,{'bodyRadiusMm':radius+search.get('planningMarginMm',10),'accessPolygons':access,'gridMm':search.get('gridMm',50),**config.get('pathComfort',{})})
        self.rooms={r['id']:r for r in bundle['model']['rooms']};self.paths={};self.links={};self.pool={};self.motion_profiles={};self.view_motion_reports={};self.view_frame_counts={}
        # Use the same verified seed geometry for early budget estimates and
        # reconstruction. Re-running A* merely to price a camera-only edit used
        # to discard safe connections before they reached final checks.
        from tour_rules import trajectory
        for ch in config['chapters']:
            frames=tour['frames'][self.m[ch['from']]:self.m[ch['to']]+1]
            path=[f['pointMm'][:] for f in frames]
            if not trajectory({'fps':self.fps,'frames':frames},config)['issues'] and all(self.p.line_free(a,b) for a,b in zip(path,path[1:])):
                self.paths[(tuple(path[0]),tuple(path[-1]))]=path
        self.obs=[(i,ch) for i,ch in enumerate(config['chapters']) if ch['phase']=='observe']
        self.budget_rejections=[]
        self.deadline=search.get('_planningDeadline',math.inf)
        self.entry=copy.deepcopy(tour['frames'][0])
        intent=config.get('entryView')
        if intent:
            q=intent.get('targetMm')
            if not isinstance(q,list) or len(q)!=3 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in q):raise ValueError('Entry framing needs a finite physical targetMm')
            dx,dy=q[0]-self.entry['pointMm'][0],q[1]-self.entry['pointMm'][1]
            if math.hypot(dx,dy)<100:raise ValueError('Entry framing target is too close')
            self.entry['yawRadians']=math.atan2(dy,dx)
            self.entry['pitchRadians']=math.atan2(q[2]-self.entry['eyeMm'],math.hypot(dx,dy))
    def observation_frames(self,ch,choice=None):
        original=self.m[ch['to']]-self.m[ch['from']]
        if not self.new_plan:return original
        locked=self.c.get('timingLocks',{}).get('viewingFrames',{}).get(ch['name'])
        if locked is not None:
            if isinstance(locked,bool) or not isinstance(locked,int) or locked<1:raise ValueError('Locked viewing frames must be a positive integer')
            return locked
        minimum=max(ch.get('minimumSeconds',0),self.c.get('viewingDurationFloors',{}).get(ch['name'],0))
        if ch.get('movingView'):
            minimum=max(minimum,original/self.fps)
            if choice is not None:
                limits=chapter_limits(self.limits,ch)
                path=self.observation_path(ch,choice)
                minimum=max(minimum,self.position_profile(path,limits)['seconds'],
                    abs(math.degrees(choice['pan']))/(limits['maxYawDegreesPerSecond']*.98),
                    abs(math.degrees(choice.get('pitch',0)-choice.get('pitchFrom',choice.get('pitch',0))))/(limits['maxPitchDegreesPerSecond']*.98))
        count=max(1,math.ceil(minimum*self.fps-1e-8)) if minimum>0 else original
        if not ch.get('movingView') or choice is None:return count
        key=(ch['name'],tuple(map(tuple,self.observation_path(ch,choice))),count)
        if key not in self.view_frame_counts:
            maximum=min(count+math.ceil(2*self.fps),count*2)
            self.view_frame_counts[key]=None
            for proposal in range(count,maximum+1):
                if time.monotonic()>self.deadline:raise ValueError('Moving observation timing reached the planning deadline')
                if not self.observation_motion_report(ch,choice,proposal)['issues']:
                    self.view_frame_counts[key]=proposal;break
        if self.view_frame_counts[key] is None:raise ValueError('Moving observation cannot meet sampled trajectory limits within bounded additional time: '+ch['name'])
        return self.view_frame_counts[key]
    def observation_motion_report(self,ch,choice,count):
        """Certify actual frame chords before a moving view becomes immutable."""
        path=self.observation_path(ch,choice);key=(ch['name'],tuple(map(tuple,path)),count)
        if key not in self.view_motion_reports:
            from tour_rules import trajectory
            motion=self.position_profile(path,chapter_limits(self.limits,ch))
            frames=[{'pointMm':speed_sample(motion,motion['seconds']*j/count)} for j in range(count+1)]
            frames[0]['pointMm']=choice['point'][:];frames[-1]['pointMm']=choice['endPoint'][:]
            # Adjacent stationary views supply the zero-speed boundary context.
            frames=[copy.deepcopy(frames[0])]+frames+[copy.deepcopy(frames[-1])]
            config={'trajectoryPolicy':self.c.get('trajectoryPolicy',{}),'chapters':[ch],
                    'ruleExceptions':[x for x in self.c.get('ruleExceptions',[]) if x.get('chapter') in (None,ch['name'])]}
            sample={'fps':self.fps,'frames':frames,'visits':[{'name':ch['from'],'frame':1},{'name':ch['to'],'frame':count+1}]}
            self.view_motion_reports[key]=trajectory(sample,config)
        return self.view_motion_reports[key]
    def observation_path(self,ch,choice):
        # A fresh fixed station stays fixed; seed seam smoothing must not turn
        # a stationary viewing window into a small loop around its anchor.
        if self.new_plan and not ch.get('movingView') and math.dist(choice['point'],choice['endPoint'])<.1:
            return [choice['point'],choice['point']]
        path=choice.get('viewPath',[choice['point'],choice['endPoint']])
        if self.new_plan and (not path or math.dist(path[0],choice['point'])>1e-6 or math.dist(path[-1],choice['endPoint'])>1e-6):
            raise ValueError('Observation path must retain its exact selected endpoints')
        return path
    def position_profile(self,path,limits):
        acceleration=min(2850.,self.c.get('trajectoryPolicy',{}).get('maximumPlanarAccelerationMps2',3)*1000*.95)
        key=(tuple(map(tuple,path)),limits['maximumSpeedMps'],acceleration,self.fps)
        if key not in self.motion_profiles:
            self.motion_profiles[key]=speed_profile(path,maximum_speed=limits['maximumSpeedMps']*1000*.995,
                acceleration=acceleration,fps=self.fps)
        return self.motion_profiles[key]
    def path(self,a,b):
        key=tuple(a),tuple(b)
        if key not in self.paths:self.paths[key]=safe_path(self.p,a,b)
        return self.paths[key]
    def connection_path(self,a,b,chapter=None):
        via=(chapter or {}).get('pathWaypoints',[])
        if not via:return self.path(a,b)
        if not isinstance(via,list) or len(via)>16:raise ValueError('At most 16 bounded connection waypoints')
        for point in via:
            if not isinstance(point,list) or len(point)!=2 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in point):raise ValueError('Finite connection waypoint required')
            if self.p.blocked(point):raise ValueError('Connection waypoint collides with the actual scheme')
        key=('via',tuple(a),tuple(b),tuple(map(tuple,via)))
        if key not in self.paths:
            raw=[a]
            for target in via+[b]:raw.extend(self.path(raw[-1],target)[1:])
            rounded=self.p.round(raw)
            if any(not self.p.line_free(x,y) for x,y in zip(rounded,rounded[1:])):raise ValueError('Connection waypoint rounding is not safe')
            self.paths[key]=rounded
        return self.paths[key]
    def incoming_path(self,a,b,observation):
        chapter=next((ch for ch in self.c['chapters'] if ch['phase']=='transit' and ch['to']==observation['from']),None)
        return self.connection_path(a,b,chapter)
    def fresh_connection(self,source,dest,path,ch,nav_policy):
        """Sample the existing safe arc with physical braking and local gaze work."""
        limits=chapter_limits(self.limits,ch);motion=self.position_profile(path,limits)
        points=motion['points'];distances=motion['arc']
        if distances[-1]<1 or ch.get('navigationPolicy',{}).get('monotoneEndpointGaze'):
            ys=[source['yawRadians']+delta(source['yawRadians'],dest['yawRadians'])*
                (d/distances[-1] if distances[-1]>=1 else i/(len(points)-1)) for i,d in enumerate(distances)]
        else:
            local_nav={**nav_policy,**ch.get('navigationPolicy',{}),'maximumSpeedMps':limits['maximumSpeedMps'],'maxYawDegreesPerSecond':limits['maxYawDegreesPerSecond']}
            key=('speed_profile',tuple(map(tuple,points)),round(source['yawRadians'],6),round(dest['yawRadians'],6),json.dumps(local_nav,sort_keys=True))
            if key not in self.links:self.links[key]=navigation_gaze(self.p,points,distances,source['yawRadians'],dest['yawRadians'],local_nav)
            ys=self.links[key]
        clock=coupled_clock(motion,ys,limits['maxYawDegreesPerSecond'])
        total=max(clock[-1],abs(math.degrees(dest['pitchRadians']-source['pitchRadians']))/limits['maxPitchDegreesPerSecond'])
        n=max(1,math.ceil(total*self.fps-1e-8));frames=[]
        import bisect
        for j in range(n+1):
            u=j/n;tm=spatial_time(motion,clock,clock[-1]*u);point=speed_sample(motion,tm)
            k=max(0,min(len(points)-2,bisect.bisect_right(motion['time'],tm)-1))
            fraction=math.dist(point,points[k])/max(1e-12,distances[k+1]-distances[k])
            yaw=ys[k]*(1-fraction)+ys[k+1]*fraction if distances[-1]>=1 else ys[0]*(1-u)+ys[-1]*u
            f=copy.deepcopy(source);f.update(pointMm=point,yawRadians=yaw,pitchRadians=source['pitchRadians']*(1-u)+dest['pitchRadians']*u);frames.append(f)
        frames[0]=copy.deepcopy(source);frames[-1]=copy.deepcopy(dest);frames[-1]['yawRadians']=ys[-1]
        return frames
    def repair_fresh_positions(self,tour,config):
        """Project sampled connection clocks without changing any viewing frame."""
        from tour_rules import trajectory
        if not self.new_plan or not trajectory(tour,config)['issues']:return tour
        from tour_connection_motion import repair_positions_numpy
        out=copy.deepcopy(tour)
        try:
            projected,evidence=repair_positions_numpy(tour,config,self.p,maximum_iterations=24000,
                speed_headroom_fraction=0,acceleration_headroom_fraction=0,projection_tolerance_mm=1e-7,
                deadline=self.deadline if math.isfinite(self.deadline) else None)
            result=trajectory(projected,config);marks=markers(tour);fixed={0,len(tour['frames'])-1}
            for ch in config['chapters']:
                if ch['phase']=='observe':fixed.update(range(marks[ch['from']],marks[ch['to']]+1))
            timebase=(len(projected['frames'])==len(tour['frames']) and projected['fps']==tour['fps']
                      and projected['seconds']==tour['seconds'] and markers(projected)==marks)
            observations=timebase and all(projected['frames'][i]==tour['frames'][i] for i in fixed)
            points=not any(self.p.blocked(f['pointMm']) for f in projected['frames'])
            edges=all(self.p.line_free(a['pointMm'],z['pointMm']) for a,z in zip(projected['frames'],projected['frames'][1:]))
            caps=edge_limits(projected,config,'maximumSpeedMps',self.limits)
            speed=all(math.dist(a['pointMm'],z['pointMm'])*self.fps/1000<=cap+1e-6
                      for a,z,cap in zip(projected['frames'],projected['frames'][1:],caps))
            accepted=bool(evidence.get('accepted') and not result['issues'] and timebase and observations and points and edges and speed)
            evidence={**evidence,'status':'accepted' if accepted else 'rejected','accepted':accepted,
                      'trajectoryIssues':result['issues'],'timebasePreserved':timebase,'observationFramesPreserved':observations,
                      'bodyPointsSafe':points,'bodyEdgesSafe':edges,'chapterWalkingLimitsPassed':speed}
            if accepted:out=projected
        except (ValueError,TimeoutError,ImportError) as exc:
            evidence={'status':'rejected','accepted':False,'reason':str(exc),'budgetExhausted':isinstance(exc,TimeoutError)}
        out['positionProjection']=evidence
        return out
    def baseline(self,ch):
        fs=self.t['frames'][self.m[ch['from']]:self.m[ch['to']]+1]
        item={'point':fs[0]['pointMm'][:],'endPoint':fs[-1]['pointMm'][:],'yaw':fs[0]['yawRadians'],'pan':fs[-1]['yawRadians']-fs[0]['yawRadians'],'source':'seed','localCost':0,'pitch':fs[0]['pitchRadians']}
        if self.new_plan:
            item['viewPath']=[f['pointMm'][:] for f in fs]
            item['pitchFrom']=fs[0]['pitchRadians'];item['pitch']=fs[-1]['pitchRadians']
            if not ch.get('movingView'):item['endPoint']=item['point'][:]
        return item
    def local_cost(self,ch,item):
        room=self.rooms[ch['roomId']];poly=room['poly'];a=item['point'];z=item['endPoint'];seconds=self.observation_frames(ch,item)/self.fps
        region=self.rooms[ch.get('observationRegionId',ch['roomId'])]['poly']
        path=self.observation_path(ch,item)
        movement=self.position_profile(path,chapter_limits(self.limits,ch)) if self.new_plan else None
        if movement and movement['seconds']>seconds+1e-8:return None
        if self.new_plan and ch.get('movingView') and self.observation_motion_report(ch,item,round(seconds*self.fps))['issues']:return None
        if length(path)/1000/seconds>self.limits['maximumSpeedMps']:return None
        if not inside(a,region) or not inside(z,region) or self.p.blocked(a) or self.p.blocked(z) or any(not self.p.line_free(x,y) for x,y in zip(path,path[1:])):return None
        if abs(math.degrees(item['pan']))/seconds>chapter_limits(self.limits,ch)['maxYawDegreesPerSecond']*.98:return None
        pitch=item.get('pitch',0);pitch_from=item.get('pitchFrom',pitch)
        if abs(math.degrees(pitch-pitch_from))/seconds>chapter_limits(self.limits,ch)['maxPitchDegreesPerSecond']*.98:return None
        frames=[{'pointMm':speed_sample(movement,movement['seconds']*u) if movement else at_distance(path,length(path)*u),
                 'yawRadians':item['yaw']+item['pan']*u,'pitchRadians':pitch_from*(1-u)+pitch*u} for u in [j/8 for j in range(9)]]
        from tour_core_targets import targets
        ids=targets(ch);last=-1
        hfov=self.c.get('cameraProfile',{}).get('horizontalFovDegrees',76)
        target_half=math.radians(max(1,hfov/2-4))
        for subject in ids:
            targets=target_samples(self.b,subject);p=visibility_planner(self.b,self.p,subject);seen=[]
            for j,f in enumerate(frames):
                if any(abs(delta(f['yawRadians'],math.atan2(q[1]-f['pointMm'][1],q[0]-f['pointMm'][0])))<=target_half and clear_distance(p,f['pointMm'],math.atan2(q[1]-f['pointMm'][1],q[0]-f['pointMm'][0]),math.dist(q[:2],f['pointMm']))>=math.dist(q[:2],f['pointMm'])-60 for q in targets):seen.append(j)
            if not seen:return None
            if subject in ch.get('orderedViewTargets',[]):
                candidates=[j for j in seen if j>=last]
                if not candidates:return None
                last=candidates[0]
        grid=self.search.get('screenGridMm',450);points=[[x,y] for x in range(int(min(p[0] for p in poly))+grid//2,int(max(p[0] for p in poly)),grid) for y in range(int(min(p[1] for p in poly))+grid//2,int(max(p[1] for p in poly)),grid) if inside([x,y],poly)]
        seen=0
        for q in points:
            if any(abs(delta(f['yawRadians'],math.atan2(q[1]-f['pointMm'][1],q[0]-f['pointMm'][0])))<=math.radians(hfov/2) and clear_distance(self.p,f['pointMm'],math.atan2(q[1]-f['pointMm'][1],q[0]-f['pointMm'][0]),math.dist(q,f['pointMm']))>=math.dist(q,f['pointMm'])-25 for f in frames):seen+=1
        wall=sum(sum(clear_distance(self.p,f['pointMm'],f['yawRadians']+math.radians(v),900)<900 for v in (-30,-15,0,15,30))>=4 for f in frames)/len(frames)
        budget=next((r['maximumSeconds'] for r in self.c.get('roomBudgetPolicy',{}).get('rooms',[]) if r['roomIds']==[ch['roomId']]),None)
        approach_penalty=0
        if budget is not None:
            gates=[]
            for w in self.b['state']['walls']:
                for op in w['opens']:
                    if op['kind'] not in ('door','sliding'):continue
                    ln=math.dist(w['a'],w['b']);v=[(w['b'][k]-w['a'][k])/ln for k in (0,1)];gate=[w['a'][k]+v[k]*(op['at']+op['width']/2) for k in (0,1)]
                    # Only real thresholds adjacent to this room, never a nearby window.
                    if any(inside([gate[0]+dx,gate[1]+dy],poly) for dx,dy in ((250,0),(-250,0),(0,250),(0,-250))):gates.append(gate)
            if gates:
                travel=min(math.dist(a,g)+math.dist(z,g) for g in gates)/1000/self.limits['maximumSpeedMps']
                approach_penalty=max(0,seconds+travel-budget)*30
        # Vertical framing affects proposals in both directions; a steep old
        # pitch is not a one-way lower bound on all future candidates.
        eye=self.t['frames'][0]['eyeMm'];hfov=self.c.get('cameraProfile',{}).get('horizontalFovDegrees',76)
        vertical=sum(framing_cost(self.b,ch,f['pointMm'],f['yawRadians'],f['pitchRadians'],eye,hfov) for f in frames)/len(frames)
        return (1-seen/max(1,len(points)))*8+wall*20+abs(item['pan'])*.15+approach_penalty+vertical*2
    def candidates(self,ch,round_index,repair=False):
        name=ch['name'];base=self.baseline(ch)
        if not repair:return [base]
        proposals=ch.get('candidatePoses')
        if proposals is not None:
            if not isinstance(proposals,list) or not 1<=len(proposals)<=32:raise ValueError('Provide 1..32 bounded case station proposals')
            base['localCost']=self.local_cost(ch,base)
            if base['localCost'] is None:base['localCost']=1000
            pool=[base]
            for pose in proposals:
                try:
                    point=pose['point'];end=pose.get('endPoint',point)
                    if any(not isinstance(q,list) or len(q)!=2 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in q) for q in (point,end)):raise ValueError('Finite station coordinates required')
                    yaw,pan,pitch=[math.radians(pose[k]) for k in ('yawDegrees','panDegrees','pitchDegrees')]
                    if not all(math.isfinite(v) for v in (yaw,pan,pitch)):raise ValueError('Finite station angles required')
                    pitch_from=pose.get('pitchFromDegrees',pose['pitchDegrees'])
                    if isinstance(pitch_from,bool) or not isinstance(pitch_from,(int,float)) or not math.isfinite(pitch_from):raise ValueError('Finite station starting pitch required')
                    pitch_from=math.radians(pitch_from)
                    # Duplicate seed poses used to occupy every beam branch and
                    # consume the local-alternative budget before any real edit.
                    if math.dist(point,base['point'])<.1 and math.dist(end,base['endPoint'])<.1 and abs(delta(yaw,base['yaw']))<1e-7 and abs(pan-base['pan'])<1e-7 and abs(pitch-base['pitch'])<1e-7 and abs(pitch_from-base.get('pitchFrom',base['pitch']))<1e-7:continue
                    item={'point':point[:],'endPoint':end[:],'yaw':yaw,'pan':pan,'pitch':pitch,'source':'case_station_proposal','viewPath':self.path(point,end)}
                    if 'pitchFromDegrees' in pose:item['pitchFrom']=pitch_from
                    cost=self.local_cost(ch,item)
                except (ValueError,KeyError,TypeError):continue
                if cost is not None:pool.append({**item,'localCost':cost})
                else:
                    # A stale narrow case proposal cannot silently drop newly
                    # discovered facilities. Search bounded whole-function scans
                    # at the same proposed station before reporting infeasibility.
                    from tour_core_targets import scan_angles
                    for yaw,pan in scan_angles(self.b,ch,point,self.observation_frames(ch)/self.fps,self.limits['maxYawDegreesPerSecond']):
                        if time.monotonic()>self.deadline:break
                        for pitch in pitch_candidates(self.b,ch,point,yaw+pan/2,item['pitch'],self.entry['eyeMm'])[:3]:
                            variant={**item,'yaw':yaw,'pan':pan,'pitch':pitch,'source':'core_function_proposal'}
                            value=self.local_cost(ch,variant)
                            if value is not None:pool.append({**variant,'localCost':value})
            self.pool[name]={'tested':len(proposals),'retained':pool}
            return pool
        positions=[base['point']];radius=self.search.get('neighbourhoodMm',400)*(round_index+1)
        for dx,dy in [(radius,0),(-radius,0),(0,radius),(0,-radius),(radius,radius),(-radius,-radius),(radius,-radius),(-radius,radius)]:positions.append([base['point'][0]+dx,base['point'][1]+dy])
        # Actual doors supply shallow inside-room alternatives. No invented openings.
        room=self.rooms[ch.get('observationRegionId',ch['roomId'])]
        for wall in self.b['state']['walls']:
            for op in wall['opens']:
                if op['kind'] in ('door','sliding') and op.get('id'):
                    for point,depth,gate in opening_candidates(self.b,self.p,room,op['id']):
                        if 200<=depth<=1000 and inside(point,room['poly']):positions.append(point)
        positions=list({tuple(round(v,3) for v in p):p for p in positions}.values())
        base['localCost']=self.local_cost(ch,base)
        if base['localCost'] is None:base['localCost']=1000
        pool=[base];tried=0
        for point in positions:
            if time.monotonic()>self.deadline:break
            if self.p.blocked(point) or not inside(point,room['poly']):continue
            angles=[(base['yaw']+math.radians(offset),base['pan']) for offset in (0,-15,15,-30,30)]
            if not ch.get('orderedViewTargets'):
                from tour_core_targets import scan_angles
                angles=scan_angles(self.b,ch,point,self.observation_frames(ch)/self.fps,self.limits['maxYawDegreesPerSecond'])+angles
            if not ch.get('orderedViewTargets'):
                aim=(ch.get('subjects') or ch.get('aimOnlySubjects') or [None])[0]  # a ceiling fixture may only aim the view
                if aim:
                    target=target_anchor(self.b,aim);bearing=math.atan2(target[1]-point[1],target[0]-point[0]);span=min(abs(base['pan']),math.radians(55))
                    angles += [(bearing-sign*span/2,sign*span) for sign in (-1,1)]
                angles += [(base['yaw']+base['pan']+math.radians(offset),-base['pan']) for offset in (0,-15,15)]
            else:
                try:
                    ys=ordered_bearings(self.b,ch['orderedViewTargets'],point)
                    if len(ys)>1:
                        direction=1 if ys[-1]>=ys[0] else -1;pad=min(math.radians(20),abs(ys[-1]-ys[0])*.25)
                        angles=[(ys[0]+direction*pad,ys[-1]-ys[0]-direction*2*pad)]+angles
                except ValueError:continue
            # Couple the end of a room scan to the first clear outside leg.
            # This avoids spending a return link undoing the room's final heading.
            aligned=set()
            oi=next(i for i,(_,q) in enumerate(self.obs) if q['name']==ch['name'])
            next_point=self.t['frames'][self.m[self.obs[oi+1][1]['from']]]['pointMm'] if oi+1<len(self.obs) else self.t['frames'][-1]['pointMm']
            try:
                exit_path=dense_path(self.path(point,next_point),100)
                k=next((i for i,q in enumerate(exit_path) if not inside(q,room['poly'])),0)
                a=exit_path[min(k+2,len(exit_path)-2)];z=exit_path[min(k+6,len(exit_path)-1)];heading=math.atan2(z[1]-a[1],z[0]-a[0])
                span=math.radians(min(70,self.observation_frames(ch)/self.fps*self.limits['maxYawDegreesPerSecond']*.92))
                if not ch.get('orderedViewTargets'):
                    for shoulder in (-90,-60,60,90):
                        end=heading+math.radians(shoulder)
                        for sign in (-1,1):
                            pair=(end-sign*span,sign*span);angles.append(pair);aligned.add(pair)
            except ValueError:pass
            for yaw,pan in angles:
                if time.monotonic()>self.deadline:break
                ends=[point];view_paths={tuple(point):[point,point]}
                shifted=[point[k]+base['endPoint'][k]-base['point'][k] for k in (0,1)]
                if shifted!=point:ends.append(shifted);view_paths[tuple(shifted)]=[point,shifted]
                # Safe short exitward observation motion is a candidate, never mandatory.
                obs_index=next(i for i,(_,q) in enumerate(self.obs) if q['name']==ch['name'])
                destination=self.t['frames'][self.m[self.obs[obs_index+1][1]['from']]]['pointMm'] if obs_index+1<len(self.obs) else self.t['frames'][-1]['pointMm']
                try:
                    route=self.path(point,destination);drift=point;drift_path=[point]
                    for q in dense_path(route,40)[1:]:
                        if math.dist(point,q)>min(self.search.get('maximumObservationDriftMm',1000),self.observation_frames(ch)/self.fps*600) or not inside(q,room['poly']):break
                        drift=q;drift_path.append(q)
                    if math.dist(point,drift)>80:ends.append(drift);view_paths[tuple(drift)]=drift_path
                except ValueError:pass
                for end in ends:
                    item={'point':point[:],'endPoint':end[:],'yaw':yaw,'pan':pan,'source':'joint_search','departureAligned':(yaw,pan) in aligned,'viewPath':view_paths.get(tuple(end),[point,end])}
                    pitches=pitch_candidates(self.b,ch,point,yaw+pan/2,base['pitch'],self.t['frames'][0]['eyeMm'],self.c.get('cameraProfile',{}).get('horizontalFovDegrees',76))
                    for pitch in pitches[:3]:
                        variant={**item,'pitch':pitch};score=self.local_cost(ch,variant);tried+=1
                        if score is not None:variant['localCost']=score;pool.append(variant)
        # Diversity by position avoids a pool consisting only of angles at one deep station.
        ranked=sorted(pool[1:],key=lambda v:v['localCost']);diverse=[];seen=set()
        for v in ranked:
            key=(tuple(v['point']),1 if v['pan']>0 else -1)
            if key not in seen:seen.add(key);diverse.append(v)
        for v in ranked:
            if v not in diverse:diverse.append(v)
        unique=[];identities=set()
        preferred=sorted((v for v in ranked if v.get('departureAligned')),key=lambda v:v['localCost'])[:3]
        for item in pool[:1]+preferred+diverse:
            key=tuple(round(v,3) for v in item['point']+item['endPoint'])+(round(item['yaw']%(2*math.pi),5),round(item['pan'],5),round(item.get('pitch',0),5))
            if key not in identities:unique.append(item);identities.add(key)
        pool=unique[:self.search.get('perRoomCandidates',6)]
        self.pool[name]={'tested':tried,'retained':pool};return pool
    def closing_pose(self):
        """Keep the confirmed door and endpoint, face out along the exit.
        No outside hallway or virtual geometry is invented. Its turn must fit
        the same connection budget and pass the final screen audit.
        """
        frame=copy.deepcopy(self.t['frames'][-1])
        if self.c['tourContract'].get('tourMode')!='full_tour':return frame
        key=self.c['tourContract'].get('entranceOpeningId')
        for wall in self.b['state']['walls']:
            for op in wall['opens']:
                if op.get('id')!=key:continue
                d=math.dist(wall['a'],wall['b']);u=(op['at']+op['width']/2)/d
                gate=[wall['a'][k]+(wall['b'][k]-wall['a'][k])*u for k in (0,1)]
                if math.dist(gate,frame['pointMm'])>30:
                    frame['yawRadians']=math.atan2(frame['pointMm'][1]-gate[1],frame['pointMm'][0]-gate[0])
                    offset=self.c.get('exitView',{}).get('yawOffsetDegrees',0)
                    if isinstance(offset,bool) or not isinstance(offset,(int,float)) or not math.isfinite(offset) or abs(offset)>60:raise ValueError('Exit view offset must remain within the forward 60-degree sector')
                    frame['yawRadians']+=math.radians(offset)
                    frame['pitchRadians']=math.radians(-5)
                    frame['closingTargetOpeningId']=key
                return frame
        raise ValueError('Closing view needs the confirmed entrance opening')
    def bind_adjacent(self,previous,current,item,choices):
        """Consecutive view windows share one pose; never insert a timed link."""
        if not previous or previous['to']!=current['from']:return item
        prior=choices[previous['name']];point=prior['endPoint'];yaw=prior['yaw']+prior['pan']
        end_yaw=item['yaw']+item['pan']
        same_point=math.dist(point,item['point'])<.1
        if same_point and abs(delta(yaw,item['yaw']))<1e-7 and (not self.new_plan or abs(prior.get('pitch',0)-item.get('pitchFrom',item.get('pitch',0)))<1e-7):return item
        v={**item,'point':point[:],'yaw':yaw,'pan':delta(yaw,end_yaw),
           'viewPath':item['viewPath'] if self.new_plan and math.dist(point,item['point'])<1e-6 and item.get('viewPath') else self.path(point,item['endPoint']),'source':'joint_boundary',
           'pitchFrom':prior.get('pitch',0)}
        v['localCost']=self.local_cost(current,v)
        return v if v['localCost'] is not None else None
    def budget_feasible(self,choices,closing=None):
        locks=self.c.get('timingLocks',{})
        if 'totalFrames' not in locks:return True
        seconds=0.;source=self.entry;previous=None
        selected=[ch for _,ch in self.obs if ch['name'] in choices]
        for ch in selected:
            item=choices[ch['name']]
            if not previous or previous['to']!=ch['from']:
                distance=length(self.incoming_path(source['pointMm'],item['point'],ch))/1000
                seconds+=max(distance/self.limits['maximumSpeedMps'],abs(math.degrees(delta(source['yawRadians'],item['yaw'])))/self.limits['maxYawDegreesPerSecond'],abs(math.degrees(item.get('pitchFrom',item.get('pitch',0))-source['pitchRadians']))/self.limits['maxPitchDegreesPerSecond'])
            source={'pointMm':item['endPoint'],'yawRadians':item['yaw']+item['pan'],'pitchRadians':item.get('pitch',0)};previous=ch
        # This is a lower-bound filter, not a compulsory extra closing turn.
        # Door framing is priced separately when that closing candidate is built.
        end=closing if closing is not None else self.t['frames'][-1]
        seconds+=max(length(self.path(source['pointMm'],end['pointMm']))/1000/self.limits['maximumSpeedMps'],abs(math.degrees(delta(source['yawRadians'],end['yawRadians'])))/self.limits['maxYawDegreesPerSecond'])
        viewing=sum(self.observation_frames(ch,choices.get(ch['name'])) for _,ch in self.obs)
        available=locks['totalFrames']-1-viewing
        required=math.ceil(seconds*self.fps-1e-8)
        if required>available:
            self.budget_rejections.append({'afterChapter':selected[-1]['name'] if selected else None,'minimumTransitFrames':required,'availableTransitFrames':available})
            return False
        return True
    def joint_beam(self,affected,round_index):
        states=[(0,{})];width=self.search.get('beamWidth',4)
        for j,(index,ch) in enumerate(self.obs):
            candidates=self.candidates(ch,round_index,ch['name'] in affected);new=[]
            previous=self.obs[j-1][1] if j else None
            for score,choices in states:
                source=choices[previous['name']]['endPoint'] if previous else self.entry['pointMm'];syaw=choices[previous['name']]['yaw']+choices[previous['name']]['pan'] if previous else self.entry['yawRadians']
                for raw in candidates:
                    try:item=self.bind_adjacent(previous,ch,raw,choices)
                    except ValueError:continue
                    if item is None:continue
                    try:d=length(self.incoming_path(source,item['point'],ch))
                    except ValueError:continue
                    # Respect the same room-wide scan direction across complementary stations.
                    if previous and previous.get('roomId')==ch.get('roomId'):
                        old=choices[previous['name']];sign=1 if old['pan']>0 else -1
                        if item['pan']*sign<0 or delta(syaw,item['yaw'])*sign< -math.radians(1):continue
                    effort=max(d/1000/self.limits['maximumSpeedMps'],abs(math.degrees(delta(syaw,item['yaw'])))/self.limits['maxYawDegreesPerSecond'],abs(math.degrees(item.get('pitchFrom',item.get('pitch',0))-(choices[previous['name']].get('pitch',0) if previous else self.t['frames'][0]['pitchRadians'])))/self.limits['maxPitchDegreesPerSecond'])
                    # Viewing quality dominates ties; safe travel/turn work couples rooms.
                    proposed={**choices,ch['name']:item}
                    try:fits=self.budget_feasible(proposed)
                    except ValueError as exc:
                        self.budget_rejections.append({'afterChapter':ch['name'],'reason':str(exc)});continue
                    if not fits:continue
                    new.append((score+item['localCost']+effort,proposed))
            ordered=sorted(new,key=lambda row:row[0]);states=ordered[:width]
            # A cheap early pose can make every subsequent shared view invalid.
            # Keep the coherent seed chain as one bounded beam branch, instead
            # of letting all slots collapse onto the same early local optimum.
            seed=next((row for row in ordered if all(v['source']=='seed' for v in row[1].values())),None)
            if seed is not None and width>1 and seed not in states:
                states=states[:width-1]+[seed]
            if not states:raise ValueError('No feasible joint candidate at '+ch['name'])
        for i,(cost,choices) in enumerate(states):
            last=choices[self.obs[-1][1]['name']];end=self.closing_pose();cost+=max(length(self.path(last['endPoint'],end['pointMm']))/1000/self.limits['maximumSpeedMps'],abs(math.degrees(delta(last['yaw']+last['pan'],end['yawRadians'])))/self.limits['maxYawDegreesPerSecond']);states[i]=(cost,choices)
        return sorted(states,key=lambda row:row[0])
    def prepare_local_repairs(self,affected,round_index):
        """A failed early beam must not starve later rooms of local proposals."""
        errors=[]
        for _,ch in self.obs:
            if ch['name'] not in affected:continue
            if ch['name'] in self.pool:continue
            if time.monotonic()>self.deadline:
                errors.append({'chapter':ch['name'],'reason':'Candidate planning time budget exhausted'});continue
            try:self.candidates(ch,round_index,True)
            except ValueError as exc:errors.append({'chapter':ch['name'],'reason':str(exc)})
        return errors
    def rebuild(self,choices,nav_policy,frozen_windows=None):
        chapters=self.c['chapters'];windows={}
        closing=self.closing_pose() if nav_policy.get('closingView','door')=='door' else copy.deepcopy(self.t['frames'][-1])
        choices=copy.deepcopy(choices)
        for j,(_,ch) in enumerate(self.obs):
            previous=self.obs[j-1][1] if j else None
            item=self.bind_adjacent(previous,ch,choices[ch['name']],choices)
            if item is None:raise ValueError('Adjacent moving view cannot fit its locked observation window')
            choices[ch['name']]=item
        if not self.budget_feasible(choices,closing):raise ValueError('Early connection budget infeasible')
        for _,ch in self.obs:
            if frozen_windows and ch['from'] in frozen_windows:
                fs=copy.deepcopy(frozen_windows[ch['from']]);choice=choices[ch['name']]
                if len(fs)!=self.m[ch['to']]-self.m[ch['from']]+1:raise ValueError('Qualified fragment changed locked viewing frames')
                if math.dist(fs[0]['pointMm'],choice['point'])>.1 or math.dist(fs[-1]['pointMm'],choice['endPoint'])>.1:raise ValueError('Qualified fragment endpoints differ from selected poses')
                windows[ch['from']]=fs
                continue
            choice=choices[ch['name']];a,z=self.m[ch['from']],self.m[ch['to']];fs=copy.deepcopy(self.t['frames'][a:z+1]);yaw=choice['yaw'];pan=choice['pan']
            n=self.observation_frames(ch,choice)
            if n!=len(fs)-1:fs=resample_segment(fs,n)
            path=self.observation_path(ch,choice)
            motion=self.position_profile(path,chapter_limits(self.limits,ch)) if self.new_plan else None
            if motion and motion['seconds']>n/self.fps+1e-8:raise ValueError('Observation movement cannot brake within its viewing window: '+ch['name'])
            if self.new_plan and ch.get('movingView') and self.observation_motion_report(ch,choice,n)['issues']:
                raise ValueError('Moving observation exceeds sampled trajectory limits at its fixed frame count: '+ch['name'])
            for j,f in enumerate(fs):
                u=j/(len(fs)-1);f['pointMm']=speed_sample(motion,motion['seconds']*u) if motion else at_distance(path,length(path)*u);f['yawRadians']=yaw+pan*u;f['pitchRadians']=choice.get('pitchFrom',choice.get('pitch',f['pitchRadians']))*(1-u)+choice.get('pitch',f['pitchRadians'])*u
            if self.new_plan:
                fs[0]['pointMm']=choice['point'][:];fs[-1]['pointMm']=choice['endPoint'][:] if ch.get('movingView') or math.dist(choice['point'],choice['endPoint'])>=.1 else choice['point'][:]
            windows[ch['from']]=fs
        output=[copy.deepcopy(self.entry)];newmarks={chapters[0]['from']:0}
        for ch in chapters:
            if ch['from'] in windows:
                choice=choices[ch['name']]
                fs=copy.deepcopy(self.t['frames'][self.m[ch['from']]:self.m[ch['to']]+1]) if choice['source']=='seed' and not self.new_plan and not (frozen_windows and ch['from'] in frozen_windows) else copy.deepcopy(windows[ch['from']])
            else:
                source=output[-1];dest=windows[ch['to']][0] if ch['to'] in windows else (closing if ch is chapters[-1] else self.t['frames'][self.m[ch['to']]])
                old=self.t['frames'][self.m[ch['from']]:self.m[ch['to']]+1]
                unchanged=math.dist(source['pointMm'],old[0]['pointMm'])<.1 and math.dist(dest['pointMm'],old[-1]['pointMm'])<.1 and abs(delta(source['yawRadians'],old[0]['yawRadians']))<1e-7 and abs(delta(dest['yawRadians'],old[-1]['yawRadians']))<1e-7 and abs(source['pitchRadians']-old[0]['pitchRadians'])<1e-7 and abs(dest['pitchRadians']-old[-1]['pitchRadians'])<1e-7
                if not self.new_plan and unchanged and not ch.get('pathWaypoints') and not ch.get('navigationPolicy') and ch['name'] not in nav_policy.get('forceChapters',[]):
                    from tour_rules import trajectory
                    if not trajectory({'frames':old,'fps':self.fps},self.c)['issues']:
                        fs=copy.deepcopy(old)
                        shift=output[-1]['yawRadians']+delta(output[-1]['yawRadians'],fs[0]['yawRadians'])-fs[0]['yawRadians']
                        for f in fs:f['yawRadians']+=shift
                        output.extend(fs[1:]);newmarks[ch['to']]=len(output)-1
                        continue
                same_positions=math.dist(source['pointMm'],old[0]['pointMm'])<.1 and math.dist(dest['pointMm'],old[-1]['pointMm'])<.1
                from tour_rules import trajectory
                old_path=[f['pointMm'] for f in old]
                if same_positions and not ch.get('pathWaypoints') and not trajectory({'fps':self.fps,'frames':old},self.c)['issues'] and all(self.p.line_free(a,b) for a,b in zip(old_path,old_path[1:])):
                    path=old_path # A framing edit does not require discarding a verified spatial path.
                else:path=self.connection_path(source['pointMm'],dest['pointMm'],ch)
                if self.new_plan:
                    fs=self.fresh_connection(source,dest,path,ch,nav_policy)
                    shift=output[-1]['yawRadians']+delta(output[-1]['yawRadians'],fs[0]['yawRadians'])-fs[0]['yawRadians']
                    for f in fs:f['yawRadians']+=shift
                    output.extend(fs[1:]);newmarks[ch['to']]=len(output)-1
                    continue
                dense=dense_path(path,20);distances=[0]
                for a,b in zip(dense,dense[1:]):distances.append(distances[-1]+math.dist(a,b))
                if distances[-1]<1:
                    dense=[source['pointMm'][:],dest['pointMm'][:]];distances=[0,0];ys=[source['yawRadians'],source['yawRadians']+delta(source['yawRadians'],dest['yawRadians'])]
                elif ch.get('movingView'):
                    ys=[source['yawRadians']+delta(source['yawRadians'],dest['yawRadians'])*d/distances[-1] for d in distances]
                elif ch.get('navigationPolicy',{}).get('monotoneEndpointGaze'):
                    # Explicit candidate policy: one shortest signed turn with
                    # no overshoot. Screen checks still reject early subject
                    # reintroduction or walls; this is not a visual exemption.
                    ys=[source['yawRadians']+delta(source['yawRadians'],dest['yawRadians'])*d/distances[-1] for d in distances]
                else:
                    local_nav={**nav_policy,**ch.get('navigationPolicy',{}),'maximumSpeedMps':self.limits['maximumSpeedMps'],'maxYawDegreesPerSecond':self.limits['maxYawDegreesPerSecond']}
                    key=(tuple(source['pointMm']),tuple(dest['pointMm']),round(source['yawRadians'],6),round(dest['yawRadians'],6),json.dumps(local_nav,sort_keys=True))
                    if key not in self.links:self.links[key]=navigation_gaze(self.p,dense,distances,source['yawRadians'],dest['yawRadians'],local_nav)
                    ys=self.links[key]
                # Allocate by actual movement/angular effort; never squeeze the timeline.
                durations=connection_effort(dense,ys,source['pitchRadians'],dest['pitchRadians'],self.limits)
                total=sum(durations);n=max(1,math.ceil(total*self.fps))
                if ch['phase']=='observe':n=max(n,self.m[ch['to']]-self.m[ch['from']])
                arc=[0]
                for d in durations:arc.append(arc[-1]+d)
                import bisect
                fs=[]
                for j in range(n+1):
                    tm=total*j/n;k=max(0,min(len(dense)-2,bisect.bisect_right(arc,tm)-1));u=(tm-arc[k])/max(1e-9,arc[k+1]-arc[k]);f=copy.deepcopy(source);f['pointMm']=[dense[k][v]*(1-u)+dense[k+1][v]*u for v in (0,1)];f['yawRadians']=ys[k]*(1-u)+ys[k+1]*u;f['pitchRadians']=source['pitchRadians']+(dest['pitchRadians']-source['pitchRadians'])*j/n;fs.append(f)
                fs[0]=copy.deepcopy(source);fs[-1]=copy.deepcopy(dest)
                # Preserve exact position while retaining the continuous angle
                # lift. Writing a wrapped destination here invents a 360° turn.
                fs[-1]['yawRadians']=ys[-1]
            shift=output[-1]['yawRadians']+delta(output[-1]['yawRadians'],fs[0]['yawRadians'])-fs[0]['yawRadians']
            for f in fs:f['yawRadians']+=shift
            if math.dist(output[-1]['pointMm'],fs[0]['pointMm'])>.1:raise ValueError('Disconnected observation window')
            output.extend(fs[1:]);newmarks[ch['to']]=len(output)-1
        for i,f in enumerate(output):f['frame']=i
        t={**copy.deepcopy(self.t),'frames':output,'seconds':len(output)/self.fps,'visits':[{'name':k,'frame':v} for k,v in newmarks.items()]}
        for key in ('stopFrames','legs','roomTimeline','roomJumpTimes','subjectAudit','qualityReview','timingMethod'):t.pop(key,None)
        c=copy.deepcopy(self.c)
        for ch in c['chapters']:
            if ch['phase']=='observe':
                a,z=newmarks[ch['from']],newmarks[ch['to']];ch['singleSweepDegrees']=math.degrees(output[z]['yawRadians']-output[a]['yawRadians'])
        t=apply_timing_locks(t,c,preserve_connection_clock=self.new_plan)
        if self.new_plan:
            t.pop('positionProjection',None)
            t=self.repair_fresh_positions(t,c)
        else:t=smooth_position_seams(t,c,self.p)
        return t,c

def rank(report,tour):
    # Hard feasibility first, never trade a collision for seconds saved.
    codes=[x['code'] for x in report['issues']];checks=report.get('checks',{})
    safety=sum(x in ('body_path_collision','scheme_mismatch','full_tour_does_not_return_to_entrance','path_tangent_discontinuity','path_acceleration_spike','camera_angular_acceleration','locked_total_duration_changed','locked_viewing_duration_changed','locked_fps_changed','revision_scope_changed') for x in codes)
    semantic=sum(x in ('split_room_view','room_wide_sweep_reversal','observation_sweep_reversal','invalid_ordered_view_target','ordered_target_not_visible_in_sequence','room_coverage_below_case_minimum','actual_mesh_target_unreadable','transit_reintroduces_subject','approach_view_reverses_into_observation','screen_near_surface_occlusion','screen_dominant_surface','subject_composition_unreadable','screen_blank_segment','known_visual_failure_unchanged','known_visual_failure_unverified') for x in codes)
    over=sum(max(0,x.get('seconds',0)-x.get('maximumSeconds',0)) for x in report['issues'] if x['code'] in ('room_visit_over_budget','total_over_budget'))
    camera=checks.get('cameraEvidence',{});acc=camera.get('angularAcceleration',{});ap=camera.get('policy',{});severity=max(acc.get('yawRadians',0)/ap.get('maximumYawAccelerationDegreesPerSecondSquared',240),acc.get('pitchRadians',0)/ap.get('maximumPitchAccelerationDegreesPerSecondSquared',120))
    evidence=checks.get('screenEvidence',{})
    unknown=int(evidence.get('required',False) and evidence.get('status')!='checked')
    regressions=len(checks.get('introducedConstraintRegressions',[]))
    doorway=checks.get('doorwayComposition',{}).get('score',0)
    # Doorway centring is soft composition evidence, after every hard gate.
    return (regressions,safety,unknown,semantic,len(codes),round(over,3),round(camera.get('wallFacing',{}).get('longestSeconds',0),3),round(doorway,4),round(severity,4),tour['seconds'])

def affected_chapters(tour,config,report):
    names=set();chapters=config['chapters'];m=markers(tour);fps=tour['fps']
    for issue in report['issues']:
        if issue.get('chapter'):names.add(issue['chapter'])
        if issue.get('roomId'):names.update(c['name'] for c in chapters if c.get('roomId')==issue['roomId'])
        if issue['code']=='room_visit_over_budget':
            row=next((r for r in config.get('roomBudgetPolicy',{}).get('rooms',[]) if r['name']==issue['name']),{})
            names.update(c['name'] for c in chapters if c.get('roomId') in row.get('roomIds',[]))
    evidence=report.get('checks',{}).get('cameraEvidence',{})
    frames=[f for span in evidence.get('wallFacing',{}).get('spansFrames',[]) if (span[1]-span[0])/fps>1 for f in span]
    if evidence.get('angularAcceleration',{}).get('yawRadians',0)>evidence.get('policy',{}).get('maximumYawAccelerationDegreesPerSecondSquared',240):frames.append(evidence['angularAccelerationPeakFrames']['yawRadians'])
    for f in frames:
        for i,ch in enumerate(chapters):
            if m[ch['from']]<=f<=m[ch['to']]:names.update(q['name'] for q in chapters[max(0,i-1):i+2])
    for problem in report['issues']:
        if problem.get('frame') is not None:seconds=problem['frame']/fps
        else:seconds=problem.get('startSeconds')
        if seconds is not None:
            for i,ch in enumerate(chapters):
                if m[ch['from']]/fps<=seconds<=m[ch['to']]/fps:names.update(q['name'] for q in chapters[max(0,i-1):i+2])
    # A changed transit affects the two room endpoint poses, not every other room.
    for i,ch in enumerate(chapters):
        if ch['name'] in names:names.update(q['name'] for q in chapters[max(0,i-1):i+2] if q['phase']=='observe')
    return {c['name'] for c in chapters if c['phase']=='observe' and c['name'] in names}


def run(job,out):
    out=Path(out).resolve()
    if out.exists():raise ValueError('Fresh pipeline output required')
    if job.get('schema')!='homeowner-production-job/1':raise ValueError('Explicit production job schema required')
    from tour_stage_chain import require_camera_entry
    spatial=require_camera_entry(job)
    b=read(job['bundle']);search={'beamWidth':3,'perRoomCandidates':6,'maximumRounds':2,'maximumFullEvaluations':40,'maximumPlanningSeconds':300,'neighbourhoodMm':400,'strictRepairRounds':True,'maximumDoorwayCandidates':3,**job.get('search',{})}
    if not all(not isinstance(search[k],bool) and isinstance(search[k],int) and 1<=search[k]<=32 for k in ('beamWidth','perRoomCandidates','maximumRounds')):raise ValueError('Bounded positive search counts required')
    for key,minimum,maximum in [('maximumFullEvaluations',1,512),('maximumCandidateMeshEvaluations',1,128),('maximumDoorwayCandidates',0,3)]:
        v=search.get(key,8)
        if isinstance(v,bool) or not isinstance(v,int) or not minimum<=v<=maximum:raise ValueError('Bounded '+key+' required')
    if isinstance(search['maximumPlanningSeconds'],bool) or not isinstance(search['maximumPlanningSeconds'],(int,float)) or not math.isfinite(search['maximumPlanningSeconds']) or not 0<search['maximumPlanningSeconds']<=1800:raise ValueError('Bounded planning deadline required')
    if job.get('seedTour'):
        t=read(job['seedTour']);c=read(job['seedConfig'])
    else:
        from design_homeowner_tour import design
        if spatial:
            from tour_stage_chain import check_brief_alignment
            drift=check_brief_alignment(read(job['brief']),spatial['value'])
            if drift:raise ValueError('Camera brief does not follow the approved route: '+'; '.join(x['code']+' '+json.dumps({k:v for k,v in x.items() if k!='code'},ensure_ascii=False) for x in drift))
        t,c,_=design(b,read(job['brief']))
    mode=job.get('planningMode') or ('revision' if job.get('seedTour') else 'new')
    if mode not in ('new','revision'):raise ValueError('planningMode must be new or revision')
    if mode=='new' and job.get('revisionScope'):raise ValueError('New planning cannot use a frozen revision scope')
    search['_planningMode']=mode
    if t['schemeSha256']!=b['schemeSha256']:raise ValueError('Frozen scheme identity mismatch')
    if not c.get('tourContract'):raise ValueError('Current contract required; no automatic legacy approval')
    scene=read(Path(job['runtime'])/'scene.json')
    if scene['schemeSha256']!=t['schemeSha256']:raise ValueError('Rehearsal geometry identity mismatch')
    frozen_tour=copy.deepcopy(t);frozen_config=copy.deepcopy(c)
    scope=revision_scope(t,c,job.get('revisionScope'))
    out.mkdir(parents=True);dump(out/'job.json',job);started=time.monotonic()
    # The final mesh audit is mandatory evidence; search may not spend its time.
    search['_finalDeadline']=started+search['maximumPlanningSeconds']
    search['_planningDeadline']=search['_finalDeadline']-min(240,search['maximumPlanningSeconds']*.25)
    workflow={'schema':'homeowner-production-workflow/1','planningMode':mode,'stage':'input_locked','frozenSchemeSha256':b['schemeSha256'],'events':[],'spatialRouteApproval':'approved' if spatial else 'missing','routeApproval':'pending','humanAcceptance':'pending','video':'not_requested'}
    def stage(name,**details):
        workflow.update(stage=name,**details);workflow['events'].append({'stage':name,'elapsedSeconds':round(time.monotonic()-started,3)});dump(out/'workflow-state.json',workflow)
    stage('candidate_search')
    engine=JointPlanner(b,t,c,search);base=attach_doorway_evidence(b,t,engine.c,contract(b,t,engine.c))
    baseline_contract=copy.deepcopy(base)
    feedback=[]
    if job.get('meshFeedback'):
        evidence=read(job['meshFeedback'])
        if evidence.get('tourSha256')!=sha(job['seedTour']) or evidence.get('schemeSha256')!=b['schemeSha256']:raise ValueError('Stale mesh repair feedback')
        feedback=[row['id'] for row in evidence['chapters'] if not row['pass']]
        for problem in evidence.get('screenQuality',{}).get('issues',[]):
            if problem.get('chapter'):feedback.append(problem['chapter'])
            elif problem.get('startSeconds') is not None:
                marks=markers(t)
                feedback.extend(ch['name'] for ch in c['chapters'] if marks[ch['from']]/t['fps']<=problem['startSeconds']<=marks[ch['to']]/t['fps'])
    # A failed real playback is not erased by a subsequent numeric pass.
    visual_path=job.get('visualFeedback')
    if not visual_path and job.get('seedTour'):
        sibling=Path(job['seedTour']).with_name('browser-visual-review.json')
        if sibling.exists():visual_path=str(sibling)
    known=[]
    if visual_path:
        visual=read(visual_path)
        if visual.get('tourSha256')!=sha(job['seedTour']):raise ValueError('Stale visual feedback')
        if visual.get('result')=='needs_revision':
            marks=markers(t)
            for problem in visual['issues']:
                seconds=problem.get('atSeconds',[problem.get('startSeconds',0)])
                for ch in c['chapters']:
                    a,z=marks[ch['from']],marks[ch['to']]
                    if problem.get('chapter')==ch['name'] or any(a/t['fps']<=v<=z/t['fps'] for v in seconds):known.append(ch['name'])
            known=list(dict.fromkeys(known));feedback+=known
    attempts=[];best=(t,engine.c,base);attempt=0;frontier=[];mesh_evaluations=0;native_budget_exhausted=False;selected_origin='frozen_seed'
    mesh_cap=search.get('maximumCandidateMeshEvaluations',8)
    phase_mesh_limit=min(mesh_cap,3)
    def mesh_candidate(tour,config,label):
        nonlocal mesh_evaluations
        if not job.get('meshPreflight',True):return None
        if mesh_evaluations>=phase_mesh_limit:return None
        node=shutil.which('node')
        if not node:return None
        directory=out/'candidate-mesh'/str(label);directory.mkdir(parents=True)
        dump(directory/'tour.json',tour);dump(directory/'config.json',config);mesh_evaluations+=1
        result=subprocess.run([node,str(Path(__file__).with_name('tour_mesh_preflight.mjs')),'--runtime',job['runtime'],'--tour',str(directory/'tour.json'),'--config',str(directory/'config.json'),'--out',str(directory/'audit.json')],capture_output=True,text=True,timeout=max(1,search['maximumPlanningSeconds']-(time.monotonic()-started)))
        (directory/'preflight.log').write_text(result.stdout+result.stderr)
        return read(directory/'audit.json') if result.returncode==0 else {'status':'error','screenQuality':{'issues':[{'code':'candidate_mesh_error'}]}}
    def consider(tour,config,origin,choices=None):
        nonlocal best,attempt,selected_origin
        report=attach_doorway_evidence(b,tour,config,contract(b,tour,config))
        scope_result=scope_check(frozen_tour,tour,config,scope)
        report.setdefault('checks',{})['revisionScope']=scope_result
        report['issues']+=scope_result['issues']
        # Same screen checks for numeric-pass AND numeric-fail candidates.
        try:audit=mesh_candidate(tour,config,attempt+1)
        except subprocess.TimeoutExpired:audit=None
        report=attach_screen_evidence(report,audit,known,job.get('meshPreflight',True))
        report=protect_satisfied_constraints(report,baseline_contract)
        attach_spatial_evidence(report,spatial,tour)
        score=rank(report,tour);attempt+=1
        attempts.append({'id':attempt,'origin':origin,'seconds':tour['seconds'],'rank':score,'issues':report['issues'],'choices':choices,'checks':report['checks'],'collisionSamples':[tour['frames'][i] for i in report['checks']['geometry']['collisionFrames'][:8]]})
        print(json.dumps({'attempt':attempt,'origin':origin,'seconds':round(tour['seconds'],3),'codes':[i['code'] for i in report['issues']]},ensure_ascii=False),flush=True)
        forbidden={'body_path_collision','scheme_mismatch','split_room_view','room_wide_sweep_reversal','observation_sweep_reversal','viewing_time_compressed','invalid_ordered_view_target','ordered_target_not_visible_in_sequence','motion_limit','camera_angular_acceleration'}
        coverage=report['checks'].get('coverage',{});gap=sum(max(0,row.get('requiredPercent',coverage.get('minimumPercent',0))-row['horizontalAreaPercent']) for row in coverage.get('rooms',[]))
        if tour['seconds']<=config['maximumSeconds'] and gap<=6 and not any(i['code'] in forbidden for i in report['issues']):
            frontier.append((tour,config,report))
        if score<rank(best[2],best[0]):
            best=(tour,config,report);selected_origin=origin;checkpoint=out/'checkpoints'/str(attempt);checkpoint.mkdir(parents=True)
            dump(checkpoint/'tour.json',tour);dump(checkpoint/'camera-config.json',config);dump(checkpoint/'contract-report.json',report)

        return report
    try:baseline_audit=mesh_candidate(t,engine.c,'seed')
    except subprocess.TimeoutExpired:baseline_audit=None
    base=attach_screen_evidence(base,baseline_audit,known,job.get('meshPreflight',True))
    attach_spatial_evidence(base,spatial,t)
    # Compare candidates with the seed as audited, not the seed before its screen evidence.
    baseline_contract=copy.deepcopy(base)
    best=(t,engine.c,base)
    attempts.append({'id':0,'origin':'frozen_seed','seconds':t['seconds'],'rank':rank(base,t),'issues':base['issues'],'checks':base['checks']})
    if scope is None:
        prepared=copy.deepcopy(t) if engine.new_plan else smooth_position_seams(t,engine.c,engine.p)
        for sec in (.12,.2):
            if attempt>=search['maximumFullEvaluations'] or time.monotonic()>search['_planningDeadline']:break
            try:consider(finalize_gaze(prepared,engine.c,sec),engine.c,'bounded_final_gaze_'+str(sec))
            except ValueError as exc:attempts.append({'origin':'bounded_final_gaze_'+str(sec),'error':str(exc)})
    working=best;engine=JointPlanner(b,working[0],working[1],search)
    for round_index in range(search['maximumRounds']):
        # Reserve mesh checks for later repairs instead of consuming the entire
        # budget on initial smoothing and the first round's early rooms.
        phase_mesh_limit=min(mesh_cap,2+math.ceil(max(0,mesh_cap-2)*(round_index+1)/search['maximumRounds']))
        # Soft doorway failures must get a bounded repair opportunity even when
        # all old numeric gates already pass. Never globally smooth a scoped edit.
        remaining=min(search['maximumDoorwayCandidates'],search['maximumFullEvaluations']-attempt,phase_mesh_limit-mesh_evaluations if job.get('meshPreflight',True) else search['maximumDoorwayCandidates'])
        if remaining>0 and time.monotonic()<search['_planningDeadline']:
            from tour_doorway import repair_candidates
            try:
                for native in repair_candidates(b,best[0],best[1],chapters=scope['chapters'] if scope else None,maximum_candidates=remaining,deadline=search['_planningDeadline']):
                    if attempt>=search['maximumFullEvaluations'] or time.monotonic()>search['_planningDeadline']:break
                    consider(native['tour'],native['config'],'native_doorway_round_'+str(round_index+1),{'repairEvidence':native['evidence']})
            except (ValueError,TimeoutError) as exc:
                if isinstance(exc,TimeoutError):native_budget_exhausted=True
                attempts.append({'origin':'native_doorway','round':round_index+1,'error':str(exc),'budgetExhausted':isinstance(exc,TimeoutError)})
        if scope is not None:
            working=best
            if not best[2]['issues']:break
            continue
        affected=set() if search.get('connectionOnly') else affected_chapters(*working)|set(feedback)
        if not best[2]['issues']:break
        # New brief jobs start with all stations participating in joint selection.
        if not job.get('seedTour') and round_index==0:affected={ch['name'] for _,ch in engine.obs}
        print(json.dumps({'round':round_index+1,'repairWindows':sorted(affected)},ensure_ascii=False),flush=True)
        try:beam=engine.joint_beam(affected,round_index)
        except ValueError as e:
            attempts.append({'origin':'candidate_pool','round':round_index+1,'error':str(e),'budgetRejections':engine.budget_rejections});beam=[]
        for error in engine.prepare_local_repairs(affected,round_index):
            attempts.append({'origin':'local_candidate_pool','round':round_index+1,**error})
        proposals=[('joint',choices) for _,choices in beam]
        evidence=working[2]['checks']['cameraEvidence'];marks=markers(working[0]);fps=working[0]['fps'];critical=[]
        for ch in working[1]['chapters']:
            if ch['phase']=='transit' and any((z-a)/fps>evidence['policy']['maximumNearWallSeconds'] and max(a,marks[ch['from']])<min(z,marks[ch['to']]) for a,z in evidence['wallFacing']['spansFrames']):critical.append(ch['name'])
        if critical:proposals.insert(0,('connection_only',{ch['name']:engine.baseline(ch) for _,ch in engine.obs}))

        # Also compare bounded local alternatives against the complete baseline.
        # A weak local proxy must not force every affected room to move at once.
        baseline_choices={ch['name']:engine.baseline(ch) for _,ch in engine.obs}
        marks=markers(working[0])
        def repair_priority(ch):
            a,z=marks[ch['from']],marks[ch['to']];score=0
            for issue in working[2]['issues']:
                f=issue.get('frame',issue.get('startSeconds',-1)*working[0]['fps'])
                if issue.get('chapter')==ch['name'] or a<=f<=z:
                    score+=100 if issue['code'] in ('path_acceleration_spike','path_tangent_discontinuity') else 10
                if issue.get('roomId')==ch.get('roomId'):score+=5
            return -score
        for _,ch in sorted(engine.obs,key=lambda row:repair_priority(row[1])):
            if ch['name'] not in affected:continue
            pool=engine.pool.get(ch['name'],{}).get('retained',[])
            for choice in [v for v in pool if v['source']!='seed']:
                proposals.append(('local_'+ch['name'],{**baseline_choices,ch['name']:choice}))
        local_evaluations={}
        for proposal_kind,choices,closing_mode in [(kind,values,mode) for kind,values in proposals for mode in ('seed','door')]:
            if attempt>=search['maximumFullEvaluations'] or time.monotonic()>search['_planningDeadline']:break
            if proposal_kind.startswith('local_') and local_evaluations.get(proposal_kind,0)>=search.get('localAlternatives',2):continue
            nav={'avoidBroadWallViews':True,'broadWallPenalty':80,'forwardWeight':6,'excessTurnPerStepWeight':30,'interpolation':'smoothstep',**search.get('navigationPolicy',{}),'closingView':closing_mode}
            if proposal_kind=='connection_only':nav['forceChapters']=critical
            try:
                candidate,cc=engine.rebuild(choices,nav)
                for sec in (.2,):consider(finalize_gaze(candidate,cc,sec),cc,f'{proposal_kind}_round_{round_index+1}_closing_{closing_mode}_smooth_{sec}',choices)
                if proposal_kind.startswith('local_'):local_evaluations[proposal_kind]=local_evaluations.get(proposal_kind,0)+1
            except ValueError as e:attempts.append({'origin':f'joint_round_{round_index+1}','proposal':proposal_kind,'closingView':closing_mode,'error':str(e),'budgetRejections':engine.budget_rejections[-4:]})
        working=best
        if frontier and best[2]['issues']:
            def exploration_key(state):
                report=state[2];cp=report['checks'].get('coverage',{});gap=sum(max(0,row.get('requiredPercent',cp.get('minimumPercent',0))-row['horizontalAreaPercent']) for row in cp.get('rooms',[]));over=sum(max(0,i.get('seconds',0)-i.get('maximumSeconds',0)) for i in report['issues'] if i['code']=='room_visit_over_budget')
                return (over+gap/10,len(report['issues']),state[0]['seconds'])
            working=min(frontier,key=exploration_key)
            dump(out/'exploration-frontier.json',{'diagnosticOnly':True,'seconds':working[0]['seconds'],'issues':working[2]['issues']})
            explore=out/'exploration-checkpoint';explore.mkdir(exist_ok=True);dump(explore/'tour.json',working[0]);dump(explore/'camera-config.json',working[1])
        frontier.clear();engine=JointPlanner(b,working[0],working[1],search)
        if attempt>=search['maximumFullEvaluations'] or time.monotonic()>search['_planningDeadline']:break
    # Fine framing repair for near-threshold coverage. Keep all positions and
    # viewing durations; use soft transitions rather than whole-camera rotation.
    fine_source=working
    cp=fine_source[2]['checks'].get('coverage',{})
    fringe=[] if scope is not None or search.get('strictRepairRounds') else [r['roomId'] for r in cp.get('rooms',[]) if 0<r.get('requiredPercent',cp.get('minimumPercent',0))-r['horizontalAreaPercent']<=6]
    for room in fringe:
        for degrees in (-2,2,-4,4,-6,6):
            if attempt>=search['maximumFullEvaluations'] or time.monotonic()>search['_planningDeadline']:break
            proposal=copy.deepcopy(fine_source[0]);pc=fine_source[1];marks=markers(proposal);radius=max(1,round(proposal['fps']*.35))
            for ch in pc['chapters']:
                if ch['phase']!='observe' or ch.get('roomId')!=room:continue
                a,z=marks[ch['from']],marks[ch['to']]
                for i in range(max(0,a-radius),min(len(proposal['frames']),z+radius+1)):
                    distance=max(a-i,i-z,0);weight=.5+.5*math.cos(math.pi*distance/radius) if distance else 1
                    proposal['frames'][i]['yawRadians']+=math.radians(degrees)*weight
            consider(finalize_gaze(proposal,pc,.06),pc,'fine_room_framing_'+room+'_'+str(degrees))
        # Compare whole-route connection policies without moving any observation station.
    # This is useful when all subjects are readable but return links dominate time.
    if scope is None and not search.get('strictRepairRounds') and best[2]['issues'] and attempt<search['maximumFullEvaluations']:
        engine=JointPlanner(b,best[0],best[1],search);fixed={ch['name']:engine.baseline(ch) for _,ch in engine.obs}
        forced=[ch['name'] for ch in best[1]['chapters'] if ch['phase']=='transit']
        for forward,turn in ((1,100),(12,30),(6,10)):
            if attempt>=search['maximumFullEvaluations'] or time.monotonic()>search['_planningDeadline']:break
            try:
                proposal,pc=engine.rebuild(fixed,{'avoidBroadWallViews':True,'broadWallPenalty':80,'forwardWeight':forward,'excessTurnPerStepWeight':turn,'interpolation':'smoothstep','forceChapters':forced})
                consider(finalize_gaze(proposal,pc,.2),pc,'whole_route_connection_policy_'+str(forward)+'_'+str(turn),fixed)
            except ValueError as exc:attempts.append({'origin':'whole_route_connection_policy','error':str(exc)})
    t,c,report=best
    if scope is None:
        c['cameraKeys']=[{'atStop':c['chapters'][0]['from'],'offsetFrames':i,'targetMm':[f['pointMm'][0]+1000*math.cos(f['yawRadians']),f['pointMm'][1]+1000*math.sin(f['yawRadians']),f['eyeMm']+1000*math.tan(f['pitchRadians'])],'yawDegrees':math.degrees(f['yawRadians']),'pitchDegrees':math.degrees(f['pitchRadians'])} for i,f in enumerate(t['frames'])]
    dump(out/'tour.json',t);dump(out/'camera-config.json',c);dump(out/'contract-report.json',report)
    dump(out/'search-report.json',{'schema':'homeowner-joint-search/1','attempts':attempts,'status':'numeric_pass_visual_pending' if not report['issues'] else 'needs_revision','remainingIssues':report['issues'],'sourceHashes':{k:sha(job[k]) for k in ('bundle','seedTour','seedConfig','brief') if job.get(k)},'videoGenerated':False,'humanAcceptance':'pending','actual3DPlayback':'not_performed','searchBounds':{k:v for k,v in search.items() if not k.startswith('_')},'elapsedSeconds':time.monotonic()-started,'engineHashes':{name:sha(Path(__file__).with_name(name)) for name in ('tour_pipeline.py','tour_contract.py','tour_camera_evidence.py','tour_coverage.py')},'limitations':['Bounded joint search, not proof of global optimum or infeasibility','Numeric and ray evidence do not grant dynamic comfort or human acceptance']})
    stage('numeric_checked',numericStatus=report['status'],remainingIssues=report['issues'])
    mesh_status='not_performed';audit=None;binding_issue=None
    if job.get('meshPreflight',True):
        node=shutil.which('node')
        if node:
            command=[node,str(Path(__file__).with_name('tour_mesh_preflight.mjs')),'--runtime',job['runtime'],'--tour',str(out/'tour.json'),'--config',str(out/'camera-config.json'),'--out',str(out/'mesh-subject-audit.json')]
            try:result=subprocess.run(command,capture_output=True,text=True,timeout=max(1,search['_finalDeadline']-time.monotonic()))
            except subprocess.TimeoutExpired:result=None;mesh_status='timeout';dump(out/'mesh-timeout.json',{'status':'action_required','reason':'Bounded planning deadline exhausted'})
            if result is not None:(out/'mesh-preflight.log').write_text(result.stdout+result.stderr)
            if result is not None and result.returncode==0:
                audit=read(out/'mesh-subject-audit.json');mesh_status=audit['status']
                if mesh_status=='pass':
                    from tour_camera_evidence import require_actual_targets
                    try:require_actual_targets(c,t,audit)
                    except ValueError as exc:
                        mesh_status='fail';binding_issue={'code':'actual_mesh_target_binding_invalid','message':str(exc)};dump(out/'mesh-order-issue.json',binding_issue)
            elif result is not None:mesh_status='error'
        else:mesh_status='unavailable'
    report=attach_doorway_evidence(b,t,c,attach_screen_evidence(contract(b,t,c),audit,known,job.get('meshPreflight',True)))
    if binding_issue:report['issues'].append(binding_issue)
    if native_budget_exhausted:report['issues'].append({'code':'native_repair_budget_exhausted','message':'Native repair reached its explicit deadline; no automatic continuation'})
    final_scope=scope_check(frozen_tour,t,c,scope);report.setdefault('checks',{})['revisionScope']=final_scope;report['issues']+=final_scope['issues']
    if report['issues']:report['status']='needs_revision'
    report=protect_satisfied_constraints(report,baseline_contract)
    attach_spatial_evidence(report,spatial,t)
    spatial_issues=report.get('checks',{}).get('spatialRoute',{}).get('issues',[])
    dump(out/'contract-report.json',report)
    summary=read(out/'search-report.json');summary.update(planningMode=mode,status=report['status'],remainingIssues=report['issues'],candidateMeshEvaluations=mesh_evaluations,finalMeshStatus=mesh_status)
    dump(out/'search-report.json',summary)
    from tour_rules import review_state
    dump(out/'self-check.json',{**review_state(report['status'],mesh_status),'actualPlayback':'not_performed','candidateMeshEvaluations':mesh_evaluations})
    from tour_revision_review import closeout_assessment
    closeout=closeout_assessment(frozen_tour,t,c,report,audit,scope=scope)
    changed=sum(a!=b for a,b in zip(frozen_tour['frames'],t['frames']))+abs(len(frozen_tour['frames'])-len(t['frames']))
    outcome={'status':'selected_revision' if changed else 'baseline_retained','selectedOrigin':selected_origin,'changedFrames':changed,'automaticVisualAcceptance':False}
    closeout['revisionOutcome']=outcome
    dump(out/'closeout-report.json',closeout)
    from tour_camera_diagnostics import build as camera_diagnostics
    dump(out/'camera-diagnostics.json',camera_diagnostics(b,t,c,engine.p,audit))
    summary=read(out/'search-report.json');summary['revisionOutcome']=outcome;dump(out/'search-report.json',summary)
    engineering=closeout['engineeringStatus']
    stage('engineering_verified' if engineering=='pass' else 'engineering_action_required',engineeringStatus=engineering,closeoutReport='closeout-report.json',humanAcceptance='pending',blockedStages=['video_capture'])
    if job.get('searchOnly',False):
        stage('search_checked_no_rehearsal',engineeringStatus=engineering,numericStatus=report['status'],meshVisibility=mesh_status,blockedStages=['video_capture'],rehearsalGenerated=False)
        return {'out':str(out),'status':'diagnostic_search_only','engineeringStatus':engineering,'seconds':t['seconds'],'remainingIssues':report['issues'],'rehearsalGenerated':False,'videoGenerated':False}
    from route_rehearsal import build
    manifest=build(out/'tour.json',out/'camera-config.json',job['bundle'],job['plan'],job['planBounds'],out/'rehearsal',c['maximumSeconds'],job['runtime'],job.get('label','全屋参观 · 镜头预演'),spatial)
    if mesh_status!='pass' or report['issues']:manifest['status']='needs_revision';dump(out/'rehearsal/rehearsal.json',manifest)
    stage('rehearsal_pending' if manifest['status']=='pending_user_review' else 'repair_required',meshVisibility=mesh_status,dynamicPlayback='not_performed',blockedStages=['video_capture'],nextAllowedStage='explicit_route_review' if manifest['status']=='pending_user_review' else 'return_to_route_confirmation' if spatial_issues else 'repair_and_recheck')
    make_synchronized_preview(out,job,t,manifest)
    from tour_revision_review import build_revision_review
    baseline_dir=out/'revision-baseline';baseline_dir.mkdir();dump(baseline_dir/'tour.json',frozen_tour);dump(baseline_dir/'camera-config.json',frozen_config)
    build_revision_review(out/'revision-review',baseline_dir/'tour.json',out/'tour.json',baseline_dir/'camera-config.json',out/'camera-config.json',job['runtime'],baseline_report=base,candidate_report={'contract':report,'mesh':audit,'scope':scope},limits={'maximumSeconds':c['maximumSeconds']})
    if scope is None and not search.get('strictRepairRounds') and mesh_status=='fail' and job.get('_meshRepairPass',0)<job.get('maximumMeshRepairPasses',1):
        child={**job,'seedTour':str(out/'tour.json'),'seedConfig':str(out/'camera-config.json'),'meshFeedback':str(out/'mesh-subject-audit.json'),'_meshRepairPass':job.get('_meshRepairPass',0)+1}
        child.pop('brief',None)
        result=run(child,out/'mesh-repair');dump(out/'continuation.json',result);stage('repair_handoff',selectedOutput=result['out']);return result
    return {'out':str(out),'status':manifest['status'],'engineeringStatus':engineering,'seconds':t['seconds'],'remainingIssues':report['issues'],'videoGenerated':False}

def make_synchronized_preview(out,job,tour,manifest):
    """Interactive 3D replay is not a captured video and grants no approval."""
    runtime=out/'runtime';runtime.mkdir()
    for name in ('scene.json','geometry.bin','renderer.html','three.module.js','three.core.js','THREE-LICENSE.txt'):shutil.copy2(Path(job['runtime'])/name,runtime/name)
    renderer_path=runtime/'renderer.html';renderer=renderer_path.read_text();renderer=renderer.replace('</style>','html,body{height:100%;background:#eeeae3}body{display:flex;align-items:center;justify-content:center}canvas{width:100%!important;height:auto!important;max-height:100%;object-fit:contain}</style>',1);renderer_path.write_text(renderer)

    dump(out/'replay.json',tour)
    label='待确认' if manifest['status']=='pending_user_review' else '内部诊断 · 尚有待调整项'
    from tour_playback import prepare_renderer,preview_page,ASSETS as playback_assets
    renderer_path.write_text(prepare_renderer(renderer_path.read_text()))
    shutil.copy2(playback_assets/'rehearsal-player.js',out/'rehearsal-player.js')
    page=preview_page(label)
    (out/'camera-preview.html').write_text(page)
    from tour_pages import build as build_pages
    build_pages(out/'rehearsal/rehearsal.json',out,existing=True)
    mp=out/'rehearsal/rehearsal.json';m=read(mp)
    m['references']['planAnimation']=m['references']['animation']
    for key,path in {'animation':out/'index.html','replay':out/'replay.json','replayRenderer':runtime/'renderer.html','cameraPreview':out/'camera-preview.html','routePage':out/'route.html','playbackModule':out/'rehearsal-player.js'}.items():m['references'][key]={'path':str(path),'sha256':sha(path)}
    pending=out/'visual-review.pending.json'
    dump(pending,{'schema':'homeowner-rehearsal-visual-review/1','result':'pending','observationMode':'not_performed','reviewedBy':'','evidence':'','tourSha256':sha(out/'tour.json'),'configSha256':sha(out/'camera-config.json'),'geometrySha256':sha(runtime/'geometry.bin'),'checks':{'transitionsNatural':False,'noRepeatedIntroduction':False,'noSustainedObstruction':False,'noUncomfortableTurns':False}})
    from tour_rules import fingerprint
    review_template=read(pending);review_template['ruleFingerprint']=fingerprint();dump(pending,review_template)
    m['references']['visualReview']={'path':str(pending),'sha256':sha(pending)}
    if (out/'mesh-subject-audit.json').exists():m['references']['screenAudit']={'path':str(out/'mesh-subject-audit.json'),'sha256':sha(out/'mesh-subject-audit.json')}
    dump(mp,m);review=read(out/'rehearsal/route-review.pending.json');review['rehearsal']['sha256']=sha(mp);dump(out/'rehearsal/route-review.pending.json',review)
    pages=read(out/'tour-pages.json');pages['inputs']['rehearsal']={'path':str(mp.resolve()),'sha256':sha(mp)};dump(out/'tour-pages.json',pages)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--job',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();result=run(read(a.job),a.out);print(json.dumps(result,ensure_ascii=False));return 0 if result.get('engineeringStatus')=='pass' else 2
if __name__=='__main__':raise SystemExit(main())
