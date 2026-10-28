"""Candidate mechanics shared by search and case regressions; never grants approval."""
import copy
import math


def protect_satisfied_constraints(report, baseline):
    """Do not exchange a previously satisfied hard constraint for fewer flags."""
    protected={'body_path_collision','scheme_mismatch','motion_limit',
        'camera_angular_acceleration','room_visit_over_budget','total_over_budget',
        'room_coverage_below_case_minimum','locked_total_duration_changed',
        'locked_viewing_duration_changed','locked_fps_changed','missing_core_view_target','core_facility_unreadable'}
    key=lambda x:(x['code'],x.get('roomId'),x.get('subjectId'),x.get('name'),x.get('axis'),x.get('chapter'),x.get('field'))
    old={key(x) for x in baseline['issues'] if x['code'] in protected}
    new=[copy.deepcopy(x) for x in report['issues'] if x['code'] in protected and key(x) not in old]
    report=copy.deepcopy(report)
    report.setdefault('checks',{})['introducedConstraintRegressions']=new
    if new:report['status']='needs_revision'
    return report


def attach_screen_evidence(report, audit, known=(), enabled=True):
    """Numeric failures do not remove the requirement for comparable screen evidence.
    Historical playback failures remain unresolved until an applicable new check
    clears them; a changed float or pose is not evidence of a repair.
    """
    report=copy.deepcopy(report)
    checked=bool(audit and audit.get('status') in ('pass','fail')
                 and audit.get('screenQuality',{}).get('status') in ('pass','needs_revision'))
    report.setdefault('checks',{})['screenEvidence']={
        'status':'checked' if checked else 'not_checked',
        'required':enabled,'meshStatus':audit.get('status') if audit else None}
    if checked:
        report['issues']+=copy.deepcopy(audit['screenQuality'].get('issues',[]))
        report['issues'] += [{'code':'actual_mesh_target_unreadable','chapter':r['id']}
                             for r in audit.get('chapters',[]) if not r['pass']]
        report['checks']['candidateMeshStatus']=audit['status']
    elif enabled:
        report['issues'].append({'code':'candidate_mesh_not_checked'})
    # The geometry proxy may clear a known geometric failure, not human comfort.
    # Unknown historical findings conservatively require the whole screen audit
    # to pass; the new rehearsal still awaits actual playback afterwards.
    cleared=checked and audit['status']=='pass'
    report['checks']['historicalVisualFindings']={
        'chapters':list(known),'geometryRechecked':checked,
        'geometryCleared':cleared,'actualPlayback':'pending'}
    if not cleared:
        report['issues'] += [{'code':'known_visual_failure_unverified','chapter':name}
                             for name in known]
    if report['issues']:report['status']='needs_revision'
    return report


def segment_effort(frames, limits):
    """Per-edge simultaneous walking/yaw/pitch work, in seconds."""
    return [max(math.dist(a['pointMm'],b['pointMm'])/1000/limits['maximumSpeedMps'],
                abs(b['yawRadians']-a['yawRadians'])*180/math.pi/limits['maxYawDegreesPerSecond'],
                abs(b['pitchRadians']-a['pitchRadians'])*180/math.pi/limits['maxPitchDegreesPerSecond'])
            for a,b in zip(frames,frames[1:])]

def connection_effort(points,yaws,start_pitch,end_pitch,limits):
    """Physical connection work, independent of redundant curve subdivisions.
    Pitch interpolates over elapsed time, so its global rate is a lower bound
    on the whole connection, not a compulsory wait at each geometry vertex.
    """
    if len(points)!=len(yaws) or len(points)<2:raise ValueError('Paired connection geometry/gaze required')
    work=[max(math.dist(a,b)/1000/limits['maximumSpeedMps'],
              abs(v-u)*180/math.pi/limits['maxYawDegreesPerSecond'])
          for a,b,u,v in zip(points,points[1:],yaws,yaws[1:])]
    total=sum(work);pitch=abs(end_pitch-start_pitch)*180/math.pi/limits['maxPitchDegreesPerSecond']
    if total<1e-12:return [pitch/len(work)]*len(work)
    scale=max(1.,pitch/total)
    return [v*scale for v in work]


