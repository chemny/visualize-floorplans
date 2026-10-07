"""Deterministic case-generation wall-back placement, in mm; not an editor auto-layout.
Furniture local +Y is front. Anchor to a finished wall face, never its centreline.
"""
import math

SIDES = {'north': (0, -1, 180), 'south': (0, 1, 0),
         'west': (-1, 0, 90), 'east': (1, 0, -90)}

def face(wall, side):
    nx, ny, rotation = SIDES[side]
    a, b = wall['a'], wall['b']
    if wall.get('demolished'): raise ValueError('Cannot anchor to a demolished wall')
    if (nx and abs(a[0]-b[0]) > .1) or (ny and abs(a[1]-b[1]) > .1):
        raise ValueError('Wall and requested side must be parallel')
    axis = 0 if nx else 1
    return a[axis] + (nx or ny)*wall['t']/2, axis, rotation

def audit(furniture, wall, side, gap=0, tolerance=.1):
    value, axis, rotation = face(wall, side)
    if abs(((furniture['rot']-rotation+180)%360)-180) > .01:
        raise ValueError('Furniture back is not parallel to the selected wall face')
    nx, ny, _ = SIDES[side]; normal = nx or ny
    centre = furniture['cx' if axis == 0 else 'cy']
    actual_gap = (centre-value)*normal-furniture['d']/2
    tangent = furniture['cy' if axis == 0 else 'cx']
    low, high = tangent-furniture['w']/2, tangent+furniture['w']/2
    a, b = wall['a'], wall['b']; span=sorted([a[1-axis], b[1-axis]])
    if low < span[0]-tolerance or high > span[1]+tolerance:
        raise ValueError('Furniture back exceeds the supporting wall span')
    length=math.dist(a,b); direction=1 if b[1-axis] > a[1-axis] else -1
    projected=sorted([(low-a[1-axis])*direction,(high-a[1-axis])*direction])
    holes=[(o['at'],o['at']+o['width']) for o in wall.get('opens',[])]
    holes += [(v[0],v[1]) for v in wall.get('removedIntervals',[])]
    if any(min(projected[1],end)-max(projected[0],start)>tolerance for start,end in holes):
        raise ValueError('Supporting span includes an opening or removed wall')
    if abs(actual_gap-gap)>tolerance: raise ValueError('Furniture back has an unexpected wall gap')
    return {'furnitureId':furniture['id'],'wallId':wall['id'],'side':side,
            'backGapMm':round(actual_gap,3),'expectedGapMm':gap,'supportSpanMm':round(length,3)}

def anchor(furniture, wall, side, gap=0):
    if not math.isfinite(gap) or gap < 0: raise ValueError('Invalid back gap')
    value, axis, rotation=face(wall,side); normal=SIDES[side][axis]
    candidate=dict(furniture);candidate['rot']=rotation
    candidate['cx' if axis==0 else 'cy']=value+normal*(candidate['d']/2+gap)
    result=audit(candidate,wall,side,gap)
    furniture.update(candidate)
    furniture['wallAnchor']={'wallId':wall['id'],'side':side,'backGapMm':gap,
                             'basis':'finished wall face; generation-time relationship'}
    return result

def supporting_run(walls):
    """Join contiguous collinear segments for support audit without changing case walls."""
    if not walls: raise ValueError('Missing support walls')
    first=walls[0];axis=0 if abs(first['a'][0]-first['b'][0])<.1 else 1;tangent=1-axis
    coord=first['a'][axis];thickness=first['t'];parts=[]
    for w in walls:
        if w.get('demolished') or any(abs(p[axis]-coord)>.1 for p in (w['a'],w['b'])) or abs(w['t']-thickness)>.1:
            raise ValueError('Support walls must be present, collinear and equal thickness')
        parts.append((min(w['a'][tangent],w['b'][tangent]),max(w['a'][tangent],w['b'][tangent]),w))
    parts.sort(key=lambda p:p[0]);start=parts[0][0];end=parts[0][1]
    for lo,hi,w in parts[1:]:
        if abs(lo-end)>.1:raise ValueError('Support wall segments must be contiguous without overlap')
        end=hi
    a=[0,0];b=[0,0];a[axis]=b[axis]=coord;a[tangent]=start;b[tangent]=end
    run={'id':first['id'],'a':a,'b':b,'t':thickness,'opens':[],'removedIntervals':[]}
    for lo,hi,w in parts:
        direction=1 if w['b'][tangent]>w['a'][tangent] else -1
        def offset(u):return w['a'][tangent]+direction*u-start
        for o in w.get('opens',[]):
            p,q=sorted([offset(o['at']),offset(o['at']+o['width'])]);run['opens'].append({'at':p,'width':q-p})
        for p,q in w.get('removedIntervals',[]):run['removedIntervals'].append(sorted([offset(p),offset(q)]))
    return run

def audit_corner(furniture, back_walls, back_side, end_wall, end_side, gap=0, end_gap=0):
    run=supporting_run(back_walls);back=audit(furniture,run,back_side,gap)
    _,back_axis,_=face(run,back_side);_,end_axis,rot=face(end_wall,end_side)
    if back_axis==end_axis:raise ValueError('Corner walls must be perpendicular')
    end=dict(furniture,w=furniture['d'],d=furniture['w'],rot=rot)
    end_result=audit(end,end_wall,end_side,end_gap)
    return {**back,'supportWallIds':[w['id'] for w in back_walls],
            'endWallId':end_wall['id'],'endSide':end_side,'endGapMm':end_result['backGapMm']}

def anchor_corner(furniture, back_walls, back_side, end_wall, end_side, gap=0, end_gap=0):
    """Place back and end against perpendicular faces, or reject atomically."""
    if not math.isfinite(end_gap) or end_gap<0:raise ValueError('Invalid end gap')
    candidate=dict(furniture);run=supporting_run(back_walls)
    value,axis,_=face(end_wall,end_side);normal=SIDES[end_side][axis]
    candidate['cx' if axis==0 else 'cy']=value+normal*(candidate['w']/2+end_gap)
    anchor(candidate,run,back_side,gap)
    result=audit_corner(candidate,back_walls,back_side,end_wall,end_side,gap,end_gap)
    candidate['wallAnchor'].update(supportWallIds=result['supportWallIds'],endWallId=end_wall['id'],endSide=end_side,endGapMm=end_gap)
    furniture.update(candidate);return result
