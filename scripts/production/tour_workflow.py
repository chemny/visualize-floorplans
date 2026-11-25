"""Shared homeowner timing, motion/intent checks, bounded edits and render gate."""
import bisect, copy, hashlib, json, math
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def markers(t):return {s['name']:s.get('frameIndex',s.get('frame')) for s in (t.get('stopFrames') or t.get('visits',[]))}
def chapter_limits(base,chapter):
 """Chapter ceilings may only tighten an explicitly supplied global ceiling."""
 local=chapter.get('motionReviewLimits',{})
 for key,value in local.items():
  if key not in base or isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<=base[key]:raise ValueError('Chapter motion limit must be positive and no higher than global ceiling: '+key)
 return {**base,**local}

def edge_limits(t,c,key,base):
 """Assign each frame chord to its chapter, including the boundary chords."""
 result=[base[key]]*max(0,len(t['frames'])-1);m=markers(t)
 for ch in c.get('chapters',[]):
  local=chapter_limits(base,ch);a,z=m.get(ch.get('from')),m.get(ch.get('to'))
  if not isinstance(a,int) or not isinstance(z,int) or not 0<=a<z<len(t['frames']):raise ValueError('Invalid chapter limit interval')
  for i in range(a,z):result[i]=min(result[i],local[key])
 return result
def metrics(t):
 f=t['frames'];fps=t['fps'];yr=[(b['yawRadians']-a['yawRadians'])*fps*180/math.pi for a,b in zip(f,f[1:])];speed=[math.dist(a['pointMm'],b['pointMm'])*fps/1000 for a,b in zip(f,f[1:])];signs=[1 if v>1 else -1 for v in yr if abs(v)>1]
 return {'maxYawDegreesPerSecond':max(map(abs,yr),default=0),'maxPitchDegreesPerSecond':max((abs(b['pitchRadians']-a['pitchRadians'])*fps*180/math.pi for a,b in zip(f,f[1:])),default=0),'maximumSpeedMps':max(speed,default=0),'minimumSpeedMps':min(speed,default=0),'stationaryFrames':sum(v<.0024 for v in speed),'positiveYawTravelDegrees':sum(max(0,v)/fps for v in yr),'negativeYawTravelDegrees':sum(max(0,-v)/fps for v in yr),'yawDirectionChanges':sum(a!=b for a,b in zip(signs,signs[1:])),'maxYawAccelerationDegreesPerSecondSquared':max((abs(b-a)*fps for a,b in zip(yr,yr[1:])),default=0)}

def intent_check(t,c):
 from tour_rules import exception
 stops=markers(t);seen=set();fail=[];reports=[]
 for ch in c.get('chapters',[]):
  a,z=stops.get(ch.get('from')),stops.get(ch.get('to'));phase=ch.get('phase');subjects=list(dict.fromkeys(ch.get('subjects',[])+ch.get('orderedViewTargets',[])))
  if a is None or z is None or a>=z:fail.append('Invalid chapter endpoints: '+str(ch.get('name')));continue
  if phase not in ('observe','transit'):fail.append('Declare observe/transit: '+str(ch.get('name')))
  if phase=='observe':
   if not subjects:fail.append('Missing observation subjects: '+str(ch.get('name')))
   overlap=seen.intersection(subjects)
   previous=c['chapters'][len(reports)-1] if reports else {}
   continuation=(previous.get('roomId')==ch.get('roomId') and previous.get('episodeId',previous.get('roomId'))==ch.get('episodeId',ch.get('roomId')) and (previous.get('movingView') or ch.get('movingView')))
   if overlap and not continuation and any(not exception(c,'repeat_subject',ch.get('name'),s) for s in overlap):fail.append('Repeated observation needs scoped ruleExceptions: '+str(ch.get('name')))
   seen.update(subjects)
  if phase=='transit' and subjects and not ch.get('observationReason'):fail.append('Transit observation needs observationReason: '+str(ch.get('name')))
  segment={'frames':t['frames'][a:z+1],'fps':t['fps']};m=metrics(segment)
  limits=ch.get('motionReviewLimits',{})
  for k,v in limits.items():
   if k not in m or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('Invalid chapter motion review limit: '+k)
   if m[k]>v:fail.append('Chapter motion limit: '+str(ch.get('name'))+' / '+k)
  reports.append({'name':ch.get('name'),'phase':phase,'subjects':subjects,'metrics':m})
 if not c.get('chapters'):fail.append('Explicit observation/transit chapters required')
 if c.get('choreographyPolicy',{}).get('enabled'):
  from tour_choreography import inspect
  fail.extend('Choreography: '+issue['code']+' / '+issue.get('chapter',issue.get('message','')) for issue in inspect(t,c)['issues'])
 return {'failures':fail,'chapters':reports,'limitations':'Intent declarations and rotation metrics do not prove visibility or comfort. Direction changes are diagnostic; no universal reversal-count threshold.'}

