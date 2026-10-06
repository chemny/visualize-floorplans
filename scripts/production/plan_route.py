"""Collision checked tour from a H5 production bundle; explicit case stops in JSON.
Standard library only. Windows remain obstacles. No teleports or room clips.
"""
import argparse, json, math, heapq
from pathlib import Path

def inside(p,poly):
 x,y=p;on=False
 for (a,b),(c,d) in zip(poly,poly[1:]+poly[:1]):
  if (b>y)!=(d>y) and x<(c-a)*(y-b)/(d-b)+a:on=not on
 return on

def dist_segment(p,a,b):
 dx,dy=b[0]-a[0],b[1]-a[1];t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def endpoint_padding(w,all_walls,end):
 p=w['b'] if end else w['a'];horizontal=abs(w['b'][1]-w['a'][1])<.01;axis=0 if horizontal else 1;other=1-axis;l=math.dist(w['a'],w['b']);out=(1 if end else -1)*(w['b'][axis]-w['a'][axis])/l;pad=0
 for n in all_walls:
  if n is w or n.get('demolished') or horizontal==(abs(n['b'][1]-n['a'][1])<.01):continue
  delta=n['a'][axis]-p[axis]
  if abs(delta)>n['t']/2+.1:continue
  lo,hi=sorted((n['a'][other],n['b'][other]))
  if lo-w['t']/2-.1<=p[other]<=hi+w['t']/2+.1:pad=max(pad,n['t']/2+delta*out)
 return pad

