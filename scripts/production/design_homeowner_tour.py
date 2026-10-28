"""Shared homeowner tour design: evidence-backed stops, distance ordering, semantic gaze.
Produces route/camera JSON only. Never captures video or grants approval.
"""
import argparse, copy, json, math
from pathlib import Path
from plan_route import Planner, inside, dist_segment
from camera_gaze import generate, PROFILE, delta
from tour_workflow import retime, intent_check


def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,x): Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')


def opening_candidates(bundle,planner,room,opening_id):
    """Choose shallow floor positions using an actual opening and its free side."""
    found=[]
    for w in bundle['state']['walls']:
        if w.get('demolished'): continue
        for o in w['opens']:
            if o.get('id')!=opening_id: continue
            if o['kind'] not in ('door','sliding'): raise ValueError('Window is not a tour entrance')
            length=math.dist(w['a'],w['b']);v=[(w['b'][i]-w['a'][i])/length for i in (0,1)];n=[-v[1],v[0]]
            for ratio in (.3,.5,.7):
                gate=[w['a'][i]+v[i]*(o['at']+o['width']*ratio) for i in (0,1)]
                for side in (-1,1):
                    inward=[gate[i]+n[i]*side*(w['t']/2+300) for i in (0,1)]
                    if not inside(inward,room['poly']):continue
                    for depth in (-400,-250,0,200,350,500,750,1000):
                        p=[gate[i]+n[i]*side*(w['t']/2+depth) for i in (0,1)]
                        if not planner.blocked(p):found.append((p,depth,gate))
    return found


def select_observation(bundle,planner,intent):
    room=next((r for r in bundle['model']['rooms'] if r['id']==intent['roomId']),None)
    if room is None: raise ValueError('Unknown room '+intent['roomId'])
    if not any(f['id']==intent['subjectId'] for f in bundle['state']['furniture']):raise ValueError('Unknown subject '+intent['subjectId'])
    from tour_camera_evidence import target_anchor,ordered_bearings,visibility_planner
    ordered=intent.get('orderedViewTargets',[])
    anchors=[target_anchor(bundle,x) for x in ordered]
    if anchors:intent={**intent,'targetMm':anchors[0]}
    target=intent['targetMm'];candidates=[]
    door_candidates=opening_candidates(bundle,planner,room,intent['openingId']) if intent.get('openingId') else []
    if not intent.get('candidatePointsOnly'):candidates=door_candidates
    observation_region=room
    if intent.get('observationRegionId'):
        observation_region=next((r for r in bundle['model']['rooms'] if r['id']==intent['observationRegionId']),None)
        if observation_region is None:raise ValueError('Unknown observationRegionId')
    for p in intent.get('candidatePoints',[]):
        nearby_door=intent.get('openingId') and any(gate and math.dist(p,gate)<1500 for _,_,gate in door_candidates)
        if (inside(p,observation_region['poly']) or nearby_door) and not planner.blocked(p):candidates.append((p,math.dist(p,intent['entryReferencePoint']) if intent.get('entryReferencePoint') else intent.get('candidateDepthMm',0),None))
    if intent.get('requireInsideRoom'):candidates=[x for x in candidates if inside(x[0],room['poly'])]
    if not candidates:raise ValueError('No supported observation candidates for '+intent['name'])
    visible=[]
    for p,depth,gate in candidates:
        distance=math.dist(p,target[:2])
        if not 650<=distance<=7000:continue
        # A wall/leaf occlusion proxy, not actual mesh visibility acceptance.
        yaw=math.atan2(target[1]-p[1],target[0]-p[0])
        primary_planner=visibility_planner(bundle,planner,ordered[0] if ordered else intent['subjectId'])
        if clear_distance(primary_planner,p,yaw,distance)<distance-60:continue
        try:bearings=ordered_bearings(bundle,ordered,p)
        except ValueError:continue
        if any(clear_distance(visibility_planner(bundle,planner,subject),p,v,math.dist(p,q[:2]))<math.dist(p,q[:2])-60 for subject,v,q in zip(ordered,bearings,anchors)):continue
        targets=intent.get('viewTargets',[])
        def target_fits(q):
            direction=math.atan2(q[1]-p[1],q[0]-p[0]);offsets=[abs(delta(yaw+math.radians(intent.get('observationPanDegrees',0))*i/12,direction)) for i in range(13)] if intent.get('viewTargetsMode')=='sweep' else [abs(delta(yaw,direction))]
            return clear_distance(planner,p,direction,math.dist(p,q[:2]))>=math.dist(p,q[:2])-60 and min(offsets)<=math.radians(33)
        if any(not target_fits(q) for q in targets):continue
        score=max(0,depth)/800+abs(distance-intent.get('preferredDistanceMm',2200))/2000
        visible.append((score,p,depth,gate))
    if not visible:raise ValueError('No unoccluded observation proxy for '+intent['name']+'; revise evidence-backed candidates')
    _,point,depth,gate=min(visible,key=lambda x:x[0])
    return {**intent,'point':point,'selectedDepthMm':depth,'gatewayPoint':gate,'candidateCount':len(candidates),'visibleCandidateCount':len(visible),'visibility':'2D wall/leaf proxy only; mesh subjects pending'}


