"""Connect qualified observation fragments using measured safe-edge work.
Writes data/diagnostics only. Candidate-graph optimum is not a global optimum.
"""
import argparse,copy,json,math
from pathlib import Path
from tour_pipeline import JointPlanner,read,dump,finalize_gaze
from tour_workflow import markers,sha
from compact_tour_visits import dense_path
from design_homeowner_tour import navigation_gaze
from tour_rules import fingerprint
from tour_contract import inspect as contract
from tour_candidate_quality import connection_effort


def pick_nodes(qualification,maximum=4):
    if not isinstance(maximum,int) or not 1<=maximum<=8:raise ValueError('Bounded connection node count required')
    rows=[]
    for room in qualification['rooms']:
        eligible=[]
        for row in room['candidates']:
            if not row['qualifiedObservationFragment']:continue
            d=Path(row['directory']);t=read(d/'tour.json');c=read(d/'config.json');fs=t['frames']
            pose=(tuple(round(v/150) for v in fs[0]['pointMm']+fs[-1]['pointMm']),round(math.degrees(fs[0]['yawRadians'])/20),round(math.degrees(fs[-1]['yawRadians'])/20))
            eligible.append((pose,{'directory':str(d),'tour':t,'config':c,'start':fs[0],'end':fs[-1]}))
        chosen=[];seen=set()
        for pose,node in eligible:
            if pose not in seen:chosen.append(node);seen.add(pose)
            if len(chosen)>=maximum:break
        for _,node in eligible:
            if len(chosen)>=maximum:break
            if all(node['directory']!=v['directory'] for v in chosen):chosen.append(node)
        rows.append((room['roomId'],chosen))
    return rows