class Planner:
 def __init__(self,bundle,config):
  self.b=bundle;self.cfg=config;self.grid=config.get('gridMm',80);self.radius=config.get('bodyRadiusMm',160);self.rooms=bundle['model']['rooms'];self.walls=[];self.leaves=[];self.furniture=[]
  for w in bundle['state']['walls']:
   if w.get('demolished'):continue
   a,b=w['a'],w['b'];l=math.dist(a,b);v=[(b[i]-a[i])/l for i in (0,1)];at=0
   pad_start=endpoint_padding(w,bundle['state']['walls'],False);pad_end=endpoint_padding(w,bundle['state']['walls'],True)
   openings=[dict(o,**bundle['state'].get('doorStyles',{}).get(o.get('id') or w['id']+':'+str(i),{})) for i,o in enumerate(w['opens'])]
   for o in sorted(openings,key=lambda o:o['at']):
    if o['at']>at:self.walls.append(([a[i]+(at-pad_start if at==0 else at)*v[i] for i in (0,1)],[a[i]+o['at']*v[i] for i in (0,1)],w['t']/2))
    end=o['at']+o['width']
    if o['kind']=='window':self.walls.append(([a[i]+o['at']*v[i] for i in (0,1)],[a[i]+end*v[i] for i in (0,1)],w['t']/2))
    if o['kind']=='sliding':
     n=3 if o.get('leaves')==3 else 2;pw=o['width']/n+min(30,o['width']*.02);opened=max(0,min(1,o.get('slideOpen',0)));direction=-1 if o.get('slideDirection')==-1 else 1
     for i in range(n):
      closed=-o['width']/2+o['width']*(i+.5)/n;target=direction*(o['width']/2-pw/2);along=o['at']+o['width']/2+closed+(target-closed)*opened;track=(i-(n-1)/2)*35
      centre=[a[k]+v[k]*along+[-v[1],v[0]][k]*track for k in (0,1)]
      self.leaves.append(([centre[k]-v[k]*pw/2 for k in (0,1)],[centre[k]+v[k]*pw/2 for k in (0,1)],20))
    if o['kind']=='door':
     inward=[-v[1]*o['swing'],v[0]*o['swing']];reverse=o.get('hingeEnd')=='end';h=end if reverse else o['at'];closed=[x*(-1 if reverse else 1) for x in v];angle=math.radians(o.get('angle',90));leaf=[closed[i]*math.cos(angle)+inward[i]*math.sin(angle) for i in (0,1)];hinge=[a[i]+h*v[i]+inward[i]*(w['t']/2+15)+closed[i]*25 for i in (0,1)]
     if bundle['state'].get('doors',{}).get(w['id']) is False:leaf=closed
     self.leaves.append((hinge,[hinge[i]+leaf[i]*(o['width']-50) for i in (0,1)],20))
    at=end
   if at<l:self.walls.append(([a[i]+(at-pad_start if at==0 else at)*v[i] for i in (0,1)],[b[i]+pad_end*v[i] for i in (0,1)],w['t']/2))
  for f in bundle['state']['furniture']:
   if f.get('planPoint') or f['type'] in ['rug','tv','stove','waterheater','acwall','threshold','skirting','doortrim','windowtrim','waterinlet','drainoutlet','floordrain','transition'] or f.get('elevation',0)>1100:continue
   self.furniture.append(f)
  self.cache={}
 def blocked(self,p):
  r=self.radius
  # Approved openings bridge room polygon insets; union with narrow door/threshold strips.
  domain=inside(p,self.b['model'].get('footprint',[])) or any(inside(p,room['poly']) for room in self.rooms) or any(inside(p,poly) for poly in self.cfg.get('accessPolygons',[]))
  if not domain:
   # Gap within wall thickness at an actual confirmed door/sliding opening only.
   for w in self.b['state']['walls']:
    if w.get('demolished'):continue
    a,b=w['a'],w['b'];l=math.dist(a,b);v=[(b[i]-a[i])/l for i in (0,1)]
    for o in w['opens']:
     if o['kind'] not in ['door','sliding']:continue
     c=[a[i]+o['at']*v[i] for i in (0,1)];d=[a[i]+(o['at']+o['width'])*v[i] for i in (0,1)]
     if dist_segment(p,c,d)<=w['t']/2+35:domain=True
  if not domain:return True
  if any(dist_segment(p,a,b)<t+r for a,b,t in self.walls+self.leaves):return True
  for f in self.furniture:
   a=math.radians(f.get('rot',0));dx,dy=p[0]-f['cx'],p[1]-f['cy'];u=dx*math.cos(a)+dy*math.sin(a);v=-dx*math.sin(a)+dy*math.cos(a)
   if abs(u)<f['w']/2+r and abs(v)<f['d']/2+r:return True
  return False
 def point(self,k):return(k[0]*self.grid,k[1]*self.grid)
 def free(self,k):
  if k not in self.cache:self.cache[k]=not self.blocked(self.point(k))
  return self.cache[k]
 def nearest(self,p):
  k=tuple(round(v/self.grid) for v in p)
  candidates=[(math.dist(p,self.point((k[0]+a,k[1]+b))),(k[0]+a,k[1]+b)) for a in range(-8,9) for b in range(-8,9)];candidates.sort()
  for _,k in candidates:
   if self.free(k):return k
  raise ValueError('No walkable point near '+str(p))
 def line_free(self,a,b):
  n=max(1,math.ceil(math.dist(a,b)/25));return all(not self.blocked([a[k]+(b[k]-a[k])*i/n for k in (0,1)]) for i in range(n+1))
 def astar(self,a,b):
  a=self.nearest(a);b=self.nearest(b);q=[(0,0,a)];came={};cost={a:0}
  while q:
   _,g,k=heapq.heappop(q)
   if g!=cost.get(k):continue
   if k==b:
    out=[self.point(k)]
    while k in came:k=came[k];out.append(self.point(k))
    return out[::-1]
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
    n=(k[0]+dx,k[1]+dy)
    if not self.free(n) or dx and dy and (not self.free((k[0]+dx,k[1])) or not self.free((k[0],k[1]+dy))):continue
    ng=g+math.hypot(dx,dy)
    if ng<cost.get(n,float('inf')):cost[n]=ng;came[n]=k;heapq.heappush(q,(ng+math.dist(n,b),ng,n))
  raise ValueError('Unreachable tour leg '+str((a,b)))
 def simplify(self,pts):
  out=[pts[0]];i=0
  while i<len(pts)-1:
   j=len(pts)-1
   while j>i+1 and not self.line_free(pts[i],pts[j]):j-=1
   out.append(pts[j]);i=j
  return out
 def round(self,pts):
  out=[pts[0]]
  for i in range(1,len(pts)-1):
   a,b,c=pts[i-1:i+2];radius=min(450,math.dist(a,b)*.35,math.dist(b,c)*.35)
   u=[b[k]+(a[k]-b[k])*radius/math.dist(a,b) for k in (0,1)];v=[b[k]+(c[k]-b[k])*radius/math.dist(b,c) for k in (0,1)]
   curve=[[u[k]*(1-t)**2+2*b[k]*t*(1-t)+v[k]*t*t for k in (0,1)] for t in [j/24 for j in range(25)]]
   if all(self.line_free(x,y) for x,y in zip([out[-1]]+curve,curve)):out.extend(curve)
   else:out.append(b)
  out.append(pts[-1]);return out

