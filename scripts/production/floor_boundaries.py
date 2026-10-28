"""Normalize small orthogonal finish-boundary discrepancies against actual walls.
Walls, openings and furniture are never moved. Large gaps/ambiguous free overlaps
are reported rather than invented as room divisions.
"""
import copy,heapq,math
from lighting_checks import inside

def wall_rects(walls):
 live=[w for w in walls if not w.get('demolished')];out=[]
 def pad(w,end):
  p=w['b'] if end else w['a'];axis=0 if abs(w['a'][1]-w['b'][1])<.01 else 1;k=1-axis;direction=(1 if w['b'][axis]>w['a'][axis] else -1)*(1 if end else -1);result=0
  for n in live:
   other=0 if abs(n['a'][1]-n['b'][1])<.01 else 1
   if n is w or axis==other:continue
   delta=n['a'][axis]-p[axis]
   if abs(delta)>n['t']/2+.1:continue
   lo,hi=sorted([n['a'][k],n['b'][k]])
   if lo-w['t']/2-.1<=p[k]<=hi+w['t']/2+.1:result=max(result,n['t']/2+delta*direction)
  return result
 for w in live:
  dx=w['b'][0]-w['a'][0];dy=w['b'][1]-w['a'][1]
  if abs(dx)>.01 and abs(dy)>.01:raise ValueError('Floor boundary normalization requires orthogonal walls')
  length=math.hypot(dx,dy)
  if not math.isfinite(length) or length<=0 or not isinstance(w.get('t'),(int,float)) or not math.isfinite(w['t']) or w['t']<=0:raise ValueError('Invalid wall dimensions for floor boundaries')
  u=[dx/length,dy/length];cuts=[]
  for o in w.get('opens',[]):
   if o.get('removed') or (o['kind']=='window' and o.get('sillHeight',850)>0):continue
   cuts.append((o['at'],o['at']+o['width']))
  cuts+=w.get('removedIntervals',[]);cuts=sorted(cuts);spans=[];start=0
  for a,b in cuts:
   if a>start:spans.append((start,min(a,length)))
   start=max(start,b)
  if start<length:spans.append((start,length))
  for a,b in spans:
   if a==0:a-=pad(w,False)
   if abs(b-length)<.1:b+=pad(w,True)
   p=[w['a'][i]+a*u[i] for i in (0,1)];q=[w['a'][i]+b*u[i] for i in (0,1)];t=w['t']/2
   out.append((min(p[0],q[0])-abs(u[1])*t,min(p[1],q[1])-abs(u[0])*t,max(p[0],q[0])+abs(u[1])*t,max(p[1],q[1])+abs(u[0])*t))
 return out

def signed_area(poly):return sum(p[0]*poly[(i+1)%len(poly)][1]-poly[(i+1)%len(poly)][0]*p[1] for i,p in enumerate(poly))/2

def contours(cells,xs,ys,nx):
 edges={}
 def add(a,b):edges.setdefault(a,set()).add(b)
 for key in cells:
  y,x=divmod(key,nx)
  if key-nx not in cells:add((x,y),(x+1,y))
  if x==nx-1 or key+1 not in cells:add((x+1,y),(x+1,y+1))
  if key+nx not in cells:add((x+1,y+1),(x,y+1))
  if x==0 or key-1 not in cells:add((x,y+1),(x,y))
 result=[]
 def direction(a,b):return 0 if b[0]>a[0] else 1 if b[1]>a[1] else 2 if b[0]<a[0] else 3
 while edges:
  start=min(edges);a=start;b=min(edges[a]);points=[a];count=0
  while True:
   incoming=direction(a,b);edges[a].remove(b)
   if not edges[a]:del edges[a]
   if b==start:break
   points.append(b);options=edges.get(b,set())
   if not options:raise ValueError('Open floor contour')
   following=min(options,key=lambda c:([1,0,3,2].index((direction(b,c)-incoming)%4),c));a,b=b,following;count+=1
   if count>100000:raise ValueError('Invalid floor contour')
  poly=[[xs[x],ys[y]] for x,y in points];poly=[p for i,p in enumerate(poly) if abs((p[0]-poly[i-1][0])*(poly[(i+1)%len(poly)][1]-p[1])-(p[1]-poly[i-1][1])*(poly[(i+1)%len(poly)][0]-p[0]))>1e-8]
  if len(poly)>=4:result.append(poly)
 return result

