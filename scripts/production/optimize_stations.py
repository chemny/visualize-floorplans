"""Choose each observation station by what the camera would actually see from it.

For every room several floor positions near the approved route station are tried with the room's
own sweep, audited together in one batch against the exported triangle mesh (no browser, no
video), scored and the best kept. Stays inside the route's station tolerance. No approval.
"""
import argparse,copy,json,math,subprocess,shutil,sys
from pathlib import Path
from plan_route import Planner,inside
from design_homeowner_tour import clear_distance,entry_apron,flow_candidates,delta,PROFILE
from tour_stage_gate import read,resolve,bound

SCHEMA='homeowner-station-optimization/1'
FPS=8
SCORES={'subject_composition_unreadable':4,'screen_near_surface_occlusion':6,'screen_dominant_surface':6,'screen_blank_segment':4}
DISTANCE_WEIGHT_PER_METRE=1.5
TURN_WEIGHT_PER_DEGREE=.05
HINGE_FROM_DEGREES=150
HINGE_WEIGHT=.5
KEEP=4

def candidates_for(planner,room_poly,station,tolerance,step=300,radius=1500,limit=16):
    """Reachable floor points around a route station, nearest first. The station itself leads."""
    found=[]
    for dx in range(-radius,radius+1,step):
        for dy in range(-radius,radius+1,step):
            p=[station[0]+dx,station[1]+dy]
            if math.hypot(dx,dy)>min(radius,tolerance) or not inside(p,room_poly) or planner.blocked(p):continue
            if (dx or dy) and not planner.line_free(station,p):continue
            found.append(p)
    found.sort(key=lambda p:(math.dist(p,station),p));return found[:limit]

def sweep_for(planner,item,furniture,point,brief):
    """The sweep this observation would use from `point`, and the eye pitch it would hold."""
    eye=brief.get('eyeMm',1600);fov=brief.get('cameraProfile',{}).get('horizontalFovDegrees',76)
    ids=[i for i in dict.fromkeys(item.get('flowSubjects') or [item['subjectId']]+item.get('subjects',[])) if i in furniture]
    bearings=[math.atan2(furniture[i]['cy']-point[1],furniture[i]['cx']-point[0]) for i in ids]
    reach=math.hypot(item['targetMm'][0]-point[0],item['targetMm'][1]-point[1]) or 1
    if brief.get('pitchPolicy')=='subject':
        pitch=max(math.radians(brief.get('observationPitchMinDegrees',-16)),min(math.radians(brief.get('observationPitchMaxDegrees',-2)),math.atan2(item['targetMm'][2]-eye,reach)))
        walking=math.radians(brief.get('walkingPitchDegrees',-3))
    else:pitch=walking=math.radians(brief.get('observationPitchDegrees',-5))
    half=math.radians(brief.get('flowSubjectHalfViewDegrees',fov/2-10));limit=read(PROFILE)['reviewLimits']['maxYawDegreesPerSecond']
    smallest=brief.get('flowMinSweepDegrees',24);reach_limits=(smallest,max(smallest,min(item.get('maxSweepDegrees',999),int(item['viewSeconds']*limit/1.5))))
    while True:
        try:rows=flow_candidates(planner,point,bearings,half,reach_limits);break
        except ValueError:
            if len(bearings)<=1:return None
            lead=bearings[0];bearings.pop(max(range(1,len(bearings)),key=lambda k:abs(delta(lead,bearings[k]))))
    _,start,pan=rows[0];return start,pan,walking,pitch,ids