def shaped_distance_times(f,policy):
 """Seconds per frame interval for walking: capped cruise, slower where the frame says so, eased into every stop
 and (a little quicker) out of it. Only ever lengthens an interval, so it cannot break a motion limit."""
 cruise=policy['cruiseMps'];floor=policy.get('floorMps',.15);stop_accel=cruise/policy['rampSeconds'];start_accel=cruise/policy.get('startRampSeconds',policy['rampSeconds']);arc=[0.]
 for a,b in zip(f,f[1:]):arc.append(arc[-1]+math.dist(a['pointMm'],b['pointMm']))
 stops=sorted(arc[i] for i in range(len(f)) if i in (0,len(f)-1) or math.dist(f[i-1]['pointMm'],f[i]['pointMm'])<.5 or (i+1<len(f) and math.dist(f[i]['pointMm'],f[i+1]['pointMm'])<.5))
 dists=[math.dist(f[i]['pointMm'],f[i+1]['pointMm']) for i in range(len(f)-1)];out=[0.]*(len(f)-1);speeds=[floor]*(len(f)-1)
 for i in range(len(f)-1):
  d=dists[i]
  if d<1e-6:continue
  mid=(arc[i]+arc[i+1])/2;k=bisect.bisect_left(stops,mid);before=(mid-stops[k-1])/1000 if k>0 else 1e9;after=(stops[k]-mid)/1000 if k<len(stops) else 1e9
  speeds[i]=min(f[i].get('speedLimitMps',cruise),cruise*(policy.get('backOutSpeedFactor',1.) if f[i].get('backOut') else 1.),math.sqrt(floor**2+2*start_accel*before),math.sqrt(floor**2+2*stop_accel*after))
 for i in range(len(f)-1):
  if dists[i]>1e-6:out[i]=dists[i]/1000/speeds[i]
 return limit_acceleration(f,out,policy)

def limit_acceleration(f,times,policy):
 """Neighbouring walking intervals may not differ by more than the ramps allow, whatever slowed them
 (a narrow gap, a bend, or a turn-rate limit). Only ever lengthens an interval."""
 cruise=policy['cruiseMps'];stop_accel=cruise/policy['rampSeconds'];start_accel=cruise/policy.get('startRampSeconds',policy['rampSeconds'])
 dists=[math.dist(f[i]['pointMm'],f[i+1]['pointMm']) for i in range(len(f)-1)];moving=[i for i in range(len(f)-1) if dists[i]>1e-6 and times[i]>0]
 speeds={i:dists[i]/1000/times[i] for i in moving}
 for a,b in zip(moving,moving[1:]):
  if b==a+1:speeds[b]=min(speeds[b],math.sqrt(speeds[a]**2+2*start_accel*dists[b]/1000))
 for a,b in zip(reversed(moving[:-1]),reversed(moving[1:])):
  if b==a+1:speeds[a]=min(speeds[a],math.sqrt(speeds[b]**2+2*stop_accel*dists[a]/1000))
 out=list(times)
 for i in moving:out[i]=max(times[i],dists[i]/1000/speeds[i])
 return out


