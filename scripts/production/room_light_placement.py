"""Explicit default room-light anchors; never relocate unmarked/manual lights."""
from lighting_checks import MAIN_TYPES,inside

def room_center(poly):
    cross=[p[0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*p[1] for i,p in enumerate(poly)]
    area=sum(cross)
    if abs(area)<1: raise ValueError('Room polygon has no area')
    center=[sum((p[k]+poly[(i+1)%len(poly)][k])*cross[i] for i,p in enumerate(poly))/(3*area) for k in (0,1)]
    if not inside(center,poly):
        # Concave partitions may have an external centroid: nearest interior sample.
        xs=[p[0] for p in poly];ys=[p[1] for p in poly]
        points=[[min(xs)+(max(xs)-min(xs))*i/50,min(ys)+(max(ys)-min(ys))*j/50] for i in range(1,50) for j in range(1,50)]
        valid=[p for p in points if inside(p,poly)]
        if not valid: raise ValueError('No interior room-center anchor')
        center=min(valid,key=lambda p:sum((p[k]-center[k])**2 for k in (0,1)))
    return [round(v) for v in center]

def apply_room_light_defaults(case):
    rooms={r['id']:r for r in case['model']['rooms']}
    for f in case['initialState']['furniture']:
        if f.get('defaultPlacement')!='room-center' or f['type'] not in MAIN_TYPES: continue
        if f.get('roomId') not in rooms: raise ValueError('Room-centered light requires valid roomId')
        f['cx'],f['cy']=room_center(rooms[f['roomId']]['poly'])
        f.pop('defaultPlacement',None)
        f['placementOrigin']='room-center-default'
    return case