def mini_tour(item,point,sweep,brief,scheme,furniture):
    """A stationary observation window, enough for the mesh audit to judge the shot."""
    start,pan,walking,pitch,ids=sweep;count=max(2,round(item['viewSeconds']*FPS));eye=brief.get('eyeMm',1600);fov=brief.get('cameraProfile',{}).get('horizontalFovDegrees',76)
    frames=[]
    for i in range(count+1):
        u=i/count;tilt=min(1,u/.45)
        frames.append({'frame':i,'pointMm':list(point),'yawRadians':start+pan*(u*u*(3-2*u)),'pitchRadians':walking+(pitch-walking)*(tilt*tilt*(3-2*tilt)),'eyeMm':eye,'horizontalFovDegrees':fov,'shiftY':0})
    tour={'schema':'floor-visualization-tour/1.0','schemeSha256':scheme,'fps':FPS,'seconds':len(frames)/FPS,'frames':frames,'visits':[{'name':'a','frame':0},{'name':'b','frame':count}]}
    declared=[i for i in dict.fromkeys([item['subjectId']]+item.get('subjects',[])) if i in furniture]
    config={'chapters':[{'name':'obs','from':'a','to':'b','phase':'observe','roomId':item.get('roomId'),'episodeId':item.get('episodeId',item.get('roomId')),'subjects':declared,'viewPurpose':item.get('viewPurpose','station trial'),'tourRole':item.get('tourRole','secondary')}]}
    return tour,config

def score_audit(audit,subjects,distance_mm):
    """Lower is better; a station that shows its subjects readably and no wall wins."""
    issues=audit.get('screenQuality',{}).get('issues',[]);chapter=audit.get('chapters',[{}])[0]
    unreadable=[i for i in subjects if not chapter.get('subjects',{}).get(i,{}).get('pass',False)]
    walls=[x for x in issues if x['code'] in ('screen_near_surface_occlusion','screen_dominant_surface','screen_blank_segment')]
    score=SCORES['subject_composition_unreadable']*len(unreadable)+sum(SCORES[x['code']] for x in walls)+DISTANCE_WEIGHT_PER_METRE*distance_mm/1000
    return {'score':round(score,2),'unreadable':unreadable,'screenIssues':[x['code'] for x in walls],'distanceMm':round(distance_mm)}

def run_batch(node,runtime,jobs,workdir):
    results={}
    for start in range(0,len(jobs),64):
        chunk=jobs[start:start+64];batch=workdir/('batch-%03d.json'%start)
        batch.write_text(json.dumps({'schema':'homeowner-mesh-batch/1','jobs':[{'tour':j['tour'],'config':j['config'],'out':j['out']} for j in chunk]}))
        done=subprocess.run([node,str(Path(__file__).with_name('tour_mesh_preflight.mjs')),'--runtime',str(runtime),'--batch',str(batch)],capture_output=True,text=True)
        if done.returncode:raise ValueError('Mesh audit failed: '+(done.stderr or done.stdout)[-400:])
        for j in chunk:results[j['key']]=read(j['out'])
    return results

PROTECTED=('excessive_transit_turn','transit_turn_beyond_path','abrupt_stop','small_room_too_deep','sustained_backward_walking')

def protected_issues(bundle,brief):
    """Camera design, gaze smoothing and the numeric contract for one brief; seconds, not minutes."""
    from design_homeowner_tour import design
    from tour_pipeline import finalize_gaze
    from tour_contract import inspect as contract
    tour,config,_=design(bundle,brief);final=finalize_gaze(tour,config,.2)
    return [x for x in contract(bundle,final,config)['issues'] if x['code'] in PROTECTED]

def repair(bundle,baseline,candidate,progress=print,limit=8):
    """Undo station moves around any connection the move made worse; never keep a new turn or reverse-walking failure."""
    before={(x['code'],x.get('chapter')) for x in protected_issues(bundle,baseline)};steps=[]
    for _ in range(limit):
        new=[x for x in protected_issues(bundle,candidate) if (x['code'],x.get('chapter')) not in before]
        if not new:return candidate,steps
        names=[n.strip() for n in str(new[0].get('chapter','')).replace('→','|').split('|')]
        moved=[x for x in candidate['rooms'] if x['name'] in names and x['candidatePoints'][0]!=next(b for b in baseline['rooms'] if b['observationId']==x['observationId'])['candidatePoints'][0]]
        if not moved:raise ValueError('A new '+new[0]['code']+' remains with no moved station to undo: '+json.dumps(new[0],ensure_ascii=False))
        target=moved[-1];original=next(b for b in baseline['rooms'] if b['observationId']==target['observationId'])
        target['candidatePoints']=copy.deepcopy(original['candidatePoints']);steps.append({'undid':target['name'],'because':new[0]['code']+' in '+str(new[0].get('chapter'))});progress('undo '+target['name']+' ('+new[0]['code']+')')
    raise ValueError('Station moves still introduce turn failures after %d undos'%limit)