def limit_frame_acceleration(frames,fps,maximum_mps2):
    """Smooth the sampled walking speed so the planar acceleration between frames stays within maximum_mps2.

    Two parts are limited separately (each to 70% of the maximum, so together they stay inside it): the change of speed along the
    path (a start from rest no longer jumps) and the sideways part of a turn (speed is capped where the path bends sharply).
    Works stretch by stretch between stops: the stretch is rescaled so it still ends on its original point. Positions stay on the
    original path; stops, yaw and pitch are untouched."""
    pts=[list(f['pointMm']) for f in frames];n=len(pts);step=.7*maximum_mps2*1000/fps/fps  # mm per frame, per frame
    moving=[math.dist(pts[i],pts[i+1])>.5 for i in range(n-1)];i=0
    wrap=lambda x:(x+math.pi)%(2*math.pi)-math.pi
    while i<n-1:
        if not moving[i]:i+=1;continue
        a=i
        while i<n-1 and moving[i]:i+=1
        b=i  # intervals a..b-1 move; frames a..b
        d=[math.dist(pts[k],pts[k+1]) for k in range(a,b)];total=sum(d)
        if len(d)<3:continue
        heading=[math.atan2(pts[k+1][1]-pts[k][1],pts[k+1][0]-pts[k][0]) for k in range(a,b)]
        bend=[max(abs(wrap(heading[k]-heading[k-1])) if k>0 else 0,abs(wrap(heading[k+1]-heading[k])) if k+1<len(d) else 0) for k in range(len(d))]
        cap=[min(d[k],step/max(bend[k],1e-3)) for k in range(len(d))]
        def fit(v):
            v[0]=min(v[0],step);v[-1]=min(v[-1],step)
            for k in range(1,len(v)):v[k]=min(v[k],v[k-1]+step)
            for k in range(len(v)-2,-1,-1):v[k]=min(v[k],v[k+1]+step)
            return v
        w=fit(cap[:])
        for _ in range(8):
            if sum(w)>=total-.05:break
            gain=total/max(1e-9,sum(w));w=fit([min(cap[k],w[k]*gain) for k in range(len(w))])
        target=[0.]
        for x in w:target.append(target[-1]+x)
        target=[x*total/target[-1] for x in target]
        cum=[0.]
        for x in d:cum.append(cum[-1]+x)
        for j,t in enumerate(target[1:-1],1):
            u=max(0,min(len(d)-1,bisect.bisect_right(cum,t)-1));r=(t-cum[u])/max(1e-9,cum[u+1]-cum[u])
            frames[a+j]['pointMm']=[pts[a+u][k]*(1-r)+pts[a+u+1][k]*r for k in (0,1)]
    return frames