def resample_segment(frames, count, efforts=None):
    """Keep both endpoint poses and use the assigned frame budget exactly."""
    import bisect
    if count<1:raise ValueError('Positive segment frame count required')
    if efforts is None:efforts=[1.]*(len(frames)-1)
    cumulative=[0.]
    for v in efforts:cumulative.append(cumulative[-1]+max(0,v))
    if cumulative[-1]<1e-10:
        cumulative=list(range(len(frames)))
    out=[]
    for i in range(count+1):
        s=cumulative[-1]*i/count
        j=max(0,min(len(frames)-2,bisect.bisect_right(cumulative,s)-1))
        u=(s-cumulative[j])/max(1e-12,cumulative[j+1]-cumulative[j])
        f=copy.deepcopy(frames[j])
        f['pointMm']=[frames[j]['pointMm'][k]*(1-u)+frames[j+1]['pointMm'][k]*u for k in (0,1)]
        for k in ('yawRadians','pitchRadians'):f[k]=frames[j][k]*(1-u)+frames[j+1][k]*u
        out.append(f)
    out[0]=copy.deepcopy(frames[0]);out[-1]=copy.deepcopy(frames[-1])
    return out


def framing_cost(bundle, chapter, point, yaw, pitch, eye, hfov=76, aspect=16/9):
    """Project physical upper/lower object bounds; lower is better.
    A geometric proposal score only. Actual mesh occlusion is checked separately.
    """
    from tour_camera_evidence import target_anchor
    from tour_core_targets import targets
    ids=targets(chapter)
    h=math.tan(math.radians(hfov/2));v=h/aspect;cost=0.;found=0
    co,si=math.cos(yaw),math.sin(yaw);cp,sp=math.cos(pitch),math.sin(pitch)
    for subject in ids:
        obj=next((x for x in bundle['state']['furniture'] if x['id']==subject),None)
        if obj:
            rot=math.radians(obj.get('rot',0));w=obj.get('w',0)/2;d=obj.get('d',0)/2
            bottom=obj.get('elevation',0);top=bottom+obj.get('h',1000)
            points=[[obj['cx']+x*math.cos(rot)-y*math.sin(rot),
                     obj['cy']+x*math.sin(rot)+y*math.cos(rot),z]
                    for x in (-w,w) for y in (-d,d) for z in (bottom,top)]
        else:
            q=target_anchor(bundle,subject);points=[q]
        projected=[]
        for q in points:
            x,y,z=q[0]-point[0],q[1]-point[1],q[2]-eye
            forward=(x*co+y*si)*cp+z*sp
            if forward<=30:continue
            projected.append(((-x*si+y*co)/forward/h,
                              (-(x*co+y*si)*sp+z*cp)/forward/v))
        if not projected:cost+=20;continue
        xs,ys=zip(*projected);left,right=min(xs),max(xs);low,high=min(ys),max(ys)
        crop=sum(max(0,abs(t)-.92) for t in (left,right,low,high))
        area=(right-left)*(high-low)/4
        cost+=crop*3+abs((low+high)/2+.05)*.3+max(0,area-.65)*4
        found+=1
    return cost/max(1,len(ids)) if found else 20.


def pitch_candidates(bundle, chapter, point, yaw, base, eye, hfov=76):
    """Search above and below the inherited pitch; 8/10 degrees are proposals only."""
    from tour_camera_evidence import target_anchor
    from tour_core_targets import targets
    ids=targets(chapter)
    heights=[]
    for subject in ids:
        q=target_anchor(bundle,subject)
        heights.append(math.atan2(q[2]-eye,max(1,math.dist(point,q[:2]))))
    centre=sum(heights)/len(heights) if heights else base
    pool={round(max(math.radians(-38),min(math.radians(1.15),p)),9)
          for p in (base,base-math.radians(5),base+math.radians(5),
                    math.radians(-5),math.radians(-8),math.radians(-10),centre)}
    return sorted(pool,key=lambda p:framing_cost(bundle,chapter,point,yaw,p,eye,hfov))


