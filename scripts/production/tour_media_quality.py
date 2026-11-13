"""Video diagnostics distinguish global flashes, local residuals and playback; never visual approval."""
import json,math
from pathlib import Path
from tour_stage_gate import resolve,bound
from remote_production import write

def analyse(frames,regions,threshold=.06):
 from runtime_requirements import module
 cv2=module('cv2');import numpy as np
 if len(frames)<2:raise ValueError('Need consecutive frames')
 if not 0<threshold<1:raise ValueError('Invalid diagnostic threshold')
 boxes=[]
 for row in regions:
  b=row['bounds']
  if len(b)!=4 or not all(type(v) in (int,float) and math.isfinite(v) for v in b) or not 0<=b[0]<b[2]<=1 or not 0<=b[1]<b[3]<=1:raise ValueError('Invalid normalized local region')
  boxes.append((row['name'],b))
 records=[];duplicates=[];previous=None
 for i,f in enumerate(frames):
  gray=cv2.resize(f,(320,180)).astype('float32')/255
  if gray.ndim==3:gray=cv2.cvtColor(gray,cv2.COLOR_BGR2GRAY)
  if previous is not None:
   if np.array_equal(previous,gray):duplicates.append(i)
   backward=cv2.calcOpticalFlowFarneback((gray*255).astype('uint8'),(previous*255).astype('uint8'),None,.5,3,17,3,5,1.2,0)
   forward=cv2.calcOpticalFlowFarneback((previous*255).astype('uint8'),(gray*255).astype('uint8'),None,.5,3,17,3,5,1.2,0)
   y,x=np.mgrid[:180,:320].astype('float32');mx=x+backward[:,:,0];my=y+backward[:,:,1]
   consistency=np.linalg.norm(backward+cv2.remap(forward,mx,my,cv2.INTER_LINEAR),axis=2)
   mask=(mx>=3)&(mx<317)&(my>=3)&(my<177)&(consistency<2)
   diff=gray-cv2.remap(previous,mx,my,cv2.INTER_LINEAR);local=[]
   for name,b in boxes:
    roi=np.zeros_like(mask);roi[int(b[1]*180):int(b[3]*180),int(b[0]*320):int(b[2]*320)]=True;valid=mask&roi
    local.append({'name':name,'validFraction':float(valid.sum()/max(1,roi.sum())),'signedMedian':float(np.median(diff[valid])) if valid.any() else None,'absoluteP90':float(np.percentile(np.abs(diff[valid]),90)) if valid.any() else None})
   records.append({'frame':i,'globalSignedMedian':float(np.median(diff[mask])) if mask.any() else None,'local':local})
  previous=gray
 return {'schema':'homeowner-temporal-diagnostic/1','frames':len(frames),'globalFlashFlags':[r['frame'] for r in records if r['globalSignedMedian'] is not None and abs(r['globalSignedMedian'])>threshold],
 'localResidualFlags':[{'frame':r['frame'],'region':v['name']} for r in records for v in r['local'] if v['validFraction']>.5 and v['absoluteP90'] is not None and v['absoluteP90']>threshold],
 'duplicateFramePairs':duplicates,'localRegions':regions,'rows':records,'localCheckStatus':'diagnostic_only' if regions else 'not_sampled',
 'limitations':['Screen regions are not world-surface tracking. Disocclusion, moving highlights and reflections may cause false positives.','Duplicate images may be intentional holds; they do not prove rendering/frame-rate failure.','No global flash flags does not prove no local flicker.','Sampling noise, denoising shimmer, thin-edge aliasing,24fps cadence and browser drops require separate diagnosis.'],
 'visualReviewRequired':True,'userApprovalGranted':False}

def inspect(job,base,out):
 from runtime_requirements import module
 cv2=module('cv2')
 from tour_pages import probe_video
 if job.get('schema')!='homeowner-video-quality-job/1':raise ValueError('Unsupported quality job')
 video=resolve(job['video'],base);probe=probe_video(video,job.get('ffprobe'));cap=cv2.VideoCapture(str(video));frames=[]
 while True:
  ok,frame=cap.read()
  if not ok:break
  frames.append(cv2.resize(frame,(320,180)))
 cap.release()
 if len(frames)!=probe['frames']:raise ValueError('Decode missing/corrupt frames')
 result=analyse(frames,job.get('regions',[]),job.get('threshold',.06));result.update(video=bound(video),probe=probe)
 write(out,result);return result

def require_visual(record,video,base):
 p=resolve(record,base);r=json.loads(p.read_text())
 if r.get('schema')!='homeowner-media-visual-review/1' or r.get('status') not in ('engineer_checked','engineer_checked_with_known_issues'):raise ValueError('Actual visual review required')
 if resolve(r['video'],p.parent)!=Path(video).resolve() or r.get('method')!='continuous_playback' or not r.get('reviewer','').strip() or not r.get('notes','').strip():raise ValueError('Incomplete/stale continuous visual review')
 if any(r.get('checks',{}).get(k) is not True for k in ('clarity','edges','localFlicker','occlusion','lighting')):raise ValueError('Visual checks incomplete')
 if r['status']=='engineer_checked_with_known_issues' and not r.get('knownIssues'):raise ValueError('Known issues must remain disclosed')
 return r
