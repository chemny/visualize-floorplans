"""Collision-preserving arc-length speed profiles; no time lock relaxation."""
import math,bisect
from compact_tour_visits import dense_path,at_distance

def profile(path,maximum_speed=1200.,acceleration=2850.,fps=24,start_speed=0.,end_speed=0.):
    if any(not math.isfinite(v) or v<0 or v>maximum_speed for v in (start_speed,end_speed)):raise ValueError('Endpoint speed must be within walking limit')
    points=[]
    for p in dense_path(path,15):
        if not points or math.dist(points[-1],p)>.01:points.append(p)
    if len(points)<2:return {'points':[path[0],path[-1]],'arc':[0,0],'time':[0,0],'seconds':0}
    ds=[math.dist(a,b) for a,b in zip(points,points[1:])];speeds=[maximum_speed]*len(points)
    for i in range(1,len(points)-1):
        a,z=points[i-1],points[i+1];p=points[i];v=[p[k]-a[k] for k in (0,1)];w=[z[k]-p[k] for k in (0,1)];angle=abs(math.atan2(v[0]*w[1]-v[1]*w[0],sum(x*y for x,y in zip(v,w))));curvature=angle/max(1e-9,(ds[i-1]+ds[i])/2)
        if curvature>1e-9:speeds[i]=min(maximum_speed,math.sqrt(2500/curvature),math.radians(11)*fps/curvature)
        if angle>math.pi*.8:speeds[i]=0
    speeds[0]=start_speed;speeds[-1]=end_speed
    for i,d in enumerate(ds):speeds[i+1]=min(speeds[i+1],math.sqrt(speeds[i]**2+2*acceleration*d))
    for i in range(len(ds)-1,-1,-1):speeds[i]=min(speeds[i],math.sqrt(speeds[i+1]**2+2*acceleration*ds[i]))
    if abs(speeds[0]-start_speed)>1e-6 or abs(speeds[-1]-end_speed)>1e-6:raise ValueError('Requested boundary speeds need more path distance')
    times=[0];arc=[0]
    for i,d in enumerate(ds):
        if speeds[i]+speeds[i+1]<1e-9:raise ValueError('Adjacent zero-speed vertices need geometric replanning')
        times.append(times[-1]+2*d/(speeds[i]+speeds[i+1]));arc.append(arc[-1]+d)
    return {'points':points,'arc':arc,'time':times,'speed':speeds,'seconds':times[-1]}

def sample(profile,seconds):
    if profile['seconds']<1e-12:return profile['points'][0][:]
    times=profile['time'];i=max(0,min(len(times)-2,bisect.bisect_right(times,seconds)-1));dt=times[i+1]-times[i];u=max(0,min(1,(seconds-times[i])/max(dt,1e-12)))
    v0,v1=profile['speed'][i:i+2];travel=v0*u*dt+.5*(v1-v0)*u*u*dt;distance=profile['arc'][i+1]-profile['arc'][i];f=travel/max(distance,1e-12)
    return [profile['points'][i][k]*(1-f)+profile['points'][i+1][k]*f for k in (0,1)]


def coupled_clock(path_profile,yaws,maximum_yaw_degrees_per_second,headroom_fraction=.005):
    """Price local gaze work before smoothing, retaining spatial correspondence.

    max(total walk, total yaw) is not sufficient: the expensive turns may all
    occur on one short doorway segment. This clock stretches those segments
    explicitly. Final-frame acceleration and occlusion checks remain required.
    """
    if len(yaws)!=len(path_profile['time']):
        raise ValueError('Gaze and path samples must have identical anchors')
    if maximum_yaw_degrees_per_second<=0:
        raise ValueError('Positive yaw speed required')
    if not isinstance(headroom_fraction,(int,float)) or isinstance(headroom_fraction,bool) or not math.isfinite(headroom_fraction) or not 0<=headroom_fraction<=.05:raise ValueError('Clock headroom must be between zero and five percent')
    cap=math.radians(maximum_yaw_degrees_per_second)*(1-headroom_fraction)
    clock=[0.]
    for i in range(len(yaws)-1):
        clock.append(clock[-1]+max(path_profile['time'][i+1]-path_profile['time'][i],abs(yaws[i+1]-yaws[i])/cap))
    return clock


