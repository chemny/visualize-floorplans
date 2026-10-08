"""Shared homeowner timing, motion/intent checks, bounded edits and render gate."""
import bisect, copy, hashlib, json, math
from pathlib import Path

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def markers(t):return {s['name']:s.get('frameIndex',s.get('frame')) for s in (t.get('stopFrames') or t.get('visits',[]))}
def metrics(t):
 f=t['frames'];fps=t['fps'];yr=[(b['yawRadians']-a['yawRadians'])*fps*180/math.pi for a,b in zip(f,f[1:])];speed=[math.dist(a['pointMm'],b['pointMm'])*fps/1000 for a,b in zip(f,f[1:])];signs=[1 if v>1 else -1 for v in yr if abs(v)>1]
 return {'maxYawDegreesPerSecond':max(map(abs,yr),default=0),'maxPitchDegreesPerSecond':max((abs(b['pitchRadians']-a['pitchRadians'])*fps*180/math.pi for a,b in zip(f,f[1:])),default=0),'maximumSpeedMps':max(speed,default=0),'minimumSpeedMps':min(speed,default=0),'stationaryFrames':sum(v<.0024 for v in speed),'positiveYawTravelDegrees':sum(max(0,v)/fps for v in yr),'negativeYawTravelDegrees':sum(max(0,-v)/fps for v in yr),'yawDirectionChanges':sum(a!=b for a,b in zip(signs,signs[1:])),'maxYawAccelerationDegreesPerSecondSquared':max((abs(b-a)*fps for a,b in zip(yr,yr[1:])),default=0)}

def intent_check(t,c):
 stops=markers(t);seen=set();fail=[];reports=[]
 for ch in c.get('chapters',[]):
  a,z=stops.get(ch.get('from')),stops.get(ch.get('to'));phase=ch.get('phase');subjects=ch.get('subjects',[])
  if a is None or z is None or a>=z:fail.append('Invalid chapter endpoints: '+str(ch.get('name')));continue
  if phase not in ('observe','transit'):fail.append('Declare observe/transit: '+str(ch.get('name')))
  if phase=='observe':
   if not subjects:fail.append('Missing observation subjects: '+str(ch.get('name')))
   if seen.intersection(subjects) and not ch.get('repeatReason'):fail.append('Repeated observation needs repeatReason: '+str(ch.get('name')))
   seen.update(subjects)
  if phase=='transit' and subjects and not ch.get('observationReason'):fail.append('Transit observation needs observationReason: '+str(ch.get('name')))
  segment={'frames':t['frames'][a:z+1],'fps':t['fps']};m=metrics(segment)
  limits=ch.get('motionReviewLimits',{})
  for k,v in limits.items():
   if k not in m or not isinstance(v,(int,float)) or not math.isfinite(v) or v<0:raise ValueError('Invalid chapter motion review limit: '+k)
   if m[k]>v:fail.append('Chapter motion limit: '+str(ch.get('name'))+' / '+k)
  reports.append({'name':ch.get('name'),'phase':phase,'subjects':subjects,'metrics':m})
 if not c.get('chapters'):fail.append('Explicit observation/transit chapters required')
 return {'failures':fail,'chapters':reports,'limitations':'Intent declarations and rotation metrics do not prove visibility or comfort. Direction changes are diagnostic; no universal reversal-count threshold.'}

def retime(t,c,limits):
 """Time each segment by maximum movement/yaw/pitch effort, then chapter reading budget.
 Never compress the calculated budget to fit an arbitrary fixed duration.
 """
 f=t['frames'];fps=t['fps'];o=copy.deepcopy(t);st=markers(t)
 if any(not isinstance(i,int) or not 0<=i<len(f) for i in st.values()):raise ValueError('Visit marker outside valid zero-based frame indices')
 for key in ['maximumSpeedMps','maxYawDegreesPerSecond','maxPitchDegreesPerSecond']:
  if not isinstance(limits.get(key),(int,float)) or not math.isfinite(limits[key]) or limits[key]<=0:raise ValueError('Positive finite timing limit required: '+key)
 density=[max(math.dist(a['pointMm'],b['pointMm'])/1000/limits['maximumSpeedMps'],abs(b['yawRadians']-a['yawRadians'])*180/math.pi/limits['maxYawDegreesPerSecond'],abs(b['pitchRadians']-a['pitchRadians'])*180/math.pi/limits['maxPitchDegreesPerSecond'],1/fps/10) for a,b in zip(f,f[1:])]
 # Optional chapter budgets may be stricter than the global motion ceilings.
 # This keeps observation pace while permitting faster already-seen connections.
 for ch in c.get('chapters',[]):
  local=ch.get('timingLimits',{})
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
 for name in ['visits','stopFrames']:
  for m in o.get(name,[]):
   index=m.get('frameIndex',m.get('frame'));at=min(n-1,round(times[index]*fps));m['seconds']=at/fps
   if 'frameIndex' in m:m['frameIndex']=at
   else:m['frame']=at
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
