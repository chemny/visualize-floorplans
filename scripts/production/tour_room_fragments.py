"""Data-only room-first qualification. No HTML, capture, or acceptance side effects.
Room-only coverage is a sufficient proposal test, not a new requirement: fragments
below it remain conditional until their actual first-entry/exit connections qualify.
"""
import argparse,copy,json,math
from pathlib import Path
from tour_pipeline import JointPlanner,finalize_gaze,length,read,dump
from compact_tour_visits import at_distance,dense_path
from tour_candidate_quality import smooth_position_seams
from tour_workflow import markers,metrics,sha
from tour_coverage import inspect as coverage
from tour_rules import trajectory,fingerprint


def groups(config):
    result=[]
    for chapter in config['chapters']:
        if chapter['phase']!='observe':continue
        if result and result[-1][-1]['to']==chapter['from'] and result[-1][-1]['roomId']==chapter['roomId']:
            result[-1].append(chapter)
        else:result.append([chapter])
    return result


def clip(engine,chapters,choices):
    frames=[];visits=[];local=[];previous=None
    for ch in chapters:
        choice=engine.bind_adjacent(previous,ch,choices[ch['name']],choices)
        if choice is None:raise ValueError('Adjacent observation cannot share physical pose')
        choices={**choices,ch['name']:choice};n=engine.m[ch['to']]-engine.m[ch['from']]
        if choice['source']=='seed':chunk=copy.deepcopy(engine.t['frames'][engine.m[ch['from']]:engine.m[ch['to']]+1])
        else:
            chunk=[];path=choice.get('viewPath',[choice['point'],choice['endPoint']]);distance=length(path)
            for j in range(n+1):
                u=j/n;f=copy.deepcopy(engine.t['frames'][engine.m[ch['from']]])
                f.update(pointMm=at_distance(path,distance*u),yawRadians=choice['yaw']+choice['pan']*u,pitchRadians=choice.get('pitchFrom',choice.get('pitch',0))*(1-u)+choice.get('pitch',0)*u);chunk.append(f)
        if not frames:frames=chunk;visits.append({'name':ch['from'],'frame':0})
        else:
            if math.dist(frames[-1]['pointMm'],chunk[0]['pointMm'])>.1:raise ValueError('Room fragment has disconnected views')
            offset=frames[-1]['yawRadians']+math.atan2(math.sin(chunk[0]['yawRadians']-frames[-1]['yawRadians']),math.cos(chunk[0]['yawRadians']-frames[-1]['yawRadians']))-chunk[0]['yawRadians']
            for f in chunk:f['yawRadians']+=offset
            frames.extend(chunk[1:])
        visits.append({'name':ch['to'],'frame':len(frames)-1});lc=copy.deepcopy(ch);lc['singleSweepDegrees']=math.degrees(chunk[-1]['yawRadians']-chunk[0]['yawRadians']);local.append(lc);previous=ch
    for i,f in enumerate(frames):f['frame']=i
    t={'schema':engine.t.get('schema'),'schemeSha256':engine.t['schemeSha256'],'fps':engine.fps,'frames':frames,'seconds':len(frames)/engine.fps,'visits':visits,'previewOnly':True,'humanAcceptance':'pending','fragmentOnly':True}
    c=copy.deepcopy(engine.c);c['chapters']=local;c.pop('cameraKeys',None)
    t=smooth_position_seams(t,c,engine.p);t=finalize_gaze(t,c,.12)
    return t,c


def inspect_fragment(engine,tour,config,room_ids):
    cp=coverage(engine.b,tour,engine.p,engine.c['coveragePolicy']['minimumPercent'],config=config)
    rows=[r for r in cp['rooms'] if r['roomId'] in room_ids]
    path=trajectory(tour,config);mm=metrics(tour);issues=path['issues'][:]
    collision=[i for i,f in enumerate(tour['frames']) if engine.p.blocked(f['pointMm'])]
    edges=[i for i,(a,z) in enumerate(zip(tour['frames'],tour['frames'][1:])) if not engine.p.line_free(a['pointMm'],z['pointMm'])]
    if collision or edges:issues.append({'code':'body_path_collision','frames':collision[:8],'edges':edges[:8]})
    limits=engine.limits
    for actual,cap in [('maximumSpeedMps','maximumSpeedMps'),('maxYawDegreesPerSecond','maxYawDegreesPerSecond'),('maxPitchDegreesPerSecond','maxPitchDegreesPerSecond')]:
        if mm[actual]>limits[cap]+1e-6:issues.append({'code':'motion_limit','field':actual,'actual':mm[actual],'limit':limits[cap]})
    gap=sum(max(0,cp['minimumPercent']-r['horizontalAreaPercent']) for r in rows)
    return {'roomCoverage':rows,'viewOnlyCoverageSufficient':gap==0,'coverageDeficitPercentagePoints':round(gap,2),'motionAndPathPass':not issues,'issues':issues,'motion':mm,'scope':'observation_windows_only','completeFirstVisitCoverage':'pending_connections'}


