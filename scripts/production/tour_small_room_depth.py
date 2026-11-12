"""Small single-door rooms (bathrooms and the like) are shown from the doorway, not walked into.

Case-enabled through config.smallRoomShallow. Measures how far past the door line the camera goes
while inside such a room. A product limit, not a standard.
"""
import math
from plan_route import inside
from tour_spatial_plan import gates

SCHEMA='homeowner-small-room-depth/1'

def area_m2(poly):return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2e6

def centroid(poly):return [sum(p[k] for p in poly)/len(poly) for k in (0,1)]

def edge_distance(p,poly):
    best=1e18
    for a,b in zip(poly,poly[1:]+poly[:1]):
        dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy or 1)));best=min(best,math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy))
    return best

def small_rooms(bundle,maximum_area=6.):
    """Rooms of at most maximum_area m2 with exactly one door, each with its door line and inward direction."""
    out=[]
    for room in bundle['model']['rooms']:
        if area_m2(room['poly'])>maximum_area:continue
        doors=[g for g in gates(bundle) if g['kind']=='door' and edge_distance([(g['a'][0]+g['b'][0])/2,(g['a'][1]+g['b'][1])/2],room['poly'])<=g['halfThicknessMm']+250]
        if len(doors)!=1:continue
        g=doors[0];mid=[(g['a'][k]+g['b'][k])/2 for k in (0,1)];dx,dy=g['b'][0]-g['a'][0],g['b'][1]-g['a'][1];l=math.hypot(dx,dy);n=[-dy/l,dx/l]
        c=centroid(room['poly'])
        if sum((c[k]-mid[k])*n[k] for k in (0,1))<0:n=[-n[0],-n[1]]
        out.append({'roomId':room['id'],'name':room.get('name',room['id']),'areaM2':area_m2(room['poly']),'doorId':g['id'],'doorMidMm':mid,'inward':n,'poly':room['poly']})
    return out

def shallow_point(room,depth_mm,planner=None):
    """A floor point `depth_mm` past the door line along the door axis, nudged sideways if blocked."""
    n=room['inward'];side=[-n[1],n[0]];mid=room['doorMidMm']
    for offset in (0,150,-150,300,-300):
        p=[mid[k]+n[k]*depth_mm+side[k]*offset for k in (0,1)]
        if inside(p,room['poly']) and (planner is None or not planner.blocked(p)):return p
    return None

def inspect(bundle,tour,config):
    policy=config.get('smallRoomShallow')
    if not policy:return {'schema':SCHEMA,'status':'not_requested','issues':[],'rooms':[]}
    maximum_depth=policy.get('maximumDepthMm',500);rows=[];issues=[]
    polys=[r['poly'] for r in bundle['model']['rooms']];first=next((r for f in tour['frames'] for r in polys if inside(f['pointMm'],r)),None)
    for room in small_rooms(bundle,policy.get('maximumAreaM2',6.)):
        if room['poly'] is first:continue  # the first room entered is the entrance, not a room to peek into
        depths=[sum((f['pointMm'][k]-room['doorMidMm'][k])*room['inward'][k] for k in (0,1)) for f in tour['frames'] if inside(f['pointMm'],room['poly'])]
        if not depths:continue
        row={'roomId':room['roomId'],'name':room['name'],'areaM2':round(room['areaM2'],2),'doorId':room['doorId'],'maximumDepthMm':round(max(depths)),'secondsInside':len(depths)/tour['fps']}
        rows.append(row)
        if max(depths)>maximum_depth+1:issues.append({'code':'small_room_too_deep','roomId':room['roomId'],'name':room['name'],'depthMm':round(max(depths)),'allowedMm':maximum_depth})
    return {'schema':SCHEMA,'status':'pass' if not issues else 'needs_revision','issues':issues,'rooms':rows,'policy':{'maximumAreaM2':policy.get('maximumAreaM2',6.),'maximumDepthMm':maximum_depth}}
