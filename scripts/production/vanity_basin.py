"""Fixed vanity bowls, paired with the shared plan/mesh geometry."""
import math

def default_layout(f):
 c=f.get('basins',2 if '双盆' in f.get('name','') else 1);w=min(550,(f['w']-100)/c-(45 if c==2 else 0));d=min(360,f['d']*.66)
 return dict(width=w,depth=d,count=c,gap=max(40,f['w']*.48-w) if c==2 else 40,alignment=f.get('basinLayout',{}).get('alignment','center'),backGap=(f['d']-d)/2,faucetInset=f['d']*.1)

def basin_geometry(f):
 l=f.get('basinLayout') or default_layout(f);c=f.get('basins',l.get('count',1));group=c*l['width']+(c-1)*l['gap']
 if isinstance(c,bool) or c not in (1,2) or l['alignment'] not in ('left','center','right') or any(isinstance(l[k],bool) or not isinstance(l[k],(int,float)) or not math.isfinite(l[k]) for k in ['width','depth','gap','backGap','faucetInset']) or l['width']<150 or l['depth']<150 or min(l['gap'],l['backGap'],l['faucetInset'])<0 or f['w']<group+100-.01 or f['d']<l['depth']+l['backGap']+40-.01:raise ValueError('Vanity cannot contain fixed basin layout')
 center=-(f['w']-group)/2+50 if l['alignment']=='left' else (f['w']-group)/2-50 if l['alignment']=='right' else 0
 return dict(width=l['width'],depth=l['depth'],centers=[center-group/2+l['width']/2+i*(l['width']+l['gap']) for i in range(c)],z=-f['d']/2+l['backGap']+l['depth']/2,faucetZ=-f['d']/2+l['faucetInset'],minWidth=group+100,minDepth=l['depth']+l['backGap']+40)

def ensure_layout(f):
 if f.get('type')!='vanity':return
 f.setdefault('basins',2 if '双盆' in f.get('name','') else 1)
 if not f.get('basinLayout') or f['basinLayout'].get('count')!=f['basins']:f['basinLayout']=default_layout(f)
 basin_geometry(f)
