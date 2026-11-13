"""Measure continuous room visits including entry, viewing and normal exit.
Budget diagnostics never retime or change motion/visibility limits.
"""
import math
from plan_route import inside
from tour_workflow import markers

def deliberate_visit_windows(bundle,tour,config,room_ids,*,gap_frames=0,observation_region=False):
    """Bound each explicit introduction by its own physical entry and exit.

    A deliberate later introduction can add a visit; a later pass-through cannot.
    Other-room introductions are barriers even in an open shared camera region.
    Callers retain their existing physical doorway-gap tolerance.
    """
    rooms={r['id']:r for r in bundle['model']['rooms']};ids=set(room_ids)
    marks=markers(tour);frames=tour['frames'];observes=[]
    for chapter in config['chapters']:
        if chapter.get('phase')!='observe':continue
        covers=set([chapter.get('roomId')]+chapter.get('coveredRoomIds',[]))
        observes.append((chapter,marks[chapter['from']],marks[chapter['to']],bool(ids&covers)))
    windows=[]
    for chapter,a,z,matching in observes:
        if not matching:continue
        lower,upper=0,len(frames)-1
        for _,ca,cz,other_matching in observes:
            if other_matching:continue
            # Shared chapter endpoints remain part of the explicit anchor, but
            # no additional frame of another introduction contributes evidence.
            if cz<=a:lower=max(lower,min(a,cz+1))
            if ca>=z:upper=min(upper,max(z,ca-1))
        physical_ids=room_ids
        if observation_region:
            region=chapter.get('observationRegionId',chapter.get('roomId'))
            physical_ids=[region] if region in rooms else room_ids
        occupied=lambda i:any(inside(frames[i]['pointMm'],rooms[r]['poly']) for r in physical_ids)
        gap=0;i=a
        while i>lower:
            i-=1;gap=0 if occupied(i) else gap+1
            if gap>gap_frames:break
            if occupied(i):a=i
        gap=0;i=z
        while i<upper:
            i+=1;gap=0 if occupied(i) else gap+1
            if gap>gap_frames:break
            if occupied(i):z=i
        windows.append([a,z])
    merged=[]
    for a,z in sorted(windows):
        if merged and a<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],z)
        else:merged.append([a,z])
    return merged

def inspect(bundle,tour,config,policy):
    rooms={r['id']:r for r in bundle['model']['rooms']};marks=markers(tour);fps=tour['fps'];frames=tour['frames'];rows=[];issues=[]
    from tour_core_targets import declared_introductions
    separate=declared_introductions(config)
    for budget in policy['rooms']:
        ids=budget['roomIds'];maximum=budget['maximumSeconds']
        if not ids or any(r not in rooms for r in ids):raise ValueError('Unknown room in visit budget')
        if not isinstance(maximum,(int,float)) or not math.isfinite(maximum) or maximum<=0:raise ValueError('Positive finite room visit limit required')
        chapters=[c for c in config['chapters'] if c['phase']=='observe' and (c.get('roomId') in ids or (separate and set(ids)&set(c.get('coveredRoomIds',[]))))]
        if not chapters:
            issues.append({'code':'missing_room_visit','name':budget['name']});continue
        if separate:
            windows=deliberate_visit_windows(bundle,tour,config,ids,gap_frames=max(1,round(.2*fps)))
            a,z=windows[0][0],windows[-1][1]
            seconds=sum(z-a for a,z in windows)/fps
        else:
            a=min(marks[c['from']] for c in chapters);z=max(marks[c['to']] for c in chapters)
            occupied=lambda i:any(inside(frames[i]['pointMm'],rooms[r]['poly']) for r in ids)
            # Semantic anchors choose the deliberate visit, not an earlier pass-through.
            # Ignore sub-0.2s polygon-inset gaps at real thresholds; geometry is checked separately.
            gap=0;i=a
            while i>0:
                i-=1;gap=0 if occupied(i) else gap+1
                if gap>max(1,round(.2*fps)):break
                if occupied(i):a=i
            gap=0;i=z
            while i<len(frames)-1:
                i+=1;gap=0 if occupied(i) else gap+1
                if gap>max(1,round(.2*fps)):break
                if occupied(i):z=i
            seconds=(z-a)/fps
        row={'name':budget['name'],'roomIds':ids,'startSeconds':a/fps,'endSeconds':z/fps,'seconds':seconds,'maximumSeconds':maximum,'withinLimit':seconds<=maximum+1/fps}
        if separate:row['visitWindows']=[{'startFrame':a,'endFrame':z,'startSeconds':a/fps,'endSeconds':z/fps,'seconds':(z-a)/fps} for a,z in windows]
        rows.append(row)
        if not row['withinLimit']:issues.append({'code':'room_visit_over_budget','name':budget['name'],'seconds':seconds,'maximumSeconds':maximum})
    maximum=policy['maximumTotalSeconds']
    if not isinstance(maximum,(int,float)) or not math.isfinite(maximum) or maximum<=0:raise ValueError('Positive finite total limit required')
    if tour['seconds']>maximum+1/fps:issues.append({'code':'total_over_budget','seconds':tour['seconds'],'maximumSeconds':maximum})
    basis=('Sum of disjoint local physical visits around explicitly declared introductions; overlapping windows merged and unrelated room introductions and later pass-throughs excluded.' if separate else 'Contiguous physical occupancy around the deliberate viewing anchors, including shallow entry and normal exit. Later pass-throughs excluded.')
    return {'schema':'homeowner-room-budgets/1','status':'needs_revision' if issues else 'within_numeric_limits','targetTotalSeconds':policy.get('targetTotalSeconds'),'maximumTotalSeconds':maximum,'totalSeconds':tour['seconds'],'rooms':rows,'issues':issues,'basis':basis+' Full source geometry and actual playback still require review.'}
