"""Shared homeowner tour design: evidence-backed stops, distance ordering, semantic gaze.
Produces route/camera JSON only. Never captures video or grants approval.
"""
import argparse, copy, json, math
from bisect import bisect_left, bisect_right
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


def back_out_hold(dense,distances,poly,limit=1200,margin=350):
    """Index up to which the camera keeps facing a small room while stepping back out of it."""
    left=next((distances[i] for i,p in enumerate(dense) if not inside(p,poly)),None)
    # Stay clearly inside the limit: the contract measures the walked frames, not this path.
    target=min(limit-60,(left if left is not None else limit)+margin)
    return max(1,min(len(dense)-2,bisect_right(distances,target)-1))


def flow_candidates(planner,point,bearings,half_view,limits,signs=(1,-1),keep=16):
    """Sweeps that keep every subject framed, best first by wall clearance and sweep size."""
    yaws=[math.radians(i*5) for i in range(72)];open_view={y:clear_distance(planner,point,y) for y in yaws};found=[]
    for dwell in (4,3,2,1):
        for s in yaws:
            for sign in signs:
                for degrees in range(limits[0],limits[1]+1,4):
                    pan=sign*math.radians(degrees);sweep=[s+pan*i/8 for i in range(9)]
                    if any(sum(abs(delta(y,b))<=half_view for y in sweep)<dwell for b in bearings):continue
                    wall=max(0,1200-open_view[s])+max(0,1200-clear_distance(planner,point,s+pan))
                    found.append((math.radians(degrees)*.05+wall/1200*math.radians(60),s,pan))
        if found:break
    if not found:raise ValueError('Subjects cannot share one sweep within the sweep limit')
    found.sort(key=lambda item:item[0]);picked=[];seen=set()
    for item in found:
        key=(round(math.degrees(item[1])/15),round(math.degrees(item[1]+item[2])/15))
        if key in seen:continue
        seen.add(key);picked.append(item)
        if len(picked)==keep:break
    return picked


def flow_sweep(planner,point,arrival,departure,bearings,half_view,limits=(12,100),signs=(1,-1),band=math.radians(60)):
    """Choose one sweep that shows every subject and turns the least against the walk.
    The arrival and exit headings are real path tangents; a subject never leaves the sweep.
    """
    yaws=[math.radians(i*5) for i in range(72)]
    open_view={y:clear_distance(planner,point,y) for y in yaws}
    # A subject should stay framed for part of the sweep; wide groups relax only as far as needed.
    for dwell in (4,3,2,1):
        best=None
        for s in yaws:
            for sign in signs:
                for degrees in range(limits[0],limits[1]+1,4):
                    pan=sign*math.radians(degrees)
                    sweep=[s+pan*i/8 for i in range(9)]
                    if any(sum(abs(delta(y,b))<=half_view for y in sweep)<dwell for b in bearings):continue
                    end=s+pan
                    wall=max(0,1200-open_view[s])+max(0,1200-clear_distance(planner,point,end))
                    # Mismatch inside the walking band costs nothing in the connection planner,
                    # so only the part beyond the band is penalised hard; the rest breaks ties.
                    a_gap,d_gap=abs(delta(arrival,s)),abs(delta(end,departure))
                    cost=max(0,a_gap-band)+max(0,d_gap-band)+.1*(a_gap+d_gap)+math.radians(degrees)*.05+wall/1200*math.radians(60)
                    if best is None or cost<best[0]-1e-9:best=(cost,s,pan)
        if best is not None:break
    if best is None:raise ValueError('Subjects cannot share one sweep within the sweep limit')
    return best[1],best[2]