def path_length(path): return sum(math.dist(a,b) for a,b in zip(path,path[1:]))


def order_groups(start,groups,distance,end_id=None,return_to=None,stages=None):
    """Held-Karp on groups; suite members stay together. Exact for chosen fixed stops."""
    n=len(groups)
    if not 1<=n<=12:raise ValueError('Use 1..12 room groups; split a larger case explicitly')
    stages=stages or [0]*n
    if len(stages)!=n:raise ValueError('One presentation stage required per group')
    prerequisites=[sum(1<<j for j in range(n) if stages[j]<stages[i]) for i in range(n)]
    cost={};parent={}
    internal=[sum(distance(a,b) for a,b in zip(g,g[1:])) for g in groups]
    for i,g in enumerate(groups):
        if prerequisites[i]:continue
        cost[1<<i,i]=distance(start,g[0])+internal[i];parent[1<<i,i]=None
    for mask in range(1,1<<n):
        for i in range(n):
            if (mask,i) not in cost:continue
            for j in range(n):
                if mask>>j&1 or mask&prerequisites[j]!=prerequisites[j]:continue
                key=(mask|1<<j,j);v=cost[mask,i]+distance(groups[i][-1],groups[j][0])+internal[j]
                if v<cost.get(key,float('inf')):cost[key]=v;parent[key]=(mask,i)
    full=(1<<n)-1;eligible=[i for i,g in enumerate(groups) if (end_id is None or g[-1]==end_id) and (full,i) in cost]
    if not eligible:raise ValueError('End must be the last member of a room group')
    terminal=lambda j:cost[full,j]+(distance(groups[j][-1],return_to) if return_to is not None else 0)
    i=min(eligible,key=terminal);best=terminal(i);key=(full,i);order=[]
    while key is not None:order.append(key[1]);key=parent[key]
    return [name for i in reversed(order) for name in groups[i]],best


def entry_apron(bundle,brief):
    """An explicit camera apron at the confirmed door, not invented corridor geometry."""
    opening_id=brief.get('entranceOpeningId')
    for wall in bundle['state']['walls']:
        if wall.get('demolished'):continue
        for opening in wall['opens']:
            if opening.get('id')!=opening_id:continue
            if opening['kind']!='door':raise ValueError('Full tour needs a confirmed entrance door')
            start=brief['startPoint'];length=math.dist(wall['a'],wall['b']);v=[(wall['b'][k]-wall['a'][k])/length for k in (0,1)]
            n=[-v[1],v[0]];projection=sum((start[k]-wall['a'][k])*v[k] for k in (0,1))
            if not opening['at']<=projection<=opening['at']+opening['width']:raise ValueError('Exterior camera point must align with the confirmed doorway')
            offset=sum((start[k]-wall['a'][k])*n[k] for k in (0,1));side=1 if offset>0 else -1
            if abs(offset)>1500 or abs(offset)<wall['t']/2+brief.get('bodyRadiusMm',180):raise ValueError('Place exterior camera within 1.5 m of the door, clear of wall')
            if inside(start,bundle['model']['footprint']):raise ValueError('Full tour must start and finish outside the footprint')
            along=[opening['at']-250,opening['at']+opening['width']+250];depth=abs(offset)+350
            poly=[[wall['a'][k]+v[k]*a+n[k]*side*d for k in (0,1)] for a,d in [(along[0],0),(along[1],0),(along[1],depth),(along[0],depth)]]
            return [poly],[start[k]+n[k]*side*1000 for k in (0,1)]+[1400]
    raise ValueError('Full tour needs entranceOpeningId from the actual scheme')


