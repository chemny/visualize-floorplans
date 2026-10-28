"""Operable shower geometry paired with source/shower-door.js; no assumed product."""
import math

def shower_geometry(f,op=None):
 s=f.get('showerDoor');op=s.get('open',0) if op is None and s else op
 if not s or s.get('type')!='hinged':raise ValueError('Explicit shower door mechanism required')
 if s.get('hinge') not in ('left','right') or any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in [s.get('angle'),op]) or not 5<=s['angle']<=100 or not 0<=op<=1 or min(f['w'],f['d'])<500:raise ValueError('Invalid shower mechanism')
 sign=1 if s['hinge']=='left' else -1;h=[-sign*(f['w']/2-20),f['d']/2];L=s.get('width',f['w']-40);a=math.radians(s['angle']*op);r=math.radians(f.get('rot',0))
 if isinstance(L,bool) or not isinstance(L,(int,float)) or not math.isfinite(L) or L<300 or L>f['w']-40+.01:raise ValueError('Shower width smaller than fixed door width plus 40mm')
 fixed=[[[h[0]+sign*L,h[1]],[sign*(f['w']/2-20),f['d']/2]]] if f['w']-40-L>.01 else []
 def world(p):return [f['cx']+p[0]*math.cos(r)-p[1]*math.sin(r),f['cy']+p[0]*math.sin(r)+p[1]*math.cos(r)]
 tip=[h[0]+sign*L*math.cos(a),h[1]+L*math.sin(a)];handle=[h[0]+sign*(L-65)*math.cos(a)-math.sin(a)*32,h[1]+(L-65)*math.sin(a)+sign*math.cos(a)*32]
 return dict(hinge=h,tip=tip,length=L,sign=sign,rotationY=-sign*a,worldHinge=world(h),worldTip=world(tip),handle=world(handle),netOpeningMm=max(0,L*(1-math.cos(a))-20),thicknessMm=10,fixedPanels=fixed,worldFixedPanels=[[world(p) for p in pair] for pair in fixed])

def enclosure_segments(f,op=None):
 r=math.radians(f.get('rot',0))
 def world(x,z):return [f['cx']+x*math.cos(r)-z*math.sin(r),f['cy']+x*math.sin(r)+z*math.cos(r)]
 w,d=f['w']/2-5,f['d']/2-5
 result=[(world(-w,-d),world(w,-d),5),(world(-w,-d),world(-w,d),5),(world(w,-d),world(w,d),5)]
 g=shower_geometry(f,op);result.extend([(a,b,5) for a,b in g['worldFixedPanels']]);result.extend([(g['worldHinge'],g['worldTip'],5),(g['handle'],g['handle'],9)])
 return result