def mark_speed_limits(frames,planner,policy):
    """Slower where the body edge is close to a wall or the path bends; open floor keeps the cruise speed."""
    narrow=policy.get('narrowGapMm',300);bend=math.radians(policy.get('bendDegrees',35));reach=8
    headings=[]
    for i,f in enumerate(frames):
        a=frames[max(0,i-reach)]['pointMm'];b=frames[min(len(frames)-1,i+reach)]['pointMm']
        headings.append(math.atan2(b[1]-f['pointMm'][1],b[0]-f['pointMm'][0]) if math.dist(b,f['pointMm'])>1 else None)
    for i,f in enumerate(frames):
        slow=planner.gap_at(f['pointMm'])<narrow
        before=frames[max(0,i-reach)]['pointMm'];after=frames[min(len(frames)-1,i+reach)]['pointMm']
        if math.dist(before,f['pointMm'])>1 and math.dist(after,f['pointMm'])>1:
            turn=abs(delta(math.atan2(f['pointMm'][1]-before[1],f['pointMm'][0]-before[0]),math.atan2(after[1]-f['pointMm'][1],after[0]-f['pointMm'][0])));slow=slow or turn>bend
        f['speedLimitMps']=policy['narrowCruiseMps'] if slow else policy['cruiseMps']


def forward_plan(dense,distances,start_yaw,end_yaw,band=60,ahead=900,grid=2.0,tie=.0005,coarse=False,clearance=None,wall_weight=1.5,wall_range=1800,start_band=None,ramp_mm=1000):
    """Fewest degrees of turning for one connection, never spinning the long way round.

    The camera stays within `band` of the look-ahead walking heading. It may pivot in place
    before stepping off and again on arrival; every degree of both pivots is counted, so a
    pivot is only used when it is cheaper than turning while walking. Wrapped angle
    differences are never used inside the track: yaw is one continuous unwrapped curve.
    """
    caps=(4.5,8,14,30,90)
    if coarse:
        # Cheap estimate used to compare candidate sweeps; the real plan is solved finely later.
        keep=list(range(0,len(dense),4))
        if keep[-1]!=len(dense)-1:keep.append(len(dense)-1)
        dense=[dense[i] for i in keep];distances=[distances[i] for i in keep];grid=4.0;caps=(20,36,70,140,360)
    n=len(dense);heading=[];last=None
    for i in range(n):
        j=min(n-1,bisect_left(distances,min(distances[-1],distances[i]+ahead),i))
        a,b=(dense[i],dense[j]) if j>i else (dense[max(0,i-4)],dense[i])
        raw=math.degrees(math.atan2(b[1]-a[1],b[0]-a[0])) if math.dist(a,b)>1 else (last if last is not None else math.degrees(start_yaw))
        if last is not None:raw=last+((raw-last+180)%360-180)
        heading.append(raw);last=raw
    y0=math.degrees(start_yaw);aim=math.degrees(end_yaw);K=int(band//grid)
    heading=[h+360*round((y0-heading[0])/360) for h in heading]
    def allowed(i):
        # Right after a stop-and-turn the view stays close to the walking direction, then opens to the full band.
        return band if start_band is None else min(band,start_band+(band-start_band)*min(1,distances[i]/max(1,ramp_mm)))
    seen={}
    def wall(i,yaw):
        # Looking straight at a nearby wall while walking is paid for per step, in degrees of turning.
        if clearance is None:return 0.
        key=(i,round(yaw)%360)
        if key not in seen:
            gap=clearance(dense[i],math.radians(key[1]))
            seen[key]=0. if gap is None else wall_weight*max(0.,1-gap/wall_range)
        return seen[key]
    def solve(h,cap):
        INF=float('inf');size=2*K+1;cost=[abs(h[0]+(k-K)*grid-y0)+tie*abs(k-K)*grid+wall(0,h[0]+(k-K)*grid) if abs((k-K)*grid)<=allowed(0)+1e-9 else INF for k in range(size)];back=[]
        for i in range(n-1):
            nxt=[INF]*size;arg=[-1]*size;dh=h[i+1]-h[i]
            for k in range(size):
                c=cost[k]
                if c==INF:continue
                for k2 in range(max(0,k-3),min(size,k+4)):
                    step=dh+(k2-k)*grid
                    if abs(step)>cap:continue
                    if abs((k2-K)*grid)>allowed(i+1)+1e-9:continue
                    v=c+abs(step)+tie*abs(k2-K)*grid+wall(i+1,h[i+1]+(k2-K)*grid)
                    if v<nxt[k2]:nxt[k2]=v;arg[k2]=k
            cost=nxt;back.append(arg)
            if min(cost)==INF:return None
        end=[(cost[k]+min(abs(aim+360*j-(h[-1]+(k-K)*grid)) for j in range(-2,3)),k) for k in range(size) if cost[k]!=INF]
        if not end:return None
        total,k=min(end);path=[k]
        for arg in reversed(back):k=arg[k];path.append(k)
        path.reverse();return total,[h[i]+(k-K)*grid for i,k in enumerate(path)]
    best=None
    for m in (-1,0,1):
        # A short hook at a path end can flip the look-ahead heading in one step; larger caps only follow it.
        for cap in caps+(180,720):
            found=solve([v+360*m for v in heading],cap)
            if found:
                if best is None or found[0]<best[0]:best=found
                break
    if best is None:raise ValueError('No turning plan within the heading band for this connection')
    total,ys=best
    def pivot(a,b):
        count=0 if abs(b-a)<1 else max(2,math.ceil(abs(b-a)/2))
        return [math.radians(a+(b-a)*(u*u*(3-2*u))) for u in (c/count for c in range(1,count+1))] if count else []
    target=min((aim+360*j for j in range(-2,3)),key=lambda v:abs(v-ys[-1]))
    return {'yaws':[math.radians(v) for v in ys],'startPivot':pivot(y0,ys[0]),'endPivot':pivot(ys[-1],target),'totalDegrees':total,'bandDegrees':band}


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
    preferred=policy.get('preferredHeadingDegrees',60)
    if isinstance(preferred,bool) or not isinstance(preferred,(int,float)) or not math.isfinite(preferred) or not 0<=preferred<=60:
        raise ValueError('Preferred navigation heading must be between zero and sixty degrees')
    if policy.get('coveragePolygons'):
        from tour_navigation_coverage import gaze
        return gaze(planner,dense,distances,start_yaw,end_yaw,policy)
    if policy.get('mode')=='forward':
        # Unwrapped look-ahead heading eased from the start view into the end view. Only
        # continuous differences are blended, so the yaw can never jump a full turn.
        total=distances[-1] or 1;blend=policy.get('blendMm',700);ahead=policy.get('lookAheadMm',900);track=[];last=None
        for i,d in enumerate(distances):
            j=min(len(dense)-1,bisect_left(distances,min(total,d+ahead),i));q=dense[j];k=max(0,i-2)
            raw=math.atan2(q[1]-dense[k][1],q[0]-dense[k][0]) if math.dist(q,dense[k])>1 else (last if last is not None else start_yaw)
            last=raw if last is None else last+delta(last,raw);track.append(last)
        shift=start_yaw-track[0];shift=2*math.pi*round(shift/(2*math.pi));track=[v+shift for v in track]
        end_aligned=end_yaw+2*math.pi*round((track[-1]-end_yaw)/(2*math.pi));out=[]
        for i,d in enumerate(distances):
            u=min(1,d/blend);u=u*u*(3-2*u);v=min(1,(total-d)/blend);v=v*v*(3-2*v)
            y=start_yaw+(track[i]-start_yaw)*u;out.append(end_aligned+(y-end_aligned)*v)
        return out
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
            orientation=max(0,off-preferred)/90*policy.get('forwardWeight',6)
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
        subjects=observation.get('subjects',[])
        if not isinstance(subjects,list) or any(not isinstance(s,str) for s in subjects):raise ValueError('Observation subjects must be actual subject IDs')
        for subject in subjects:target_anchor(bundle,subject)
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
    comfort=brief.get('navigationPolicy',{}).get('comfortClearanceMm',0);comfort_weight=brief.get('navigationPolicy',{}).get('comfortWeight',2.5)
    planner=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':brief.get('bodyRadiusMm',180)+brief.get('planningMarginMm',25),'gridMm':brief.get('gridMm',50),'comfortClearanceMm':comfort,'comfortWeight':comfort_weight})
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
    paths={};comfort_fallbacks=[]
    from tour_choreography import path_turning as choreography_path_turn_frames
    choreography_path_turn=lambda path:choreography_path_turn_frames([{'pointMm':q} for q in path])
    comfort_length_ratio=brief.get('navigationPolicy',{}).get('comfortMaxLengthRatio',1.12);comfort_turn_slack=brief.get('navigationPolicy',{}).get('comfortMaxExtraTurnDegrees',45)
    plain_planner=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':brief.get('bodyRadiusMm',180)+brief.get('planningMarginMm',25),'gridMm':brief.get('gridMm',50)}) if comfort else planner
    def route(a,b):
        if (a,b) not in paths:
            from compact_tour_visits import safe_path
            plain=safe_path(plain_planner,points[a],points[b]) if plain_planner is not planner else None
            try:chosen=safe_path(planner,points[a],points[b])
            except ValueError:
                if plain is None:raise
                chosen=plain
            if plain is not None and chosen is not plain:
                # Comfort may bend a path a little, never loop it or turn it into a long detour.
                base_turn=choreography_path_turn(plain);new_turn=choreography_path_turn(chosen)
                if path_length(chosen)>comfort_length_ratio*path_length(plain) or new_turn>base_turn+comfort_turn_slack:
                    chosen=plain;comfort_fallbacks.append({'from':a,'to':b,'lengthRatio':round(path_length(chosen)/max(1,path_length(plain)),3)})
            paths[a,b]=chosen
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
    if brief.get('panPolicy')=='flow':
        # Sweeps are chosen together: each room's start/end view is scored by the turning the
        # real connections before and after it would need, so no room is optimised alone.
        navigation=brief.get('navigationPolicy',{});band=navigation.get('forwardBandDegrees',60)
        half=math.radians(brief.get('flowSubjectHalfViewDegrees',brief.get('cameraProfile',{}).get('horizontalFovDegrees',76)/2-10))
        items={f['id']:f for f in bundle['state']['furniture']};limit={**read(PROFILE)['reviewLimits'],**brief.get('motionReviewLimits',{})}['maxYawDegreesPerSecond']
        def dense_of(a,b):
            polyline=route(a,b);out=[polyline[0]]
            for u,v in zip(polyline,polyline[1:]):
                count=max(1,math.ceil(math.dist(u,v)/35));out.extend([[u[k]+(v[k]-u[k])*j/count for k in (0,1)] for j in range(1,count+1)])
            run=[0]
            for u,v in zip(out,out[1:]):run.append(run[-1]+math.dist(u,v))
            return out,run
        leg_cost=lambda a,b,y0,y1:forward_plan(*dense_of(a,b),y0,y1,band,coarse=True)['totalDegrees']
        consistency=brief.get('navigationPolicy',{}).get('sweepConsistencyWeight',0);ends={}
        def leg_ends(a,b):
            # Walking headings over the first and last stretch of a connection.
            if (a,b) not in ends:
                dense,run=dense_of(a,b);near=lambda target:min(range(len(dense)),key=lambda i:abs(run[i]-target))
                head=lambda i,j:math.atan2(dense[j][1]-dense[i][1],dense[j][0]-dense[i][0])
                ends[(a,b)]=(head(0,near(700)),head(near(max(0,run[-1]-700)),len(dense)-1))
            return ends[(a,b)]
        wrap=lambda v:(v+math.pi)%(2*math.pi)-math.pi
        def wobble(a,b,end_yaw,pan_before,s0,pan0):
            # Turning against the sweep that follows, or against the sweep that just finished, is a left-right-left wobble.
            if not consistency or a==b:return 0.
            depart,arrive=leg_ends(a,b);cost=0.
            if pan_before:cost+=max(0.,-math.copysign(1,pan_before)*math.degrees(wrap(depart-end_yaw)))
            cost+=max(0.,-math.copysign(1,pan0)*math.degrees(wrap(s0-arrive)))
            return consistency*cost
        candidates={}
        for rid in order:
            obs=by_id[rid];bearings=[math.atan2(items[i]['cy']-obs['point'][1],items[i]['cx']-obs['point'][0]) for i in dict.fromkeys(obs.get('flowSubjects') or [obs['subjectId']]+obs.get('subjects',[])) if i in items]
            smallest=brief.get('flowMinSweepDegrees',24);reach=(smallest,max(smallest,min(obs.get('maxSweepDegrees',999),int(obs['viewSeconds']*limit/1.5))))
            # Subjects too far apart for one sweep: keep the primary and drop the farthest until it fits, and say so.
            dropped=[]
            while True:
                try:candidates[rid]=flow_candidates(planner,obs['point'],bearings,half,reach);break
                except ValueError:
                    if len(bearings)<=1:raise
                    lead=bearings[0];far=max(range(1,len(bearings)),key=lambda k:abs(delta(lead,bearings[k])));dropped.append(round(math.degrees(bearings[far])));bearings.pop(far)
            if dropped:obs['flowDroppedBearingsDegrees']=dropped
        if full:points['__exit__']=brief['startPoint']
        first=route(start,order[0]);first_yaw=math.atan2(first[1][1]-first[0][1],first[1][0]-first[0][0])
        exit_aim=math.atan2(outward[1]-brief['startPoint'][1],outward[0]-brief['startPoint'][0]) if full else None
        table=[]
        for position,rid in enumerate(order):
            row=[]
            for index,(local,s0,pan0) in enumerate(candidates[rid]):
                best=(math.inf,None)
                previous=[(first_yaw,0.,None)] if position==0 else [(candidates[order[position-1]][k][1]+candidates[order[position-1]][k][2],table[position-1][k][0],k) for k in range(len(candidates[order[position-1]]))]
                for end_yaw,before,k in previous:
                    if k is not None:
                        a=by_id[order[position-1]];b=by_id[rid]
                        if a.get('roomId')==b.get('roomId') and a.get('episodeId')==b.get('episodeId') and (candidates[order[position-1]][k][2]>0)!=(pan0>0):continue
                    here=start if position==0 else order[position-1];cost=before+math.degrees(local)+leg_cost(here,rid,end_yaw,s0)+wobble(here,rid,end_yaw,candidates[order[position-1]][k][2] if k is not None else 0,s0,pan0)
                    if cost<best[0]:best=(cost,k)
                row.append(best)
            table.append(row)
        final=[]
        for k,(local,s0,pan0) in enumerate(candidates[order[-1]]):
            if table[-1][k][0]==math.inf:continue
            tail=leg_cost(order[-1],'__exit__' if full else order[-1],s0+pan0,exit_aim) if full else 0
            final.append((table[-1][k][0]+tail,k))
        if not final:raise ValueError('No consistent sweep choice for the whole tour')
        k=min(final)[1]
        for position in range(len(order)-1,-1,-1):
            rid=order[position];local,s0,pan0=candidates[rid][k];by_id[rid]['flowStartYaw']=s0;by_id[rid]['selectedPanDegrees']=math.degrees(pan0);k=table[position][k][1]
    initial=route(start,order[0]);initial_yaw=math.atan2(initial[1][1]-initial[0][1],initial[1][0]-initial[0][0]);append(points[start],initial_yaw,math.radians(brief.get('walkingPitchDegrees',-3) if brief.get('pitchPolicy')=='subject' else -5));mark('开始');key('开始')
    previous=start;previous_marker='开始'
    small_rooms={};back_out_rows=[]
    if brief.get('navigationPolicy',{}).get('smallRoomBackOut'):
        from tour_spatial_plan import gates,room_exits
        from tour_forward_motion import polygon_area_m2,SMALL_ROOM_AREA_M2
        exits=room_exits(planner,bundle['model']['rooms'],gates(bundle))
        small_rooms={r['id']:r for r in bundle['model']['rooms'] if polygon_area_m2(r['poly'])<=SMALL_ROOM_AREA_M2 and exits.get(r['id'],{}).get('exitCount')==1}
    sequence=order[:]
    if full:
        by_id['__exit__']={'name':'入户门外','point':brief['startPoint'],'targetMm':outward,'viewSeconds':0}
        points['__exit__']=brief['startPoint'];sequence.append('__exit__')
    for ix,rid in enumerate(sequence):
        obs=by_id[rid];polyline=route(previous,rid);dense=[polyline[0]]
        for a,b in zip(polyline,polyline[1:]):
            count=max(1,math.ceil(math.dist(a,b)/35))
            dense.extend([[a[k]+(b[k]-a[k])*j/count for k in (0,1)] for j in range(1,count+1)])
        leg_start=len(frames)-1;last_key_yaw=frames[-1]['yawRadians'];start_yaw=last_key_yaw
        aim=obs.get('flowStartYaw',math.atan2(obs['targetMm'][1]-obs['point'][1],obs['targetMm'][0]-obs['point'][0]))
        # Walking looks nearly level; each viewing window tilts only as far as its subject needs.
        subject_pitch=brief.get('pitchPolicy')=='subject';leg_pitch0=frames[-1]['pitchRadians']
        walk_pitch=math.radians(brief.get('walkingPitchDegrees',-3)) if subject_pitch else math.radians(brief.get('observationPitchDegrees',-5))
        if subject_pitch:
            reach=math.hypot(obs['targetMm'][0]-obs['point'][0],obs['targetMm'][1]-obs['point'][1]) or 1
            view_pitch=max(math.radians(brief.get('observationPitchMinDegrees',-16)),min(math.radians(brief.get('observationPitchMaxDegrees',-2)),math.atan2(obs['targetMm'][2]-eye,reach)))
        else:view_pitch=walk_pitch
        pitch=leg_pitch0 if subject_pitch else walk_pitch
        distances=[0]
        for a,b in zip(dense,dense[1:]):distances.append(distances[-1]+math.dist(a,b))
        total_distance=distances[-1]
        leg_policy={**brief.get("navigationPolicy",{}),**by_id.get(previous,{}).get("exitNavigationPolicy",{}),**obs.get("approachNavigationPolicy",{})}
        planned_yaws=navigation_gaze(planner,dense,distances,start_yaw,aim,leg_policy)
        prior=by_id.get(previous,{})
        same_region=obs.get('observationRegionId',obs.get('roomId'))==prior.get('observationRegionId',prior.get('roomId'))
        if same_region and obs.get('episodeId') and obs.get('episodeId')==prior.get('episodeId') and obs['roomId']==prior.get('roomId'):
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
        forward=None
        if leg_policy.get('mode')=='forward' and len(dense)>2 and not obs.get('approachViewTargetMm') and not (same_region and obs.get('episodeId') and obs.get('episodeId')==prior.get('episodeId') and obs['roomId']==prior.get('roomId')):
            band=leg_policy.get('forwardBandDegrees',60);ahead_mm=leg_policy.get('lookAheadMm',900)
            room=next((r for r in small_rooms.values() if previous!=start and inside(by_id[previous]['point'],r['poly'])),None)
            if room is not None:
                # Step back out still facing the small room, then turn once outside it.
                y0=frames[-1]['yawRadians'];longest=back_out_hold(dense,distances,room['poly'],limit=leg_policy.get('smallRoomBackOutMm',1200))
                free=lambda q,y:clear_distance(planner,q,y,3000) if leg_policy.get('avoidWallFacing',True) else None
                weight=leg_policy.get('wallFacingWeight',2.5)
                # Where the turn happens matters: pivot where the arc does not sweep a close wall.
                options=sorted({min(longest,max(1,bisect_right(distances,d)-1)) for d in (250,450,650,850,1050)}|{longest}|({0} if leg_policy.get('turnInsideSmallRoom') else set()))
                best=None
                for hold in options:
                    if hold>len(dense)-3:continue
                    rest=forward_plan(dense[hold:],[d-distances[hold] for d in distances[hold:]],y0,aim,band,ahead_mm,clearance=free,wall_weight=weight,start_band=leg_policy.get('afterStopBandDegrees'))
                    near=lambda q,y:max(0.,1-free(q,y)/1800) if free(q,y) is not None else 0.
                    arc=sum(near(dense[hold],y) for y in rest['startPivot'])*2*weight
                    backing=sum(near(dense[i],y0) for i in range(0,hold+1))*weight
                    score=rest['totalDegrees']+arc+backing
                    if leg_policy.get('hardWallGapMm'):
                        # Turning in place against a wall nearer than the gap is paid per step, so it costs more than turning elsewhere.
                        score+=leg_policy.get('hardWallCost',15.)*sum(1 for y in rest['startPivot'] if free(dense[hold],y) is not None and free(dense[hold],y)<leg_policy['hardWallGapMm'])
                    if best is None or score<best[0]:best=(score,hold,rest)
                _,hold,rest=best
                forward={'yaws':[y0]*(hold+1)+rest['yaws'][1:],'startPivot':[],'pivotAtHold':rest['startPivot'],'holdIndex':hold,'endPivot':rest['endPivot']}
                back_out_rows.append({'roomId':room['id'],'areaM2':round(polygon_area_m2(room['poly']),3),'chapter':('入户' if previous==start else by_id[previous]['name'])+' → '+obs['name'],'holdMm':round(distances[hold])})
            else:forward=forward_plan(dense,distances,frames[-1]['yawRadians'],aim,band,ahead_mm,clearance=lambda q,y:clear_distance(planner,q,y,3000) if leg_policy.get('avoidWallFacing',True) else None,wall_weight=leg_policy.get('wallFacingWeight',2.5))
            planned_yaws=forward['yaws']
            for yaw in forward['startPivot']:
                append(dense[0],yaw,pitch)
                if abs(delta(last_key_yaw,yaw))>=math.radians(8):key(previous_marker,len(frames)-1-leg_start);last_key_yaw=yaw
        for j,point in enumerate(dense[1:],1):
            yaw=planned_yaws[j]
            if subject_pitch:
                ramp=min(900,total_distance*.5) or 1;u=min(1,distances[j]/ramp);pitch=leg_pitch0+(walk_pitch-leg_pitch0)*(u*u*(3-2*u))
            append(point,yaw,pitch)
            if abs(delta(last_key_yaw,yaw))>=math.radians(8) or j==len(dense)-1:
                key(previous_marker,len(frames)-1-leg_start);last_key_yaw=yaw
            if forward and forward.get('holdIndex')==j:
                for turn in forward['pivotAtHold']:
                    append(point,turn,pitch)
                    if abs(delta(last_key_yaw,turn))>=math.radians(8):key(previous_marker,len(frames)-1-leg_start);last_key_yaw=turn
        if forward:
            for yaw in forward['endPivot']:
                append(dense[-1],yaw,pitch)
                if abs(delta(last_key_yaw,yaw))>=math.radians(8):key(previous_marker,len(frames)-1-leg_start);last_key_yaw=yaw
            key(previous_marker,len(frames)-1-leg_start);last_key_yaw=frames[-1]['yawRadians']
        arrive=obs['name']+' · 到达';mark(arrive)
        chapters.append({'name':('入户' if previous==start else by_id[previous]['name'])+' → '+obs['name'],'from':previous_marker,'to':arrive,'phase':'transit','subjects':[],'purpose':'沿真实通路连接；不重复介绍已看主体'})
        moving_view=bool(same_region and obs.get('episodeId') and obs.get('episodeId')==prior.get('episodeId') and obs['roomId']==prior.get('roomId'))
        if moving_view:
            chapters[-1].update(phase='observe',subjects=[obs['subjectId']],roomId=obs['roomId'],episodeId=obs['episodeId'],viewPurpose=obs['viewPurpose'],tourRole=obs.get('tourRole','secondary'),minimumSeconds=0,singleSweepDegrees=math.degrees(delta(start_yaw,aim)),movingView=True)
            chapters[-1]['observationRegionId']=obs.get('observationRegionId',obs['roomId'])
            for field in ('adjacentViewReason','coveredRoomIds'):
                if field in obs:chapters[-1][field]=copy.deepcopy(obs[field])

        legs.append({'from':previous_marker,'to':arrive,'waypoints':polyline,'lengthM':path_length(polyline)/1000})
        if rid=='__exit__':
            previous_marker=arrive;previous=rid;continue
        # Reading begins after approach and target alignment, with no invented move.
        view_start=arrive;arrival_pitch=frames[-1]['pitchRadians']
        steps=max(2,round(obs['viewSeconds']*fps));pan=math.radians(obs['selectedPanDegrees'])
        for step in range(1,steps+1):
            u=step/steps;tilt=min(1,u/.45);append(obs['point'],aim+pan*(u*u*(3-2*u)),arrival_pitch+(view_pitch-arrival_pitch)*(tilt*tilt*(3-2*tilt)))
            # Preserve the short room sweep itself, not just its end gaze.
            key(arrive,step)
        view_end=obs['name']+' · 看完';mark(view_end);key(view_end)
        chapters.append({'name':obs['name']+' · 观看','from':view_start,'to':view_end,'phase':'observe','subjects':obs.get('orderedViewTargets') or [obs['subjectId']],'minimumSeconds':obs['viewSeconds'],'singleSweepDegrees':obs['selectedPanDegrees'],'episodeId':obs.get('episodeId',obs['roomId']),'roomId':obs['roomId'],'viewPurpose':obs.get('viewPurpose','展示当前房间的主要功能与空间关系'),'tourRole':obs['tourRole'],'observationId':rid,'secondPointReason':obs.get('secondPointReason',''),'orderedViewTargets':obs.get('orderedViewTargets',[]),'observationRegionId':obs.get('observationRegionId',obs['roomId'])})
        chapters[-1]['subjects']=list(dict.fromkeys([obs['subjectId']]+obs.get('subjects',[])+obs.get('orderedViewTargets',[])))
        for field in ('adjacentViewReason','coveredRoomIds'):
            if field in obs:chapters[-1][field]=obs[field]
        if moving_view:chapters[-1]['viewContinuation']=True
        previous_marker=view_end
        previous=rid
    # Resolve duplicate key frame indices created at semantic boundaries deterministically.
    positions={v['name']:v['frame'] for v in visits};unique={positions[k['atStop']]+k.get('offsetFrames',0):k for k in camera_keys}
    config={'schema':'homeowner-camera-config/1','method':'subject-key-curves-v1','cameraProfile':{'eyeMm':eye,'horizontalFovDegrees':76,'shiftY':0,'headBob':False,'gazeSmoothSeconds':.12,'finalSmoothSeconds':.15},'cameraKeys':[unique[i] for i in sorted(unique)],'chapters':chapters,'choreographyPolicy':{'enabled':True,'maximumTransitYawDegrees':180,'maximumObservationReversals':1,'maximumTransitFraction':.8,**brief.get('choreographyPolicy',{})},'maximumSeconds':brief['maximumSeconds'],'roomViewingPolicy':room_policy,'observationPointPolicy':point_policy,'tourContract':contract_policy}
    config['cameraProfile']={**defaults,'eyeMm':eye,**brief.get('cameraProfile',{})}
    if 'coverageReferencePolicy' in brief:config['coverageReferencePolicy']=copy.deepcopy(brief['coverageReferencePolicy'])
    from tour_core_targets import bind
    config=bind(bundle,config)
    if comfort:config['pathComfort']={'comfortClearanceMm':comfort,'comfortWeight':comfort_weight}
    shallow=brief.get('navigationPolicy',{}).get('smallRoomShallowMm')
    if shallow:config['smallRoomShallow']={'maximumAreaM2':brief['navigationPolicy'].get('smallRoomShallowAreaM2',6),'maximumDepthMm':shallow}
    if brief.get('speedPolicy'):
        config['speedPolicy']=copy.deepcopy(brief['speedPolicy'])
        for key in ('cruiseMps','narrowCruiseMps','rampSeconds'):
            if not isinstance(config['speedPolicy'].get(key),(int,float)) or isinstance(config['speedPolicy'][key],bool) or config['speedPolicy'][key]<=0:raise ValueError('speedPolicy needs positive cruiseMps, narrowCruiseMps and rampSeconds')
    if back_out_rows:config['smallRoomBackOut']={'maximumAreaM2':12,'maximumMeters':1.2,'maximumSeconds':2.5,'rooms':back_out_rows}
    for k in ('ruleExceptions','motionReviewLimits','timingLocks','trajectoryPolicy','cameraEvidencePolicy','visualQualityPolicy','visualReview','choreographyOverrideReason'):
        if k in brief:config[k]=copy.deepcopy(brief[k])
    tour={'schema':'floor-visualization-tour/1.0','previewOnly':True,'humanAcceptance':'pending','schemeSha256':bundle['schemeSha256'],'fps':fps,'seconds':len(frames)/fps,'frames':frames,'visits':visits,'legs':legs}
    if config.get('speedPolicy'):mark_speed_limits(tour['frames'],planner,config['speedPolicy'])
    profile=read(PROFILE);tour=generate(tour,config,profile)
    tour=retime(tour,config,{**profile['reviewLimits'],**config.get('motionReviewLimits',{})})
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
