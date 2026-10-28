"""Explicit facility approach/open/use/exit checks. No automatic product selection.
Case declarations select operators and moving envelopes; missing declarations stay pending.
"""
import copy,math
from plan_route import Planner,dist_segment
from shower_door import shower_geometry,enclosure_segments
from door_operation_review import leaf_segments,rect_object
from door_checks import door_leaves,segment_in_body,effective_openings,is_closed,sliding_geometry
from floor_connection_checks import solid_wall_rects

IGNORE={'threshold','doortrim','windowtrim','skirting','floordrain','transition','rug'}
def local_world(f,p):
 a=math.radians(f.get('rot',0));return [f['cx']+p[0]*math.cos(a)-p[1]*math.sin(a),f['cy']+p[0]*math.sin(a)+p[1]*math.cos(a)]
def obstructions(state,omit):
 walls=[(w['id'],rect_object(r)) for w in state['walls'] if not w.get('demolished') for r in solid_wall_rects([w])]
 furniture=[(f['id'],f) for f in state['furniture'] if f['id']!=omit and f['type'] not in IGNORE and not f.get('planPoint') and f.get('elevation',0)<2100]
 return walls+furniture

def path(state,model,a,b,radius,extra=None):
 p=Planner({'state':state,'model':model},{'bodyRadiusMm':radius,'gridMm':25})
 if extra:p.furniture.extend(extra)
 def precise_line(u,v):
  n=max(1,math.ceil(math.dist(u,v)/5));return all(not p.blocked([u[k]+(v[k]-u[k])*j/n for k in (0,1)]) for j in range(n+1))
 p.line_free=precise_line
 points=p.simplify([a]+p.astar(a,b)+[b])
 for u,v in zip(points,points[1:]):
  n=max(1,math.ceil(math.dist(u,v)/5))
  if any(p.blocked([u[k]+(v[k]-u[k])*j/n for k in (0,1)]) for j in range(n+1)):raise ValueError('Route grazes an obstacle')
 return points

