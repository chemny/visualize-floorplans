"""Per-chapter camera diagnostics written next to every plan-tour result.

Turning, pitch, time facing a close wall, backward walking and screen issues by chapter and time,
so a reviewer can say which seconds are wrong instead of reading issue counts. No approval.
"""
import math
from design_homeowner_tour import clear_distance
from tour_forward_motion import inspect as forward_motion
from tour_workflow import markers
from tour_choreography import path_turning

SCHEMA='homeowner-camera-diagnostics/1'
NEAR_WALL_MM=1000


def room_wobble(tour,marks,window_seconds=2.,swing_degrees=10.):
    """Left-right-left inside one room's stay (from window_seconds before arrival to after it is finished).

    Each row lists the signed swings between turning points; a wobble is two consecutive swings of at least swing_degrees
    in opposite directions."""
    fs=tour['frames'];fps=tour['fps'];step=max(1,fps//4);yaw=[fs[0]['yawRadians']]
    for f in fs[1:]:yaw.append(yaw[-1]+(f['yawRadians']-yaw[-1]+math.pi)%(2*math.pi)-math.pi)
    rows=[]
    for name in sorted({k.rsplit(' · ',1)[0] for k in marks if k.endswith(' · 到达')}):
        a,z=marks.get(name+' · 到达'),marks.get(name+' · 看完')
        if a is None or z is None:continue
        lo=max(0,a-round(window_seconds*fps));hi=min(len(fs)-1,z+round(window_seconds*fps))
        points=[(i,math.degrees(yaw[i])) for i in range(lo,hi+1,step)];turns=[points[0]];direction=0
        for i,v in points[1:]:
            if direction==0:
                if abs(v-turns[-1][1])>=4:direction=1 if v>turns[-1][1] else -1;turns.append((i,v))
            elif (v-turns[-1][1])*direction>=0:turns[-1]=(i,v)
            elif abs(v-turns[-1][1])>=6:turns.append((i,v));direction=-direction
        swings=[round(q[1]-p[1]) for p,q in zip(turns,turns[1:])]
        flips=sum(1 for x,y in zip(swings,swings[1:]) if abs(x)>=swing_degrees and abs(y)>=swing_degrees)
        rows.append({'room':name,'startSeconds':lo/fps,'swingsDegrees':swings,'reversals':flips})
    return rows


def wall_facing_runs(tour,ahead,marks,gap_mm=600,minimum_seconds=.4):
    """Stretches where the view looks at a wall nearer than gap_mm, with the chapter they fall in."""
    fps=tour['fps'];runs=[];start=None
    for i,v in enumerate(ahead+[1e9]):
        if v<gap_mm:start=i if start is None else start
        elif start is not None:
            if (i-start)/fps>=minimum_seconds:runs.append((start,i))
            start=None
    ordered=sorted(marks.items(),key=lambda kv:kv[1])
    def label(i):
        before=[n for n,f in ordered if f<=i];return before[-1] if before else None
    return [{'startSeconds':a/fps,'seconds':(z-a)/fps,'after':label(a)} for a,z in runs]


def time_breakdown(tour,marks):
    """Where the seconds go: stays, turning in place, walking. Walking is compared with walking at the speed ceiling."""
    fs=tour['frames'];fps=tour['fps'];still=sum(1 for p,q in zip(fs,fs[1:]) if math.dist(p['pointMm'],q['pointMm'])<2)
    walked=sum(math.dist(p['pointMm'],q['pointMm']) for p,q in zip(fs,fs[1:]))/1000
    return {'inPlaceSeconds':still/fps,'walkedMetres':walked,'walkSecondsAtOneMetrePerSecond':walked}


def build(bundle,tour,config,planner,audit=None):
    fs=tour['frames'];fps=tour['fps'];marks=markers(tour);chapters=[];by_time=[]
    ahead=[clear_distance(planner,f['pointMm'],f['yawRadians'],3000) for f in fs]
    for ch in config.get('chapters',[]):
        a,z=marks[ch['from']],marks[ch['to']]
        if z<=a:continue
        yaw=sum(abs(math.degrees((q['yawRadians']-p['yawRadians']+math.pi)%(2*math.pi)-math.pi)) for p,q in zip(fs[a:z],fs[a+1:z+1]))
        pitches=[math.degrees(f['pitchRadians']) for f in fs[a:z+1]];path_turn=path_turning(fs[a:z+1])
        near=[i for i in range(a,z+1) if ahead[i]<NEAR_WALL_MM]
        moving=[i for i in near if i<len(fs)-1 and math.dist(fs[i]['pointMm'],fs[i+1]['pointMm'])*fps/1000>.2]
        row={'name':ch['name'],'phase':ch['phase'],'startSeconds':a/fps,'seconds':(z-a)/fps,
             'distanceM':sum(math.dist(p['pointMm'],q['pointMm']) for p,q in zip(fs[a:z],fs[a+1:z+1]))/1000,
             'yawTravelDegrees':yaw,'pathTurnDegrees':path_turn,'excessTurnDegrees':yaw-path_turn,'pitchMinDegrees':min(pitches),'pitchMaxDegrees':max(pitches),
             'secondsFacingWallUnderOneMetre':len(near)/fps,'secondsFacingWallWhileWalking':len(moving)/fps}
        chapters.append(row);by_time.append((a/fps,z/fps,ch['name']))
    def chapter_at(seconds):return next((name for a,z,name in by_time if a<=seconds<=z),None)
    walking=forward_motion(tour,config)
    screen=[]
    for item in (audit or {}).get('screenQuality',{}).get('issues',[]):
        if 'startSeconds' in item:screen.append({'code':item['code'],'startSeconds':item['startSeconds'],'endSeconds':item.get('endSeconds'),'chapter':chapter_at(item['startSeconds'])})
        else:screen.append({'code':item['code'],'chapter':item.get('chapter'),'subjectId':item.get('subjectId'),'readableSeconds':item.get('readableSeconds')})
    observe=sum(r['seconds'] for r in chapters if r['phase']=='observe')
    return {'schema':SCHEMA,'totalSeconds':tour['seconds'],'observeSeconds':observe,'transitFraction':(tour['seconds']-observe)/tour['seconds'],
            'eyeMm':sorted({round(f['eyeMm']) for f in fs}),'pitchRangeDegrees':[min(math.degrees(f['pitchRadians']) for f in fs),max(math.degrees(f['pitchRadians']) for f in fs)],
            'chapters':chapters,'backwardSpans':[{**s,'chapter':(s['chapters'] or [None])[0]} for s in walking['backwardSpans']],
            'roomWobble':room_wobble(tour,marks),'wallFacingRuns':wall_facing_runs(tour,ahead,marks),'timeBreakdown':time_breakdown(tour,marks),
            'screenIssues':screen,'meshStatus':(audit or {}).get('status','not_checked'),
            'limitations':'Wall distance is a 2D wall/leaf ray; screen issues come from the mesh audit when it ran. Diagnostics grant no acceptance.'}
