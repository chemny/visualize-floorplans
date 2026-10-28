"""Fixed-time transit repair with immutable observation frames.
Convex local velocity/acceleration projections propose a trajectory; actual body
collision and final contract remain mandatory. No threshold relaxation or capture.
"""
import copy,math,time
from tour_workflow import markers
from camera_gaze import PROFILE
import json

def repair_positions(tour,config,planner,maximum_iterations=16000):
    fs=tour['frames'];n=len(fs);fps=tour['fps'];m=markers(tour);fixed=set()
    for ch in config['chapters']:
        if ch['phase']=='observe':fixed.update(range(m[ch['from']],m[ch['to']]+1))
    fixed.update((0,n-1));x=[f['pointMm'][:] for f in fs]
    limits={**json.loads(PROFILE.read_text())['reviewLimits'],**config.get('motionReviewLimits',{})}
    speed=limits['maximumSpeedMps']*1000/fps*.999
    accel=config.get('trajectoryPolicy',{}).get('maximumPlanarAccelerationMps2',3)*1000/fps**2*.98
    constraints=[]
    for i in range(n-1):constraints.append(((i,i+1),(-1.,1.),speed))
    for i in range(n-2):constraints.append(((i,i+1,i+2),(1.,-2.,1.),accel))
    dual=[[0.,0.] for _ in constraints]
    for iteration in range(maximum_iterations):
        for k,(ids,weights,cap) in enumerate(constraints):
            value=[sum(x[i][axis]*w for i,w in zip(ids,weights)) for axis in (0,1)];norm=sum(w*w for i,w in zip(ids,weights) if i not in fixed)
            if not norm:
                if math.hypot(*value)>cap+1e-6:raise ValueError('Frozen observation movement itself exceeds physical limit')
                continue
            # Dykstra correction in image coordinates of this sparse operator.
            proposed=[value[a]+norm*dual[k][a] for a in (0,1)];mag=math.hypot(*proposed);scale=max(0,1-cap/max(mag,1e-12));next_dual=[v*scale/norm for v in proposed]
            change=[next_dual[a]-dual[k][a] for a in (0,1)];dual[k]=next_dual
            for i,w in zip(ids,weights):
                if i in fixed:continue
                for a in (0,1):x[i][a]-=w*change[a]
        if iteration%20==0:
            residual=max((math.hypot(*(sum(x[i][a]*w for i,w in zip(ids,weights)) for a in (0,1)))-cap for ids,weights,cap in constraints),default=0)
            if residual<1e-5:break
    residual=max((math.hypot(*(sum(x[i][a]*w for i,w in zip(ids,weights)) for a in (0,1)))-cap for ids,weights,cap in constraints),default=0)
    out=copy.deepcopy(tour)
    for f,p in zip(out['frames'],x):f['pointMm']=p
    collisions=[i for i,p in enumerate(x) if planner.blocked(p)];edges=[i for i,(a,z) in enumerate(zip(x,x[1:])) if not planner.line_free(a,z)]
    evidence={'iterations':iteration+1,'residualMm':residual,'maximumDisplacementMm':max(math.dist(f['pointMm'],p) for f,p in zip(fs,x)),'frozenObservationFrames':len(fixed),'observationPositionsPreserved':all(x[i]==fs[i]['pointMm'] for i in fixed),'collisionFrames':collisions,'collisionEdges':edges,'accepted':residual<1e-5 and not collisions and not edges}
    return out,evidence


def check_deadline(deadline):
    if deadline is None:return
    if isinstance(deadline,bool) or not isinstance(deadline,(int,float)) or not math.isfinite(deadline):raise ValueError('Finite projection deadline required')
    if time.monotonic()>=deadline:raise TimeoutError('Bounded projection deadline exhausted')

