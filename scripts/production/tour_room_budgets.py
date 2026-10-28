"""Measure continuous room visits including entry, viewing and normal exit.
Budget diagnostics never retime or change motion/visibility limits.
"""
import math
from plan_route import inside
from tour_workflow import markers

def inspect(bundle,tour,config,policy):
    rooms={r['id']:r for r in bundle['model']['rooms']};marks=markers(tour);fps=tour['fps'];frames=tour['frames'];rows=[];issues=[]
    for budget in policy['rooms']:
        ids=budget['roomIds'];maximum=budget['maximumSeconds']
        if not ids or any(r not in rooms for r in ids):raise ValueError('Unknown room in visit budget')
        if not isinstance(maximum,(int,float)) or not math.isfinite(maximum) or maximum<=0:raise ValueError('Positive finite room visit limit required')
        chapters=[c for c in config['chapters'] if c.get('roomId') in ids and c['phase']=='observe']
        if not chapters:
            issues.append({'code':'missing_room_visit','name':budget['name']});continue
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
        rows.append(row)
        if not row['withinLimit']:issues.append({'code':'room_visit_over_budget','name':budget['name'],'seconds':seconds,'maximumSeconds':maximum})
    maximum=policy['maximumTotalSeconds']
    if not isinstance(maximum,(int,float)) or not math.isfinite(maximum) or maximum<=0:raise ValueError('Positive finite total limit required')
    if tour['seconds']>maximum+1/fps:issues.append({'code':'total_over_budget','seconds':tour['seconds'],'maximumSeconds':maximum})
    return {'schema':'homeowner-room-budgets/1','status':'needs_revision' if issues else 'within_numeric_limits','targetTotalSeconds':policy.get('targetTotalSeconds'),'maximumTotalSeconds':maximum,'totalSeconds':tour['seconds'],'rooms':rows,'issues':issues,'basis':'Contiguous physical occupancy around the deliberate viewing anchors, including shallow entry and normal exit. Later pass-throughs excluded. Full source geometry and actual playback still require review.'}