def smooth_position_seams(tour,config,planner):
    """Repair C1 joins in fixed time, with a short brake for a true reversal.
    Never moves chapter boundary points or changes frame counts. Candidate curves
    are rejected if unsafe or if their local speed/acceleration is not improved.
    """
    from tour_workflow import markers
    from tour_rules import trajectory
    out=copy.deepcopy(tour);fs=out['frames'];fps=out['fps'];marks=markers(tour)
    boundaries=sorted({marks[c['to']] for c in config['chapters'][:-1]})
    changes=[]
    for at in boundaries:
        if not 2<=at<len(fs)-2:continue
        before=[fs[at]['pointMm'][k]-fs[at-1]['pointMm'][k] for k in (0,1)]
        after=[fs[at+1]['pointMm'][k]-fs[at]['pointMm'][k] for k in (0,1)]
        if math.dist(before,after)*fps*fps/1000<=config.get('trajectoryPolicy',{}).get('maximumPlanarAccelerationMps2',3):continue
        left_bound=max([0]+[x for x in boundaries if x<at]);right_bound=min([len(fs)-1]+[x for x in boundaries if x>at])
        available=min(at-left_bound,right_bound-at)
        chosen=None;old_peak=None
        for width in sorted({min(available,max(3,round(fps*s))) for s in (.25,.4,.6,.8,1.2,1.5)}):
            if width<3:continue
            a,z=at-width,at+width
            original={'fps':fps,'frames':fs[max(0,a-1):min(len(fs),z+2)]}
            old_score=trajectory(original,config)
            candidate=copy.deepcopy(fs[a:z+1]);centre=fs[at]['pointMm'];reverse=sum(x*y for x,y in zip(before,after))<0
            tangent=[0.,0.] if reverse else [(x+y)/2 for x,y in zip(before,after)]
            # A sampled zero-velocity interval makes a reversal explicit, instead
            # of hiding an instantaneous 180 degree flip between moving frames.
            for lo,hi,p,q,v0,v1 in (
                (0,width,fs[a]['pointMm'],centre,
                 [fs[a]['pointMm'][k]-fs[a-1]['pointMm'][k] if a else before[k] for k in (0,1)],tangent),
                (width+(1 if reverse else 0),2*width,centre,fs[z]['pointMm'],tangent,
                 [fs[z+1]['pointMm'][k]-fs[z]['pointMm'][k] if z+1<len(fs) else after[k] for k in (0,1)])):
                n=hi-lo
                for j in range(n+1):
                    u=j/n;h00=2*u**3-3*u**2+1;h10=u**3-2*u**2+u;h01=-2*u**3+3*u**2;h11=u**3-u**2
                    candidate[lo+j]['pointMm']=[h00*p[k]+h10*n*v0[k]+h01*q[k]+h11*n*v1[k] for k in (0,1)]
            if reverse:candidate[width+1]['pointMm']=centre[:]
            # In a narrow doorway a spatial spline may cut a wall. Also try
            # braking along the existing safe arc, without taking a shortcut.
            from compact_tour_visits import at_distance
            arc_candidate=copy.deepcopy(fs[a:z+1]);arc_ok=True
            for lo,hi,points,start_speed,end_speed in (
                (0,width,[f['pointMm'] for f in fs[a:at+1]],math.dist(fs[a]['pointMm'],fs[a-1]['pointMm']) if a else math.hypot(*before),0.),
                (width+(1 if reverse else 0),2*width,[f['pointMm'] for f in fs[at:z+1]],0.,math.dist(fs[z+1]['pointMm'],fs[z]['pointMm']) if z+1<len(fs) else math.hypot(*after))):
                n=hi-lo;distance=sum(math.dist(x,y) for x,y in zip(points,points[1:]))
                for j in range(n+1):
                    u=j/n;d=(u**3-2*u**2+u)*n*start_speed+(-2*u**3+3*u**2)*distance+(u**3-u**2)*n*end_speed
                    if d< -1e-6 or d>distance+1e-6:arc_ok=False;break
                    arc_candidate[lo+j]['pointMm']=at_distance(points,max(0,min(distance,distance if j==n else d)))
            if reverse:arc_candidate[width+1]['pointMm']=centre[:]
            proposals=[candidate]+([arc_candidate] if arc_ok else [])
            for candidate in proposals:
                seq=fs[max(0,a-1):a]+candidate+fs[z+1:min(len(fs),z+2)]
                if any(planner.blocked(f['pointMm']) for f in candidate) or any(not planner.line_free(x['pointMm'],y['pointMm']) for x,y in zip(seq,seq[1:])):continue
                limits=config.get('motionReviewLimits',{})
                if max((math.dist(x['pointMm'],y['pointMm'])*fps/1000 for x,y in zip(seq,seq[1:])),default=0)>limits.get('maximumSpeedMps',1.2)+1e-6:continue
                score=trajectory({'fps':fps,'frames':seq},config)
                if score['maximumPlanarAccelerationMps2']>=old_score['maximumPlanarAccelerationMps2']-1e-6:continue
                value=(len(score['issues']),score['maximumPlanarAccelerationMps2'])
                if chosen is None or value<old_peak:chosen=(a,z,candidate);old_peak=value
        if chosen:
            a,z,candidate=chosen;fs[a:z+1]=candidate;changes.append(at)
    out['positionSeamRepair']={'boundaryFrames':changes,'frameCountPreserved':True,
                               'boundaryPositionsPreserved':True,'acceptance':'final_contract_required'}
    return out
