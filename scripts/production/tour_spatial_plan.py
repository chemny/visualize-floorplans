"""Stage-one spatial route: rooms, openings, ordered path, returns and rough budget.
No cameras, frames, rendering or automatic approval. Stations come from room geometry.
"""
import argparse,heapq,html,json,math,time
from pathlib import Path
from plan_route import Planner,inside,dist_segment
from door_operation_review import segment_distance
from tour_stage_gate import bound,resolve,read
PLAN_SCHEMA='homeowner-spatial-plan/1';APPROVAL_SCHEMA='homeowner-spatial-approval/1'
CHECKS=('orderApproved','pathApproved','necessaryReturnsApproved')
MIN_BODY_RADIUS_MM=160
ENVELOPE={'maximumDeviationMm':900,'visitedRoomDeviationMm':2800,'maximumLengthRatio':1.3,'stationToleranceMm':2800}
NON_SIGNERS=('synthetic','fixture','agent','codex','claude','assistant','自动','代签')
# Only tests patch this. No CLI flag, job field or environment variable can enable it.
ALLOW_SYNTHETIC_FOR_TESTS=False

class SpatialBlocked(ValueError):
 def __init__(self,message,report):
  super().__init__(message);self.report=report

def finite(p,n=2):return isinstance(p,list) and len(p)==n and all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in p)
def polyline_length(points):return sum(math.dist(a,b) for a,b in zip(points,points[1:]))
def orient(a,b,c):return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def crosses(a,b,c,d):return orient(a,b,c)*orient(a,b,d)<0 and orient(c,d,a)*orient(c,d,b)<0

def gates(bundle):
 """Every traversable opening as an explicit centreline across the wall."""
 out=[]
 for w in bundle['state']['walls']:
  if w.get('demolished'):continue
  l=math.dist(w['a'],w['b']);v=[(w['b'][k]-w['a'][k])/l for k in (0,1)]
  for i,o in enumerate(w['opens']):
   if o['kind'] not in ('door','sliding'):continue
   out.append({'id':o.get('id') or w['id']+':'+str(i),'kind':o['kind'],'a':[w['a'][k]+v[k]*o['at'] for k in (0,1)],'b':[w['a'][k]+v[k]*(o['at']+o['width']) for k in (0,1)],'halfThicknessMm':w['t']/2})
 return out

def explain_point(planner,p):
 """Name each reason a point is rejected. Never changes the collision rule."""
 reasons=[];r=planner.radius
 declared=inside(p,planner.b['model'].get('footprint',[])) or any(inside(p,x['poly']) for x in planner.rooms) or any(inside(p,q) for q in planner.cfg.get('accessPolygons',[]))
 if not declared and not any(dist_segment(p,g['a'],g['b'])<=g['halfThicknessMm']+35 for g in gates(planner.b)):reasons.append({'code':'outside_declared_domain','accessPolygons':len(planner.cfg.get('accessPolygons',[]))})
 for a,b,half in planner.walls:
  if dist_segment(p,a,b)<half+r:reasons.append({'code':'wall_clearance','a':[round(v) for v in a],'b':[round(v) for v in b]})
 for a,b,half in planner.leaves:
  if dist_segment(p,a,b)<half+r:reasons.append({'code':'door_leaf_clearance','a':[round(v) for v in a],'b':[round(v) for v in b]})
 for f in planner.furniture:
  angle=math.radians(f.get('rot',0));dx,dy=p[0]-f['cx'],p[1]-f['cy'];u=dx*math.cos(angle)+dy*math.sin(angle);v=-dx*math.sin(angle)+dy*math.cos(angle)
  if abs(u)<f['w']/2+r and abs(v)<f['d']/2+r:reasons.append({'code':'furniture_clearance','id':f['id'],'type':f['type']})
 return reasons

def field(planner,source,targets,deadline,forbidden=None,reused=None,reuse_weight=1,reused_gates=None,gate_cost=0):
 """Dijkstra on the shared walkable grid, stopping when all targets are settled."""
 best={source:0.};came={};queue=[(0.,source)];left=set(targets)-{source}
 while queue and left:
  g,k=heapq.heappop(queue)
  if g!=best.get(k):continue
  left.discard(k)
  if time.monotonic()>deadline:raise TimeoutError('Spatial planning reached its explicit deadline')
  for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
   n=(k[0]+dx,k[1]+dy)
   if not planner.free(n) or (forbidden and n in forbidden):continue
   if dx and dy and (not planner.free((k[0]+dx,k[1])) or not planner.free((k[0],k[1]+dy))):continue
   v=g+math.hypot(dx,dy)*(reuse_weight if reused and n in reused else 1)+(gate_cost if reused_gates and n in reused_gates else 0)
   if v<best.get(n,math.inf):best[n]=v;came[n]=k;heapq.heappush(queue,(v,n))
 return best,came

def trace(came,k):
 out=[k]
 while k in came:k=came[k];out.append(k)
 return out[::-1]