def retime(t,c,limits):
 """Time each segment by maximum movement/yaw/pitch effort, then chapter reading budget.
 Never compress the calculated budget to fit an arbitrary fixed duration.
 """
 f=t['frames'];fps=t['fps'];o=copy.deepcopy(t);st=markers(t)
 if any(not isinstance(i,int) or not 0<=i<len(f) for i in st.values()):raise ValueError('Visit marker outside valid zero-based frame indices')
 for key in ['maximumSpeedMps','maxYawDegreesPerSecond','maxPitchDegreesPerSecond']:
  if not isinstance(limits.get(key),(int,float)) or not math.isfinite(limits[key]) or limits[key]<=0:raise ValueError('Positive finite timing limit required: '+key)
 density=[max(math.dist(a['pointMm'],b['pointMm'])/1000/limits['maximumSpeedMps'],abs(b['yawRadians']-a['yawRadians'])*180/math.pi/limits['maxYawDegreesPerSecond'],abs(b['pitchRadians']-a['pitchRadians'])*180/math.pi/limits['maxPitchDegreesPerSecond'],1/fps/10) for a,b in zip(f,f[1:])]
 if c.get('speedPolicy'):
  density=[max(a,b) for a,b in zip(density,shaped_distance_times(f,c['speedPolicy']))]
  density=limit_acceleration(f,density,c['speedPolicy'])
 # Optional chapter budgets may be stricter than the global motion ceilings.
 # This keeps observation pace while permitting faster already-seen connections.
 for ch in c.get('chapters',[]):
  local={**ch.get('motionReviewLimits',{}),**ch.get('timingLimits',{})}
  if not local:continue
  a,z=st.get(ch.get('from')),st.get(ch.get('to'))
  if a is None or z is None or not 0<=a<z<len(f):raise ValueError('Invalid chapter timing endpoints')
  for key,value in local.items():
   if key not in limits or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<=limits[key]:raise ValueError('Chapter timing limits must be positive and no higher than global ceilings: '+key)
  effective={**limits,**local}
  for i in range(a,z):
   one,two=f[i:i+2]
   density[i]=max(density[i],math.dist(one['pointMm'],two['pointMm'])/1000/effective['maximumSpeedMps'],abs(two['yawRadians']-one['yawRadians'])*180/math.pi/effective['maxYawDegreesPerSecond'],abs(two['pitchRadians']-one['pitchRadians'])*180/math.pi/effective['maxPitchDegreesPerSecond'])
 # Raise local minima near transitions without reducing any segment's required time.
 padded=density[:]
 radius=max(1,round(.2*fps))
 for i,v in enumerate(density):padded[i]=max(v,sum(density[max(0,i-radius):i+radius+1])/len(density[max(0,i-radius):i+radius+1]))
 if c.get('speedPolicy'):padded=limit_acceleration(f,padded,c['speedPolicy'])
 records=[];last_end=0
 for ch in c.get('chapters',[]):
  a,z=st.get(ch.get('from')),st.get(ch.get('to'))
  if a is None or z is None or not 0<=a<z<len(f) or a<last_end:raise ValueError('Timing chapters must be ordered nonoverlapping visit intervals')
  last_end=z;minimum=sum(padded[a:z]);requested=ch.get('minimumSeconds',ch.get('seconds',0))
  if not isinstance(requested,(int,float)) or not math.isfinite(requested) or requested<0:raise ValueError('Nonnegative finite chapter duration required')
  scale=max(1,requested/minimum)
  for i in range(a,z):padded[i]*=scale
  records.append({'name':ch.get('name'),'fromIndex':a,'toIndex':z,'minimumSeconds':minimum,'allocatedSeconds':minimum*scale})
 times=[0]
 for d in padded:times.append(times[-1]+d)
 # N frames at fps produce N/fps seconds; include the endpoint as a final sample.
 n=math.ceil(times[-1]*fps)+1;new=[]
 factor=((n-1)/fps)/times[-1];times=[v*factor for v in times]
 def frame_at(tm):
  ix=max(0,min(len(f)-2,bisect.bisect_right(times,tm)-1));u=max(0,min(1,(tm-times[ix])/(times[ix+1]-times[ix])));a,b=f[ix:ix+2];v=copy.deepcopy(a)
  for key in ['pointMm']:v[key]=[x*(1-u)+y*u for x,y in zip(a[key],b[key])]
  for key in ['yawRadians','pitchRadians','eyeMm','pathDistanceMm']:
   if key in a and key in b:v[key]=a[key]*(1-u)+b[key]*u
  v['sourceFrameIndex']=ix+u;return v
 for i in range(n):v=frame_at(min(times[-1],i/fps));v['frame']=i;new.append(v)
 # Retiming changes angular derivatives; smooth the final sampled gaze again.
 # This is the same final offline stage used in the accepted reference method.
 from camera_gaze import smooth
 for key in ['yawRadians','pitchRadians']:
  values=smooth([v[key] for v in new],c.get('cameraProfile',{}).get('finalSmoothSeconds',.5),fps)
  for frame,value in zip(new,values):frame[key]=value
 o['frames']=new;o['seconds']=n/fps
 if c.get('speedPolicy',{}).get('frameAccelerationMps2'):limit_frame_acceleration(o['frames'],fps,c['speedPolicy']['frameAccelerationMps2'])
 for name in ['visits','stopFrames']:
  for m in o.get(name,[]):
   index=m.get('frameIndex',m.get('frame'));at=min(n-1,round(times[index]*fps));m['seconds']=at/fps
   if 'frameIndex' in m:m['frameIndex']=at
   else:m['frame']=at
 # Final smoothing must not reverse an explicitly declared one-way room sweep.
 marks={m['name']:m.get('frameIndex',m.get('frame')) for m in o.get('stopFrames',o.get('visits',[]))}
 for ch in c.get('chapters',[]):
  sweep=ch.get('singleSweepDegrees')
  if ch.get('phase')!='observe' or sweep is None or abs(sweep)<.001:continue
  a,z=marks[ch['from']],marks[ch['to']];direction=1 if sweep>0 else -1
  values=[direction*frame['yawRadians'] for frame in new[a:z+1]]
  if values[-1]<values[0]:continue  # Report the invalid intent, never silently reverse it.
  low,high=values[0],values[-1];blocks=[]
  for value in values:
   blocks.append([min(high,max(low,value)),1])
   while len(blocks)>1 and blocks[-2][0]>blocks[-1][0]:
    right=blocks.pop();left=blocks.pop();count=left[1]+right[1];blocks.append([(left[0]*left[1]+right[0]*right[1])/count,count])
  fitted=[value for value,count in blocks for _ in range(count)]
  for frame,value in zip(new[a:z+1],fitted):frame['yawRadians']=direction*value
 for ch in records:ch.update(startSeconds=times[ch['fromIndex']],endSeconds=times[ch['toIndex']],allocatedSeconds=times[ch['toIndex']]-times[ch['fromIndex']])
 # Old timeline and review evidence have obsolete frame indices/hashes.
 for k in ['roomTimeline','roomJumpTimes','humanAcceptance','subjectAudit','qualityReview']:o.pop(k,None)
 o.update(previewOnly=True,humanAcceptance='pending');o['timingMethod']={'method':'distance-yaw-pitch-effort-v1','chapters':records,'sourceSeconds':t.get('seconds'),'outputSeconds':o['seconds'],'limits':limits,'requiresNewMeshAndSubjectAudit':True};o.setdefault('cameraMethod',{})['positionsAndFrameTimingUnchanged']=False;o['audit']={**metrics(o),'lengthM':sum(math.dist(a['pointMm'],b['pointMm']) for a,b in zip(new,new[1:]))/1000,'averageSpeedMps':sum(math.dist(a['pointMm'],b['pointMm']) for a,b in zip(new,new[1:]))/1000/o['seconds'],'meshAndSubjectAudit':'pending after resampling'}
 o['cameraMethod']['thresholdFailures']=[k for k,v in limits.items() if k in o['audit'] and o['audit'][k]>v+1e-6]
 return o

