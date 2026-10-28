"""Fixed bathtub body inside a resizeable surround footprint, in mm."""
import math

def body_geometry(f):
 b=f.get('bathtubBody') or dict(width=f['w'],depth=f['d'],alignment='center')
 if b.get('alignment') not in ('left','center','right') or any(isinstance(b.get(k),bool) or not isinstance(b.get(k),(int,float)) or not math.isfinite(b[k]) for k in ['width','depth']) or b['width']<400 or b['depth']<300 or f['w']<b['width']-.01 or f['d']<b['depth']-.01:raise ValueError('Surround cannot be smaller than fixed bathtub body')
 return dict(width=b['width'],depth=b['depth'],x=-(f['w']-b['width'])/2 if b['alignment']=='left' else (f['w']-b['width'])/2 if b['alignment']=='right' else 0,z=0,minWidth=b['width'],minDepth=b['depth'])

def ensure_body(f):
 if f.get('type')!='bathtub':return
 f.setdefault('bathtubBody',dict(width=f['w'],depth=f['d'],alignment='center'));body_geometry(f)