def gate_cells(planner,gate):
 """Grid cells inside one physical opening; passing it again is a discouraged repeat."""
 g=planner.grid;pad=gate['halfThicknessMm']+planner.radius;xs=[gate['a'][0],gate['b'][0]];ys=[gate['a'][1],gate['b'][1]];cells=set()
 for i in range(int((min(xs)-pad)//g),int((max(xs)+pad)//g)+2):
  for j in range(int((min(ys)-pad)//g),int((max(ys)+pad)//g)+2):
   if dist_segment((i*g,j*g),gate['a'],gate['b'])<=gate['halfThicknessMm']:cells.add((i,j))
 return cells

def corridor(keys,span):
 return {(x+i,y+j) for x,y in keys for i in range(-span,span+1) for j in range(-span,span+1)}

def turning_points(points):
 out=[points[0]]
 for a,b,c in zip(points,points[1:],points[2:]):
  if abs(orient(a,b,c))>1e-6:out.append(b)
 return out+[points[-1]] if len(points)>1 else out

def opening_passability(planner,all_gates):
 """Why an opening may be impassable at this body radius; evidence, never a relaxation."""
 rows=[]
 for g in all_gates:
  mid=[(g['a'][k]+g['b'][k])/2 for k in (0,1)];reasons=explain_point(planner,mid)
  rows.append({'id':g['id'],'kind':g['kind'],'widthMm':round(math.dist(g['a'],g['b'])),'centrePassable':not reasons,'reasons':reasons[:4]})
 return rows

def furniture_box_distance(f,p):
 angle=math.radians(f.get('rot',0));dx,dy=p[0]-f['cx'],p[1]-f['cy'];u=dx*math.cos(angle)+dy*math.sin(angle);v=-dx*math.sin(angle)+dy*math.cos(angle)
 return math.hypot(max(0,abs(u)-f['w']/2),max(0,abs(v)-f['d']/2))

def ray_clear(planner,a,b):return not any(segment_distance(a,b,c,d)<half for c,d,half in planner.walls)

def room_samples(room,step=480):
 xs=[p[0] for p in room['poly']];ys=[p[1] for p in room['poly']];out=[]
 for i in range(int((max(xs)-min(xs))/step)+1):
  for j in range(int((max(ys)-min(ys))/step)+1):
   q=[min(xs)+step/2+i*step,min(ys)+step/2+j*step]
   if inside(q,room['poly']):out.append(q)
 return out[:48]

def anchor_of(bundle,room,visit):
 anchor=visit.get('anchor')
 if not anchor:return None
 rows=[f for f in bundle['state']['furniture'] if f['id']==anchor.get('furnitureId') or f['type'] in anchor.get('furnitureTypes',[])]
 rows=[f for f in rows if inside([f['cx'],f['cy']],room['poly'])]
 if not rows:raise ValueError('Visit anchor not found inside its room: '+visit['name'])
 return rows[0]

def room_gates(room,all_gates):
 """Openings that belong to a room: their centre lies inside it or within a wall thickness of its outline."""
 out=[];poly=room['poly']
 for g in all_gates:
  mid=[(g['a'][k]+g['b'][k])/2 for k in (0,1)]
  d=0 if inside(mid,poly) else min(dist_segment(mid,poly[i],poly[(i+1)%len(poly)]) for i in range(len(poly)))
  if d<=g['halfThicknessMm']+200:out.append(g)
 return out

def station_candidates(bundle,planner,visit,limit,all_gates):
 """Cheap floor feasibility only: clearance, shallow depth, 2D wall view. Not a camera check."""
 room=next((r for r in planner.rooms if r['id']==visit['roomId']),None)
 if room is None:raise ValueError('Unknown room in spatial visit: '+str(visit['roomId']))
 if visit.get('pointMm') is not None:
  p=visit['pointMm'];reasons=explain_point(planner,p)
  if reasons:raise SpatialBlocked('Blocked station '+visit['name']+' '+str(p)+': '+reasons[0]['code'],{'visit':visit['name'],'pointMm':p,'reasons':reasons})
  return [{'point':p,'viewFraction':None,'source':'explicit_point'}],room,None
 anchor=anchor_of(bundle,room,visit);samples=room_samples(room);depth=visit.get('stationDepthMm',500)
 xs=[p[0] for p in room['poly']];ys=[p[1] for p in room['poly']];step=planner.grid*3;rows=[]
 for i in range(int(min(xs)//step),int(max(xs)//step)+2):
  for j in range(int(min(ys)//step),int(max(ys)//step)+2):
   p=[i*step,j*step];k=(i*3,j*3)
   if not inside(p,room['poly']) or not planner.free(k):continue
   if any(dist_segment(p,g['a'],g['b'])<depth for g in all_gates):continue
   if anchor:
    d=furniture_box_distance(anchor,p)
    if not visit['anchor'].get('minimumMm',400)<=d<=visit['anchor'].get('maximumMm',1800) or not ray_clear(planner,p,[anchor['cx'],anchor['cy']]):continue
   rows.append(p)
 if not rows:raise SpatialBlocked('No walkable station candidates for '+visit['name'],{'visit':visit['name'],'roomId':room['id'],'bodyRadiusMm':planner.radius,'anchor':anchor and anchor['id']})
 rows=rows[::max(1,len(rows)//60)];scored=[]
 gates=room_gates(room,all_gates)
 entry=lambda p:min((dist_segment(p,g['a'],g['b']) for g in gates),default=None)
 for p in rows:scored.append({'point':p,'viewFraction':sum(ray_clear(planner,p,q) for q in samples)/max(1,len(samples)),'source':'room_geometry','entryDepthMm':None if not gates else round(entry(p))})
 # Shallow stations: stand just inside the door instead of at the middle of the room. A room whose depth limit
 # cannot be met keeps its shallowest candidates and says so, never fails the plan.
 limit_mm=visit.get('maxEntryDepthMm')
 if limit_mm is not None and gates:
  near=[c for c in scored if c['entryDepthMm']<=limit_mm]
  if not near:
   floor=min(c['entryDepthMm'] for c in scored);near=[c for c in scored if c['entryDepthMm']<=floor+200]
   for c in near:c['depthLimitRelaxed']=True
  scored=near
 # Farthest-first keeps real alternatives across the room, not one cluster near a corner.
 top=max(c['viewFraction'] for c in scored);pool=[c for c in scored if c['viewFraction']>=top-.1]
 cx=sum(c['point'][0] for c in pool)/len(pool);cy=sum(c['point'][1] for c in pool)/len(pool)
 picked=[min(pool,key=lambda c:(math.dist(c['point'],(cx,cy)),c['point']))]
 while len(picked)<limit:
  c=max(pool,key=lambda c:(min(math.dist(c['point'],x['point']) for x in picked),c['point']))
  if min(math.dist(c['point'],x['point']) for x in picked)<480:break
  picked.append(c)
 return picked,room,anchor

def entrance_view(bundle,opening_id,start,rooms,all_gates):
 """The room and sight line a person gets on stepping through the actual door."""
 gate=next(g for g in all_gates if g['id']==opening_id);mid=[(gate['a'][k]+gate['b'][k])/2 for k in (0,1)]
 dx,dy=gate['b'][0]-gate['a'][0],gate['b'][1]-gate['a'][1];l=math.hypot(dx,dy);n=[-dy/l,dx/l]
 if sum((start[k]-mid[k])*n[k] for k in (0,1))>0:n=[-n[0],-n[1]]
 for depth in (300,600,900):
  point=[mid[k]+n[k]*(gate['halfThicknessMm']+depth) for k in (0,1)];room=locate(rooms,all_gates,point)
  if not room.startswith('opening:') and room!='exterior':return {'room':room,'pointMm':point,'axis':n}
 return {'room':None,'pointMm':[mid[k]+n[k]*(gate['halfThicknessMm']+300) for k in (0,1)],'axis':n}

def choose_order(planner,start,end,visits,candidates,deadline,view,tie_ratio=.05):
 """Shortest loop, entry room first; near-equal directions go by what the door shows first."""
 from design_homeowner_tour import order_groups
 if len(visits)>12:raise ValueError('Shortest order supports 1..12 visits; give a fixed order for more')
 anchors={v['name']:candidates[v['name']][0]['point'] for v in visits};fields={}
 def distance(a,b):
  pa=start if a=='__start__' else end if a=='__end__' else anchors[a];pb=end if b=='__end__' else start if b=='__start__' else anchors[b]
  ka,kb=planner.nearest(pa),planner.nearest(pb)
  if ka not in fields:fields[ka]=field(planner,ka,[planner.nearest(anchors[n]) for n in anchors]+[planner.nearest(start),planner.nearest(end)],deadline)[0]
  if kb not in fields[ka]:raise SpatialBlocked('No walkable connection between '+a+' and '+b,{'from':a,'to':b,'bodyRadiusMm':planner.radius,'openings':opening_passability(planner,gates(planner.b))})
  return fields[ka][kb]*planner.grid
 inside_entry=[v['name'] for v in visits if v['roomId']==view['room']]
 first=min(inside_entry,key=lambda n:math.dist(anchors[n],view['pointMm'])) if inside_entry else None
 stages=[0 if v['name']==first else 1 for v in visits] if first else None
 names,_=order_groups('__start__',[[v['name']] for v in visits],distance,return_to='__end__',stages=stages)
 def total(order):
  chain=['__start__']+order+['__end__'];return sum(distance(a,b) for a,b in zip(chain,chain[1:]))
 tail=names[1:] if first else names;other=([first] if first else [])+tail[::-1]
 def seen(order):
  target=anchors[(order[1:] if first else order)[0]] if (order[1:] if first else order) else view['pointMm']
  dx,dy=target[0]-view['pointMm'][0],target[1]-view['pointMm'][1];l=math.hypot(dx,dy) or 1
  return (0 if ray_clear(planner,view['pointMm'],target) else 1,round(math.acos(max(-1,min(1,(dx*view['axis'][0]+dy*view['axis'][1])/l))),4))
 length,alternative=total(names),total(other);chosen=names;basis='shortest_walk'
 if other!=names and alternative<=length*(1+tie_ratio) and length<=alternative*(1+tie_ratio):
  chosen=min((names,other),key=lambda o:(seen(o),total(o)));basis='first_seen_from_entrance'
 by={v['name']:v for v in visits}
 return [by[n] for n in chosen],{'rule':'Shortest loop; entry room first; directions within the tie ratio are decided by what is visible straight ahead from the door','entryRoomId':view['room'],'firstVisit':first,'basis':basis,'tieRatio':tie_ratio,'chosenLengthM':round(total(chosen)/1000,2),'reverseLengthM':round(total(other if chosen==names else names)/1000,2)}

def locate(rooms,all_gates,p):
 for r in rooms:
  if inside(p,r['poly']):return r['id']
 for g in all_gates:
  if dist_segment(p,g['a'],g['b'])<=g['halfThicknessMm']+35:return 'opening:'+g['id']
 return 'exterior'

def room_exits(planner,rooms,all_gates):
 """Clusters of free grid edges leaving each room: evidence for single-door branches."""
 result={}
 for r in rooms:
  xs=[p[0] for p in r['poly']];ys=[p[1] for p in r['poly']];g=planner.grid;edges=[]
  for i in range(int(min(xs)//g)-2,int(max(xs)//g)+3):
   for j in range(int(min(ys)//g)-2,int(max(ys)//g)+3):
    k=(i,j)
    if not planner.free(k) or not inside(planner.point(k),r['poly']):continue
    for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
     n=(i+dx,j+dy)
     if planner.free(n) and not inside(planner.point(n),r['poly']):edges.append(n)
  clusters=[]
  for n in sorted(set(edges)):
   hit=[c for c in clusters if any(abs(n[0]-m[0])<=2 and abs(n[1]-m[1])<=2 for m in c)]
   merged=[n]
   for c in hit:merged+=c;clusters.remove(c)
   clusters.append(merged)
  exits=[]
  for c in clusters:
   centre=[sum(planner.point(n)[k] for n in c)/len(c) for k in (0,1)]
   near=[g2['id'] for g2 in all_gates if dist_segment(centre,g2['a'],g2['b'])<=g2['halfThicknessMm']+planner.grid*3]
   exits.append({'via':near[0] if near else 'open_boundary','centreMm':[round(v) for v in centre]})
  result[r['id']]={'exitCount':len(exits),'exits':exits,'singleExit':len(exits)==1}
 return result

def resample(points,step=100):
 out=[];total=0
 for a,b in zip(points,points[1:]):
  l=math.dist(a,b);n=max(1,math.ceil(l/step))
  for i in range(n):out.append(([a[k]+(b[k]-a[k])*i/n for k in (0,1)],total+l*i/n))
  total+=l
 out.append((points[-1],total));return out

def retraces(planner,points,rooms,all_gates,deadline,tolerance=200,gap=1500,minimum=500):
 """Report path reuse; test whether it was forced by removing the earlier corridor."""
 samples=resample(points);buckets={};flags=[]
 for i,(p,d) in enumerate(samples):
  key=(int(p[0]//tolerance),int(p[1]//tolerance));hit=None
  for x in range(key[0]-1,key[0]+2):
   for y in range(key[1]-1,key[1]+2):
    for q,e,j in buckets.get((x,y),[]):
     if d-e>=gap and math.dist(p,q)<=tolerance:hit=j;break
    if hit is not None:break
   if hit is not None:break
  flags.append(hit);buckets.setdefault(key,[]).append((p,d,i))
 chunks=[];i=0
 while i<len(samples):
  if flags[i] is None:i+=1;continue
  j=i
  while j+1<len(samples) and flags[j+1] is not None:j+=1
  if samples[j][1]-samples[i][1]>=minimum:chunks.append((i,j))
  i=j+1
 rows=[]
 for i,j in chunks:
  earlier=[samples[flags[n]][0] for n in range(i,j+1)];a,b=samples[i][0],samples[j][0];forbidden=set()
  for q in earlier:
   cx,cy=round(q[0]/planner.grid),round(q[1]/planner.grid);span=math.ceil(tolerance/planner.grid)
   for x in range(cx-span,cx+span+1):
    for y in range(cy-span,cy+span+1):
     p=planner.point((x,y))
     if math.dist(p,q)<=tolerance and math.dist(p,a)>300 and math.dist(p,b)>300:forbidden.add((x,y))
  section=[samples[n][0] for n in range(i,j+1)];visited=[locate(rooms,all_gates,p) for p in section];openings=sorted({v[8:] for v in visited if v.startswith('opening:')})
  row={'startMm':[round(v) for v in a],'endMm':[round(v) for v in b],'lengthM':round((samples[j][1]-samples[i][1])/1000,3),'rooms':sorted({v for v in visited if not v.startswith('opening:')}),'openings':openings}
  try:
   ka,kb=planner.nearest(a),planner.nearest(b);best,_=field(planner,ka,[kb],deadline,forbidden)
   if kb in best:row.update(classification='alternative_exists',alternativeLengthM=round(best[kb]*planner.grid/1000,3))
   else:row.update(classification='required_bottleneck')
  except ValueError:row.update(classification='not_evaluated')
  rows.append(row)
 return rows

def self_crossings(points):
 rows=[]
 for i in range(len(points)-1):
  for j in range(i+2,len(points)-1):
   if crosses(points[i],points[i+1],points[j],points[j+1]):rows.append({'segments':[i,j],'nearMm':[round(v) for v in points[i+1]]})
 return rows

ZONE_TYPES=(('vanity','洗手台'),('sofa','客厅'),('table','餐厅'))
def auto_visits(bundle):
 """One visit per room; a room holding several functions is split at its actual furniture."""
 out=[]
 for room in bundle['model']['rooms']:
  found=[(t,name) for t,name in ZONE_TYPES if any(f['type']==t and inside([f['cx'],f['cy']],room['poly']) for f in bundle['state']['furniture'])]
  if len(found)>=2:out+=[{'name':name,'roomId':room['id'],'anchor':{'furnitureTypes':[t]},'autoZone':True} for t,name in found]
  else:out.append({'name':room.get('name') or room['id'],'roomId':room['id']})
 names=[v['name'] for v in out]
 for v in out:
  if names.count(v['name'])>1:v['name']+=' '+v['roomId']
 return out

def exterior_start(bundle,opening_id,radius):
 """Nearest clear exterior point on the door's axis, outside the footprint."""
 from design_homeowner_tour import entry_apron
 gate=next((g for g in gates(bundle) if g['id']==opening_id),None)
 if gate is None or gate['kind']!='door':raise ValueError('Entrance must be an actual door: '+str(opening_id))
 mid=[(gate['a'][k]+gate['b'][k])/2 for k in (0,1)];dx,dy=gate['b'][0]-gate['a'][0],gate['b'][1]-gate['a'][1];l=math.hypot(dx,dy);n=[-dy/l,dx/l]
 for depth in range(300,1300,100):
  for side in (1,-1):
   p=[round(mid[k]+side*n[k]*(gate['halfThicknessMm']+radius+depth)) for k in (0,1)]
   if inside(p,bundle['model']['footprint']):continue
   access,_=entry_apron(bundle,{'entranceOpeningId':opening_id,'startPoint':p,'bodyRadiusMm':radius})
   if not explain_point(Planner(bundle,{'bodyRadiusMm':radius,'gridMm':80,'accessPolygons':access}),p):return p
 raise ValueError('No clear exterior point at entrance '+str(opening_id)+': both sides are inside the footprint or blocked. Check the entrance record or give startPoint with its evidence')

def fill_defaults(job,base):
 """Minimal job: bundle plus the case that records its entrance. Filled values are reported."""
 job=dict(job);auto=[]
 if job.get('schema')!='homeowner-spatial-job/1':return job,auto
 b=read(source_path(job.get('bundle'),base))
 if not job.get('entranceOpeningId'):
  if not job.get('caseFile'):raise ValueError('Give entranceOpeningId or caseFile; the entrance is never guessed from geometry')
  case=source_path(job['caseFile'],base);entrances=read(case).get('entranceOpenings',[])
  if len(entrances)!=1:raise ValueError('Case must record exactly one entrance opening; found '+str(entrances))
  job.update(entranceOpeningId=entrances[0],entranceSource=str(case)+' entranceOpenings');auto.append('entrance')
 if job.get('startPoint') is None:
  job['startPoint']=exterior_start(b,job['entranceOpeningId'],job.get('bodyRadiusMm',180));auto.append('startPoint')
 if job.get('visits') is None:
  job['visits']=auto_visits(b);job.setdefault('order',{'mode':'shortest'});auto.append('visits')
 return job,auto

def source_path(record,base):
 """Hash-checked when the job binds a hash; a plain path is bound by the plan itself."""
 if isinstance(record,dict) and record.get('sha256'):return resolve(record,base)
 value=record.get('path') if isinstance(record,dict) else record
 if not isinstance(value,str) or not value:raise ValueError('Missing spatial job file reference')
 p=Path(value);p=(p if p.is_absolute() else Path(base)/p).resolve()
 if not p.is_file():raise ValueError('Missing spatial job file: '+str(p))
 return p

def validate_job(job):
 if job.get('schema')!='homeowner-spatial-job/1':raise ValueError('Explicit spatial job required')
 for key in ('frames','cameraKeys','seedTour','seedConfig','tour'):
  if key in job:raise ValueError('Spatial job must not contain camera or frame data: '+key)
 visits=job.get('visits')
 if not isinstance(visits,list) or not 1<=len(visits)<=32:raise ValueError('Require 1..32 ordered visits')
 names=[v.get('name') for v in visits]
 if not all(isinstance(n,str) and n.strip() for n in names) or len(set(names))!=len(names):raise ValueError('Visits require unique names')
 for v in visits:
  if not isinstance(v.get('roomId'),str):raise ValueError('Visit requires roomId: '+v['name'])
  if v.get('pointMm') is not None and not finite(v['pointMm']):raise ValueError('Invalid visit point: '+v['name'])
 radius=job.get('bodyRadiusMm',180);grid=job.get('gridMm',80)
 if not isinstance(radius,(int,float)) or isinstance(radius,bool) or not MIN_BODY_RADIUS_MM<=radius<=400:raise ValueError('bodyRadiusMm must stay within 160..400; never shrink it to pass')
 if not isinstance(grid,(int,float)) or isinstance(grid,bool) or not 40<=grid<=200:raise ValueError('gridMm must be within 40..200')
 if not finite(job.get('startPoint')):raise ValueError('Exterior startPoint required')
 end=job.get('endPoint',job['startPoint'])
 if not finite(end):raise ValueError('Invalid endPoint')
 if math.dist(end,job['startPoint'])>1 and not str(job.get('openEndReason','')).strip():raise ValueError('A full tour returns to its entrance; give openEndReason for another exit')
 if not str(job.get('entranceSource','')).strip():raise ValueError('entranceSource must cite where the actual entrance opening was confirmed')
 order=job.get('order',{}).get('mode')
 if order not in ('fixed','shortest'):raise ValueError('order.mode must be fixed or shortest')
 if order=='fixed' and not str(job['order'].get('source','')).strip():raise ValueError('A fixed order must cite its source')
 limit=job.get('search',{}).get('maximumPlanningSeconds',180)
 if isinstance(limit,bool) or not isinstance(limit,(int,float)) or not 0<limit<=900:raise ValueError('Bounded planning deadline required')
 count=job.get('search',{}).get('candidatesPerVisit',5)
 if isinstance(count,bool) or not isinstance(count,int) or not 1<=count<=12:raise ValueError('Bounded candidatesPerVisit required')
 envelope={**ENVELOPE,**job.get('cameraEnvelope',{})}
 if not all(isinstance(envelope[k],(int,float)) and not isinstance(envelope[k],bool) and envelope[k]>0 for k in ENVELOPE) or envelope['maximumLengthRatio']<1:raise ValueError('Invalid cameraEnvelope')
 return radius,grid,end,limit,count,envelope

def build(job,base='.'):
 base=Path(base).resolve();job,filled=fill_defaults(job,base);started=time.monotonic();radius,grid,end,limit,count,envelope=validate_job(job);deadline=started+limit
 bundle=source_path(job.get('bundle'),base);b=read(bundle)
 if not isinstance(b.get('schemeSha256'),str) or len(b['schemeSha256'])!=64:raise ValueError('Bundle needs a scheme hash')
 from design_homeowner_tour import entry_apron
 start=job['startPoint'];opening=job.get('entranceOpeningId')
 access,_=entry_apron(b,{'entranceOpeningId':opening,'startPoint':start,'bodyRadiusMm':radius})
 if math.dist(start,end)>1:access+=entry_apron(b,{'entranceOpeningId':opening,'startPoint':end,'bodyRadiusMm':radius})[0]
 planner=Planner(b,{'bodyRadiusMm':radius,'gridMm':grid,'accessPolygons':access});all_gates=gates(b);rooms=b['model']['rooms']
 for label,p in (('start',start),('end',end)):
  reasons=explain_point(planner,p)
  if reasons:raise SpatialBlocked('Blocked '+label+' '+str(p)+': '+reasons[0]['code'],{'point':label,'pointMm':p,'reasons':reasons,'accessPolygons':access})
 visits=job['visits'];candidates={};meta={};dropped=[]
 default_depth=job.get('maxEntryDepthMm')
 if default_depth is not None:
  if isinstance(default_depth,bool) or not isinstance(default_depth,(int,float)) or not 300<=default_depth<=4000:raise ValueError('maxEntryDepthMm must stay within 300..4000')
  for v in visits:v.setdefault('maxEntryDepthMm',default_depth)
 for v in visits:
  m=v.get('maxEntryDepthMm')
  if m is not None and (isinstance(m,bool) or not isinstance(m,(int,float)) or not 300<=m<=4000):raise ValueError('maxEntryDepthMm must stay within 300..4000: '+v['name'])
 for v in visits:
  try:rows,room,anchor=station_candidates(b,planner,v,count,all_gates)
  except SpatialBlocked as error:
   if 'visits' not in filled:raise
   dropped.append({'roomId':v['roomId'],'name':v['name'],'reason':'自动判定：无可站立位置（'+str(error)+'）'});continue
  candidates[v['name']]=rows;meta[v['name']]=(room,anchor)
 origin=planner.nearest(start);reach,_=field(planner,origin,[planner.nearest(c['point']) for rows in candidates.values() for c in rows]+[planner.nearest(end)],deadline)
 if planner.nearest(end) not in reach:raise SpatialBlocked('No walkable connection: start -> end',{'bodyRadiusMm':radius,'openings':opening_passability(planner,all_gates)})
 for v in visits:
  # A free cell can be an isolated pocket between furniture; only connected floor is a station.
  if v['name'] not in candidates:continue
  rows=[c for c in candidates[v['name']] if planner.nearest(c['point']) in reach]
  if not rows and 'visits' in filled:
   dropped.append({'roomId':v['roomId'],'name':v['name'],'reason':'自动判定：与入口不连通，请核对门洞'});del candidates[v['name']];continue
  if not rows:raise SpatialBlocked('No station connected to the entrance: '+v['name'],{'visit':v['name'],'roomId':v['roomId'],'bodyRadiusMm':radius,'isolatedCandidates':[c['point'] for c in candidates[v['name']]],'openings':opening_passability(planner,all_gates)})
  candidates[v['name']]=rows
 visits=[v for v in visits if v['name'] in candidates];order_detail=None
 if not visits:raise SpatialBlocked('No visitable room',{'dropped':dropped})
 if job['order']['mode']=='shortest':visits,order_detail=choose_order(planner,start,end,visits,candidates,deadline,entrance_view(b,opening,start,rooms,all_gates),job.get('search',{}).get('directionTieRatio',.05))
 penalty=job.get('search',{}).get('viewPenaltyMm',2500)
 layers=[[{'point':start,'viewFraction':None}]]+[candidates[v['name']] for v in visits]+[[{'point':end,'viewFraction':None}]]
 reuse=job.get('search',{}).get('reuseWeight',2);span=max(1,round(240/grid))
 # Forward states keep their own walked corridor, so reuse is a cost, never a hard ban:
 # a single-door branch still returns through its door when no other way exists.
 opening_cells=[gate_cells(planner,g) for g in all_gates];gate_cost=job.get('search',{}).get('openingRepeatMm',4000)/grid/max(1,round(200/grid))
 states=[{0:{'cost':0.,'previous':None,'corridor':set(),'gates':set(),'grid':None}}]
 for depth in range(1,len(layers)):
  row={};targets=[planner.nearest(c['point']) for c in layers[depth]]
  for i,state in states[-1].items():
   src=layers[depth-1][i];key=planner.nearest(src['point']);best,came=field(planner,key,targets,deadline,reused=state['corridor'],reuse_weight=reuse,reused_gates=state['gates'],gate_cost=gate_cost)
   for j,c in enumerate(layers[depth]):
    t=targets[j]
    if t not in best:continue
    total=state['cost']+best[t]*grid+math.dist(src['point'],planner.point(key))+math.dist(c['point'],planner.point(t))+(0 if c['viewFraction'] is None else (1-c['viewFraction'])*penalty)
    if total<row.get(j,{'cost':math.inf})['cost']:row[j]={'cost':total,'previous':i,'grid':trace(came,t),'source':state}
  if not row:
   source=visits[depth-2]['name'] if depth>1 else 'start';target=visits[depth-1]['name'] if depth<=len(visits) else 'end'
   raise SpatialBlocked('No walkable connection: '+source+' -> '+target,{'from':source,'to':target,'bodyRadiusMm':radius,'openings':opening_passability(planner,all_gates)})
  for value in row.values():
   origin=value.pop('source');walked=set(value['grid']);value['corridor']=origin['corridor']|corridor(walked,span);value['gates']=origin['gates']|{c for cells in opening_cells if cells&walked for c in cells}
  states.append(row)
 chosen=[0]*len(layers)
 for depth in range(len(layers)-1,0,-1):chosen[depth-1]=states[depth][chosen[depth]]['previous']
 picks=[layers[d][chosen[d]] for d in range(len(layers))];labels=['入户']+[v['name'] for v in visits]+['出户'];legs=[];route=[]
 for d in range(len(picks)-1):
  a,z=picks[d]['point'],picks[d+1]['point']
  raw=[a]+[list(planner.point(k)) for k in states[d+1][chosen[d+1]]['grid']]+[z]
  points=[list(map(float,p)) for p in planner.simplify(turning_points(raw))]
  if any(not planner.line_free(x,y) for x,y in zip(points,points[1:])):raise SpatialBlocked('Unsafe spatial edge: '+labels[d]+' -> '+labels[d+1],{'pointsMm':points})
  through=[g['id'] for x,y in zip(points,points[1:]) for g in all_gates if crosses(x,y,g['a'],g['b'])]
  legs.append({'from':labels[d],'to':labels[d+1],'pointsMm':points,'distanceM':polyline_length(points)/1000,'openings':through})
  route+=points if not route else points[1:]
 distance=polyline_length(route)/1000
 issues=[];excluded={r['roomId']:r.get('reason') for r in job.get('excludedRooms',[])+dropped};stations=[]
 for v,pick in zip(visits,picks[1:-1]):
  room,anchor=meta[v['name']]
  if not inside(pick['point'],room['poly']):issues.append({'code':'station_outside_room','visit':v['name']})
  stations.append({'name':v['name'],'roomId':v['roomId'],'roomName':room.get('name'),'pointMm':[round(x,1) for x in pick['point']],'roomPolygon':room['poly'],'anchor':anchor and anchor['id'],'stationSource':pick.get('source'),'entryDepthMm':pick.get('entryDepthMm'),'maxEntryDepthMm':v.get('maxEntryDepthMm'),'depthLimitRelaxed':bool(pick.get('depthLimitRelaxed')),'wallViewFraction2D':pick['viewFraction'] if pick['viewFraction'] is None else round(pick['viewFraction'],2)})
 missing=[r['id'] for r in rooms if r['id'] not in {v['roomId'] for v in visits} and r['id'] not in excluded and not any(inside(p,r['poly']) for p,_ in resample(route))]
 for roomId in missing:issues.append({'code':'room_not_visited','roomId':roomId})
 if any(not str(v or '').strip() for v in excluded.values()):issues.append({'code':'exclusion_without_reason'})
 if opening not in legs[0]['openings']:issues.append({'code':'entrance_not_crossed','opening':opening})
 if opening not in legs[-1]['openings'] and math.dist(start,end)<=1:issues.append({'code':'exit_not_crossed','opening':opening})
 sequence=[g for leg in legs for g in leg['openings']];crossing=self_crossings(route);exits=room_exits(planner,rooms,all_gates);returns=retraces(planner,route,rooms,all_gates,deadline)
 visited={v['roomId'] for v in visits}
 for row in returns:
  branch=[x for x in row['rooms'] if x in visited and exits.get(x,{}).get('singleExit')]
  if branch and row['classification']!='required_bottleneck':row.update(classification='required_single_exit_branch',branchRooms=branch)
 budget=job.get('budget',{});speed=budget.get('walkSpeedMps',.5);view=budget.get('observeSecondsPerVisit',2);rough=distance/speed+view*len(visits)
 result={'schema':PLAN_SCHEMA,'bundle':bound(bundle),'schemeSha256':b['schemeSha256'],'caseId':b.get('caseId'),'title':b['model'].get('title'),'schemeConfirmations':{k:v.get('status') for k,v in b.get('confirmations',{}).items()},
  'navigation':{'bodyRadiusMm':radius,'gridMm':grid},'entrance':{'openingId':opening,'source':job['entranceSource'],'startPointMm':start,'endPointMm':end,'accessPolygons':access,'accessScope':'Declared exterior apron at the actual door; not modelled corridor geometry'},
  'order':{'mode':job['order']['mode'],'source':job['order'].get('source','engine proposal; needs user confirmation'),'direction':order_detail},
  'stations':stations,'legs':legs,'routeMm':route,'distanceM':distance,'openingSequence':sequence,'openings':all_gates,'roomExits':exits,'retraces':returns,'selfCrossings':crossing,'excludedRooms':job.get('excludedRooms',[])+dropped,'autoFilled':filled,
  'budget':{'estimatedSeconds':round(rough,1),'walkSpeedMps':speed,'observeSecondsPerVisit':view,'maximumSeconds':budget.get('maximumSeconds'),'scope':'Rough estimate only; not a confirmed film duration','overEstimate':bool(budget.get('maximumSeconds') and rough>budget['maximumSeconds'])},
  'cameraEnvelope':envelope,'issues':issues,'status':'pending_user_confirmation' if not issues else 'needs_revision','cameraGenerated':False,'framesGenerated':False,'videoGenerated':False,'approvalGranted':False,'elapsedSeconds':round(time.monotonic()-started,2),
  'optimalityScope':'Shortest grid walk across bounded station candidates for this order; not a certificate of global optimum. Station view is a 2D wall proxy.'}
 return result

def conformance(plan,tour):
 """Camera stage stays inside the approved route: order, openings, deviation and length."""
 e=plan['cameraEnvelope'];route=plan['routeMm'];frames=[f['pointMm'] for f in tour['frames']];issues=[]
 if tour.get('schemeSha256')!=plan['schemeSha256']:issues.append({'code':'spatial_scheme_mismatch'})
 stride=max(1,round(tour.get('fps',24)/4));worst=0;outside=[]
 for p in frames[::stride]+frames[-1:]:
  d=min(dist_segment(p,a,b) for a,b in zip(route,route[1:]));worst=max(worst,d)
  allowed=e['visitedRoomDeviationMm'] if any(inside(p,s['roomPolygon']) for s in plan['stations']) else e['maximumDeviationMm']
  if d>allowed:outside.append({'pointMm':[round(v) for v in p],'deviationMm':round(d),'allowedMm':allowed})
 if outside:issues.append({'code':'spatial_route_deviation','count':len(outside),'samples':outside[:6]})
 length=polyline_length(frames);ratio=length/max(1,polyline_length(route))
 if ratio>e['maximumLengthRatio']:issues.append({'code':'spatial_route_length','ratio':round(ratio,3),'allowed':e['maximumLengthRatio']})
 sequence=[]
 for a,b in zip(frames,frames[1:]):
  for g in plan['openings']:
   if crosses(a,b,g['a'],g['b']):sequence.append(g['id'])
 if sequence!=plan['openingSequence']:issues.append({'code':'spatial_opening_sequence','approved':plan['openingSequence'],'actual':sequence})
 cursor=0
 for s in plan['stations']:
  hit=next((i for i in range(cursor,len(frames)) if math.dist(frames[i],s['pointMm'])<=e['stationToleranceMm']),None)
  if hit is None:issues.append({'code':'spatial_visit_order','visit':s['name']});continue
  cursor=hit
 if frames and math.dist(frames[0],plan['entrance']['startPointMm'])>e['stationToleranceMm']:issues.append({'code':'spatial_entrance_changed'})
 if frames and math.dist(frames[-1],plan['entrance']['endPointMm'])>e['stationToleranceMm']:issues.append({'code':'spatial_exit_changed'})
 return {'schema':'homeowner-spatial-conformance/1','status':'pass' if not issues else 'return_to_route_confirmation','issues':issues,'maximumDeviationMm':round(worst,1),'lengthRatio':round(ratio,4),'openingSequence':sequence}

def require_approval(approval,plan,bundle=None):
 """Real stage-one gate: explicit user words bound to this plan, page and bundle."""
 p=Path(approval).resolve();r=read(p);base=p.parent
 source=r.get('approvalSource')
 if ALLOW_SYNTHETIC_FOR_TESTS and source=='synthetic_test_fixture':pass
 elif source!='explicit_user_confirmation' or any(word in str(r.get('confirmedBy','')).lower() for word in NON_SIGNERS):raise ValueError('Explicit spatial route confirmation by the actual user required; agents and fixtures cannot sign')
 if r.get('schema')!=APPROVAL_SCHEMA or r.get('status')!='approved' or not all(str(r.get(k,'')).strip() for k in ('confirmedBy','evidence')):raise ValueError('Explicit spatial route confirmation required')
 if any(r.get('checks',{}).get(k) is not True for k in CHECKS):raise ValueError('Incomplete spatial approval')
 plan_path=resolve(r.get('plan'),base)
 if plan is not None and bound(plan_path)['sha256']!=bound(plan)['sha256']:raise ValueError('Changed spatial plan')
 value=read(plan_path)
 if value.get('schema')!=PLAN_SCHEMA:raise ValueError('Invalid spatial plan')
 if value.get('status')!='pending_user_confirmation':raise ValueError('Spatial plan has unresolved issues and cannot be approved: '+str(value.get('status')))
 source_bundle=resolve(r.get('bundle'),base)
 if value['bundle']['sha256']!=bound(source_bundle)['sha256']:raise ValueError('Spatial plan belongs to a different bundle')
 if bundle is not None and bound(bundle)['sha256']!=value['bundle']['sha256']:raise ValueError('Changed spatial bundle')
 if read(source_bundle).get('schemeSha256')!=value['schemeSha256']:raise ValueError('Spatial plan scheme identity mismatch')
 page=r.get('presentedPage')
 if not page:raise ValueError('Approval must identify the displayed route page')
 resolve(page,base)
 return value

def page(plan,image=None,bounds=None):
 """Static SVG from the same plan data; no player, camera or timing presentation."""
 from tour_pages import fill,theme,navigation,ASSETS
 b=read(plan['bundle']['path']);xs=[p[0] for p in b['model']['footprint']]+[p[0] for p in plan['routeMm']];ys=[p[1] for p in b['model']['footprint']]+[p[1] for p in plan['routeMm']];margin=500
 view=bounds or [min(xs)-margin,min(ys)-margin,max(xs)-min(xs)+2*margin,max(ys)-min(ys)+2*margin]
 parts=[f'<svg xmlns="http://www.w3.org/2000/svg" role="img" aria-label="平面路线" viewBox="{view[0]} {view[1]} {view[2]} {view[3]}" style="width:100%;max-height:78vh;background:#fff;display:block">']
 if image:parts.append(f'<image x="{view[0]}" y="{view[1]}" width="{view[2]}" height="{view[3]}" href="{html.escape(image)}"/>')
 else:
  for r in b['model']['rooms']:parts.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in r['poly'])+'" fill="#f5f1ea" stroke="#d6cfc2" stroke-width="12"/>')
  for f in b['state']['furniture']:
   if f.get('elevation',0)<=1100 and f.get('w',0)>=300 and f.get('d',0)>=300:parts.append(f'<rect x="{f["cx"]-f["w"]/2}" y="{f["cy"]-f["d"]/2}" width="{f["w"]}" height="{f["d"]}" transform="rotate({f.get("rot",0)} {f["cx"]} {f["cy"]})" fill="#e7e0d3" stroke="#bdb3a2" stroke-width="8"/>')
  for w in b['state']['walls']:
   if not w.get('demolished'):parts.append(f'<line x1="{w["a"][0]}" y1="{w["a"][1]}" x2="{w["b"][0]}" y2="{w["b"][1]}" stroke="#5d564c" stroke-width="{w["t"]}" opacity=".55"/>')
  for g in plan['openings']:parts.append(f'<line x1="{g["a"][0]}" y1="{g["a"][1]}" x2="{g["b"][0]}" y2="{g["b"][1]}" stroke="#fff" stroke-width="{g["halfThicknessMm"]*2+10}"/>')
 line=' '.join(f'{x},{y}' for x,y in plan['routeMm']);parts.append(f'<polyline points="{line}" fill="none" stroke="#fff" stroke-width="90" stroke-linejoin="round"/><polyline points="{line}" fill="none" stroke="#27788b" stroke-width="46" stroke-linejoin="round"/>')
 colors={'required_bottleneck':'#b77c39','required_single_exit_branch':'#b77c39','alternative_exists':'#c0483b','not_evaluated':'#c0483b'}
 for row in plan['retraces']:parts.append(f'<circle cx="{(row["startMm"][0]+row["endMm"][0])/2}" cy="{(row["startMm"][1]+row["endMm"][1])/2}" r="110" fill="{colors[row["classification"]]}" opacity=".8"/>')
 marks=[('入',plan['entrance']['startPointMm'])]+[(str(i+1),s['pointMm']) for i,s in enumerate(plan['stations'])]
 for label,p in marks:parts.append(f'<circle cx="{p[0]}" cy="{p[1]}" r="170" fill="#94623e" stroke="#fff" stroke-width="30"/><text x="{p[0]}" y="{p[1]+70}" text-anchor="middle" font-size="200" fill="#fff" font-family="system-ui,sans-serif">{label}</text>')
 parts.append('</svg>')
 rows=''.join(f'<tr><td>{html.escape(leg["from"])} → {html.escape(leg["to"])}</td><td>{leg["distanceM"]:.1f} 米</td></tr>' for leg in plan['legs'])
 words={'required_bottleneck':'必经往返','required_single_exit_branch':'单出口房间必要往返','alternative_exists':'可调整，待确认','not_evaluated':'未能判定'}
 returns=''.join(f'<li>{words[r["classification"]]}：{" / ".join(html.escape(room_name(b,x)) for x in r["rooms"])}，约 {r["lengthM"]:.1f} 米</li>' for r in plan['retraces']) or '<li>无重复路段</li>'
 issues=''.join('<li>'+html.escape(i['code'])+'</li>' for i in plan['issues'])
 body='<div style="display:grid;grid-template-columns:minmax(0,2fr) minmax(260px,1fr);gap:18px"><div>'+''.join(parts)+'</div><aside><h2>参观顺序</h2><table style="width:100%;font-size:14px">'+rows+f'</table><p>全程约 {plan["distanceM"]:.1f} 米；路径自交 {len(plan["selfCrossings"])} 处；粗略用时约 {plan["budget"]["estimatedSeconds"]:.0f} 秒，非成片时长。</p><h2>重复路段</h2><ul>'+returns+'</ul>'+(('<h2>未走入</h2><ul>'+''.join('<li>'+html.escape(r.get('name') or room_name(b,r['roomId']))+'：'+html.escape(str(r.get('reason')))+'</li>' for r in plan['excludedRooms'])+'</ul>') if plan['excludedRooms'] else '')+(('<h2>需调整</h2><ul>'+issues+'</ul>') if issues else '')+'</aside></div>'
 status='路线待确认' if plan['status']=='pending_user_confirmation' else '路线需调整'
 title=html.escape(str(plan.get('title') or '全屋参观'))
 return fill((ASSETS/'stage-template.html').read_text(),{'TITLE':'参观路线','STYLE':theme()+'@media(max-width:760px){main div[style*="grid-template-columns"]{grid-template-columns:1fr!important}}','CASE_TITLE':title,'NAV':navigation(1),'INTRO':'先确认走向、经过的门和必要往返；此页没有镜头和时间线。','STATUS':status,'BODY':body,'SCRIPTS':''})

def room_name(bundle,room_id):
 return next((r.get('name',room_id) for r in bundle['model']['rooms'] if r['id']==room_id),{'exterior':'门外'}.get(room_id,room_id))

def empty_stage(stage,title,message,case_title):
 from tour_pages import fill,theme,navigation,ASSETS
 return fill((ASSETS/'stage-template.html').read_text(),{'TITLE':title,'STYLE':theme(),'CASE_TITLE':html.escape(str(case_title or '全屋参观')),'NAV':navigation(stage),'INTRO':message,'STATUS':'待准备','BODY':f'<section class="stage-empty"><h2>{title}待准备</h2><p>{message}</p><a href="route.html">返回参观路线 →</a></section>','SCRIPTS':''})

def run(job,base,out):
 out=Path(out).resolve()
 if out.exists():raise ValueError('Fresh spatial output required')
 try:result=build(job,base)
 except SpatialBlocked as error:
  out.mkdir(parents=True);(out/'spatial-diagnostics.json').write_text(json.dumps({'schema':'homeowner-spatial-diagnostics/1','status':'blocked','message':str(error),'details':error.report,'approvalGranted':False},ensure_ascii=False,indent=2));raise ValueError(str(error)+'; inspect '+str(out/'spatial-diagnostics.json'))
 out.mkdir(parents=True);plan=out/'spatial-plan.json';plan.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 image=None
 if job.get('planImage'):
  source=source_path(job['planImage'],base);image='route-plan.png';(out/image).write_bytes(source.read_bytes())
 (out/'route.html').write_text(page(result,image,job.get('planBounds') if image else None),encoding='utf-8');(out/'index.html').write_bytes((out/'route.html').read_bytes())
 for stage,file,title,message in [(2,'preview.html','镜头预演','用户确认路线后，在已确认路线内设计镜头。'),(3,'video.html','视频审阅','镜头预演确认后，再制作完整视频。'),(4,'narrated.html','讲解成片','视频确认后，再加入讲解、音乐和字幕。')]:
  (out/file).write_text(empty_stage(stage,title,message,result.get('title')),encoding='utf-8')
 from tour_pages import validate_presentation
 validate_presentation(out,embed=False)
 pending={'schema':APPROVAL_SCHEMA,'status':'pending','approvalSource':'explicit_user_confirmation','confirmedBy':'','evidence':'','plan':bound(plan),'bundle':result['bundle'],'presentedPage':bound(out/'route.html'),'checks':{k:False for k in CHECKS}}
 (out/'spatial-review.pending.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2),encoding='utf-8')
 from tour_stage_chain import evaluate
 state=evaluate({'bundle':result['bundle'],'spatialPlan':bound(plan),'spatialReview':None},out)
 (out/'stage-state.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
 return result

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--job',required=True);a.add_argument('--out',required=True);v=a.parse_args()
 result=run(read(v.job),Path(v.job).resolve().parent,v.out);print(json.dumps({'status':result['status'],'distanceM':round(result['distanceM'],3)},ensure_ascii=False))
if __name__=='__main__':
 try:main()
 except (ValueError,KeyError,OSError,TimeoutError) as e:raise SystemExit(str(e))
