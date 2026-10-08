#!/usr/bin/env python3
"""Reusable offline subject gaze, extracted from the accepted homeowner tour.
Path, sampling and visit markers are retained. Output is diagnostic until reviewed.
"""
import argparse, bisect, copy, hashlib, json, math
from pathlib import Path
from tour_workflow import retime, intent_check
PROFILE = Path(__file__).resolve().parents[2] / 'assets/h5/tour/homeowner-profile.json'
def delta(a,b): return (b-a+math.pi)%(2*math.pi)-math.pi

def smooth(values, seconds, fps):
    sigma=seconds*fps
    if sigma<=0:return values[:]
    radius=math.ceil(3*sigma)
    weights=[math.exp(-.5*(i/sigma)**2) for i in range(-radius,radius+1)]
    return [sum(values[max(0,min(len(values)-1,j+i))]*w for i,w in zip(range(-radius,radius+1),weights))/sum(weights) for j in range(len(values))]

def generate(tour, config, profile):
    out=copy.deepcopy(tour);frames=out['frames'];fps=out['fps'];opts={**profile['defaults'],**config.get('cameraProfile',{})}
    if len(frames)<2 or not math.isfinite(fps) or fps<=0:raise ValueError('At least two frames and positive fps required')
    for key in ['eyeMm','horizontalFovDegrees','shiftY','gazeSmoothSeconds','finalSmoothSeconds','pitchMinDegrees','pitchMaxDegrees']:
        if not isinstance(opts.get(key),(int,float)) or not math.isfinite(opts[key]):raise ValueError('Finite camera profile required: '+key)
    if opts['eyeMm']<=0 or not 10<opts['horizontalFovDegrees']<150 or min(opts['gazeSmoothSeconds'],opts['finalSmoothSeconds'])<0 or opts['pitchMinDegrees']>opts['pitchMaxDegrees']:raise ValueError('Invalid camera profile bounds')
    markers=tour.get('stopFrames') or tour.get('visits',[])
    stops={}
    for s in markers:
        if s['name'] in stops:raise ValueError('Stop names must be unique')
        stops[s['name']]=s.get('frameIndex',s.get('frame'))
    keys=[]
    for k in config['cameraKeys']:
        if k.get('atStop') not in stops:raise ValueError('Unknown camera stop: '+str(k.get('atStop')))
        at=stops[k['atStop']]+k.get('offsetFrames',0)
        if not isinstance(at,int) or not 0<=at<len(frames):raise ValueError('Camera key outside frame range')
        q=k.get('targetMm')
        if not isinstance(q,list) or len(q)!=3 or not all(isinstance(v,(int,float)) and math.isfinite(v) for v in q):raise ValueError('Camera key requires finite targetMm [x,y,z]')
        keys.append({**k,'at':at})
    if len(keys)<2 or any(a['at']>=z['at'] for a,z in zip(keys,keys[1:])):raise ValueError('At least two strictly ordered camera keys required')
    curves=[]
    for k in keys:
        ys=[];ps=[];q=k['targetMm']
        for f in frames:
            p=f['pointMm'];y=math.radians(k['yawDegrees']) if 'yawDegrees' in k else math.atan2(q[1]-p[1],q[0]-p[0])
            if ys:y=ys[-1]+delta(ys[-1],y)
            ys.append(y)
            ps.append(math.radians(k['pitchDegrees']) if 'pitchDegrees' in k else max(math.radians(opts['pitchMinDegrees']),min(math.radians(opts['pitchMaxDegrees']),math.atan2(q[2]-opts['eyeMm'],math.dist(p,q[:2])))))
        if curves:
            ref=curves[-1][0][keys[len(curves)-1]['at']];shift=ref+delta(ref,ys[k['at']])-ys[k['at']];ys=[v+shift for v in ys]
        curves.append((ys,ps))
    head=[];pitch=[];ats=[k['at'] for k in keys]
    for i in range(len(frames)):
        if i<=ats[0]:y,p=curves[0][0][i],curves[0][1][i]
        elif i>=ats[-1]:y,p=curves[-1][0][i],curves[-1][1][i]
        else:
            ix=bisect.bisect_right(ats,i)-1;a,z=keys[ix:ix+2];u=(i-a['at'])/(z['at']-a['at']);u=u*u*(3-2*u)
            if a['targetMm']==z['targetMm'] and a.get('yawDegrees')==z.get('yawDegrees') and a.get('pitchDegrees')==z.get('pitchDegrees'):y,p=curves[ix][0][i],curves[ix][1][i]
            else:
                y=curves[ix][0][a['at']]*(1-u)+curves[ix+1][0][z['at']]*u
                p=curves[ix][1][a['at']]*(1-u)+curves[ix+1][1][z['at']]*u
        head.append(y);pitch.append(p)
    for seconds in [opts['gazeSmoothSeconds'],opts['finalSmoothSeconds']]:head=smooth(head,seconds,fps);pitch=smooth(pitch,seconds,fps)
    for f,y,p in zip(frames,head,pitch):f.update(yawRadians=y,pitchRadians=p,eyeMm=opts['eyeMm'],horizontalFovDegrees=opts['horizontalFovDegrees'],shiftY=opts['shiftY'])
    yaw=[(z['yawRadians']-a['yawRadians'])*fps*180/math.pi for a,z in zip(frames,frames[1:])]
    speed=[math.dist(a['pointMm'],z['pointMm'])*fps/1000 for a,z in zip(frames,frames[1:])]
    metrics={'maxYawDegreesPerSecond':max(map(abs,yaw)),'maxPitchDegreesPerSecond':max(abs(z['pitchRadians']-a['pitchRadians'])*fps*180/math.pi for a,z in zip(frames,frames[1:])),'maximumSpeedMps':max(speed),'minimumSpeedMps':min(speed),'maxYawAccelerationDegreesPerSecondSquared':max([abs(z-a)*fps for a,z in zip(yaw,yaw[1:])] or [0])}
    limits={**profile['reviewLimits'],**config.get('motionReviewLimits',{})}
    for k,v in limits.items():
        if k not in metrics or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('Invalid global motion limit: '+k)
    failures=[k for k,v in limits.items() if metrics[k]>v]
    out.update(previewOnly=True,humanAcceptance='pending');out['audit']={**out.get('audit',{}),**metrics}
    out['cameraMethod']={'method':profile['method'],'profile':opts,'positionsAndFrameTimingUnchanged':True,'thresholdFailures':failures,'limits':limits,'limitations':'No visibility or mesh audit performed here; retime or revise case keys when thresholds fail, then rerun subject and body audits.'}
    return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--tour',required=True);ap.add_argument('--config',required=True);ap.add_argument('--output',required=True);ap.add_argument('--profile',default=str(PROFILE));ap.add_argument('--retime',action='store_true');a=ap.parse_args();target=Path(a.output)
    if target.exists():raise ValueError('Use a fresh output; do not overwrite approved camera data')
    read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
    config=read(a.config);profile=read(a.profile);result=generate(read(a.tour),config,profile)
    if a.retime:result=retime(result,config,{**profile['reviewLimits'],**config.get('motionReviewLimits',{})})
    result['chapterReview']=intent_check(result,config)
    result['cameraMethod']['sourceTourSha256']=hashlib.sha256(Path(a.tour).read_bytes()).hexdigest();target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result['cameraMethod'],ensure_ascii=False))
    return 2 if result['cameraMethod']['thresholdFailures'] or result['chapterReview']['failures'] else 0
if __name__=='__main__':raise SystemExit(main())