def spatial_time(path_profile,clock,seconds):
    i=max(0,min(len(clock)-2,bisect.bisect_right(clock,seconds)-1))
    u=max(0,min(1,(seconds-clock[i])/max(1e-12,clock[i+1]-clock[i])))
    return path_profile['time'][i]*(1-u)+path_profile['time'][i+1]*u


def assemble(engine,windows,navigation_policy,frozen_transits=None):
    """Preserve window counts and viewing shapes, price acceleration before joins.
    Observation coordinates may be reparameterized along their identical safe
    polyline to brake at boundaries; those changes require fresh full validation.
    """
    import copy
    from tour_workflow import markers
    from camera_gaze import delta
    from tour_workflow import chapter_limits
    from design_homeowner_tour import navigation_gaze
    headroom=navigation_policy.get('clockHeadroomFraction',.005)
    if not isinstance(headroom,(int,float)) or isinstance(headroom,bool) or not math.isfinite(headroom) or not 0<=headroom<=.05:raise ValueError('Clock headroom must be between zero and five percent')
    settle=navigation_policy.get('clockSettleSeconds',.12)
    if not isinstance(settle,(int,float)) or isinstance(settle,bool) or not math.isfinite(settle) or not 0<=settle<=.5:raise ValueError('Finite clock settling reserve required')
    chapters=engine.c['chapters'];windows=copy.deepcopy(windows);fps=engine.fps;config=copy.deepcopy(engine.c);groups=[]
    for ch in chapters:
        if ch['phase']!='observe':continue
        if groups and groups[-1][-1]['to']==ch['from']:groups[-1].append(ch)
        else:groups.append([ch])
    changes=[]
    for group in groups:
        original=[];ends=[]
        for ch in group:
            chunk=windows[ch['from']];original.extend(chunk if not original else chunk[1:]);ends.append((ch,len(original)-1))
        if navigation_policy.get('preserveObservationPositions') and all(
            len(windows[ch['from']])==engine.m[ch['to']]-engine.m[ch['from']]+1 and
            all(a['pointMm']==b['pointMm'] for a,b in zip(windows[ch['from']],engine.t['frames'][engine.m[ch['from']]:engine.m[ch['to']]+1]))
            for ch in group):
            changes.extend({'chapter':ch['name'],'maximumPositionDisplacementMm':0,'sourcePositionsFrozen':True} for ch in group)
            continue
        path=[f['pointMm'] for f in original];p=profile(path,engine.limits['maximumSpeedMps']*1000*(1-headroom),fps=fps);seconds=(len(original)-1)/fps
        if p['seconds']>seconds+1e-6:raise ValueError(f'Observation movement cannot brake within fixed window: {group[0]["name"]}, needs {p["seconds"]:.6f}s, available {seconds:.6f}s')
        updated=copy.deepcopy(original)
        original_speed=max((math.dist(a['pointMm'],z['pointMm'])*fps for a,z in zip(original,original[1:])),default=0)
        slow=0<original_speed<=120
        if slow:p={'seconds':0}
        if p['seconds']>0:
            for i,f in enumerate(updated):f['pointMm']=sample(p,p['seconds']*i/(len(updated)-1))
            updated[0]['pointMm']=original[0]['pointMm'][:];updated[-1]['pointMm']=original[-1]['pointMm'][:]
        if slow:
            # Brake only the boundary samples, retaining the qualified interior.
            width=min(8,max(4,(len(original)-3)//2));last=len(updated)-1
            for side in ('start','end'):
                if side=='start':a,z=1,1+width;points=[f['pointMm'] for f in original[:z+1]];v=math.dist(original[z+1]['pointMm'],original[z]['pointMm']);initial=False
                else:a,z=last-width-1,last-1;points=[f['pointMm'] for f in original[a:]];v=math.dist(original[a]['pointMm'],original[a-1]['pointMm']);initial=True
                distance=sum(math.dist(x,y) for x,y in zip(points,points[1:]));n=z-a
                for j in range(n+1):
                    u=j/n;d=(-2*u**3+3*u**2)*distance+((u**3-2*u**2+u)*n*v if initial else (u**3-u**2)*n*v)
                    updated[a+j]['pointMm']=at_distance(points,max(0,min(distance,d)))
            updated[0]['pointMm']=updated[1]['pointMm']=original[0]['pointMm'][:];updated[-2]['pointMm']=updated[-1]['pointMm']=original[-1]['pointMm'][:]
        start=0
        for ch,end in ends:
            windows[ch['from']]=updated[start:end+1];changes.append({'chapter':ch['name'],'maximumPositionDisplacementMm':max(math.dist(a['pointMm'],z['pointMm']) for a,z in zip(original[start:end+1],updated[start:end+1]))});start=end
    source=engine.entry;segments=[];frozen_transits=frozen_transits or {}
    if set(frozen_transits)-{ch['name'] for ch in chapters if ch['phase']=='transit'}:raise ValueError('Frozen transit must name an existing transit chapter')
    for ch in chapters:
        if ch['phase']=='observe':
            frames=windows[ch['from']];segments.append({'chapter':ch,'frames':frames,'fixed':True,'count':len(frames)-1});source=frames[-1];continue
        dest=windows[ch['to']][0] if ch['to'] in windows else engine.closing_pose()
        if ch['name'] in frozen_transits:
            chunk=copy.deepcopy(frozen_transits[ch['name']])
            if len(chunk)<2:raise ValueError('Frozen transit needs endpoint context')
            for actual,expected in ((chunk[0],source),(chunk[-1],dest)):
                if math.dist(actual['pointMm'],expected['pointMm'])>.001 or abs(delta(actual['yawRadians'],expected['yawRadians']))>1e-8 or abs(actual['pitchRadians']-expected['pitchRadians'])>1e-8:raise ValueError('Frozen transit endpoints differ from current room framing')
                for field in ('eyeMm','horizontalFovDegrees','shiftY'):
                    if actual.get(field)!=expected.get(field):raise ValueError('Frozen transit camera profile differs from current framing')
            segments.append({'chapter':ch,'frames':chunk,'fixed':True,'count':len(chunk)-1});source=chunk[-1];continue
        path=engine.connection_path(source['pointMm'],dest['pointMm'],ch);p=profile(path,engine.limits['maximumSpeedMps']*1000*(1-headroom),fps=fps)
        limits=chapter_limits(engine.limits,ch)
        distances=p['arc'];local={**navigation_policy,**ch.get('navigationPolicy',{}),'maximumSpeedMps':limits['maximumSpeedMps'],'maxYawDegreesPerSecond':limits['maxYawDegreesPerSecond']}
        if local.get('gazeVia'):
            anchors=[(0.,source['yawRadians'])]
            for fraction,degrees in local['gazeVia']:
                if not 0<fraction<1 or fraction<=anchors[-1][0]:raise ValueError('Ordered connection gaze fractions required')
                yaw=math.radians(degrees);anchors.append((fraction,anchors[-1][1]+delta(anchors[-1][1],yaw)))
            anchors.append((1.,anchors[-1][1]+delta(anchors[-1][1],dest['yawRadians'])))
            ys=[]
            for d in distances:
                f=d/max(1e-12,distances[-1]);k=max(0,min(len(anchors)-2,bisect.bisect_right([v[0] for v in anchors],f)-1));u=(f-anchors[k][0])/(anchors[k+1][0]-anchors[k][0]);ys.append(anchors[k][1]*(1-u)+anchors[k+1][1]*u)
        elif local.get('monotoneEndpointGaze') or p['seconds']==0:ys=[source['yawRadians']+delta(source['yawRadians'],dest['yawRadians'])*d/max(distances[-1],1e-12) for d in distances]
        else:ys=navigation_gaze(engine.p,p['points'],distances,source['yawRadians'],dest['yawRadians'],local)
        turn=sum(abs(z-a) for a,z in zip(ys,ys[1:]))*180/math.pi/limits['maxYawDegreesPerSecond'];pitch=abs(dest['pitchRadians']-source['pitchRadians'])*180/math.pi/limits['maxPitchDegreesPerSecond'];clock=coupled_clock(p,ys,limits['maxYawDegreesPerSecond'],headroom);needed=max(clock[-1],turn+settle,pitch+settle)
        minimum_frames=ch.get('minimumTransitFrames',0)
        if isinstance(minimum_frames,bool) or not isinstance(minimum_frames,int) or minimum_frames<0:raise ValueError('minimumTransitFrames must be a nonnegative integer')
        segments.append({'chapter':ch,'fixed':False,'source':source,'dest':dest,'profile':p,'clock':clock,'yaws':ys,'count':max(1,minimum_frames,math.ceil(needed*fps)),'minimumSeconds':needed});source=dest
    available=config['timingLocks']['totalFrames']-1-sum(s['count'] for s in segments if s['fixed']);required=sum(s['count'] for s in segments if not s['fixed'])
    pricing={'clockHeadroomFraction':headroom,'clockSettleSeconds':settle,'actualMotionLimits':engine.limits.copy(),'frozenTransitChapters':list(frozen_transits),'requiredTransitFrames':required,'availableTransitFrames':available,'differenceFrames':required-available,'differenceSeconds':(required-available)/fps,'legs':[{'chapter':s['chapter']['name'],'frames':s['count'],'minimumSeconds':s['minimumSeconds']} for s in segments if not s['fixed']],'observationReparameterization':changes}
    if required>available:return None,config,pricing
    free=[s for s in segments if not s['fixed']];slack=available-required;weights=[max(1,sum(abs(math.atan2((b[0]-a[0])*(d[1]-b[1])-(b[1]-a[1])*(d[0]-b[0]),(b[0]-a[0])*(d[0]-b[0])+(b[1]-a[1])*(d[1]-b[1]))) for a,b,d in zip(s['profile']['points'],s['profile']['points'][1:],s['profile']['points'][2:]))*100) for s in free];total=sum(weights);additions=[slack*w/total for w in weights]
    for s,addition in zip(free,additions):s['count']+=int(addition)
    remainder=available-sum(s['count'] for s in free)
    for i in sorted(range(len(free)),key=lambda i:additions[i]-int(additions[i]),reverse=True)[:remainder]:free[i]['count']+=1
    frames=[copy.deepcopy(engine.entry)];visits=[{'name':chapters[0]['from'],'frame':0}]
    for s in segments:
        if s['fixed']:chunk=copy.deepcopy(s['frames'])
        else:
            p=s['profile'];ys=s['yaws'];chunk=[]
            for i in range(s['count']+1):
                u=i/s['count'];tm=spatial_time(p,s['clock'],u*s['clock'][-1]);point=sample(p,tm);k=max(0,min(len(p['time'])-2,bisect.bisect_right(p['time'],tm)-1));d=math.dist(point,p['points'][k]);frac=d/max(1e-12,p['arc'][k+1]-p['arc'][k]);yaw=ys[k]*(1-frac)+ys[k+1]*frac if p['arc'][-1]>1e-12 else ys[0]*(1-u)+ys[-1]*u;f=copy.deepcopy(s['source']);f.update(pointMm=point,yawRadians=yaw,pitchRadians=s['source']['pitchRadians']*(1-u)+s['dest']['pitchRadians']*u);chunk.append(f)
            chunk[0]=copy.deepcopy(s['source']);chunk[-1]=copy.deepcopy(s['dest']);chunk[-1]['yawRadians']=ys[-1]
        offset=frames[-1]['yawRadians']+delta(frames[-1]['yawRadians'],chunk[0]['yawRadians'])-chunk[0]['yawRadians']
        for f in chunk:f['yawRadians']+=offset
        frames.extend(chunk[1:]);visits.append({'name':s['chapter']['to'],'frame':len(frames)-1})
    for i,f in enumerate(frames):f['frame']=i
    return {**copy.deepcopy(engine.t),'frames':frames,'visits':visits,'seconds':len(frames)/fps},config,pricing
