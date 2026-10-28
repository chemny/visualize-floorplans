"""Bounded smoothness proposals, not visual approval or a path-follow camera.

Targets come from semantic case framing. Changes stay inside declared windows;
geometry and final subject checks remain mandatory. No time/threshold relaxation.
"""
import copy,math
from tour_connection_motion import project_gaze_numpy

def cubic_path(controls,count):
    if len(controls)!=4 or count<2:raise ValueError('Four physical control points and at least two intervals required')
    result=[]
    for i in range(count+1):
        u=i/count;weights=[(1-u)**3,3*(1-u)**2*u,3*(1-u)*u*u,u**3]
        result.append([sum(w*p[k] for w,p in zip(weights,controls)) for k in (0,1)])
    return result

def creep_arc_window(tour,planner,a,z,creep_speed,blend_seconds,config=None):
    """Redistribute an authored hold into a gentle approach on its identical arc.
    The case chooses the observation pace/window. End pose, end speed, time and
    the remainder of the route are retained. Unsafe/nonmonotone clocks reject.
    """
    from compact_tour_visits import at_distance
    from camera_gaze import PROFILE
    import json
    if not 1<=a<z<len(tour['frames'])-1:raise ValueError('Approach window requires boundary context')
    limit=(config or {}).get('motionReviewLimits',{}).get('maximumSpeedMps',json.loads(PROFILE.read_text())['reviewLimits']['maximumSpeedMps'])
    fs=tour['frames'];fps=tour['fps'];points=[fs[a]['pointMm'][:]]
    for f in fs[a+1:z+1]:
        if math.dist(points[-1],f['pointMm'])>1e-8:points.append(f['pointMm'][:])
    distance=sum(math.dist(x,y) for x,y in zip(points,points[1:]));seconds=(z-a)/fps
    terminal=math.dist(fs[z+1]['pointMm'],fs[z]['pointMm'])*fps
    if not 0<creep_speed<terminal or not 0<blend_seconds<seconds:raise ValueError('Positive case pace and blend below terminal speed/time required')
    ramp=2*(distance-creep_speed*(seconds-blend_seconds/2))/(terminal-creep_speed)
    if not 0<ramp<seconds-blend_seconds:raise ValueError('Continuous approach cannot fit this fixed arc/time')
    def integral(u):return u**3-.5*u**4
    out=copy.deepcopy(tour)
    for i in range(a,z+1):
        t=(i-a)/fps;u=min(1,t/blend_seconds)
        d=creep_speed*(blend_seconds*integral(u)+max(0,t-blend_seconds))
        v=max(0,min(1,(t-(seconds-ramp))/ramp));d+=(terminal-creep_speed)*ramp*integral(v)
        out['frames'][i]['pointMm']=at_distance(points,min(distance,max(0,d)))
    out['frames'][a]['pointMm']=fs[a]['pointMm'][:];out['frames'][z]['pointMm']=fs[z]['pointMm'][:]
    seq=out['frames'][a-1:z+2]
    if any(planner.blocked(f['pointMm']) for f in seq) or any(not planner.line_free(x['pointMm'],y['pointMm']) for x,y in zip(seq,seq[1:])):raise ValueError('Continuous approach clips a physical obstacle')
    if max(math.dist(x['pointMm'],y['pointMm'])*fps/1000 for x,y in zip(seq,seq[1:]))>limit+1e-6:raise ValueError('Continuous approach exceeds walking cap')
    return out,{'window':[a,z],'sameArc':True,'timePreserved':True,'creepSpeedMmPerSecond':creep_speed,'terminalSpeedMmPerSecond':terminal,'endPosePreserved':True}

def regularize(values,second_weight=24,third_weight=800):
    import numpy as np
    x=np.asarray(values,dtype=float);n=len(x)
    if n<8:return x.copy()
    eye=np.eye(n);d2=np.diff(eye,n=2,axis=0);d3=np.diff(eye,n=3,axis=0)
    matrix=eye+second_weight*d2.T@d2+third_weight*d3.T@d3
    fixed=np.array([0,1,2,n-3,n-2,n-1]);free=np.array([i for i in range(n) if i not in fixed]);out=x.copy()
    out[free]=np.linalg.solve(matrix[np.ix_(free,free)],x[free]-matrix[np.ix_(free,fixed)]@x[fixed])
    return out

