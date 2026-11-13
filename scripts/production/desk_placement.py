"""Case-declared desk-to-room-entry spacing; does not choose or move furniture."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from layout_access_checks import footprint
from lighting_checks import inside
from door_operation_review import segment_distance
import math

def review_desks(case):
 policy=case.get('deskPlacementPolicy')
 if not policy:return {'status':'not_provided','scope':'No placement approval inferred; declare door approach distance and operating paths per case.'}
 minimum=policy.get('minimumOpeningDistanceMm')
 if not isinstance(minimum,(int,float)) or isinstance(minimum,bool) or not math.isfinite(minimum) or minimum<0:raise ValueError('Invalid case desk-entry distance')
 state=case['initialState'];rooms={r['id']:r for r in case['model']['rooms']};rows=[]
 for f in state['furniture']:
  if f['type']!='desk':continue
  room=rooms.get(f.get('roomId'))
  if not room:rows.append({'id':f['id'],'status':'fail','reason':'Desk room unassigned'});continue
  x0,y0,x1,y1=footprint(f);corners=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]];distances=[]
  for w in state['walls']:
   if w.get('demolished'):continue
   length=math.dist(w['a'],w['b'])
   if not length:continue
   u=[(w['b'][i]-w['a'][i])/length for i in (0,1)];n=[-u[1],u[0]]
   for o in w['opens']:
    if o['kind'] not in ['door','sliding']:continue
    mid=[w['a'][i]+u[i]*(o['at']+o['width']/2) for i in (0,1)]
    if not any(inside([mid[i]+n[i]*sign*(w['t']/2+20) for i in (0,1)],room['poly']) for sign in (-1,1)):continue
    a=[w['a'][i]+u[i]*o['at'] for i in (0,1)];b=[a[i]+u[i]*o['width'] for i in (0,1)]
    distance=min(segment_distance(a,b,corners[i],corners[(i+1)%4]) for i in range(4));distances.append({'openingId':o.get('id'), 'distanceMm':round(distance,1)})
  rows.append({'id':f['id'],'status':'pass' if distances and all(d['distanceMm']>=minimum for d in distances) else 'fail','openingDistances':distances})
 return {'status':'fail' if any(r['status']=='fail' for r in rows) else 'pass','minimumOpeningDistanceMm':minimum,'desks':rows,'scope':'Room-adjacent opening distance using conservative desk footprint; operating chair, door sweep and paths remain separate checks.'}
