"""Room observation stations are separate from navigation vertices and furniture targets."""
import math
from collections import Counter
from tour_workflow import markers

DEFAULTS = {'defaultPointsPerRoom': 1, 'maximumPointsPerRoom': 2,
            'recommendedSeconds': [1.5, 2.5], 'maximumSecondsPerPoint': 3,
            'maximumStillSeconds': .5}

def validate(rooms, policy=None):
    policy = {**DEFAULTS, **(policy or {})}
    if policy['maximumPointsPerRoom'] != 2 or policy['defaultPointsPerRoom'] != 1:
        raise ValueError('Room observation policy requires default one and maximum two points')
    for key in ('maximumSecondsPerPoint', 'maximumStillSeconds'):
        if not isinstance(policy[key], (int,float)) or not math.isfinite(policy[key]) or policy[key] <= 0:
            raise ValueError('Positive finite observation point limit required')
    counts = Counter()
    for room in rooms:
        counts[room['roomId']] += 1
        if counts[room['roomId']] > 2:
            raise ValueError('At most two observation points per real room; furniture targets are not stops')
        if counts[room['roomId']] == 2 and not str(room.get('secondPointReason','')).strip():
            raise ValueError('Second observation point needs a concrete occlusion or distinct-area reason')
        if room['viewSeconds'] > policy['maximumSecondsPerPoint']:
            raise ValueError('Requested observation point time exceeds limit')
    return policy

def inspect(tour, config):
    policy = config.get('observationPointPolicy')
    if not policy:
        return {'status':'not_configured','issues':[],'points':[]}
    policy=validate([],policy)
    marks=markers(tour);fps=tour['fps'];frames=tour['frames'];counts=Counter();rows=[];issues=[]
    for ch in config['chapters']:
        if ch['phase'] != 'observe' or ch.get('movingView'):
            continue
        room=ch.get('roomId');counts[room]+=1
        a,z=marks[ch['from']],marks[ch['to']];seconds=(z-a)/fps
        row={'roomId':room,'observationId':ch.get('observationId'), 'seconds':seconds,
             'secondPointReason':ch.get('secondPointReason','')}
        rows.append(row)
        if counts[room]>policy['maximumPointsPerRoom']:
            issues.append({'code':'too_many_observation_points','roomId':room})
        if counts[room]==2 and not row['secondPointReason'].strip():
            issues.append({'code':'unjustified_second_point','roomId':room})
        if seconds>policy['maximumSecondsPerPoint']+1/fps:
            issues.append({'code':'observation_point_over_budget','roomId':room,'seconds':seconds})
        run=longest=0
        for before,after in zip(frames[a:z],frames[a+1:z+1]):
            still=(math.dist(before['pointMm'],after['pointMm'])<.1 and
                   abs(after['yawRadians']-before['yawRadians'])<1e-5 and
                   abs(after.get('pitchRadians',0)-before.get('pitchRadians',0))<1e-5)
            run=run+1 if still else 0;longest=max(longest,run)
        row['simultaneouslyStillSeconds']=longest/fps
        if longest/fps>policy['maximumStillSeconds']+1/fps:
            issues.append({'code':'stationary_camera_hold','roomId':room,'seconds':longest/fps})
    return {'schema':'homeowner-observation-points/1','status':'needs_revision' if issues else 'within_numeric_limits',
            'points':rows,'countsByRoom':dict(counts),'policy':policy,'issues':issues,
            'basis':'Only deliberate room observation stations count. Navigation vertices and ordered furniture targets do not.'}
