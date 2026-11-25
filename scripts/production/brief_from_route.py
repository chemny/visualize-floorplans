"""Camera brief from an approved spatial route: order, stations, subjects, times, budgets.

Everything chosen here is a stated default, listed in brief-assumptions.json for the user to
check. Case numbers the Skills must not invent (total time, coverage percentage, eye height
reason) are required inputs. Grants no approval and renders nothing.
"""
import argparse,copy,json,math
from pathlib import Path
from plan_route import inside
from tour_core_targets import inventory
from tour_stage_gate import read,resolve,bound

SCHEMA='homeowner-brief-assumptions/1'
# Which core facility introduces a room when it has several.
FUNCTION_PRIORITY=['sleep','seating','dining','cooking','kitchen_wash','work','shower','bathing','toilet','wash','television','storage','laundry','cold_storage','worktop']
IGNORE_TYPES={'rug','threshold','skirting','doortrim','windowtrim','downlight','ceilinground','switchplate','socketplate','transition','waterinlet','drainoutlet','floordrain','acwall','curtain','lamp','tv','backsplash'}
ROLES=[('primary',('主卧','主卫','套卫','衣帽间')),('service',('厨房','公卫','卫生间','洗手台','储藏')),('secondary',('次卧','儿童','书房','客房','客书')),('public',('客厅','餐厅','阳台','玄关','过道','起居'))]
MAIN_ROOMS=('客厅','厨房')
VIEW_SECONDS={'primary':3.0,'public':2.5,'secondary':2.5,'service':2.0}
ENTER_EXIT_SECONDS=12.0
DEFAULT_EYE_MM=1300  # default eye height (user decision 2026-11-15: 1.6 m is too high); lower or higher needs camera_profile_override

def role_of(name):
    return next((role for role,words in ROLES if any(w in name for w in words)),'secondary')

def seconds_of(name,role,tier=None):
    if tier:return tier['viewSeconds']  # room-size tier: smaller rooms are looked at more briefly
    if '阳台' in name:return 2.0
    if any(w in name for w in MAIN_ROOMS):return 3.0
    return VIEW_SECONDS[role]

def standing_room(rooms,station):
    return next((r['id'] for r in rooms if inside(station['pointMm'],r['poly'])),station['roomId'])

def pick_subjects(bundle,room_id,station,inv,taken,furniture):
    """Subjects for one station, with where the choice came from."""
    if station.get('anchor') in furniture:
        return station['anchor'],[station['anchor']],'route anchor'
    required=[f for f in inv.get(room_id,[]) if f['subjectId'] not in taken]
    if required:
        required.sort(key=lambda f:FUNCTION_PRIORITY.index(f['function']) if f['function'] in FUNCTION_PRIORITY else 99)
        return required[0]['subjectId'],[f['subjectId'] for f in required],'core facilities of the room'
    poly=next(r['poly'] for r in bundle['model']['rooms'] if r['id']==room_id)
    rows=[f for f in bundle['state']['furniture'] if f.get('type') not in IGNORE_TYPES and not f.get('assemblyOwner') and not f.get('planPoint') and f.get('elevation',0)<=1100 and inside([f['cx'],f['cy']],poly) and f['w']>=300 and f['d']>=300]
    if not rows:return None,[],'nothing to show'
    best=max(rows,key=lambda f:f['w']*f['d'])
    return best['id'],[best['id']],'largest low furniture (no core facility in this room)'