def apply_camera_cues(frames, fps, cues, max_yaw=35):
 """Explicit observation windows with smooth connections; no camera position edits."""
 if not cues:return
 if not isinstance(fps,(int,float)) or isinstance(fps,bool) or not math.isfinite(fps) or fps<=0 or not isinstance(max_yaw,(int,float)) or isinstance(max_yaw,bool) or not math.isfinite(max_yaw) or max_yaw<=0:raise ValueError('Camera cue fps and yaw limit must be finite and positive')
 last_end=-1
 for cue in cues:
  a,b=cue.get('startSeconds'),cue.get('endSeconds');target=cue.get('targetMm')
  if not isinstance(a,(int,float)) or isinstance(a,bool) or not isinstance(b,(int,float)) or isinstance(b,bool) or not math.isfinite(a+b) or not 0<=a<b<=len(frames)/fps or a<last_end:raise ValueError('Camera cue windows must be finite, ordered and nonoverlapping')
  if not isinstance(target,list) or len(target)!=3 or not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in target):raise ValueError('Camera cue target requires three finite mm coordinates')
  last_end=b
 def angles(f,q):
  dx,dy=q[0]-f['pointMm'][0],q[1]-f['pointMm'][1]
  return math.atan2(dy,dx),max(-math.radians(30),min(math.radians(12),math.atan2(q[2]-f['eyeMm'],math.hypot(dx,dy))))
 desired=[]
 for i,f in enumerate(frames):
  t=i/fps
  active=next((c for c in cues if c['startSeconds']<=t<=c['endSeconds']),None)
  if active:yaw,pitch=angles(f,active['targetMm'])
  elif t<cues[0]['startSeconds']:yaw,pitch=angles(f,cues[0]['targetMm'])
  elif t>cues[-1]['endSeconds']:yaw,pitch=angles(f,cues[-1]['targetMm'])
  else:
   prev=max((c for c in cues if c['endSeconds']<t),key=lambda c:c['endSeconds']);nxt=min((c for c in cues if c['startSeconds']>t),key=lambda c:c['startSeconds'])
   u=(t-prev['endSeconds'])/(nxt['startSeconds']-prev['endSeconds']);u=u*u*(3-2*u)
   a,p=angles(f,prev['targetMm']);b,q=angles(f,nxt['targetMm']);yaw=a+((b-a+math.pi)%(2*math.pi)-math.pi)*u;pitch=p+(q-p)*u
  desired.append((yaw,pitch))
 last_yaw,last_pitch=desired[0]
 for f,(yaw,pitch) in zip(frames,desired):
  delta=(yaw-last_yaw+math.pi)%(2*math.pi)-math.pi
  last_yaw+=max(-math.radians(max_yaw)/fps,min(math.radians(max_yaw)/fps,delta))
  last_pitch+=max(-math.radians(20)/fps,min(math.radians(20)/fps,pitch-last_pitch))
  f.update(yawRadians=last_yaw,pitchRadians=last_pitch)

