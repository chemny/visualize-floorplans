"""Derive main functions from the scene, independently of the camera target list.

Only actual primary objects in intentionally presented rooms are required. Detail
assemblies/decorations are not stops. Full-tour room scope remains a separate
contract. No room names, case IDs, coordinates or exclusion switch are defaults.
"""
import copy, json, math
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[2]/'assets/h5/tour/core-functions.json'
SCHEMA = 'homeowner-core-targets/1'


def inventory(bundle):
    spec = json.loads(CATALOG.read_text()); rooms = bundle['model']['rooms']
    from plan_route import inside
    result = {r['id']: [] for r in rooms}
    for f in bundle['state']['furniture']:
        function = spec['types'].get(f.get('type'))
        if not function or f.get('assemblyOwner') or f.get('planPoint') or f.get('demolished'):
            continue
        point = [f['cx'], f['cy']]
        matches = [r['id'] for r in rooms if inside(point, r['poly'])]
        room = f.get('roomId') if f.get('roomId') in matches else next(iter(matches), None)
        if room is not None:
            result[room].append({'subjectId': f['id'], 'type': f['type'], 'function': function})
    return {k: sorted(v, key=lambda x: x['subjectId']) for k, v in result.items() if v}


def first_episodes(config):
    result = {}; closed = set(); previous = set()
    for ch in config.get('chapters', []):
        if ch.get('phase') != 'observe': continue
        rooms = set([ch.get('roomId')]+ch.get('coveredRoomIds', [])) - {None}
        closed.update(previous-rooms)
        for room in rooms-closed: result.setdefault(room, []).append(ch)
        previous = rooms
    return result


def excused_rooms(config):
    """Rooms the user chose to pass through without presenting them (explicit case policy with the user's reason)."""
    rows=config.get('coreTargetPolicy',{}).get('excludedRooms',[])
    return {r['roomId'] for r in rows if isinstance(r,dict) and isinstance(r.get('reason'),str) and r['reason'].strip()}


def declared_introductions(config):
    """Use separate introductions only for an explicit, justified case policy."""
    reason=config.get('tourContract',{}).get('singleEpisodeExceptionReason')
    return (config.get('roomViewingPolicy',{}).get('singleEpisode') is False
            and isinstance(reason,str) and bool(reason.strip()))


def introduction_episodes(config):
    """Group observe chapters by real room, retaining explicit episode breaks.

    Transits never provide core readability. A covered room keeps its actual
    inventory even when the camera station is in an adjacent physical room.
    """
    result={};active={}
    for ch in config.get('chapters',[]):
        if ch.get('phase')!='observe':continue
        rooms=list(dict.fromkeys([ch.get('roomId')]+ch.get('coveredRoomIds',[])))
        rooms=[room for room in rooms if room is not None]
        for room in set(active)-set(rooms):active.pop(room)
        for room in rooms:
            token=ch.get('episodeId')
            if room not in active or active[room][0]!=token:
                episode=[];result.setdefault(room,[]).append(episode);active[room]=(token,episode)
            active[room][1].append(ch)
    return result


def inspect(bundle, config):
    actual = inventory(bundle); rows = []; issues = []
    separate=declared_introductions(config)
    excused=excused_rooms(config)
    episodes=(introduction_episodes(config) if separate
              else {room:[chapters] for room,chapters in first_episodes(config).items()})
    for room, room_episodes in episodes.items():
        chapters=[ch for episode in room_episodes for ch in episode]
        required = [] if room in excused else actual.get(room, [])
        declared = {s for ch in chapters for s in ch.get('subjects', [])+ch.get('orderedViewTargets', [])}
        missing = [f['subjectId'] for f in required if f['subjectId'] not in declared]
        permitted={}
        for f in required:
            episode=next((episode for episode in room_episodes
                          if any(f['subjectId'] in targets(ch) for ch in episode)),[]) if separate else room_episodes[0]
            permitted[f['subjectId']]=[ch['name'] for ch in episode]
        rows.append({'roomId': room, 'required': required, 'chapters': [c['name'] for c in chapters],
                     'subjectChapters':permitted,'missingTargets': missing})
        issues += [{'code': 'missing_core_view_target', 'roomId': room, 'subjectId': s} for s in missing]
    return {'schema': SCHEMA, 'status': 'needs_revision' if issues else 'pass', 'rooms': rows,
            'minimumReadableSeconds': json.loads(CATALOG.read_text())['minimumReadableSeconds'], 'issues': issues}