def refine(t,windows):
 o=copy.deepcopy(t);fps=t['fps'];last=-1
 for w in windows:
  a,z=w['startSeconds'],w['endSeconds']
  if not 0<=a<z<=(len(t['frames'])-1)/fps or a<last:raise ValueError('Refinements must be ordered nonoverlapping windows')
  last=z
  for k in ['yawBumpDegrees','pitchBumpDegrees']:
   if not isinstance(w.get(k,0),(int,float)) or not math.isfinite(w.get(k,0)):raise ValueError('Finite local angle correction required')
  for i,f in enumerate(o['frames']):
   sec=i/fps
   if a<=sec<=z:
    weight=math.sin(math.pi*(sec-a)/(z-a))**2
    f['yawRadians']+=math.radians(w.get('yawBumpDegrees',0))*weight;f['pitchRadians']+=math.radians(w.get('pitchBumpDegrees',0))*weight
 o.update(previewOnly=True,humanAcceptance='pending');o['localRefinement']={'windows':windows,'positionsEyeAndTimingUnchanged':True,'subjectAndDynamicReview':'invalidated'};o['audit']={**o.get('audit',{}),**metrics(o)};return o

def scene_review_sha(runtime):
 d=json.loads((Path(runtime)/'scene.json').read_text());d=copy.deepcopy(d)
 d.get('renderSettings',{}).pop('size',None)
 return hashlib.sha256(json.dumps(d,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def require_preview(review_path,tour_path,runtime):
 if not review_path:raise ValueError('Full production/HD capture requires --preview-review; make a low-cost dynamic preview first')
 p=Path(review_path);r=json.loads(p.read_text());t=json.loads(Path(tour_path).read_text())
 if r.get('schema')!='homeowner-preview-review/1' or r.get('status')!='passed' or not r.get('reviewedBy'):raise ValueError('Preview review must record an actual reviewer and passed status')
 if r.get('approvalSource')!='explicit_user_confirmation' or not str(r.get('confirmedBy','')).strip() or not str(r.get('evidence','')).strip():raise ValueError('Dynamic preview needs explicit user confirmation; an engineering pass or reviewer name is insufficient')
 if r.get('tourSha256')!=sha(tour_path) or r.get('schemeSha256')!=t['schemeSha256']:raise ValueError('Preview review is stale for this tour/scheme')
 if r.get('rendererSha256')!=sha(Path(runtime)/'renderer.html'):raise ValueError('Preview renderer changed')
 if r.get('sceneReviewSha256')!=scene_review_sha(runtime) or r.get('geometrySha256')!=sha(Path(runtime)/'geometry.bin'):raise ValueError('Preview scene geometry/materials changed')
 for check in ['turnSamplesViewed','wholePreviewViewed','subjectsReadable','paceComfortable','noBlankCaptureEdges']:
  if r.get('checks',{}).get(check) is not True:raise ValueError('Preview review check missing/failed: '+check)
 for key in ['turnSamples','wholePreview','subjectAudit','meshAudit']:
  artifact=r.get('artifacts',{}).get(key,{})
  q=Path(artifact.get('path',''));q=q if q.is_absolute() else p.parent/q
  if not q.is_file() or not artifact.get('sha256') or sha(q)!=artifact['sha256']:raise ValueError('Preview review artifact missing/changed: '+key)
  if key in ['subjectAudit','meshAudit']:
   d=json.loads(q.read_text())
   if d.get('tourSha256')!=sha(tour_path) or d.get('schemeSha256')!=t['schemeSha256']:raise ValueError('Audit is stale: '+key)
   if key=='subjectAudit' and d.get('status')!='pass':raise ValueError('Subjects did not pass')
   if key=='meshAudit' and (d.get('errors') or d.get('meshAudit',{}).get('hits') or 'meshAudit' not in d):raise ValueError('Mesh audit did not pass')
 return r