def build(plan_path,options):
    plan_path=Path(plan_path).resolve();plan=read(plan_path)
    if plan.get('schema')!='homeowner-spatial-plan/1':raise ValueError('Expected a spatial plan')
    if plan.get('status')!='pending_user_confirmation':raise ValueError('Spatial plan has unresolved issues: '+str(plan.get('status')))
    maximum=options.get('maximumSeconds') or plan.get('budget',{}).get('maximumSeconds')
    if not isinstance(maximum,(int,float)) or isinstance(maximum,bool) or maximum<=0:raise ValueError('maximumSeconds required: pass it, or set budget.maximumSeconds in the spatial job')
    coverage=options.get('coverageMinimumPercent');other_coverage=options.get('coverageOtherPercent')
    if options.get('roomSizeTiers',True) and not options.get('coverageOff'):
        # Product default (user decision 2026-11-15): main rooms 80%, other rooms (bathroom, balcony, passage, bay window) 50%.
        coverage=80 if coverage is None else coverage;other_coverage=50 if other_coverage is None else other_coverage
    if coverage is None and not options.get('coverageOff'):raise ValueError('Give coverageMinimumPercent for this case, or coverageOff for a diagnostic-only brief')
    eye=options.get('eyeMm',DEFAULT_EYE_MM)
    if eye!=DEFAULT_EYE_MM and not str(options.get('eyeReason','')).strip():raise ValueError('A non-default eye height needs its reason (ruleExceptions camera_profile_override)')
    bundle=read(resolve(plan['bundle'],plan_path.parent));rooms=bundle['model']['rooms'];room_name={r['id']:r.get('name',r['id']) for r in rooms}
    inv=inventory(bundle);furniture={f['id']:f for f in bundle['state']['furniture']};stations=plan['stations']
    notes={'defaults':[],'stations':[],'passThrough':[],'reassigned':[],'needsReview':[]}
    standing=[standing_room(rooms,s) for s in stations];assigned=list(standing)
    taken={s['anchor'] for s in stations if s.get('anchor')}
    # A real room may carry at most two observation points; extra zone stations are filed under the neighbouring room they belong to on the route.
    def counts():
        out={}
        for room in assigned:out[room]=out.get(room,0)+1
        return out
    guard=0
    while any(n>2 for n in counts().values()) and guard<20:
        guard+=1;crowded=next(r for r,n in counts().items() if n>2)
        movable=[i for i,room in enumerate(assigned) if room==crowded]
        movable.sort(key=lambda i:(0 if stations[i].get('anchor') else 1,i))
        for i in movable:
            neighbours=[j for j in (i+1,i-1) if 0<=j<len(stations) and assigned[j]!=crowded and counts().get(assigned[j],0)<2]
            if neighbours:
                assigned[i]=assigned[neighbours[0]];notes['reassigned'].append({'station':stations[i]['name'],'standingRoom':standing[i],'filedUnder':assigned[i],'because':'more than two observation points would stand in '+room_name[crowded]});break
        else:raise ValueError('Too many stations in '+room_name[crowded]+'; give an override that merges or drops one')
    from tour_small_room_depth import small_rooms,shallow_point
    SHALLOW_MM=500
    shallow_stations={r['roomId']:r for r in small_rooms(bundle)} if options.get('cameraOptions','tuned')=='tuned' else {}
    first_room=standing[0] if standing else None
    if first_room in shallow_stations:del shallow_stations[first_room]  # the entrance room is where the tour begins
    items=[];moved=set()
    for i,s in enumerate(stations):
        forced=((options.get('overrides') or {}).get(s['name']) or {}).get('viewSubject')
        if forced:
            # A room with nothing to show can still be looked at: the named fixture only gives the view direction (its plan position).
            if forced not in furniture:raise ValueError('viewSubject is not a furniture id in the bundle: '+str(forced))
            subject,subjects,source=forced,[forced],'user-specified view target'
        else:subject,subjects,source=pick_subjects(bundle,standing[i],s,inv,taken-{s.get('anchor')},furniture)
        if subject is None:
            notes['passThrough'].append({'station':s['name'],'reason':'no furniture or facility to show; the route passes through'});continue
        role=role_of(s['name']);f=furniture[subject]
        target=[f['cx'],f['cy'],round(min(max(f.get('elevation',0)+f['h']*.5,400),1200))]
        x,y=s['pointMm']
        shallow=shallow_stations.get(standing[i])
        if shallow:
            depth=(x-shallow['doorMidMm'][0])*shallow['inward'][0]+(y-shallow['doorMidMm'][1])*shallow['inward'][1]
            if depth>SHALLOW_MM:
                moved_point=shallow_point(shallow,SHALLOW_MM-100)
                if moved_point:
                    x,y=moved_point;notes['needsReview'].append('站位“%s”在小空间“%s”里原深度 %d 毫米，已移到门内 %d 毫米处（小空间只在门口拍一轮）'%(s['name'],room_name[standing[i]],depth,SHALLOW_MM-100))
        near=[[x+a,y+b] for a,b in ((0,0),(80,0),(-80,0),(0,80),(0,-80),(80,80),(-80,-80),(160,0),(-160,0),(0,160),(0,-160))]
        tier_name=tier=None
        if options.get('roomSizeTiers',True):
            from tour_room_tiers import tier_for_room
            standing_poly=next(r for r in rooms if r['id']==(s['roomId'] if s.get('outsideStation') else standing[i]));tier_name,tier=tier_for_room(standing_poly)  # a doorway station takes the tier of the room it shows
        seconds=seconds_of(s['name'],role,tier);types=sorted({furniture[i]['type'] for i in subjects if i in furniture})
        item={'observationId':'s%02d'%i,'name':s['name'],'roomId':assigned[i],'tourRole':role,'subjectId':subject,'subjects':subjects,'targetMm':target,
              'candidatePoints':near,'candidatePointsOnly':True,'candidateDepthMm':0,'viewSeconds':seconds,**({'maxSweepDegrees':tier['maxSweepDegrees'],'roomSizeTier':tier_name} if tier else {}),'observationPanDegrees':0,'lockPanDirection':True,'preferredDistanceMm':2000,
              'episodeId':(standing[i]+'-'+str(furniture[s['anchor']]['type'])) if s.get('anchor') else assigned[i],
              'viewPurpose':('在'+s['name']+'门口看房间整体（没有可介绍的家具，视线朝向指定物件的位置），按已批准路线观看') if source=='user-specified view target' else '在'+s['name']+'看'+('、'.join(types) or '主要陈设')+'，按已批准路线观看'}
        if s.get('outsideStation') and s['roomId']!=standing[i]:
            # Introduced from its doorway: the observation stands in the neighbouring room and still counts for the room it shows.
            item.update(coveredRoomIds=[s['roomId']],adjacentViewReason='在'+room_name[standing[i]]+'的门口外侧看'+room_name[s['roomId']]+'（该处过窄不进入，按用户选择在门口定位）。')
            notes['needsReview'].append('站位“%s”在门口外侧，不进入房间'%s['name'])
        if assigned[i]!=standing[i]:
            item.update(observationRegionId=standing[i],coveredRoomIds=[standing[i]],adjacentViewReason='按已批准路线在'+room_name[standing[i]]+'看属于相邻房间的功能；物件及房间归属不改变。')
        items.append(item);notes['stations'].append({'station':s['name'],'observationId':item['observationId'],'standingRoom':standing[i],'filedUnder':assigned[i],'subject':subject,'subjects':subjects,'subjectSource':source,'tourRole':role,'viewSeconds':seconds})
    # Every core facility of a room must belong to some station standing in it; leftovers go to the nearest one.
    used={}
    for item,s0 in zip(items,[s for s in stations if s['name'] in {i['name'] for i in items}]):used.setdefault(standing_room(rooms,s0),[]).append((item,s0))
    for room,group in used.items():
        have={i for item,_ in group for i in item['subjects']}
        for facility in inv.get(room,[]):
            if facility['subjectId'] in have:continue
            f=furniture[facility['subjectId']];item,_=min(group,key=lambda g:math.dist(g[1]['pointMm'],[f['cx'],f['cy']]))
            item['subjects'].append(facility['subjectId']);notes['needsReview'].append('核心设施 %s（%s）并入站位“%s”'%(facility['subjectId'],facility['type'],item['name']))
    seen={}
    for item in items:
        seen[item['roomId']]=seen.get(item['roomId'],0)+1
        if seen[item['roomId']]==2:item['secondPointReason']='同一房间内按路线观看不同功能区，第二点交代与第一点不同的区域。'
    if not items:raise ValueError('No station has anything to show')
    order=[x['observationId'] for x in items]
    by_standing={}
    for item,s in zip(items,[s for s in stations if s['name'] in {i['name'] for i in items}]):by_standing.setdefault(standing_room(rooms,s),[]).append(item)
    budgets=[{'name':room_name[r],'roomIds':[r],'maximumSeconds':round(sum(x['viewSeconds'] for x in group)+ENTER_EXIT_SECONDS*len(group),1)} for r,group in by_standing.items()]
    if options.get('roomSizeTiers',True):notes['defaults'].append('房间大小分档（5/10/20 平方米）：停留 1.5/2.25/3.0/4.75 秒，单向扫视上限 40/60/80/100 度；路线站位深度上限 400/600/900/1200 毫米（见 tour_room_tiers.py）')
    notes['defaults']+=['停留：主卧、主卫等 primary 3秒，客厅、厨房 3秒，公共/次要 2.5秒，服务空间 2秒，阳台 2秒（单点上限3秒）','房间预算：每站观看时间加 %g 秒进出估算，请按案例核对'%ENTER_EXIT_SECONDS,'目标高度取主体半高，限制在 400–1200 毫米']
    notes['needsReview']+=['subjectSource 为“largest low furniture”的站位','passThrough 列出的站位在镜头中只经过不观看']+(['房间预算为估算值'] if budgets else [])
    cameraProfile={'eyeMm':eye,'horizontalFovDegrees':options.get('fovDegrees',76),'shiftY':0,'headBob':False,'gazeSmoothSeconds':.12,'finalSmoothSeconds':.15}
    tuned=options.get('cameraOptions','tuned')=='tuned'
    navigation={'avoidBroadWallViews':True,'broadWallPenalty':150,'forwardWeight':8,'preferredHeadingDegrees':60}
    brief={'schema':'homeowner-design-brief/1','tourMode':'full_tour','entranceOpeningId':plan['entrance']['openingId'],'startPoint':plan['entrance']['startPointMm'],'maximumSeconds':maximum,'fps':24,
           'bodyRadiusMm':plan['navigation']['bodyRadiusMm'],'planningMarginMm':35,'gridMm':50,'eyeMm':eye,'cameraProfile':cameraProfile,'observationPitchDegrees':-5,
           'coveragePolicy':{'enabled':not options.get('coverageOff'),**({'minimumPercent':coverage} if coverage is not None else {}),**({'otherMinimumPercent':other_coverage} if other_coverage is not None else {})},
           'roomViewingPolicy':{'singleEpisode':False,'excludeNormalTransit':True},
           'observationPointPolicy':{'defaultPointsPerRoom':1,'maximumPointsPerRoom':2,'recommendedSeconds':[1.5,2.5],'maximumSecondsPerPoint':3,'maximumStillSeconds':.5},
           'roomBudgetPolicy':{'maximumTotalSeconds':maximum,'rooms':budgets},'navigationPolicy':navigation,'rooms':items,'groups':[[i] for i in order],'ruleExceptions':[],
           'fixedOrder':order,'orderOverrideReason':'按用户已确认的空间路线顺序','singleEpisodeExceptionReason':'按用户已确认的空间路线顺序，开放空间分区单独介绍，普通经过不重复介绍。'}
    if brief['coveragePolicy'].get('otherMinimumPercent'):notes['defaults'].append('覆盖率：主要房间（卧室、客厅、餐厅、厨房、书房等，按房内设施的功能判定）不低于 %g%%，其他房间（卫生间、阳台、过道、飘窗等）不低于 %g%%；见 tour_room_class.py'%(brief['coveragePolicy']['minimumPercent'],brief['coveragePolicy']['otherMinimumPercent']))
    if eye!=DEFAULT_EYE_MM or cameraProfile['horizontalFovDegrees']!=76:
        brief['ruleExceptions'].append({'code':'camera_profile_override','reason':str(options.get('eyeReason') or '').strip() or '本案使用非默认视野，实际构图、碰撞、运动与时长门槛保持，镜头仍待用户确认。'})
    if tuned:
        if options.get('roomSizeTiers',True):navigation.update(sweepConsistencyWeight=3,roomSizeTiers=True,pivotWeight=3)  # one-way sweeps: price left-right-left wobble inside a room
        navigation.update(mode='forward',forwardBandDegrees=70,smallRoomBackOut=True,smallRoomBackOutMm=800,comfortClearanceMm=450,comfortWeight=2.5,smallRoomShallowMm=500,smallRoomShallowAreaM2=6)
        brief['speedPolicy']={'cruiseMps':1.1,'narrowCruiseMps':.95,'rampSeconds':.85,'startRampSeconds':.65,'narrowGapMm':150,'floorMps':.15,'frameAccelerationMps2':2.6}
        brief.update(panPolicy='flow',pitchPolicy='subject',walkingPitchDegrees=-3,observationPitchMinDegrees=-8,observationPitchMaxDegrees=-2)
        notes['defaults'].append('速度取开阔 1.1、窄处 0.95 米/秒，停顿缓停 0.85 秒、起步 0.65 秒；路径离墙偏好 45 厘米；6 平方米以内单门小空间只在门内 50 厘米内拍一轮。总时长会比全程 1.2 米/秒略长，请确认 maximumSeconds 够用')
        notes['defaults'].append('镜头选项取“tuned”：最少转头、联合扫视、小房间回退、按主体俯仰；只在一个户型上调试过，见 tour-camera-options-and-lessons.md')
    for name,change in (options.get('overrides') or {}).items():
        if name=='_brief':brief.update(change);continue
        match=[x for x in items if x['name']==name]
        if not match:raise ValueError('Override names an unknown station: '+name)
        change={k:v for k,v in change.items() if k!='viewSubject'}
        match[0].update(change);notes['needsReview'].append('已按覆盖修改：'+name)
    # Rooms the approved route declares as not entered (with a reason) are not counted as uncovered; the reason stays in the brief.
    declared=[{'roomId':r['roomId'],'reason':str(r['reason']).strip()} for r in plan.get('excludedRooms',[]) if r.get('roomId') and str(r.get('reason') or '').strip() and not str(r['reason']).startswith('自动判定')]
    if declared and brief['coveragePolicy'].get('enabled'):
        brief['coveragePolicy']['excludedRooms']=declared;notes['needsReview'].append('路线声明未走入、不计覆盖率的房间：'+'、'.join(r['roomId'] for r in declared))
    from tour_stage_chain import check_brief_alignment,pass_through_stations
    drift=check_brief_alignment(brief,plan)
    if drift:raise ValueError('Generated brief drifts from the route: '+json.dumps(drift,ensure_ascii=False))
    notes['routePlan']=bound(plan_path);notes['schema']=SCHEMA;notes['routePassThrough']=pass_through_stations(brief,plan)
    return brief,notes

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--plan',required=True);a.add_argument('--out',required=True)
    a.add_argument('--maximum-seconds',type=float);a.add_argument('--coverage-minimum-percent',type=float);a.add_argument('--coverage-other-percent',type=float);a.add_argument('--coverage-off',action='store_true')
    a.add_argument('--camera-options',choices=('tuned','basic'),default='tuned');a.add_argument('--eye-mm',type=float,default=DEFAULT_EYE_MM);a.add_argument('--eye-reason');a.add_argument('--fov',type=float,default=76);a.add_argument('--overrides');a.add_argument('--no-room-size-tiers',action='store_true')
    v=a.parse_args();out=Path(v.out)
    if out.exists():raise ValueError('Use a new output directory')
    brief,notes=build(v.plan,{'maximumSeconds':v.maximum_seconds,'coverageMinimumPercent':v.coverage_minimum_percent,'coverageOtherPercent':v.coverage_other_percent,'coverageOff':v.coverage_off,'cameraOptions':v.camera_options,'eyeMm':v.eye_mm,'eyeReason':v.eye_reason,'fovDegrees':v.fov,'roomSizeTiers':not v.no_room_size_tiers,'overrides':read(v.overrides) if v.overrides else None})
    out.mkdir(parents=True);(out/'brief.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8');(out/'brief-assumptions.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'stations':len(brief['rooms']),'passThrough':[x['station'] for x in notes['passThrough']]+notes['routePassThrough'],'output':str(out)},ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError) as e:raise SystemExit(str(e))