def rect_overlap(a,b):
 def corners(f):return [local_world(f,[x*f['w']/2,y*f['d']/2]) for x,y in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 aa,bb=corners(a),corners(b)
 for f in (a,b):
  r=math.radians(f.get('rot',0))
  for axis in ([math.cos(r),math.sin(r)],[-math.sin(r),math.cos(r)]):
   x=[sum(p[k]*axis[k] for k in (0,1)) for p in aa];y=[sum(p[k]*axis[k] for k in (0,1)) for p in bb]
   if min(max(x),max(y))-max(min(x),min(y))<=.1:return False
 return True

def extension(f,s,portion=1):
 ext=s['extensionMm']*portion+s.get('handleMm',0);r=math.radians(f.get('rot',0));p=local_world(f,[0,f['d']/2+ext/2]);return dict(id=f['id']+':operation',type='operation',cx=p[0],cy=p[1],w=f['w']-2*s.get('edgeInsetMm',0),d=ext,rot=f.get('rot',0))

def review_facilities(case):
 policy=case.get('facilityUsePolicy');state=case['initialState'];model=case['model']
 if not policy:return {'status':'not_provided','facilities':[],'scope':'No facility operation declarations'}
 rows=[];declared={s['id'] for s in policy.get('facilities',[])}
 for ident in policy.get('scope',[]):
  if ident not in declared:rows.append({'id':ident,'status':'fail','issues':['Missing required facility scenario']})
 for spec in policy.get('facilities',[]):
  f=next((f for f in state['furniture'] if f['id']==spec['id']),None);row={'id':spec['id'],'status':'pass','issues':[],'paths':{},'checks':{}}
  try:
   if not f:raise ValueError('Unknown facility')
   if not isinstance(spec.get('bodyRadiusMm'),(int,float)) or isinstance(spec['bodyRadiusMm'],bool) or not math.isfinite(spec['bodyRadiusMm']) or spec['bodyRadiusMm']<=0:raise ValueError('Positive declared body radius required')
   for key in ('from','operator','usePoint'):
    if len(spec.get(key,[]))!=2 or any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) for v in spec[key]):raise ValueError('Finite declared '+key+' required')
   r=spec['bodyRadiusMm'];start=spec['from'];op=spec['operator'];use=spec['usePoint'];obstacles=obstructions(state,f['id'])
   working=copy.deepcopy(state)
   if spec.get('closeRoomDoor'):
    door_id=spec['closeRoomDoor'];hit=next(( (w,i,o) for w in state['walls'] for i,o in effective_openings(state,w) if o.get('id')==door_id),None)
    if not hit:raise ValueError('Unknown room door')
    w,i,o=hit;hold=spec['roomDoorOperator']
    if o['kind'] not in ('door','sliding') or o.get('leafRemoved'):raise ValueError('Privacy door needs a real operable leaf')
    row['paths']['enter_room']=path(state,model,start,hold,r)
    if o['kind']=='sliding':
     for j in range(51):
      g=sliding_geometry(w,{**o,'slideOpen':j/50});v=[(w['b'][k]-w['a'][k])/math.dist(w['a'],w['b']) for k in (0,1)]
      for pane in g['panels']:
       a=[pane['cx']-v[0]*pane['pw']/2,pane['cy']-v[1]*pane['pw']/2];b=[pane['cx']+v[0]*pane['pw']/2,pane['cy']+v[1]*pane['pw']/2]
       if dist_segment(hold,a,b)<r+pane['thickness']/2:raise ValueError('Room slider closing intersects operator')
       if o.get('leaves')==1:
        pull=[pane['cx']+v[0]*pane['pw']*.34-v[1]*o.get('slideSide',-1)*30,pane['cy']+v[1]*pane['pw']*.34+v[0]*o.get('slideSide',-1)*30]
        if math.dist(hold,pull)<r+15:raise ValueError('Room slider pull intersects operator')
     working['walls'][next(k for k,rw in enumerate(working['walls']) if rw['id']==w['id'])]['opens'][i]['slideOpen']=0
     if o.get('id') in working.get('doorStyles',{}):working['doorStyles'][o['id']]['slideOpen']=0
    else:
     for leaf in door_leaves(w,o):
      for j in range(51):
       for part,a,b,pad in leaf_segments(leaf,leaf['angleDegrees']*j/50):
        if dist_segment(hold,a,b)<r+pad:raise ValueError('Room-door closing operator intersects '+part)
     key=w['id'] if i==0 else w['id']+':'+str(o.get('id') or i)
     working.setdefault('doors',{})[key]=False
    path(working,model,hold,hold,r)
    row['checks']['closeRoomDoorBeforeUse']=door_id
    start=hold

   if f['type']=='shower':
    if not f.get('showerDoor'):raise ValueError('No operable shower door; shape is not usable evidence')
    closed=copy.deepcopy(working);next(x for x in closed['furniture'] if x['id']==f['id'])['showerDoor']['open']=0
    opened=copy.deepcopy(closed);next(x for x in opened['furniture'] if x['id']==f['id'])['showerDoor']['open']=1
    for j in range(51):
     g=shower_geometry(f,j/50)
     for name,a,b,pad in [('leaf',g['worldHinge'],g['worldTip'],5),('pull',g['handle'],g['handle'],9)]:
      for oid,ob in obstacles:
       if segment_in_body(a,b,ob,pad):raise ValueError('Moving '+name+' conflicts with '+oid)
      from door_operation_review import segment_distance
      for rw in state['walls']:
       if rw.get('demolished'):continue
       for ri,ro in effective_openings(working,rw):
        for rl in door_leaves(rw,ro,is_closed(working,rw,ro,ri)):
         for rp,ra,rb,rpad in leaf_segments(rl,rl['angleDegrees']):
          if segment_distance(a,b,ra,rb)<pad+rpad-.1:raise ValueError('Shower motion conflicts with room door '+str(ro.get('id')))
      if dist_segment(op,a,b)<r+pad:raise ValueError('Opening operator intersects '+name)
    for a,b,pad in enclosure_segments(f,0)[:3]:
     for oid,ob in obstacles:
      if segment_in_body(a,b,ob,pad):raise ValueError('Fixed enclosure conflicts with '+oid)
    if shower_geometry(f,1)['netOpeningMm']<2*r:raise ValueError('Shower clear opening narrower than declared body')
    row['paths']['approach']=path(closed,model,start,op,r)
    row['paths']['enter']=path(opened,model,op,use,r)
    row['paths']['use_closed']=path(closed,model,use,use,r)
    row['paths']['exit']=path(opened,model,use,op,r)
    row['paths']['leave']=path(closed,model,op,start,r)
    row['checks'].update(mechanism='hinged_shower',sweepIncludesPull=True,openingAndClosingSameSweep=True,clearOpeningMm=shower_geometry(f,1)['netOpeningMm'],insideDoorClosed=True)
   elif spec.get('motion',{}).get('type')=='static_use':
    row['paths']['approach']=path(working,model,start,use,r);row['paths']['exit']=path(working,model,use,start,r)
    row['checks'].update(mechanism='static_use',operation='declared floor body envelope; seated/reach product ergonomics not inferred')
   else:
    if spec.get('motion',{}).get('type')!='front_extension':raise ValueError('Explicit cabinet/drawer envelope required')
    m=spec['motion']
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 for v in [m.get('extensionMm'),m.get('handleMm',0),m.get('edgeInsetMm',0)]) or 2*m.get('edgeInsetMm',0)>=f['w']:raise ValueError('Invalid explicit motion envelope')
    moving=extension(f,spec['motion'])
    for oid,ob in obstacles:
     if rect_overlap(moving,ob):raise ValueError('Declared extension conflicts with '+oid)
    # Operator stays outside complete extension while pulling; use after closing.
    path(working,model,op,op,r,[moving]);row['paths']['approach']=path(working,model,start,op,r)
    row['paths']['withdraw_open']=path(working,model,op,op,r,[moving]);row['paths']['use']=path(working,model,op,use,r);row['paths']['exit']=path(working,model,use,start,r)
    row['checks'].update(mechanism='declared_front_extension',includesHandleMm=spec['motion'].get('handleMm',0),operatorOutsideFullExtension=True,closeBeforeUsing=True,productMechanism='case envelope; not an animated product cabinet')
   if spec.get('closeRoomDoor'):row['paths']['leave_room']=path(state,model,start,spec['from'],r)
   row['checks']['bodyWidthMm']=2*r
  except (ValueError,KeyError,TypeError) as error:row['status']='fail';row['issues'].append(str(error))
  rows.append(row)
 return {'status':'fail' if any(x['status']=='fail' for x in rows) else 'pass' if rows else 'not_provided','facilities':rows,'limitations':['Declared body and operator points are case assumptions','No hand/arm inverse kinematics, product certification or unprovided simultaneous-user combinations','Cabinet front extensions are explicit motion envelopes, not inferred product hardware']}