def prepare(job,out):
    out=Path(out).resolve()
    if out.exists():raise ValueError('Fresh fragment output required')
    b,t,c=[read(job[k]) for k in ('bundle','seedTour','seedConfig')]
    if b['schemeSha256']!=t['schemeSha256']:raise ValueError('Current scheme required')
    maximum=job.get('roomFirst',{}).get('maximumMeshCandidatesPerRoom',8)
    if not isinstance(maximum,int) or not 1<=maximum<=12:raise ValueError('Bounded per-room mesh candidate count required')
    out.mkdir(parents=True);e=JointPlanner(b,t,c,job.get('search',{}));records=[];jobs=[];summary=[]
    for group in groups(c):
        if job.get('roomFirst',{}).get('onlyRoomIds') and group[0]['roomId'] not in job['roomFirst']['onlyRoomIds']:continue
        rid=group[0]['roomId'];room_ids=list(dict.fromkeys([rid]+[r for ch in group for r in ch.get('coveredRoomIds',[])]));base={ch['name']:e.baseline(ch) for ch in group};variants=[('seed',base)]
        if len(group)==1:
            ch=group[0]
            for k,pose in enumerate(e.candidates(ch,0,True)[1:]):variants.append((f'pose-{k}',{ch['name']:pose}))
        # Framing search changes pitch only, preserving original shape/positions/timing.
        for deg in (-5,-10,-15,-20,-25):
            variants.append((f'pitch{deg}',{name:{**v,'pitch':math.radians(deg),'source':'room_framing'} for name,v in base.items()}))
        if len(group)==1 and len(variants)<10:
            ch=group[0];v=base[ch['name']];seconds=(e.m[ch['to']]-e.m[ch['from']])/e.fps
            for offset in (-10,0,10):
                for span in (30,40):
                    if span/seconds>e.limits['maxYawDegreesPerSecond']*.98:continue
                    for pitch in (-10,-15):
                        sign=1 if v['pan']>=0 else -1
                        variants.append((f'angle{offset}-{span}-{pitch}',{ch['name']:{**v,'yaw':v['yaw']+math.radians(offset),'pan':math.radians(sign*span),'pitch':math.radians(pitch),'source':'room_framing'}}))
        if len(group)>1:
            # Plan one safe geometric curve for the continuous room episode.
            # Do not join three independently directed furniture movements.
            start=base[group[0]['name']]['point'];end=base[group[-1]['name']]['endPoint'];total=sum(e.m[ch['to']]-e.m[ch['from']] for ch in group)
            for wi,waypoint in enumerate([base[ch['name']]['point'] for ch in group[1:]]):
                try:
                    path=e.p.round([start,waypoint,end])
                    if any(not e.p.line_free(a,z) for a,z in zip(path,path[1:])):continue
                except ValueError:continue
                distance=length(path);dense=dense_path(path,20);ds=[0]
                for a,z in zip(dense,dense[1:]):ds.append(ds[-1]+math.dist(a,z))
                for widen in (0,8):
                    for pitch in (-5,-10,-15,-20):
                        choice={};offset=0
                        for gi,ch in enumerate(group):
                            n=e.m[ch['to']]-e.m[ch['from']];lo=distance*offset/total;hi=distance*(offset+n)/total
                            piece=[at_distance(path,lo)]+[q for q,d in zip(dense,ds) if lo<d<hi]+[at_distance(path,hi)]
                            value={**base[ch['name']],'point':piece[0],'endPoint':piece[-1],'viewPath':piece,'pitch':math.radians(pitch),'source':'room_group_curve'}
                            if gi==0:value.update(yaw=value['yaw']-math.radians(widen),pan=value['pan']+math.radians(widen))
                            if gi==len(group)-1:value['pan']+=math.radians(widen)
                            choice[ch['name']]=value;offset+=n
                        variants.append((f'curve{wi}-wide{widen}-pitch{pitch}',choice))
        tested=[]
        for name,choices in variants:
            try:
                ft,fc=clip(e,group,copy.deepcopy(choices));result=inspect_fragment(e,ft,fc,room_ids)
                tested.append({'name':name,'tour':ft,'config':fc,'choices':choices,'result':result})
            except ValueError as exc:records.append({'roomId':rid,'proposal':name,'error':str(exc)})
        tested.sort(key=lambda v:(not v['result']['motionAndPathPass'],v['result']['coverageDeficitPercentagePoints'],sum(x.get('localCost',0) for x in v['choices'].values())))
        # Preserve exit heading/position diversity among qualified proposals.
        chosen=[];keys=set()
        for v in tested:
            f=v['tour']['frames'][-1];key=(round(f['pointMm'][0]/250),round(f['pointMm'][1]/250),round(math.degrees(f['yawRadians'])/30),round(math.degrees(f['pitchRadians'])/5))
            if key not in keys:chosen.append(v);keys.add(key)
            if len(chosen)>=maximum:break
        for v in tested:
            if len(chosen)>=maximum:break
            if all(v['name']!=q['name'] for q in chosen):chosen.append(v)
        for v in chosen:
            directory=out/rid/v['name'];directory.mkdir(parents=True);dump(directory/'tour.json',v['tour']);dump(directory/'config.json',v['config']);dump(directory/'numeric.json',{**v['result'],'tourSha256':sha(directory/'tour.json'),'configSha256':sha(directory/'config.json'),'engineFingerprint':fingerprint()});dump(directory/'choices.json',v['choices'])
            jobs.append({'tour':str(directory/'tour.json'),'config':str(directory/'config.json'),'out':str(directory/'mesh.json')})
        summary.append({'roomId':rid,'coveredRoomIds':room_ids,'proposalCount':len(variants),'numericEvaluated':len(tested),'meshCandidateCount':len(chosen),'viewingIntervals':{ch['name']:e.m[ch['to']]-e.m[ch['from']] for ch in group},'bestViewOnlyCoverage':tested[0]['result']['roomCoverage'] if tested else [],'meshValidation':'pending'})
        print(json.dumps(summary[-1],ensure_ascii=False),flush=True)
    batch={'schema':'homeowner-mesh-batch/1','jobs':jobs};dump(out/'mesh-batch.json',batch);dump(out/'rooms.json',summary);dump(out/'rejected-proposals.json',records)
    dump(out/'input-lock.json',{'schemeSha256':b['schemeSha256'],'sources':{k:sha(job[k]) for k in ('bundle','seedTour','seedConfig')},'timingLocks':c.get('timingLocks',{}),'geometrySha256':sha(Path(job['runtime'])/'geometry.bin') if job.get('runtime') else None,'rehearsalGenerated':False,'videoGenerated':False})
    return summary