def plan(bundle,config,preview=False):
 if bundle.get('schema')!='floor-visualization-production/1.0':raise ValueError('Unsupported production schema')
 if not preview and (set(bundle.get('confirmations',{}))!=set(('structure','layout','style')) or any(v['status']!='confirmed' for v in bundle['confirmations'].values())):raise ValueError('Unconfirmed scheme')
 p=Planner(bundle,config);stops=config['stops'];legs=[];points=[]
 for a,b in zip(stops,stops[1:]):
  leg=p.simplify(p.astar(a['point'],b['point']));legs.append({'from':a['name'],'to':b['name'],'waypoints':leg});points.extend(leg if not points else leg[1:])
 # Preserve each explicit visit endpoint. Rounding a concatenated route can move
 # visits and a nearest-point search can bind them to a later return trip.
 smooth=[];stop_distances=[0];total=0
 for leg in legs:
  rounded=p.round(leg['waypoints'])
  for a,b in zip(rounded,rounded[1:]):total+=math.dist(a,b)
  smooth.extend(rounded if not smooth else rounded[1:]);stop_distances.append(total)
 dense=[]
 for a,b in zip(smooth,smooth[1:]):
  n=max(1,math.ceil(math.dist(a,b)/25));dense.extend([[a[k]+(b[k]-a[k])*j/n for k in (0,1)] for j in range(n)])
 dense.append(smooth[-1]);lengths=[0]
 for a,b in zip(dense,dense[1:]):lengths.append(lengths[-1]+math.dist(a,b))
 length=lengths[-1];fps=config.get('fps',24);seconds=config.get('seconds',30);count=round(fps*seconds);frames=[];j=0
 def sample(d):
  import bisect
  i=max(0,min(len(dense)-2,bisect.bisect_right(lengths,d)-1));t=(d-lengths[i])/(lengths[i+1]-lengths[i] or 1);return[dense[i][k]+(dense[i+1][k]-dense[i][k])*t for k in (0,1)]
 # Time allocation slows compact rooms without stopping, and keeps one continuous path.
 import bisect
 weights=[]
 for i,(a,b) in enumerate(zip(dense,dense[1:])):
  mid=[(a[k]+b[k])/2 for k in (0,1)];weight=max([config.get('roomSpeedWeights',{}).get(r['id'],1) for r in p.rooms if inside(mid,r['poly'])] or [1]);weights.append(weight)
 # A 400mm neighbourhood softens speed transitions at room thresholds.
 weights=[sum(weights[max(0,i-8):min(len(weights),i+9)])/len(weights[max(0,i-8):min(len(weights),i+9)]) for i in range(len(weights))]
 weighted=[0]
 for i,(a,b) in enumerate(zip(dense,dense[1:])):weighted.append(weighted[-1]+math.dist(a,b)*weights[i])
 for i in range(count):
  time_distance=weighted[-1]*i/(count-1);k=max(0,min(len(dense)-2,bisect.bisect_right(weighted,time_distance)-1));fraction=(time_distance-weighted[k])/(weighted[k+1]-weighted[k] or 1);d=lengths[k]+fraction*(lengths[k+1]-lengths[k]);pos=sample(d);ahead=sample(min(length,d+650));behind=sample(max(0,d-150));target=math.atan2(ahead[1]-behind[1],ahead[0]-behind[0]);frames.append({'frame':i+1,'pathDistanceMm':d,'pointMm':pos,'eyeMm':config.get('eyeMm',1650),'yawRadians':target,'pitchRadians':-.06,'horizontalFovDegrees':config.get('horizontalFovDegrees',70)})
 visits=[];visit_times=[]
 for stop,d in zip(stops,stop_distances):
  at=min(range(count),key=lambda i:abs(frames[i]['pathDistanceMm']-d))
  visit_times.append({'name':stop['name'],'frame':at,'seconds':at/fps,'pointMm':frames[at]['pointMm'],'requestedPointMm':stop['point']})
  if stop.get('lookAt'):visits.append((at,stop['lookAt']))
 def view_clear(pos,gaze):
  distance=math.dist(pos,gaze[:2]);samples=max(1,math.ceil(distance/60));return all(not any(dist_segment([pos[k]+(gaze[k]-pos[k])*t/samples for k in (0,1)],a,b)<half for a,b,half in p.walls) for t in range(samples+1))
 last=None;last_pitch=-.06
 for i,f in enumerate(frames):
  pos=f['pointMm'];target=f['yawRadians'];target_pitch=-.06;eligible=sorted([(abs(i-at),at,gaze) for at,gaze in visits if at-fps*2.5<=i<=at+fps*.8])
  for _,at,gaze in eligible:
   if view_clear(pos,gaze):
    target=math.atan2(gaze[1]-pos[1],gaze[0]-pos[0]);height=gaze[2] if len(gaze)>2 else 1100;target_pitch=max(-math.radians(25),min(math.radians(10),math.atan2(height-f['eyeMm'],math.dist(pos,gaze[:2]))));break
  if i>count*.92 and config.get('exitLookAt'):
   q=config['exitLookAt'];target=math.atan2(q[1]-pos[1],q[0]-pos[0])
  if last is None:last=target
  delta=(target-last+math.pi)%(2*math.pi)-math.pi;last+=max(-math.radians(config.get('maxYawDegreesPerSecond',75))/fps,min(math.radians(config.get('maxYawDegreesPerSecond',75))/fps,delta*.18));f['yawRadians']=last
  delta_pitch=target_pitch-last_pitch;last_pitch+=max(-math.radians(25)/fps,min(math.radians(25)/fps,delta_pitch*.18));f['pitchRadians']=last_pitch
 apply_camera_cues(frames,fps,config.get('cameraCues',[]),config.get('maxYawDegreesPerSecond',35))
 # A frame chord can shortcut a safe rounded polyline at a tight corner.
 # Retain a real path vertex for that frame instead of walking across the corner.
 corner_repairs=[]
 for i in range(1,len(frames)-1):
  a,f,b=frames[i-1:i+2]
  if p.line_free(a['pointMm'],f['pointMm']):continue
  lo=bisect.bisect_left(lengths,a['pathDistanceMm']);hi=bisect.bisect_right(lengths,b['pathDistanceMm'])
  for k in sorted(range(lo,hi),key=lambda k:abs(lengths[k]-f['pathDistanceMm'])):
   q=dense[k]
   if math.dist(a['pointMm'],q)>.01 and math.dist(q,b['pointMm'])>.01 and p.line_free(a['pointMm'],q) and p.line_free(q,b['pointMm']):
    f['pointMm']=q[:];f['pathDistanceMm']=lengths[k];corner_repairs.append(i);break
 collisions=sum(p.blocked(f['pointMm']) for f in frames)+sum(not p.line_free(a['pointMm'],b['pointMm']) for a,b in zip(frames,frames[1:]))
 if collisions:raise ValueError('Route has collisions: '+str(collisions))
 rooms=[r['id'] for r in p.rooms if any(inside(f['pointMm'],r['poly']) for f in frames)]
 if set(rooms)!=set(r['id'] for r in p.rooms):raise ValueError('Unvisited rooms '+str(set(r['id'] for r in p.rooms)-set(rooms)))
 return {'previewOnly':preview,'humanAcceptance':'pending','schema':'floor-visualization-tour/1.0','schemeSha256':bundle['schemeSha256'],'seconds':seconds,'fps':fps,'frames':frames,'legs':legs,'visits':visit_times,'audit':{'lengthM':length/1000,'averageSpeedMps':length/1000/seconds,'collisions':collisions,'coveredRooms':rooms,'maximumSpeedMps':max(math.dist(a['pointMm'],b['pointMm'])*fps/1000 for a,b in zip(frames,frames[1:])), 'minimumFrameStepMm':min(math.dist(a['pointMm'],b['pointMm']) for a,b in zip(frames,frames[1:])),'maxYawDegreesPerSecond':max(abs(b['yawRadians']-a['yawRadians'])*fps*180/math.pi for a,b in zip(frames,frames[1:])),'resampledCornerFrames':corner_repairs,'bodyRadiusMm':p.radius,'globallyShortestClaim':False,'deadEndsRequireReturn':True,'slidingDoors':'Traversable openings require open leaves in playback; never treat windows as doors'}}

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--bundle',required=True);ap.add_argument('--config',required=True);ap.add_argument('--output',required=True);ap.add_argument('--preview',action='store_true');a=ap.parse_args();bundle=json.loads(Path(a.bundle).read_text(encoding='utf-8'));config=json.loads(Path(a.config).read_text(encoding='utf-8'));result=plan(bundle,config,a.preview);Path(a.output).write_text(json.dumps(result,ensure_ascii=False), encoding='utf-8');print(json.dumps(result['audit'],ensure_ascii=False))