def connect(job,qualification_path,out):
    out=Path(out).resolve()
    if out.exists():raise ValueError('Fresh connection output required')
    report=read(qualification_path);b,t,c=[read(job[k]) for k in ('bundle','seedTour','seedConfig')];e=JointPlanner(b,t,c,job.get('search',{}));rows=pick_nodes(report,job.get('roomFirst',{}).get('maximumConnectionCandidatesPerRoom',4));out.mkdir(parents=True)
    missing=[rid for rid,nodes in rows if not nodes]
    if missing:
        result={'status':'room_qualification_blocked','roomsWithoutQualifiedFragment':missing,'rehearsalGenerated':False,'videoGenerated':False};dump(out/'connection-report.json',result);return result
    for _,nodes in rows:
        for node in nodes:
            evidence=read(Path(node['directory'])/'mesh.json')
            if evidence['ruleFingerprint']!=fingerprint() or evidence['tourSha256']!=sha(Path(node['directory'])/'tour.json') or evidence['configSha256']!=sha(Path(node['directory'])/'config.json') or evidence['schemeSha256']!=b['schemeSha256']:raise ValueError('Qualified fragment evidence is stale')
    edges=[];cache={};nav={'avoidBroadWallViews':True,'broadWallPenalty':80,'forwardWeight':6,'excessTurnPerStepWeight':100,'interpolation':'linear'}
    def edge(source,dest,ch):
        a,z=source['pointMm'],dest['pointMm'];path=e.connection_path(a,z,ch);dense=dense_path(path,20);dist=[0]
        for p,q in zip(dense,dense[1:]):dist.append(dist[-1]+math.dist(p,q))
        if len(dense)<2:dense=[a,z];dist=[0,math.dist(a,z)]
        local={**nav,**ch.get('navigationPolicy',{}),'maximumSpeedMps':e.limits['maximumSpeedMps'],'maxYawDegreesPerSecond':e.limits['maxYawDegreesPerSecond']}
        key=(tuple(a),tuple(z),round(source['yawRadians'],6),round(dest['yawRadians'],6),json.dumps(local,sort_keys=True))
        if key not in cache:
            cache[key]=navigation_gaze(e.p,dense,dist,source['yawRadians'],dest['yawRadians'],local) if dist[-1]>=1 else [source['yawRadians'],source['yawRadians']+math.atan2(math.sin(dest['yawRadians']-source['yawRadians']),math.cos(dest['yawRadians']-source['yawRadians']))]
        ys=cache[key];work=sum(connection_effort(dense,ys,source['pitchRadians'],dest['pitchRadians'],e.limits));return {'minimumFrames':max(1,math.ceil(work*e.fps-1e-8)),'minimumSeconds':work,'lengthMm':dist[-1]}
    states=[{'frames':0,'selection':[],'source':e.entry,'legs':[]}]
    for rid,nodes in rows:
        next_states=[]
        for ni,node in enumerate(nodes):
            ch=next(ch for ch in c['chapters'] if ch['phase']=='transit' and ch['to']==node['config']['chapters'][0]['from'])
            candidates=[]
            for state in states:
                try:leg=edge(state['source'],node['start'],ch)
                except ValueError as exc:edges.append({'chapter':ch['name'],'destination':node['directory'],'error':str(exc)});continue
                edges.append({'chapter':ch['name'],'destination':node['directory'],**leg})
                candidates.append({'frames':state['frames']+leg['minimumFrames'],'selection':state['selection']+[node['directory']],'source':node['end'],'legs':state['legs']+[{'chapter':ch['name'],**leg}]})
            if candidates:next_states.append(min(candidates,key=lambda s:s['frames']))
        states=next_states
        print(json.dumps({'room':rid,'connectedStates':len(states),'bestMinimumTransitFrames':min((s['frames'] for s in states),default=None)},ensure_ascii=False),flush=True)
        if not states:break
    final=[]
    if states:
        closing=e.closing_pose();last_ch=c['chapters'][-1]
        for state in states:
            try:leg=edge(state['source'],closing,last_ch)
            except ValueError as exc:edges.append({'chapter':last_ch['name'],'error':str(exc)});continue
            final.append({**state,'frames':state['frames']+leg['minimumFrames'],'legs':state['legs']+[{'chapter':last_ch['name'],**leg}]})
    available=c['timingLocks']['totalFrames']-1-sum(c['timingLocks']['viewingFrames'].values());best=min(final,key=lambda s:s['frames']) if final else None
    result={'schema':'homeowner-fragment-connections/1','status':'connection_graph_blocked' if best is None else 'connection_budget_conflict' if best['frames']>available else 'assembly_pending','availableTransitFrames':available,'availableTransitSeconds':available/e.fps,'bestMinimumTransitFrames':best['frames'] if best else None,'bestMinimumTransitSeconds':best['frames']/e.fps if best else None,'deficitFrames':max(0,best['frames']-available) if best else None,'deficitSeconds':max(0,best['frames']-available)/e.fps if best else None,'selectedFragments':best['selection'] if best else [],'legs':best['legs'] if best else [],'edges':edges,'engineFingerprint':fingerprint(),'fixedViewingFrames':c['timingLocks']['viewingFrames'],'totalFrames':c['timingLocks']['totalFrames'],'totalSeconds':c['timingLocks']['totalSeconds'],'rehearsalGenerated':False,'videoGenerated':False,'actualPlayback':'not_performed','limitations':['Optimum only within this fixed room order, qualified fragment set and safe edge planner. This does not prove global infeasibility.','Connection work is a lower bound; final sampled acceleration, first-visit coverage, complete room budgets and mesh screen audit are mandatory.']}
    dump(out/'connection-report.json',result)
    if best and best['frames']<=available:
        choices={};windows={};cc=copy.deepcopy(c)
        for directory in best['selection']:
            d=Path(directory);ft=read(d/'tour.json');fc=read(d/'config.json');m=markers(ft)
            for ch in fc['chapters']:
                fs=ft['frames'][m[ch['from']]:m[ch['to']]+1];windows[ch['from']]=fs
                choices[ch['name']]={'point':fs[0]['pointMm'],'endPoint':fs[-1]['pointMm'],'yaw':fs[0]['yawRadians'],'pan':fs[-1]['yawRadians']-fs[0]['yawRadians'],'pitchFrom':fs[0]['pitchRadians'],'pitch':fs[-1]['pitchRadians'],'source':'qualified_fragment','viewPath':[f['pointMm'] for f in fs],'localCost':0}
                existing=next(q for q in cc['chapters'] if q['name']==ch['name']);existing.update(ch)
        engine=JointPlanner(b,t,cc,job.get('search',{}))
        try:
            assembled,config=engine.rebuild(choices,{**nav,'closingView':'door'},frozen_windows=windows);assembled=finalize_gaze(assembled,config,.12)
            config['cameraKeys']=[{'atStop':config['chapters'][0]['from'],'offsetFrames':i,'targetMm':[f['pointMm'][0]+1000*math.cos(f['yawRadians']),f['pointMm'][1]+1000*math.sin(f['yawRadians']),f['eyeMm']+1000*math.tan(f['pitchRadians'])],'yawDegrees':math.degrees(f['yawRadians']),'pitchDegrees':math.degrees(f['pitchRadians'])} for i,f in enumerate(assembled['frames'])]
            dump(out/'tour.json',assembled);dump(out/'config.json',config);numeric=contract(b,assembled,config);dump(out/'contract-report.json',numeric)
            result['status']='numeric_pass_mesh_pending' if not numeric['issues'] else 'assembled_needs_revision';result['issues']=numeric['issues'];dump(out/'connection-report.json',result)
        except ValueError as exc:
            result['status']='assembly_blocked';result['assemblyError']=str(exc);dump(out/'connection-report.json',result)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--qualification',required=True);p.add_argument('--out',required=True);a=p.parse_args();connect(read(a.job),a.qualification,a.out)