def normalize_floor_boundaries(case):
 c=copy.deepcopy(case);policy=c.get('floorBoundaryPolicy',{});model=c['model'];rooms=model['rooms'];patches=model.get('floorConnections',[])
 report={'status':'pass','toleranceMm':policy.get('toleranceMm',120),'source':'wall faces and explicit opening spans','rooms':[],'wallOverlapRemovedMm2':0,'outsideRemovedMm2':0,'gapFilledMm2':0,'unresolvedGapMm2':0}
 if policy.get('enabled') is False:return c,{**report,'status':'disabled'}
 tol=report['toleranceMm']
 if not isinstance(tol,(int,float)) or isinstance(tol,bool) or not 0<=tol<=200:raise ValueError('Floor boundary tolerance must be 0–200 mm')
 polys=[model['footprint']]+[r['poly'] for r in rooms]+[p['poly'] for p in patches]
 if any(abs(a[0]-b[0])>.01 and abs(a[1]-b[1])>.01 for poly in polys for a,b in zip(poly,poly[1:]+poly[:1])):raise ValueError('Floor boundary normalization requires orthogonal polygons')
 rects=wall_rects(c['initialState']['walls']);xs=sorted({round(x,6) for p in polys for x,y in p}|{round(x,6) for r in rects for x in (r[0],r[2])});ys=sorted({round(y,6) for p in polys for x,y in p}|{round(y,6) for r in rects for y in (r[1],r[3])});nx=len(xs)-1;ny=len(ys)-1;owner={};free=set();gaps=set();roomids={r['id'] for r in rooms}
 for y in range(ny):
  for x in range(nx):
   key=y*nx+x;p=((xs[x]+xs[x+1])/2,(ys[y]+ys[y+1])/2);area=(xs[x+1]-xs[x])*(ys[y+1]-ys[y]);hits={r['id'] for r in rooms if inside(p,r['poly'])};hits|={patch['materialRoomId'] for patch in patches if inside(p,patch['poly'])}
   if not hits<=roomids:raise ValueError('Floor patch has unknown material owner')
   if not inside(p,model['footprint']):
    if hits:report['outsideRemovedMm2']+=area
    continue
   if any(a<p[0]<b and d<p[1]<e for a,d,b,e in rects):
    if hits:report['wallOverlapRemovedMm2']+=area
    continue
   free.add(key)
   if len(hits)>1:raise ValueError('Ambiguous room overlap in free floor at '+str(p))
   if hits:owner[key]=next(iter(hits))
   else:gaps.add(key)
 def adjacent(key):
  y,x=divmod(key,nx)
  for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
   xx,yy=x+dx,y+dy
   if 0<=xx<nx and 0<=yy<ny:yield yy*nx+xx,(xs[x+1]-xs[x]) if dx else (ys[y+1]-ys[y])
 heap=[];dist={}
 for key in gaps:
  for other,cost in adjacent(key):
   if other in owner:heapq.heappush(heap,(cost,owner[other],key))
 while heap:
  distance,rid,key=heapq.heappop(heap)
  if key in dist or distance>tol:continue
  dist[key]=distance;owner[key]=rid
  for other,_ in adjacent(key):
   if other in gaps and other not in dist:
    yy,xx=divmod(other,nx);y,x=divmod(key,nx);step=xs[xx+1]-xs[xx] if xx!=x else ys[yy+1]-ys[yy];heapq.heappush(heap,(distance+step,rid,other))
 for key in gaps:
  y,x=divmod(key,nx);area=(xs[x+1]-xs[x])*(ys[y+1]-ys[y]);report['gapFilledMm2' if key in owner else 'unresolvedGapMm2']+=area
 if report['unresolvedGapMm2']>.01:raise ValueError('Unassigned floor exceeds small-gap repair range: '+str(report['unresolvedGapMm2'])+' mm²')
 # A tiny detached overrun beside another room is not a new room island.
 report['reassignedFragments']=[]
 for rid in sorted(roomids):
  remaining={key for key,value in owner.items() if value==rid};components=[]
  while remaining:
   seed=min(remaining);component={seed};stack=[seed];remaining.remove(seed)
   while stack:
    key=stack.pop()
    for other,_ in adjacent(key):
     if other in remaining:remaining.remove(other);component.add(other);stack.append(other)
   components.append(component)
  def component_area(cells):return sum((xs[k%nx+1]-xs[k%nx])*(ys[k//nx+1]-ys[k//nx]) for k in cells)
  components.sort(key=component_area,reverse=True)
  for component in components[1:]:
   area=component_area(component);scores={}
   if area>tol*tol:continue
   for key in component:
    y,x=divmod(key,nx)
    for other,_ in adjacent(key):
     target=owner.get(other)
     if target and target!=rid:scores[target]=scores.get(target,0)+(ys[y+1]-ys[y] if other//nx==y else xs[x+1]-xs[x])
   if scores:
    target=max(scores,key=lambda k:(scores[k],k))
    for key in component:owner[key]=target
    report['reassignedFragments'].append({'from':rid,'to':target,'areaMm2':area})
 for room in rooms:
  cells={key for key,rid in owner.items() if rid==room['id']};loops=contours(cells,xs,ys,nx)
  if len(loops)!=1 or signed_area(loops[0])<=0:raise ValueError('Room needs explicit multiple/hole-region review: '+room['id']+' '+str([(signed_area(p),p) for p in loops]))
  before=abs(signed_area(room['poly']));after=abs(signed_area(loops[0]));room['poly']=loops[0];report['rooms'].append({'id':room['id'],'beforeMm2':before,'afterMm2':after})
 model['floorConnections']=[];report['mergedConnectionCount']=len(patches);report['exactSharedEdges']=True;return c,report
