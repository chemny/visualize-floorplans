"""Horizontal room-area screening. Never certifies actual 3D surface visibility."""
import math
from plan_route import inside

def inspect(bundle,tour,planner,minimum_percent=None,grid_mm=300,sample_hz=4,config=None):
    # Import lazily to keep the design entry point acyclic.
    from design_homeowner_tour import clear_distance,delta
    if isinstance(minimum_percent,bool) or not isinstance(minimum_percent,(int,float)) or not math.isfinite(minimum_percent) or not 0<minimum_percent<=100:raise ValueError('Coverage minimum must be in (0,100]')
    if grid_mm<=0 or sample_hz<=0:raise ValueError('Positive coverage sampling parameters required')
    from tour_core_targets import declared_introductions
    separate=config is not None and declared_introductions(config)
    scoped={};room_ids={r['id'] for r in bundle['model']['rooms']}
    # Rooms the approved route declares as not entered stay out of the denominator, with their reason on the report.
    excluded={}
    for value in ((config or {}).get('coveragePolicy') or {}).get('excludedRooms',[]):
        room=value.get('roomId') if isinstance(value,dict) else None
        if not isinstance(room,str) or room not in room_ids or room in excluded or not isinstance(value.get('reason'),str) or not value['reason'].strip():
            raise ValueError('Coverage exclusion requires one known roomId, a unique entry and a reason')
        excluded[room]=value['reason'].strip()
    for value in (config or {}).get('ruleExceptions',[]):
        if value.get('code')!='room_coverage_minimum_override':continue
        room=value.get('roomId');limit=value.get('minimumPercent')
        if (not isinstance(room,str) or room not in room_ids
                or not isinstance(value.get('reason'),str) or not value['reason'].strip()
                or isinstance(limit,bool) or not isinstance(limit,(int,float))
                or not math.isfinite(limit) or not 0<limit<minimum_percent):
            raise ValueError('Coverage exception requires one known roomId, lower minimumPercent and reason')
        if room in scoped:raise ValueError('Duplicate room coverage exception')
        scoped[room]={'code':value['code'],'roomId':room,'minimumPercent':limit,'reason':value['reason'].strip()}
    stride=max(1,round(tour['fps']/sample_hz))
    # Anchor temporal samples at semantic interval boundaries. An unrelated earlier
    # connection must not change which unchanged room frames get tested.
    boundaries=sorted({0,len(tour['frames'])-1}|{v.get('frameIndex',v.get('frame')) for v in (tour.get('stopFrames') or tour.get('visits',[]))})
    if any(not isinstance(i,int) or not 0<=i<len(tour['frames']) for i in boundaries):raise ValueError('Invalid coverage time anchor')
    indices=set(boundaries)
    for a,z in zip(boundaries,boundaries[1:]):indices.update(range(a,z+1,stride))
    rows=[]
    for room in bundle['model']['rooms']:
        if room['id'] in excluded:continue
        allowed=set(indices);window=None;windows=None
        if config is not None:
            from tour_workflow import markers
            marks=markers(tour)
            chapters=[c for c in config['chapters'] if c.get('phase')=='observe' and (c.get('roomId')==room['id'] or room['id'] in c.get('coveredRoomIds',[]))]
            if chapters and separate:
                from tour_room_budgets import deliberate_visit_windows
                windows=deliberate_visit_windows(bundle,tour,config,[room['id']],observation_region=True)
                a,z=windows[0][0],windows[-1][1]
            elif chapters:
                first=chapters[0];episode=first.get('episodeId',first.get('roomId'))
                contiguous=[c for c in chapters if c.get('episodeId',c.get('roomId'))==episode]
                a=marks[first['from']];z=max(marks[c['to']] for c in contiguous)
                # Only the physical entry/exit of this deliberate visit may add coverage.
                region=next((r['poly'] for r in bundle['model']['rooms'] if r['id']==first.get('observationRegionId',first.get('roomId'))),room['poly'])
                while a>0 and inside(tour['frames'][a-1]['pointMm'],region):a-=1
                while z<len(tour['frames'])-1 and inside(tour['frames'][z+1]['pointMm'],region):z+=1
                # Never extend over an introduction to a different room.
                for c in config['chapters']:
                    if c.get('phase')=='observe' and c.get('roomId')!=first.get('roomId'):
                        ca,cz=marks[c['from']],marks[c['to']]
                        if cz<=marks[first['from']]:a=max(a,cz)
                        if ca>=max(marks[q['to']] for q in contiguous):z=min(z,ca)
            else:
                # Passage-only spaces use their first contiguous physical visit, not a later return.
                occupied=[i for i,f in enumerate(tour['frames']) if inside(f['pointMm'],room['poly'])]
                a=occupied[0] if occupied else 0;z=a
                while z+1<len(tour['frames']) and inside(tour['frames'][z+1]['pointMm'],room['poly']):z+=1
                if not occupied:z=-1
            allowed={i for i in indices if any(a<=i<=z for a,z in windows)} if windows is not None else {i for i in indices if a<=i<=z}
            window=[a,z]
        frames=[tour['frames'][i] for i in sorted(allowed)]
        poly=room['poly'];points=[[x,y] for x in range(int(min(q[0] for q in poly))+grid_mm//2,int(max(q[0] for q in poly)),grid_mm) for y in range(int(min(q[1] for q in poly))+grid_mm//2,int(max(q[1] for q in poly)),grid_mm) if inside([x,y],poly)]
        seen=set()
        for f in frames:
            for i,q in enumerate(points):
                if i in seen:continue
                distance=math.dist(q,f['pointMm'])
                if distance<100 or distance>7000:continue
                yaw=math.atan2(q[1]-f['pointMm'][1],q[0]-f['pointMm'][0])
                if abs(delta(f['yawRadians'],yaw))<=math.radians(f.get('horizontalFovDegrees',76)/2) and clear_distance(planner,f['pointMm'],yaw,distance)>=distance-25:seen.add(i)
        percent=100*len(seen)/len(points) if points else 0
        concession=scoped.get(room['id']);limit=concession['minimumPercent'] if concession else minimum_percent
        row={'roomId':room['id'],'sampleCount':len(points),'visibleSamples':len(seen),'horizontalAreaPercent':round(percent,2),'meetsProxyMinimum':bool(points) and percent>=limit,'visitFrames':window}
        if windows is not None:row['visitWindows']=windows
        if concession:row.update(minimumPercent=limit,defaultMinimumPercent=minimum_percent,
            meetsDefaultMinimum=bool(points) and percent>=minimum_percent,thresholdException=concession)
        rows.append(row)
    status='proxy_pass_actual_3d_pending' if all(r['meetsProxyMinimum'] for r in rows) else 'needs_revision'
    report={'schema':'homeowner-room-coverage/1','scope':'declared_introduction_visits' if separate else 'first_continuous_visit' if config is not None else 'whole_timeline_diagnostic','minimumPercent':minimum_percent,'scopedExceptions':list(scoped.values()),'excludedRooms':[{'roomId':k,'reason':v} for k,v in excluded.items()],'gridMm':grid_mm,'sampleHz':sample_hz,'temporalSampleCount':len(indices),'temporalSampling':'interval-anchored with endpoints','rooms':rows,'status':status,'actual3DVisibility':'pending','limitations':'Full room polygon denominator, including furniture footprints. Horizontal field and wall/door bounds only; furniture occlusion, vertical FOV and visible surfaces are not modelled. No actual 3D or human acceptance.'}
    reference=(config or {}).get('coverageReferencePolicy')
    if reference is not None:
        if reference.get('mode')!='reference_not_visual_acceptance':raise ValueError('Unknown explicit coverage reference mode')
        targets=reference.get('roomTargets');tolerance=reference.get('reviewTolerancePercentagePoints')
        if (not isinstance(targets,dict) or set(targets)!=room_ids
                or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<v<=100 for v in targets.values())
                or isinstance(tolerance,bool) or not isinstance(tolerance,(int,float)) or not math.isfinite(tolerance) or not 0<=tolerance<100):
            raise ValueError('Explicit reference targets for every room and finite review tolerance required')
        findings=[]
        for row in rows:
            gap=max(0,targets[row['roomId']]-row['horizontalAreaPercent'])
            if gap:findings.append({'roomId':row['roomId'],'targetPercent':targets[row['roomId']],'actualPercent':row['horizontalAreaPercent'],'gapPercentagePoints':round(gap,2),'severity':'within_review_tolerance' if gap<=tolerance else 'material_gap','visualAcceptance':'pending'})
        report.update(mode='reference',proxyMinimumStatus=status,referencePolicy=reference,referenceFindings=findings,status='reference_review_required' if findings else 'reference_targets_met_actual_3d_pending')
    return report