def clear_distance(planner,point,yaw,maximum=1800):
    """Ray against current wall/door bounds; short-wall view proxy, not a screenshot."""
    dx,dy=math.cos(yaw),math.sin(yaw);best=maximum
    for a,b,half in planner.walls+getattr(planner,'vision_leaves',planner.leaves):
        length=math.dist(a,b)
        # Intersect the actual oriented strip with flat ends. An axis-aligned
        # bounding box turns open air beside an oblique leaf into an opaque
        # wall and adds fictitious thickness along each doorway jamb.
        ux,uy=((b[0]-a[0])/length,(b[1]-a[1])/length) if length>1e-9 else (1.,0.)
        px,py=point[0]-a[0],point[1]-a[1]
        origin=(px*ux+py*uy,-px*uy+py*ux)
        direction=(dx*ux+dy*uy,-dx*uy+dy*ux)
        low=(0.,-half) if length>1e-9 else (-half,-half)
        high=(length,half) if length>1e-9 else (half,half);near=0;far=maximum
        for k,v in enumerate(direction):
            if abs(v)<1e-8:
                if not low[k]<=origin[k]<=high[k]:near=maximum+1;break
            else:
                u,z=sorted(((low[k]-origin[k])/v,(high[k]-origin[k])/v));near=max(near,u);far=min(far,z)
        if near<=far and far>0:best=min(best,max(0,near))
    return best


def navigation_gaze(planner,dense,distances,start_yaw,end_yaw,policy=None):
    """Spatial gaze DP: favour open, forward views with little turning/reversal.
    Endpoints are room/exit intents. No fixed-time path chasing or full-room sweep.
    """
    import bisect
    policy=policy or {}
    if policy.get('coveragePolygons'):
        from tour_navigation_coverage import gaze
        return gaze(planner,dense,distances,start_yaw,end_yaw,policy)
    indices=[0]
    for i,d in enumerate(distances[1:-1],1):
        if d-distances[indices[-1]]>=350:indices.append(i)
    indices.append(len(dense)-1)
    candidates=[math.radians(i*15) for i in range(24)]+[start_yaw,end_yaw]
    start_index=24;end_index=25;states={(start_index,0):0};parents=[]
    for node,index in enumerate(indices[1:],1):
        pos=dense[index];a=dense[max(0,index-10)];b=dense[min(len(dense)-1,index+15)];bearing=math.atan2(b[1]-a[1],b[0]-a[0])
        step=distances[index]-distances[indices[node-1]];options=[end_index] if node==len(indices)-1 else range(len(candidates))
        new={};back={};edge_cache={}
        for j in options:
            yaw=candidates[j];clear=clear_distance(planner,pos,yaw);off=abs(math.degrees(delta(bearing,yaw)))
            visibility=max(0,1100-clear)/1100*55
            fan=[clear_distance(planner,pos,yaw+math.radians(a)) for a in (-35,-21,-7,7,21,35)]
            if sum(d<900 for d in fan)/len(fan)>=.7:visibility+=policy.get('broadWallPenalty',0)
            if policy.get('avoidBroadWallViews') and sum(clear_distance(planner,pos,yaw+math.radians(a))<900 for a in (-30,-15,0,15,30))>=4:visibility+=2000
            # Furniture/wall costs must not purchase sustained backwards travel.
            # Endpoint gaze can still need a stationary pre-turn; the final-frame
            # forward-motion contract rejects infeasible timing after smoothing.
            if node<len(indices)-1 and off>90:continue
            orientation=max(0,off-60)/90*policy.get('forwardWeight',6)
            local=(visibility+orientation)*max(.2,step/350)
            for (previous,sign),cost in states.items():
                change=math.degrees(delta(candidates[previous],yaw));direction=1 if change>2 else -1 if change< -2 else sign
                initial_direction=policy.get('initialTurnDirection',0)
                if distances[index]<=policy.get('initialTurnDistanceMm',900) and initial_direction and change*initial_direction<-.001:continue
                edge_key=(previous,j)
                if edge_key not in edge_cache:
                    before=dense[indices[node-1]];penalties=[]
                    for u in (.33,.66):
                        sample=[before[k]+(pos[k]-before[k])*u for k in (0,1)]
                        direction_yaw=candidates[previous]+delta(candidates[previous],yaw)*u
                        clearance=clear_distance(planner,sample,direction_yaw)
                        penalty=max(0,850-clearance)/850*80
                        local_bearing=math.atan2(pos[1]-before[1],pos[0]-before[0])
                        if abs(math.degrees(delta(local_bearing,direction_yaw)))>90:penalty+=10000
                        if policy.get('avoidBroadWallViews') and sum(clear_distance(planner,sample,direction_yaw+math.radians(a))<900 for a in (-30,-15,0,15,30))>=4:penalty+=2000
                        penalties.append(penalty)
                    edge_cache[edge_key]=sum(penalties)/len(penalties)*max(.2,step/350)
                # Penalize turns that cannot overlap walking at the existing ceilings.
                excess=max(0,abs(change)-step/1200*32)
                value=cost+abs(change)*.35+(5 if sign and direction!=sign else 0)+local+edge_cache[edge_key]+policy.get('excessTurnPerStepWeight',0)*excess
                key=(j,direction)
                if value<new.get(key,float('inf')):new[key]=value;back[key]=(previous,sign)
        if not new:raise ValueError('No forward-facing navigation gaze; replan the doorway approach or allow a stationary turn budget')
        states=new;parents.append(back)
    state=min(states,key=states.get);chosen=[state[0]]
    for back in reversed(parents):state=back[state];chosen.append(state[0])
    chosen.reverse();angles=[candidates[chosen[0]]]
    for j in chosen[1:]:angles.append(angles[-1]+delta(angles[-1],candidates[j]))
    result=[]
    key_distances=[distances[i] for i in indices]
    for distance in distances:
        k=max(0,min(len(indices)-2,bisect.bisect_right(key_distances,distance)-1));u=(distance-key_distances[k])/max(1,key_distances[k+1]-key_distances[k]);u=max(0,min(1,u))
        if policy.get('interpolation')!='linear':u=u*u*(3-2*u)
        result.append(angles[k]+(angles[k+1]-angles[k])*u)
    return result