def optimize(brief_path,plan_path,runtime,out,node=None,progress=print,verify=True):
    out=Path(out)
    if out.exists():raise ValueError('Use a new output directory')
    node=node or shutil.which('node')
    if not node:raise ValueError('Existing Node.js required; pass --node')
    brief=read(brief_path);plan_path=Path(plan_path).resolve();plan=read(plan_path);bundle=read(resolve(plan['bundle'],plan_path.parent))
    scene=read(Path(runtime)/'scene.json')
    if scene.get('schemeSha256')!=bundle['schemeSha256']:raise ValueError('Runtime belongs to another scheme')
    furniture={f['id']:f for f in bundle['state']['furniture']};rooms={r['id']:r for r in bundle['model']['rooms']};stations={s['name']:s for s in plan['stations']}
    access,_=entry_apron(bundle,brief);planner=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':brief.get('bodyRadiusMm',180)+brief.get('planningMarginMm',25),'gridMm':brief.get('gridMm',50)})
    tolerance=plan['cameraEnvelope']['stationToleranceMm'];work=out/'trials';work.mkdir(parents=True);jobs=[];trials={}
    for item in brief['rooms']:
        station=stations.get(item['name'])
        if station is None:continue
        poly=rooms[item.get('observationRegionId',item['roomId'])]['poly']
        for n,point in enumerate(candidates_for(planner,poly,station['pointMm'],tolerance)):
            sweep=sweep_for(planner,item,furniture,point,brief)
            if sweep is None:continue
            tour,config=mini_tour(item,point,sweep,brief,bundle['schemeSha256'],furniture);key=(item['observationId'],n)
            paths={k:work/('%s-%02d-%s.json'%(item['observationId'],n,k)) for k in ('tour','config','audit')}
            paths['tour'].write_text(json.dumps(tour));paths['config'].write_text(json.dumps(config))
            jobs.append({'key':key,'tour':str(paths['tour']),'config':str(paths['config']),'out':str(paths['audit'])});trials[key]=(item,point,[i for i in dict.fromkeys([item['subjectId']]+item.get('subjects',[])) if i in furniture],station['pointMm'],sweep)
    progress('trying %d candidate stations for %d observations'%(len(jobs),len({k[0] for k in trials})))
    audits=run_batch(node,runtime,jobs,work);report=[];result=copy.deepcopy(brief)
    from compact_tour_visits import safe_path
    from design_homeowner_tour import forward_plan
    band=brief.get('navigationPolicy',{}).get('forwardBandDegrees',60);legs={}
    def turning(a,b,y0,y1):
        key=(tuple(a),tuple(b),round(math.degrees(y0)),round(math.degrees(y1)))
        if key not in legs:
            try:
                path=safe_path(planner,a,b);dense=[path[0]];run=[0]
                for u,v in zip(path,path[1:]):
                    n=max(1,math.ceil(math.dist(u,v)/35));dense+=[[u[k]+(v[k]-u[k])*j/n for k in (0,1)] for j in range(1,n+1)]
                for u,v in zip(dense,dense[1:]):run.append(run[-1]+math.dist(u,v))
                legs[key]=forward_plan(dense,run,y0,y1,band,coarse=True)['totalDegrees']
            except ValueError:legs[key]=720.
        return legs[key]
    chosen_by={};ordered=[x for x in result['fixedOrder']];by_id={x['observationId']:x for x in result['rooms']}
    options={}
    for oid in ordered:
        rows=[]
        for key,(source,point,ids,station,sweep) in trials.items():
            if key[0]==oid:rows.append({'point':point,'sweep':sweep,**score_audit(audits[key],ids,math.dist(point,station))})
        if rows:
            rows.sort(key=lambda r:(r['score'],r['distanceMm']));keep=rows[:KEEP]
            at_station=next((r for r in rows if r['distanceMm']==0),None)
            if at_station is not None and at_station not in keep:keep.append(at_station)
            options[oid]=(rows,keep)
    sequence=[oid for oid in ordered if oid in options];start=brief['startPoint']
    first=None
    table=[]
    for position,oid in enumerate(sequence):
        row=[]
        for cand in options[oid][1]:
            sweep=cand['sweep'];start_yaw=sweep[0];best=(math.inf,None)
            previous=[(start,None,None,0.)] if position==0 else [(p['point'],p['sweep'][0]+p['sweep'][1],k,table[position-1][k][0]) for k,p in enumerate(options[sequence[position-1]][1])]
            for point,end_yaw,k,before in previous:
                if position==0:
                    path=safe_path(planner,start,cand['point']);end_yaw=math.atan2(path[1][1]-path[0][1],path[1][0]-path[0][0])
                turn=turning(point,cand['point'],end_yaw,start_yaw)
                # Past about 150 degrees a connection is close to the 180 limit once pivots and sweep changes are added.
                cost=before+cand['score']+TURN_WEIGHT_PER_DEGREE*turn+HINGE_WEIGHT*max(0.,turn-HINGE_FROM_DEGREES)
                if cost<best[0]:best=(cost,k)
            row.append(best)
        table.append(row)
    k=min(range(len(table[-1])),key=lambda i:table[-1][i][0]);choice={}
    for position in range(len(sequence)-1,-1,-1):
        choice[sequence[position]]=options[sequence[position]][1][k];k=table[position][k][1] if table[position][k][1] is not None else 0
    for item in result['rooms']:
        oid=item['observationId']
        if oid not in choice:continue
        rows,_=options[oid];best=choice[oid];at_station=next((r for r in rows if r['distanceMm']==0),rows[0])
        item['candidatePoints']=[best['point']]+[p for p in item['candidatePoints'] if p!=best['point']][:4]
        strip=lambda r:{k:v for k,v in r.items() if k!='sweep'}
        report.append({'name':item['name'],'observationId':oid,'routeStation':stations[item['name']]['pointMm'],'chosen':strip(best),'atRouteStation':strip(at_station),'tried':len(rows),'moved':best['point']!=at_station['point'],'improvedScoreBy':round(at_station['score']-best['score'],2)})
    steps=[]
    if verify:result,steps=repair(bundle,brief,result,progress)
    for item in result['rooms']:
        row=next((r for r in report if r['observationId']==item['observationId']),None)
        if row:row['moved']=item['candidatePoints'][0]!=row['atRouteStation']['point'];row['finalPoint']=item['candidatePoints'][0]
    from tour_stage_chain import check_brief_alignment
    drift=check_brief_alignment(result,plan)
    if drift:raise ValueError('Optimized brief drifts from the route: '+json.dumps(drift,ensure_ascii=False))
    result.setdefault('routeAlignment',{})['stationOptimization']='按网格画面检查选择站位，范围不超出已批准路线的站位容差'
    out.mkdir(exist_ok=True);(out/'brief.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    (out/'station-report.json').write_text(json.dumps({'schema':SCHEMA,'rows':report,'verification':{'performed':verify,'undone':steps,'protected':list(PROTECTED)},'scoring':{'weights':SCORES,'distancePerMetre':DISTANCE_WEIGHT_PER_METRE},'limitations':'Each station is judged alone with its own sweep and no walking; turning between rooms is checked later by plan-tour. Stations are chosen together: each candidate score plus the turning the connections between neighbouring stations would need. Scores order candidates; they do not accept a view.','routePlan':bound(plan_path)},ensure_ascii=False,indent=2),encoding='utf-8')
    return result,report

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--brief',required=True);a.add_argument('--plan',required=True);a.add_argument('--runtime',required=True);a.add_argument('--out',required=True);a.add_argument('--node');a.add_argument('--no-verify',action='store_true')
    v=a.parse_args();brief,report=optimize(v.brief,v.plan,v.runtime,v.out,v.node,verify=not v.no_verify)
    print(json.dumps({'moved':[r['name'] for r in report if r['moved']],'kept':[r['name'] for r in report if not r['moved']],'output':v.out},ensure_ascii=False))
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError) as e:raise SystemExit(str(e))