def gaze_windows(tour,config,windows):
    from tour_workflow import markers
    from camera_gaze import PROFILE
    from tour_camera_evidence import DEFAULTS
    import json
    limits={**json.loads(PROFILE.read_text())['reviewLimits'],**config.get('motionReviewLimits',{})};acceleration={**DEFAULTS,**config.get('cameraEvidencePolicy',{})}
    result=copy.deepcopy(tour);fps=tour['fps'];marks=markers(tour);evidence=[]
    if any(a<=p for (_,p),(a,_) in zip(sorted(windows),sorted(windows)[1:])):raise ValueError('Comfort windows must not overlap')
    for a,z in windows:
        if not 2<=a<z<len(tour['frames'])-2:raise ValueError('Window needs two frozen context frames on each side')
        for axis,speed,accel in [('yawRadians',limits['maxYawDegreesPerSecond'],acceleration['maximumYawAccelerationDegreesPerSecondSquared']),('pitchRadians',limits['maxPitchDegreesPerSecond'],acceleration['maximumPitchAccelerationDegreesPerSecondSquared'])]:
            values=[math.degrees(f[axis]) for f in result['frames'][a-2:z+3]]
            target=regularize(values).tolist();fixed={i:values[i] for i in [0,1,2,len(values)-3,len(values)-2,len(values)-1]};signs={}
            if axis=='yawRadians':
                for ch in config['chapters']:
                    if ch.get('phase')!='observe':continue
                    sign=1 if ch.get('singleSweepDegrees',0)>0 else -1 if ch.get('singleSweepDegrees',0)<0 else 0
                    for i in range(max(a,marks[ch['from']]),min(z,marks[ch['to']])):signs[i-(a-2)]=sign
            solved=project_gaze_numpy(target,fps,speed*.999/fps,accel*.995/fps**2,signs,fixed_values=fixed)
            for i in range(a+1,z):result['frames'][i][axis]=math.radians(solved[i-(a-2)])
        evidence.append({'fromFrame':a,'toFrame':z})
    return result,{'windows':evidence,'positionsPreserved':True,'timePreserved':True,'actualPlayback':'pending'}

def position_window(tour,planner,a,z,config=None):
    """Only accept a smoother same-time proposal if every frame/chord is safe."""
    import numpy as np
    from camera_gaze import PROFILE
    import json
    if not 2<=a<z<len(tour['frames'])-2:raise ValueError('Position window needs frozen context')
    config=config or {};limit=config.get('motionReviewLimits',{}).get('maximumSpeedMps',json.loads(PROFILE.read_text())['reviewLimits']['maximumSpeedMps'])
    source=np.array([f['pointMm'] for f in tour['frames'][a-2:z+3]],dtype=float);fps=tour['fps']
    def jerk(v):return float(np.max(np.linalg.norm(np.diff(v,n=3,axis=0),axis=1),initial=0))
    for weight in (800,160,24):
        proposed=regularize(source,third_weight=weight);points=proposed.tolist()
        if any(planner.blocked(p) for p in points) or any(not planner.line_free(x,y) for x,y in zip(points,points[1:])):continue
        if max((math.dist(x,y)*fps/1000 for x,y in zip(points,points[1:])),default=0)>limit+1e-6:continue
        if jerk(proposed)>=jerk(source)-1e-9:continue
        out=copy.deepcopy(tour)
        for i in range(a+1,z):out['frames'][i]['pointMm']=points[i-(a-2)]
        return out,{'accepted':True,'window':[a,z],'weight':weight,'jerkBefore':jerk(source)*fps**3/1000,'jerkAfter':jerk(proposed)*fps**3/1000}
    return copy.deepcopy(tour),{'accepted':False,'window':[a,z],'reason':'No safe speed-preserving improvement'}