def summarize(out):
    out=Path(out);rooms=read(out/'rooms.json');records=[];binding=read(out/'input-lock.json')
    for room in rooms:
        rows=[]
        for numeric in (out/room['roomId']).glob('*/numeric.json'):
            d=numeric.parent;n=read(numeric);mesh=read(d/'mesh.json') if (d/'mesh.json').exists() else None
            fresh=bool(mesh and mesh.get('ruleFingerprint')==fingerprint() and mesh.get('tourSha256')==sha(d/'tour.json') and mesh.get('configSha256')==sha(d/'config.json') and n.get('engineFingerprint')==fingerprint() and n.get('tourSha256')==sha(d/'tour.json') and n.get('configSha256')==sha(d/'config.json') and mesh.get('schemeSha256')==binding['schemeSha256'] and (not binding.get('geometrySha256') or mesh.get('geometrySha256')==binding['geometrySha256']))
            target_order=True
            if mesh is not None:
                from tour_camera_evidence import require_actual_targets
                try:require_actual_targets(read(d/'config.json'),read(d/'tour.json'),mesh)
                except ValueError:target_order=False
            issues=[] if mesh is None else mesh['screenQuality']['issues']+[{'code':'actual_mesh_target_unreadable','chapter':ch['id'],'subjectId':id} for ch in mesh['chapters'] for id,v in ch['subjects'].items() if not v['pass']]
            if not target_order:issues.append({'code':'actual_mesh_target_order_or_visibility'})
            rows.append({'directory':str(d),'viewOnlyCoverageSufficient':n['viewOnlyCoverageSufficient'],'coverage':n['roomCoverage'],'coverageDeficitPercentagePoints':n['coverageDeficitPercentagePoints'],'motionAndPathPass':n['motionAndPathPass'],'meshChecked':mesh is not None,'evidenceFresh':fresh,'meshAndCompositionPass':fresh and mesh['status']=='pass' and target_order,'meshIssues':issues,'numericIssues':n['issues'],'qualifiedObservationFragment':n['viewOnlyCoverageSufficient'] and n['motionAndPathPass'] and fresh and mesh['status']=='pass' and target_order})
        rows.sort(key=lambda r:(not r['qualifiedObservationFragment'],not r['motionAndPathPass'],not r['meshAndCompositionPass'],r['coverageDeficitPercentagePoints'],len(r['meshIssues'])))
        records.append({**room,'meshValidation':'checked' if all(r['meshChecked'] for r in rows) else 'incomplete','qualifiedObservationFragments':[r['directory'] for r in rows if r['qualifiedObservationFragment']],'candidates':rows,'connectionStatus':'pending','actualPlayback':'not_performed'})
    dump(out/'qualification-report.json',{'schema':'homeowner-room-qualification/1','rooms':records,'allRoomsHaveQualifiedObservationFragment':all(r['qualifiedObservationFragments'] for r in records),'rehearsalGenerated':False,'videoGenerated':False,'actualPlayback':'not_performed','limitations':['Observation-only coverage is sufficient, not necessary: below-threshold candidates may still qualify within their same physical first-entry/exit window.','Passing fragments do not certify joins, complete visit budgets, transit gaze or full-tour acceptance.']})
    return records

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--job');p.add_argument('--out',required=True);p.add_argument('--summarize',action='store_true');a=p.parse_args()
    if a.summarize:summarize(a.out)
    else:prepare(read(a.job),a.out)