def project_gaze_numpy(target,fps,speed,accel,signs,maximum_iterations=24000,fixed_values=None,tolerance=1e-7,deadline=None):
    """Accelerated sparse Dykstra projection of scalar angles in degrees.
    ``fixed_values`` optionally maps frame indices to immutable angle values.
    Its equality set participates in Dykstra, rather than overwriting a solved
    curve and silently violating derivatives at local repair boundaries.
    """
    check_deadline(deadline)
    import numpy as np
    x=np.array(target,dtype=float);n=len(x);groups=[]
    if x.ndim!=1 or not n or not np.isfinite(x).all():raise ValueError('Finite nonempty angle vector required')
    if not all(math.isfinite(v) and v>0 for v in (fps,accel)):raise ValueError('Positive finite gaze limits required')
    speeds=np.full(max(0,n-1),speed,dtype=float) if np.isscalar(speed) else np.asarray(speed,dtype=float)
    if speeds.shape!=(max(0,n-1),) or not np.isfinite(speeds).all() or (speeds<=0).any():raise ValueError('Positive finite per-edge gaze limits required')
    if not isinstance(maximum_iterations,int) or maximum_iterations<1:raise ValueError('Positive projection iteration budget required')
    if not math.isfinite(tolerance) or not 0<tolerance<=1e-7:raise ValueError('Projection tolerance may only tighten the default precision')
    fixed=dict(fixed_values or {})
    if any(not isinstance(i,int) or not 0<=i<n or not math.isfinite(v) for i,v in fixed.items()):raise ValueError('Invalid fixed gaze frame/value')
    for i,value in fixed.items():x[i]=value
    for order,weights,colors in ((1,[-1.,1.],2),(2,[1.,-2.,1.],3)):
        for color in range(colors):
            starts=np.arange(color,n-order,colors,dtype=int);ids=starts[:,None]+np.arange(order+1)[None,:];w=np.array(weights);norm=float(sum(v*v for v in weights));lo=-speeds[starts] if order==1 else np.full(len(starts),-accel);hi=-lo.copy()
            if order==1:
                for j,i in enumerate(starts):
                    sign=signs.get(int(i))
                    if sign in (1,0):lo[j]=0
                    if sign in (-1,0):hi[j]=0
            for j,row in enumerate(ids):
                if all(int(i) in fixed for i in row):
                    value=sum(fixed[int(i)]*weight for i,weight in zip(row,w))
                    if value<lo[j]-1e-6 or value>hi[j]+1e-6:raise ValueError('Fixed gaze values themselves violate speed, acceleration or sweep direction')
            groups.append([ids,w,norm,lo,hi,np.zeros(len(starts))])
    if fixed:
        indices=np.array(sorted(fixed),dtype=int)[:,None];values=np.array([fixed[int(i)] for i in indices[:,0]])
        groups.append([indices,np.array([1.]),1.,values,values,np.zeros(len(values))])
        # Reject endpoint pairs that cannot physically connect even before
        # local acceleration constraints are considered.
        ids=sorted(fixed)
        for a,z in zip(ids,ids[1:]):
            if abs(fixed[z]-fixed[a])>float(speeds[a:z].sum())+1e-6:raise ValueError('Fixed gaze endpoints cannot connect within speed limit')
    def violation():
        return max((float(np.max(np.maximum(lo-(x[ids]*w).sum(axis=1),(x[ids]*w).sum(axis=1)-hi),initial=0)) for ids,w,norm,lo,hi,dual in groups),default=0.)
    residual=float('inf')
    for iteration in range(maximum_iterations):
        if iteration%40==0:check_deadline(deadline)
        for group in groups:
            ids,w,norm,lo,hi,dual=group
            val=(x[ids]*w).sum(axis=1);p=val+norm*dual;nd=(p-np.clip(p,lo,hi))/norm;change=nd-dual;group[-1]=nd
            x[ids]-=change[:,None]*w
        if iteration%40==0:
            residual=violation()
            if residual<tolerance:break
    # Preserve fixed values bit-for-bit, then certify the resulting complete
    # vector. This catches tiny equality roundoff instead of leaking it outside
    # the authorized repair window.
    for i,value in fixed.items():x[i]=value
    residual=violation()
    if residual>tolerance*10:raise ValueError(f'Gaze projection did not converge: residual {residual:.9g} degrees')
    return x.tolist()


