"""Check declared axis-aligned route strips against furniture and occupied envelopes.
Case authors select connected routes and design targets; this is not an auto planner.
"""
import math

def footprint(f):
    rotation=f['rot']%180
    if min(abs(rotation),abs(rotation-90),abs(rotation-180))>.01:raise ValueError('Orthogonal footprints required')
    w,d=(f['d'],f['w']) if abs(rotation-90)<.01 else (f['w'],f['d'])
    return [f['cx']-w/2,f['cy']-d/2,f['cx']+w/2,f['cy']+d/2]

def overlap(a,b,tolerance=.1):
    return min(a[2],b[2])-max(a[0],b[0])>tolerance and min(a[3],b[3])-max(a[1],b[1])>tolerance

def chair_envelope(f,pull_mm):
    if not math.isfinite(pull_mm) or pull_mm<0:raise ValueError('Invalid chair pull distance')
    rect=footprint(f);r=math.radians(f['rot']);dx=math.sin(r)*pull_mm;dy=-math.cos(r)*pull_mm
    return [min(rect[0],rect[0]+dx),min(rect[1],rect[1]+dy),max(rect[2],rect[2]+dx),max(rect[3],rect[3]+dy)]

def check_routes(routes,obstacles):
    if not routes:raise ValueError('Declare route strips before checking')
    for route in routes:
        a=route['rect']
        if len(a)!=4 or not all(map(math.isfinite,a)) or a[2]<=a[0] or a[3]<=a[1]:raise ValueError('Invalid route rectangle')
        if min(a[2]-a[0],a[3]-a[1])+0.1<route['targetWidthMm']:raise ValueError('Route strip below its design target')
    conflicts=[]
    for route in routes:
        for o in obstacles:
            if overlap(route['rect'],o['rect']):conflicts.append({'routeId':route['id'],'obstacleId':o['id']})
    return conflicts