def design(bundle,brief):
    from tour_core_targets import inventory
    actual=inventory(bundle);brief=copy.deepcopy(brief)
    for room in brief.get('rooms',[]):
        from tour_camera_evidence import target_anchor
        ids=[f['subjectId'] for f in actual.get(room['roomId'],[])]
        room['coreTargetIds']=ids
        # Seed geometry remains diagnostic. Joint search adapts the scan to all
        # bound core targets; a narrow inherited pan must not prevent that search.
    if brief.get('schema')!='homeowner-design-brief/1':raise ValueError('Unsupported design brief')
    if isinstance(brief.get('maximumSeconds'),bool) or not isinstance(brief.get('maximumSeconds'),(int,float)) or not math.isfinite(brief['maximumSeconds']) or brief['maximumSeconds']<=0:raise ValueError('Positive finite maximumSeconds required')
    if not brief.get('rooms'):raise ValueError('At least one case room observation required')
    for observation in brief['rooms']:
        if not str(observation.get('viewPurpose','')).strip():raise ValueError('Each observation needs a viewing purpose, not only a furniture target')
        if not math.isfinite(observation.get('viewSeconds',0)) or observation['viewSeconds']<=0:raise ValueError('Positive viewing budget required')
    from tour_observation_points import validate as validate_points
    point_policy=validate_points(brief['rooms'],brief.get('observationPointPolicy'))
    from tour_contract import from_brief
    contract_policy=from_brief(brief)
    room_policy={'singleEpisode':True,'excludeNormalTransit':True,**brief.get('roomViewingPolicy',{})}
    if room_policy['singleEpisode']:
        seen={}
        for x in brief['rooms']:
            room=x['roomId'];episode=x.get('episodeId')
            if room in seen and (not episode or episode!=seen[room]):raise ValueError('A room must be completed in one viewing episode; distinct observation IDs do not allow an entry/return split')
            seen[room]=episode
    full=brief.get('tourMode','full_tour')=='full_tour'
    access,outward=entry_apron(bundle,brief) if full else ([],None)
    planner=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':brief.get('bodyRadiusMm',180)+brief.get('planningMarginMm',25),'gridMm':brief.get('gridMm',50)})
    selected=[select_observation(bundle,planner,{**x,'requireInsideRoom':x.get('requireInsideRoom',not bool(x.get('observationRegionId')))}) for x in brief['rooms']]
    for observation in selected:
        point=observation['point'];target=observation['targetMm'];centre=math.atan2(target[1]-point[1],target[0]-point[0]);requested=observation.get('observationPanDegrees',brief.get('observationPanDegrees',0))
        if observation.get('orderedViewTargets'):
            from tour_camera_evidence import ordered_bearings
            angles=ordered_bearings(bundle,observation['orderedViewTargets'],point)
            requested=math.degrees(angles[-1]-angles[0]);observation['lockPanDirection']=True
        options=[requested] if observation.get('lockPanDirection') else list(dict.fromkeys([requested,-requested,requested/2,-requested/2,0]))
        def openness(degrees):
            for q in observation.get('viewTargets',[]):
                offsets=[abs(delta(centre+math.radians(degrees)*i/12,math.atan2(q[1]-point[1],q[0]-point[0]))) for i in range(13)]
                if (min(offsets) if observation.get('viewTargetsMode')=='sweep' else max(offsets))>math.radians(33):return -float('inf')
            return min(clear_distance(planner,point,centre+math.radians(degrees)*i/12) for i in range(13))
        observation['selectedPanDegrees']=max(options,key=openness)
        if not math.isfinite(openness(observation['selectedPanDegrees'])):raise ValueError('Required viewing targets do not fit requested sweep')
    by_id={x.get('observationId',x['roomId']):x for x in selected}
    if len(by_id)!=len(selected):raise ValueError('Duplicate observation room')
    start='__entry__';points={start:brief['startPoint'],**{x.get('observationId',x['roomId']):x['point'] for x in selected}}
    if planner.blocked(points[start]):raise ValueError('Blocked entrance start')
    groups=brief.get('groups',[[x] for x in by_id]);flat=[x for g in groups for x in g]
    if len(flat)!=len(set(flat)) or set(flat)!=set(by_id):raise ValueError('Groups must cover each observation exactly once')
    paths={}
    def route(a,b):
        if (a,b) not in paths:
            paths[a,b]=planner.simplify(planner.astar(points[a],points[b]))
        return paths[a,b]
    distance=lambda a,b:path_length(route(a,b))
    priorities={'public':0,'primary':1,'secondary':2,'service':3,'return':4,'return_public':1.5}
    try:stages=[priorities[by_id[g[0]]['tourRole']] for g in groups]
    except KeyError as e:raise ValueError('Each room/group needs an explicit tourRole: public, primary, secondary or service') from e
    if any(len({by_id[r]['tourRole'] for r in g})!=1 for g in groups):raise ValueError('A presentation group cannot mix incompatible roles')
    if brief.get('fixedOrder'):
        order=brief['fixedOrder']
        if len(order)!=len(by_id) or set(order)!=set(by_id):raise ValueError('Fixed order must cover each observation exactly once')
        length=sum(distance(a,b) for a,b in zip([start]+order,order))+(distance(order[-1],start) if full else 0)
    else:order,length=order_groups(start,groups,distance,brief.get('endRoomId'),start if full else None,stages)
    if room_policy['singleEpisode']:
        closed=set();last=None
        for rid in order:
            episode=by_id[rid].get('episodeId',by_id[rid]['roomId'])
            if episode!=last:
                if episode in closed:raise ValueError('Viewing episode must be contiguous; cannot return to finish a room')
                if last is not None:closed.add(last)
                last=episode
    old=brief.get('baselineOrder',list(by_id));old_length=sum(distance(a,b) for a,b in zip([start]+old,old))+(distance(old[-1],start) if full else 0)
    from tour_rules import profile as shared_profile
    defaults=shared_profile();fps=brief.get('fps',24);eye=brief.get('eyeMm',defaults['eyeMm']);frames=[];visits=[];chapters=[];camera_keys=[];legs=[]
    def append(point,yaw,pitch):
        if frames:yaw=frames[-1]['yawRadians']+delta(frames[-1]['yawRadians'],yaw)
        frames.append({'frame':len(frames),'pointMm':list(point),'yawRadians':yaw,'pitchRadians':pitch,'eyeMm':eye,'horizontalFovDegrees':76,'shiftY':0})
    def mark(name):visits.append({'name':name,'frame':len(frames)-1,'pointMm':frames[-1]['pointMm']})
    def key(name,offset=0):
        f=frames[-1];camera_keys.append({'atStop':name,'offsetFrames':offset,'targetMm':[f['pointMm'][0]+1000*math.cos(f['yawRadians']),f['pointMm'][1]+1000*math.sin(f['yawRadians']),eye-100],'yawDegrees':math.degrees(f['yawRadians']),'pitchDegrees':math.degrees(f['pitchRadians'])})
    initial=route(start,order[0]);initial_yaw=math.atan2(initial[1][1]-initial[0][1],initial[1][0]-initial[0][0]);append(points[start],initial_yaw,math.radians(-5));mark('开始');key('开始')
    previous=start;previous_marker='开始'
    sequence=order[:]
    if full:
        by_id['__exit__']={'name':'入户门外','point':brief['startPoint'],'targetMm':outward,'viewSeconds':0}
        points['__exit__']=brief['startPoint'];sequence.append('__exit__')
    for ix,rid in enumerate(sequence):
        obs=by_id[rid];polyline=planner.round(route(previous,rid));dense=[polyline[0]]
        for a,b in zip(polyline,polyline[1:]):
            count=max(1,math.ceil(math.dist(a,b)/35))
            dense.extend([[a[k]+(b[k]-a[k])*j/count for k in (0,1)] for j in range(1,count+1)])
        leg_start=len(frames)-1;last_key_yaw=frames[-1]['yawRadians'];start_yaw=last_key_yaw
        aim=math.atan2(obs['targetMm'][1]-obs['point'][1],obs['targetMm'][0]-obs['point'][0]);pitch=math.radians(brief.get('observationPitchDegrees',-5))
        distances=[0]
        for a,b in zip(dense,dense[1:]):distances.append(distances[-1]+math.dist(a,b))
        total_distance=distances[-1]
        leg_policy={**brief.get("navigationPolicy",{}),**by_id.get(previous,{}).get("exitNavigationPolicy",{}),**obs.get("approachNavigationPolicy",{})}
        planned_yaws=navigation_gaze(planner,dense,distances,start_yaw,aim,leg_policy)
        prior=by_id.get(previous,{})
        if obs.get('episodeId') and obs.get('episodeId')==prior.get('episodeId') and obs['roomId']==prior.get('roomId'):
            # Within one open room episode, reveal the next subject once rather
            # than inserting independent navigation sweeps between every feature.
            planned_yaws=[start_yaw+delta(start_yaw,aim)*(u*u*(3-2*u)) for u in [d/max(1,total_distance) for d in distances]]

        if obs.get('approachViewTargetMm'):
            q=obs['approachViewTargetMm'];angles=[];revealed=False;finished=False
            for j,point in enumerate(dense):
                bearing=math.atan2(q[1]-point[1],q[0]-point[0]);distance=math.dist(point,q[:2]);ahead=dense[min(len(dense)-1,j+12)];behind=dense[max(0,j-5)]
                travel=math.atan2(ahead[1]-behind[1],ahead[0]-behind[0]);visible=clear_distance(planner,point,bearing,distance)>=distance-60
                if revealed and abs(delta(travel,bearing))>math.radians(75):finished=True
                if visible and not finished:
                    desired=bearing;revealed=True
                elif finished:
                    next_bearing=math.atan2(obs['targetMm'][1]-point[1],obs['targetMm'][0]-point[0]);next_distance=math.dist(point,obs['targetMm'][:2])
                    desired=next_bearing if clear_distance(planner,point,next_bearing,next_distance)>=next_distance-60 else planned_yaws[j]
                else:desired=planned_yaws[j]
                if distances[-1]-distances[j]<500:
                    u=max(0,(distances[-1]-distances[j])/500);u=u*u*(3-2*u);desired=aim+delta(aim,desired)*u
                angles.append(desired)
            for j in range(len(angles)):
                u=min(1,distances[j]/500);u=u*u*(3-2*u);angles[j]=start_yaw+delta(start_yaw,angles[j])*u
            planned_yaws=angles
        for j,point in enumerate(dense[1:],1):
            yaw=planned_yaws[j];append(point,yaw,pitch)
            if abs(delta(last_key_yaw,yaw))>=math.radians(8) or j==len(dense)-1:
                key(previous_marker,len(frames)-1-leg_start);last_key_yaw=yaw
        arrive=obs['name']+' · 到达';mark(arrive)
        chapters.append({'name':('入户' if previous==start else by_id[previous]['name'])+' → '+obs['name'],'from':previous_marker,'to':arrive,'phase':'transit','subjects':[],'purpose':'沿真实通路连接；不重复介绍已看主体'})
        moving_view=bool(obs.get('episodeId') and obs.get('episodeId')==prior.get('episodeId') and obs['roomId']==prior.get('roomId'))
        if moving_view:
            chapters[-1].update(phase='observe',subjects=[obs['subjectId']],roomId=obs['roomId'],episodeId=obs['episodeId'],viewPurpose=obs['viewPurpose'],tourRole=obs.get('tourRole','secondary'),minimumSeconds=0,singleSweepDegrees=math.degrees(delta(start_yaw,aim)),movingView=True)

        legs.append({'from':previous_marker,'to':arrive,'waypoints':polyline,'lengthM':path_length(polyline)/1000})
        if rid=='__exit__':
            previous_marker=arrive;previous=rid;continue
        # Reading begins after approach and target alignment, with no invented move.
        view_start=arrive
        steps=max(2,round(obs['viewSeconds']*fps));pan=math.radians(obs['selectedPanDegrees'])
        for step in range(1,steps+1):
            u=step/steps;append(obs['point'],aim+pan*(u*u*(3-2*u)),pitch)
            # Preserve the short room sweep itself, not just its end gaze.
            key(arrive,step)
        view_end=obs['name']+' · 看完';mark(view_end);key(view_end)
        chapters.append({'name':obs['name']+' · 观看','from':view_start,'to':view_end,'phase':'observe','subjects':obs.get('orderedViewTargets') or [obs['subjectId']],'minimumSeconds':obs['viewSeconds'],'singleSweepDegrees':obs['selectedPanDegrees'],'episodeId':obs.get('episodeId',obs['roomId']),'roomId':obs['roomId'],'viewPurpose':obs.get('viewPurpose','展示当前房间的主要功能与空间关系'),'tourRole':obs['tourRole'],'observationId':rid,'secondPointReason':obs.get('secondPointReason',''),'orderedViewTargets':obs.get('orderedViewTargets',[]),'observationRegionId':obs.get('observationRegionId',obs['roomId'])})
        for field in ('adjacentViewReason','coveredRoomIds'):
            if field in obs:chapters[-1][field]=obs[field]
        if moving_view:chapters[-1]['viewContinuation']=True
        previous_marker=view_end
        previous=rid
    # Resolve duplicate key frame indices created at semantic boundaries deterministically.
    positions={v['name']:v['frame'] for v in visits};unique={positions[k['atStop']]+k.get('offsetFrames',0):k for k in camera_keys}
    config={'schema':'homeowner-camera-config/1','method':'subject-key-curves-v1','cameraProfile':{'eyeMm':eye,'horizontalFovDegrees':76,'shiftY':0,'headBob':False,'gazeSmoothSeconds':.12,'finalSmoothSeconds':.15},'cameraKeys':[unique[i] for i in sorted(unique)],'chapters':chapters,'choreographyPolicy':{'enabled':True,'maximumTransitYawDegrees':180,'maximumObservationReversals':1,'maximumTransitFraction':.55,**brief.get('choreographyPolicy',{})},'maximumSeconds':brief['maximumSeconds'],'roomViewingPolicy':room_policy,'observationPointPolicy':point_policy,'tourContract':contract_policy}
    config['cameraProfile']={**defaults,'eyeMm':eye,**brief.get('cameraProfile',{})}
    from tour_core_targets import bind
    config=bind(bundle,config)
    for k in ('ruleExceptions','timingLocks','trajectoryPolicy','visualQualityPolicy','visualReview','choreographyOverrideReason'):
        if k in brief:config[k]=copy.deepcopy(brief[k])
    tour={'schema':'floor-visualization-tour/1.0','previewOnly':True,'humanAcceptance':'pending','schemeSha256':bundle['schemeSha256'],'fps':fps,'seconds':len(frames)/fps,'frames':frames,'visits':visits,'legs':legs}
    profile=read(PROFILE);tour=generate(tour,config,profile)
    tour=retime(tour,config,profile['reviewLimits'])
    tour['chapterReview']=intent_check(tour,config)
    # Recheck actual frame chords; no rounded path receives automatic geometry approval.
    validator=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':brief.get('bodyRadiusMm',180),'gridMm':brief.get('gridMm',50)})
    collisions=[i for i,(a,b) in enumerate(zip(tour['frames'],tour['frames'][1:])) if validator.blocked(b['pointMm']) or not validator.line_free(a['pointMm'],b['pointMm'])]
    report={'schema':'homeowner-design-report/1','method':'group-distance-order+shallow-candidates+semantic-gaze/1','order':order,'orderBasis':'User specified fixed feature chain' if brief.get('fixedOrder') else 'public → primary → secondary → service first; walking distance only within allowed presentation stages','baselineOrder':old,'baselineDistanceM':old_length/1000,'selectedDistanceM':length/1000,'distanceReductionPercent':100*(1-length/old_length),'observations':selected,'seconds':tour['seconds'],'maximumSeconds':brief['maximumSeconds'],'tourMode':brief.get('tourMode','full_tour'),'entranceOpeningId':brief.get('entranceOpeningId'),'exteriorCameraApron':access,'startPoint':tour['frames'][0]['pointMm'],'endPoint':tour['frames'][-1]['pointMm'],'collisions':collisions,'motionFailures':tour['cameraMethod']['thresholdFailures'],'limitations':['Shortest order only for selected fixed candidates and declared groups; not a global apartment optimum','2D wall/door visibility proxy; actual mesh visibility and dynamic visual review pending'],'humanAcceptance':'pending','videoGenerated':False}
    from tour_choreography import inspect
    report['choreography']=inspect(tour,config)
    report['chapterFailures']=tour['chapterReview']['failures']
    coverage_policy=dict(brief['coveragePolicy'])
    config['coveragePolicy']=coverage_policy
    if 'cameraEvidencePolicy' in brief:config['cameraEvidencePolicy']=brief['cameraEvidencePolicy']
    if 'cameraEvidenceOverrideReason' in brief:config['cameraEvidenceOverrideReason']=brief['cameraEvidenceOverrideReason']
    if coverage_policy['enabled']:
        from tour_coverage import inspect as inspect_coverage
        report['coverage']=inspect_coverage(bundle,tour,validator,coverage_policy.get('minimumPercent'),config=config)
        report['chapterFailures']+=['Coverage below minimum: '+r['roomId'] for r in report['coverage']['rooms'] if not r['meetsProxyMinimum']]
    if brief.get('roomBudgetPolicy'):
        from tour_room_budgets import inspect as inspect_budgets
        config['roomBudgetPolicy']=brief['roomBudgetPolicy']
        report['roomBudgets']=inspect_budgets(bundle,tour,config,brief['roomBudgetPolicy'])
        report['chapterFailures']+=['Visit budget: '+x['code']+' / '+x.get('name','total') for x in report['roomBudgets']['issues']]
    from tour_observation_points import inspect as inspect_points
    report['observationPoints']=inspect_points(tour,config)
    report['chapterFailures']+=['Observation point: '+x['code']+' / '+str(x.get('roomId')) for x in report['observationPoints']['issues']]
    from tour_contract import inspect as inspect_contract
    report['contract']=inspect_contract(bundle,tour,config)
    report['chapterFailures']+=['Tour contract: '+x['code'] for x in report['contract']['issues']]
    report['status']='needs_revision' if collisions or report['motionFailures'] or report['chapterFailures'] or tour['seconds']>brief['maximumSeconds'] else 'pending_user_review'
    return tour,config,report


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for k in ('bundle','brief','out'):ap.add_argument('--'+k,required=True)
    args=ap.parse_args();out=Path(args.out)
    if out.exists():raise ValueError('Fresh design output required')
    tour,config,report=design(read(args.bundle),read(args.brief));out.mkdir(parents=True)
    for name,value in [('tour.json',tour),('camera-config.json',config),('design-report.json',report)]:dump(out/name,value)
    print(json.dumps({k:report[k] for k in ('status','order','baselineDistanceM','selectedDistanceM','seconds','collisions','motionFailures')},ensure_ascii=False))
    return 0 if report['status']=='pending_user_review' else 2
if __name__=='__main__':raise SystemExit(main())
