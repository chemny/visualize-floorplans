"""Explain unnecessary tour motion; diagnostics are not visual acceptance."""
import math


def path_turning(frames,minimum_mm=8):
    """Degrees the walking path itself turns over these frames (what turning the connection forces)."""
    headings=[math.atan2(b['pointMm'][1]-a['pointMm'][1],b['pointMm'][0]-a['pointMm'][0]) for a,b in zip(frames,frames[1:]) if math.dist(a['pointMm'],b['pointMm'])>minimum_mm]
    return sum(abs(math.degrees((y-x+math.pi)%(2*math.pi)-math.pi)) for x,y in zip(headings,headings[1:]))


def inspect(tour,config):
    policy={'maximumTransitYawDegrees':180,'maximumTransitExcessDegrees':90,'maximumObservationReversals':1,'maximumTransitFraction':.8,**config.get('choreographyPolicy',{})}
    for key in ('maximumTransitYawDegrees','maximumTransitExcessDegrees','maximumObservationReversals','maximumTransitFraction'):
        value=policy[key]
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:raise ValueError('Finite nonnegative choreography limit required: '+key)
    if not 0<policy['maximumTransitFraction']<=1:raise ValueError('Transit fraction must be in (0,1]')
    marks={v['name']:v.get('frameIndex',v.get('frame')) for v in tour.get('stopFrames',tour.get('visits',[]))}
    fps=tour['fps'];rows=[];issues=[];observe=0;viewed_rooms={}
    for ch in config.get('chapters',[]):
        if ch.get('from') not in marks or ch.get('to') not in marks:continue
        start,end=marks[ch['from']],marks[ch['to']];fs=tour['frames'][start:end+1]
        if len(fs)<2:continue
        changes=[(b['yawRadians']-a['yawRadians'])*180/math.pi for a,b in zip(fs,fs[1:])]
        runs=[]
        for d in changes:
            if abs(d)<1e-6:continue
            if runs and runs[-1]*d>0:runs[-1]+=d
            else:runs.append(d)
        significant=[v for v in runs if abs(v)>=8]
        reversals=sum(a*b<0 for a,b in zip(significant,significant[1:]))
        degrees=sum(map(abs,changes));seconds=(end-start)/fps
        path_turn=path_turning(fs);excess=degrees-path_turn
        distance=sum(math.dist(a['pointMm'],b['pointMm']) for a,b in zip(fs,fs[1:]))/1000
        row={'name':ch['name'],'phase':ch['phase'],'startSeconds':start/fps,'endSeconds':end/fps,'seconds':seconds,'distanceM':distance,'yawTravelDegrees':degrees,'pathTurnDegrees':path_turn,'excessDegrees':excess,'significantReversals':reversals,'necessaryTurn':ch.get('necessaryTurn',False)};rows.append(row)
        if ch['phase']=='observe':
            if config.get('roomViewingPolicy',{}).get('singleEpisode'):
                room=ch.get('roomId')
                episode=ch.get('episodeId',room)
                if room and room in viewed_rooms and viewed_rooms[room]!=episode:issues.append({'code':'split_room_view','chapter':ch['name'],'message':'One room is split across multiple viewing episodes'})
                if room:viewed_rooms[room]=episode
            observe+=seconds
            if reversals>policy['maximumObservationReversals']:issues.append({'code':'repeated_scan','chapter':ch['name'],'message':'Observation reverses direction repeatedly','startSeconds':start/fps,'endSeconds':end/fps})
        elif excess>policy['maximumTransitExcessDegrees']+1:
            issues.append({'code':'transit_turn_beyond_path','chapter':ch['name'],'message':f'Camera turns {degrees:.0f} degrees where the path itself turns {path_turn:.0f}; {excess:.0f} degrees are extra','startSeconds':start/fps,'endSeconds':end/fps,'cameraDegrees':degrees,'pathDegrees':path_turn,'excessDegrees':excess})
            if degrees>policy['maximumTransitYawDegrees']+1:issues.append({'code':'excessive_transit_turn','chapter':ch['name'],'message':f'{distance:.1f} m connection accumulates {degrees:.0f} degrees of turning','startSeconds':start/fps,'endSeconds':end/fps})
        elif degrees>policy['maximumTransitYawDegrees']+1:
            issues.append({'code':'excessive_transit_turn','chapter':ch['name'],'message':f'{distance:.1f} m connection accumulates {degrees:.0f} degrees of turning','startSeconds':start/fps,'endSeconds':end/fps})
    fraction=(tour['seconds']-observe)/tour['seconds']
    if fraction>policy['maximumTransitFraction']:
        issues.append({'code':'transit_dominates','message':f'Connections occupy {fraction:.0%} of the tour; revise order/standing points before slowing or extending'})
    # Reused spatial edges are evidence, not automatic faults: dead ends require return.
    edges={};repeated=0
    for a,b in zip(tour['frames'],tour['frames'][1:]):
        qa=tuple(round(v/300) for v in a['pointMm']);qb=tuple(round(v/300) for v in b['pointMm'])
        if qa==qb:continue
        key=tuple(sorted((qa,qb)));edges[key]=edges.get(key,0)+1
    repeated=sum(v-1 for v in edges.values() if v>1)
    return {'schema':'homeowner-choreography/1','status':'needs_revision' if issues else 'no_numeric_flags','issues':issues,'chapters':rows,'transitFraction':fraction,'observeSeconds':observe,'repeatedSpatialEdgeTransitions':repeated,'policy':policy,'limitations':'Necessary dead-end returns are allowed. Repeated edges and numeric flags do not measure actual visibility, comfort or user approval.'}