def bind(bundle, config):
    """Enrich planning input once. Validators always reconstruct independently."""
    c = copy.deepcopy(config); episodes = first_episodes(c)
    # A case with several introductions must declare each function's intended
    # episode; assigning it to an arbitrary earlier visit would change intent.
    if declared_introductions(c):return c
    for row in inspect(bundle, c)['rooms']:
        if row['missingTargets']:
            ch = episodes[row['roomId']][0]
            ch['subjects'] = list(dict.fromkeys(ch.get('subjects', [])+row['missingTargets']))
    return c


def targets(ch):
    return list(dict.fromkeys(ch.get('orderedViewTargets', [])+ch.get('subjects', [])))


def scan_angles(bundle,chapter,point,seconds,max_rate,hfov=76):
    """Bounded one-way proposals for the whole function set, without full circles."""
    from tour_camera_evidence import target_anchor
    angles=sorted(math.atan2(q[1]-point[1],q[0]-point[0])%(2*math.pi)
                  for q in (target_anchor(bundle,s) for s in targets(chapter)))
    if len(angles)<2:return []
    gap,k=max(((angles[(i+1)%len(angles)]-v)%(2*math.pi),i) for i,v in enumerate(angles))
    lo=angles[(k+1)%len(angles)];ys=[lo+(v-lo)%(2*math.pi) for v in angles];span=max(ys)-lo
    if span>math.pi:return []
    need=max(0,math.degrees(span)-hfov+max_rate*.5*2)
    pan=math.radians(min(need,max_rate*seconds*.98));mid=(lo+max(ys))/2
    return [(mid-sign*pan/2+math.radians(shift),sign*pan) for sign in (-1,1) for shift in (-6,0,6)]


def readability(bundle, config, chapters, policy, fps):
    report=inspect(bundle,config); rows=[]; issues=report['issues'][:]
    p={'sampleHz':4,'minVisibleSamples':2,'minVisibleFraction':.03,'minScreenAreaFraction':.005,**policy}
    gap=1.5/max(1,p['sampleHz'])+1/fps
    for row in report['rooms']:
        for f in row['required']:
            permitted=row['subjectChapters'][f['subjectId']]
            samples=sorted([s for ch in chapters if ch.get('id') in permitted for s in ch.get('samples',[])],key=lambda s:s['seconds'])
            start=last=None; longest=0
            for s in samples:
                v=s.get('subjects',{}).get(f['subjectId'],{})
                ok=(v.get('unoccludedSamples',0)>=p['minVisibleSamples'] and v.get('unoccludedSamples',0)/max(1,v.get('totalSamples',0))>=p['minVisibleFraction'] and v.get('screenAreaFraction',0)>=p['minScreenAreaFraction'])
                if not ok:start=last=None;continue
                if start is None or s['seconds']-last>gap:start=s['seconds']
                last=s['seconds'];longest=max(longest,last-start)
            passed=longest+1e-6>=report['minimumReadableSeconds']
            rows.append({'roomId':row['roomId'],'subjectId':f['subjectId'],'chapters':permitted,
                         'longestContinuousSeconds':longest,'pass':passed})
            if not passed:issues.append({'code':'core_facility_unreadable','roomId':row['roomId'],'subjectId':f['subjectId']})
    return {**report,'status':'needs_revision' if issues else 'pass','readability':rows,'issues':issues}