def repair_positions_numpy(tour,config,planner,maximum_iterations=24000,speed_headroom_fraction=.001,acceleration_headroom_fraction=.02,projection_tolerance_mm=1e-5,deadline=None):
    check_deadline(deadline)
    import numpy as np
    fs=tour['frames'];n=len(fs);fps=tour['fps'];m=markers(tour);fixed=np.zeros(n,dtype=bool)
    for ch in config['chapters']:
        if ch['phase']=='observe':fixed[m[ch['from']]:m[ch['to']]+1]=True
    fixed[0]=fixed[-1]=True;x=np.array([f['pointMm'] for f in fs],dtype=float);original=x.copy()
    for value in (speed_headroom_fraction,acceleration_headroom_fraction):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<=value<=.05:raise ValueError('Position projection reserve must be finite and between zero and five percent')
    if isinstance(projection_tolerance_mm,bool) or not isinstance(projection_tolerance_mm,(int,float)) or not math.isfinite(projection_tolerance_mm) or not 0<projection_tolerance_mm<=1e-5:raise ValueError('Position projection tolerance may only tighten default precision')
    limits={**json.loads(PROFILE.read_text())['reviewLimits'],**config.get('motionReviewLimits',{})};speed=limits['maximumSpeedMps']*1000/fps*(1-speed_headroom_fraction);accel=config.get('trajectoryPolicy',{}).get('maximumPlanarAccelerationMps2',3)*1000/fps**2*(1-acceleration_headroom_fraction);groups=[]
    for order,weights,colors,cap in ((1,[-1.,1.],2,speed),(2,[1.,-2.,1.],3,accel)):
        for color in range(colors):
            starts=np.arange(color,n-order,colors,dtype=int);ids=starts[:,None]+np.arange(order+1)[None,:];w=np.array(weights);free=~fixed[ids];norm=(free*w*w).sum(axis=1);active=norm>0
            values=(x[ids]*w[None,:,None]).sum(axis=1)
            if np.any(np.linalg.norm(values[~active],axis=1)>cap+1e-6):raise ValueError('Frozen observation movement itself exceeds physical limit')
            groups.append([ids[active],w,free[active],norm[active],cap,np.zeros((int(active.sum()),2))])
    # Each obstacle supplies a separating half-plane through its inflated
    # boundary, selected at the original safe point. This prevents a smoothing
    # step from cutting the inside of a door or wall corner.
    planes=[]
    for i,p in enumerate(original):
        if fixed[i]:continue
        for a,z,thickness in planner.walls+planner.leaves:
            dx,dy=z[0]-a[0],z[1]-a[1];den=dx*dx+dy*dy
            u=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/max(den,1e-12)));q=[a[0]+u*dx,a[1]+u*dy];v=p-np.array(q);d=float(np.linalg.norm(v));radius=planner.radius+thickness
            if d<radius-1e-6:raise ValueError('Original connection already collides')
            if d-radius<300 and d>1e-9:
                normal=v/d;planes.append((i,normal,float(np.dot(normal,q)+radius+1e-4)))
        for f in planner.furniture:
            angle=math.radians(f.get('rot',0));co,si=math.cos(angle),math.sin(angle);dx,dy=p[0]-f['cx'],p[1]-f['cy'];uv=[dx*co+dy*si,-dx*si+dy*co];ext=[f['w']/2+planner.radius,f['d']/2+planner.radius];side=max((0,1),key=lambda k:abs(uv[k])-ext[k]);gap=abs(uv[side])-ext[side]
            if gap< -1e-6:raise ValueError('Original connection intersects furniture')
            if gap<300:
                sign=1 if uv[side]>=0 else -1;normal=np.array([co,si] if side==0 else [-si,co])*sign;planes.append((i,normal,float(np.dot(normal,[f['cx'],f['cy']])+ext[side]+1e-4)))
    if planes:
        plane_ids=np.array([v[0] for v in planes],dtype=int);plane_normals=np.array([v[1] for v in planes]);plane_bounds=np.array([v[2] for v in planes]);plane_dual=np.zeros(len(planes))
        # Multiple obstacles may constrain one vertex; process each local
        # obstacle slot separately to keep vector updates non-overlapping.
        slots=[];counts={}
        for k,(i,_,_) in enumerate(planes):
            slot=counts.get(i,0);counts[i]=slot+1
            while len(slots)<=slot:slots.append([])
            slots[slot].append(k)
        slots=[np.array(v,dtype=int) for v in slots]
    residual=float('inf')
    for iteration in range(maximum_iterations):
        if iteration%40==0:check_deadline(deadline)
        for group in groups:
            ids,w,free,norm,cap,dual=group;v=(x[ids]*w[None,:,None]).sum(axis=1);proposed=v+norm[:,None]*dual;mag=np.linalg.norm(proposed,axis=1);nd=proposed*np.maximum(0,1-cap/np.maximum(mag,1e-12))[:,None]/norm[:,None];change=nd-dual;group[-1]=nd
            x[ids]-=change[:,None,:]*w[None,:,None]*free[:,:,None]
        if planes:
            for slot in slots:
                ids=plane_ids[slot];normal=plane_normals[slot];value=(x[ids]*normal).sum(axis=1);nd=np.maximum(0,plane_dual[slot]+plane_bounds[slot]-value);change=nd-plane_dual[slot];plane_dual[slot]=nd;x[ids]+=normal*change[:,None]
        if iteration%40==0:
            residual=max(float(np.max(np.linalg.norm((x[ids]*w[None,:,None]).sum(axis=1),axis=1)-cap,initial=0)) for ids,w,free,norm,cap,dual in groups)
            if residual<projection_tolerance_mm:break
    residual=max(float(np.max(np.linalg.norm((x[ids]*w[None,:,None]).sum(axis=1),axis=1)-cap,initial=0)) for ids,w,free,norm,cap,dual in groups)
    out=copy.deepcopy(tour)
    for f,p in zip(out['frames'],x):f['pointMm']=p.tolist()
    collisions=[i for i,p in enumerate(x) if planner.blocked(p)];edges=[i for i,(a,z) in enumerate(zip(x,x[1:])) if not planner.line_free(a,z)]
    evidence={'iterations':iteration+1,'residualMm':residual,'projectionToleranceMm':projection_tolerance_mm,'maximumDisplacementMm':float(np.linalg.norm(x-original,axis=1).max()),'frozenObservationFrames':int(fixed.sum()),'observationPositionsPreserved':bool(np.array_equal(x[fixed],original[fixed])),'collisionFrames':collisions,'collisionEdges':edges,'accepted':residual<projection_tolerance_mm and not collisions and not edges}
    return out,evidence
