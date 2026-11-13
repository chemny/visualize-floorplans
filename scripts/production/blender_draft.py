"""Exact-route Blender review capture with separate short/full authorization."""
import json,math,subprocess,sys,shutil,hashlib,uuid
from pathlib import Path
from tour_stage_gate import resolve,bound
from tour_render import validate_route

def validate(job,base,*,review=False):
 if job.get('schema')!=('homeowner-blender-review-job/1' if review else 'homeowner-blender-draft-job/1'):raise ValueError('Unsupported draft job')
 refs={k:resolve(job.get(k),base) for k in ('scene','tour','bundle','staticApproval','authorization','routeReview','routeScene','routeGeometry')}
 if job.get('executionProfile'):
  refs['executionProfile']=resolve(job['executionProfile'],base)
  from blender_execution import validate as validate_execution
  validate_execution(json.loads(refs['executionProfile'].read_text()))
 if job.get('roomPresentation'):
  refs['roomPresentation']=resolve(job['roomPresentation'],base)
  if json.loads(refs['roomPresentation'].read_text()).get('schema')!='blender-room-presentation/1':raise ValueError('Unsupported room presentation')
 if job.get('qualityProfile'):
  refs['qualityProfile']=resolve(job['qualityProfile'],base)
  from blender_render_quality import validate as validate_quality
  validate_quality(json.loads(refs['qualityProfile'].read_text()),job.get('samples',48))
 auth=json.loads(refs['authorization'].read_text());approval=json.loads(refs['staticApproval'].read_text());t=json.loads(refs['tour'].read_text())
 bundle=json.loads(refs['bundle'].read_text());validate_route(t,bundle['schemeSha256'])
 from route_rehearsal import require_route
 require_route(refs['routeReview'],refs['tour'],runtime_scene=refs['routeScene'],runtime_geometry=refs['routeGeometry'])
 route_scene=json.loads(refs['routeScene'].read_text())
 if any(route_scene.get(k)!=bundle.get(k) for k in ('schemeSha256','model','state')):raise ValueError('Approved route scene differs from current bundle')
 if job.get('model')!={k:bundle['model'][k] for k in ('width','depth')}:raise ValueError('Model dimensions differ from source bundle')
 if auth.get('scope')!=('blender_review_film' if review else 'blender_dynamic_draft') or auth.get('status')!='approved' or auth.get('approvalSource')!='explicit_user_confirmation' or not auth.get('evidence','').strip():raise ValueError('Explicit draft authorization required')
 for k in ('scene','tour','bundle','staticApproval','routeReview','routeScene','routeGeometry',*(['roomPresentation'] if 'roomPresentation' in refs else []),*(['qualityProfile'] if 'qualityProfile' in refs else []),*(['executionProfile'] if 'executionProfile' in refs else [])):
  if resolve(auth.get(k),refs['authorization'].parent)!=refs[k]:raise ValueError('Draft authorization source mismatch')
 if approval.get('status')!='user_confirmed' or not approval.get('evidence','').strip():raise ValueError('Static sample is not user confirmed')
 resolve(approval.get('image'),refs['staticApproval'].parent)
 if resolve(approval.get('scene'),refs['staticApproval'].parent)!=refs['scene']:raise ValueError('Static approval belongs to different scene')
 a,z=job.get('startFrame'),job.get('endFrameExclusive')
 if any(not isinstance(v,int) or isinstance(v,bool) for v in (a,z)) or not 0<=a<z<=len(t['frames']):raise ValueError('Invalid source frame interval')
 if review:
  if a!=0 or z!=len(t['frames']):raise ValueError('Review film must preserve the entire exact route')
  from blender_review_film import require_evidence
  require_evidence(job,auth,base,refs)
 elif (z-a)/t['fps']>5 or z-a==len(t['frames']):raise ValueError('Only a short draft up to 5 seconds is allowed')
 if auth.get('startFrame')!=a or auth.get('endFrameExclusive')!=z:raise ValueError('Frame interval differs from authorization')
 for key,lo,hi in [('width',320,1920),('samples',8,128)]:
  v=job.get(key,960 if key=='width' else 48)
  if not isinstance(v,int) or isinstance(v,bool) or not lo<=v<=hi:raise ValueError('Invalid '+key)
 workers=job.get('captureWorkers',1)
 if type(workers)!=int or not 1<=workers<=2 or (workers!=1 and not review):raise ValueError('Invalid capture worker count')
 anchor=job.get('anchorFrame')
 if not isinstance(anchor,int) or isinstance(anchor,bool) or not 0<=anchor<len(t['frames']):raise ValueError('Invalid static anchor')
 if auth.get('anchorFrame')!=anchor:raise ValueError('Static anchor differs from authorization')
 return refs,t

def verify_frames(out,job):
 out=Path(out);audit=json.loads((out/'capture-audit.json').read_text());a,z=job['startFrame'],job['endFrameExclusive'];count=z-a
 if not audit.get('interiorGeometryUnchanged') or not audit.get('cameraFromExactSourceFrames') or [r['sourceFrame'] for r in audit['frames']]!=list(range(a,z)):raise ValueError('Capture audit/frame sequence mismatch')
 if audit['samples']!=job.get('samples',48) or audit['resolution']!=[job.get('width',960),round(job.get('width',960)*9/16)]:raise ValueError('Capture quality differs from bound job')
 files=sorted((out/'frames').glob('frame-*.png'))
 if [f.name for f in files]!=[f'frame-{i:06d}.png' for i in range(count)]:raise ValueError('Missing/extra rendered frames')
 receipts={}
 for path in out.glob('frame-receipts*.jsonl'):
  latest={}
  for line in path.read_text().splitlines():
   try:r=json.loads(line);latest[r['frame']]=r
   except (ValueError,KeyError):continue
  for key,row in latest.items():
   if key in receipts:raise ValueError('Duplicate frame across capture shards')
   receipts[key]=row
 if set(receipts)!=set(range(count)):raise ValueError('Incomplete frame receipts')
 digest=hashlib.sha256()
 for i,f in enumerate(files):
  row=receipts[i]
  if row['sourceFrame']!=a+i or bound(f)['sha256']!=row['sha256']:raise ValueError('Rendered frame hash/source mismatch')
  digest.update(row['sha256'].encode())
 return audit,digest.hexdigest()

def run(job,base,out,blender,ffmpeg,*,review=False,on_phase=None):
 phase=on_phase or (lambda name:None)
 refs,t=validate(job,base,review=review);out=Path(out).resolve()
 capture=Path(__file__).with_name('capture_blender_draft.py')
 implementations=[capture,Path(__file__),Path(__file__).with_name('blender_room_presentation.py'),Path(__file__).with_name('import_blender.py'),Path(__file__).with_name('blender_execution.py'),Path(__file__).with_name('blender_render_quality.py'),Path(__file__).with_name('route_rehearsal.py'),Path(__file__).with_name('runtime_requirements.py')]
 normalized={**job,**{k:bound(v) for k,v in refs.items()},'model':job['model'],'captureImplementation':[bound(p) for p in implementations]}
 if out.exists():
  if not (out/'job.json').is_file() or json.loads((out/'job.json').read_text())!=normalized:raise ValueError('Use fresh output; resume requires identical bound job')
 from runtime_requirements import blender as require_blender,program
 blender=require_blender(blender);ffmpeg=program(ffmpeg,'ffmpeg')
 out.mkdir(parents=True,exist_ok=True)
 (out/'job.json').write_text(json.dumps(normalized,indent=2))
 from blender_execution import arguments
 graphics=arguments(json.loads(refs['executionProfile'].read_text())) if 'executionProfile' in refs else []
 cmd=[blender,'--background','--factory-startup',*graphics,'--disable-autoexec',str(refs['scene']),'--python-exit-code','1','--python',str(capture),'--','--job',str(out/'job.json'),'--out',str(out)]
 workers=job.get('captureWorkers',1)
 complete=False
 if (out/'capture-audit.json').exists():
  try:verify_frames(out,job);complete=True
  except (ValueError,KeyError,FileNotFoundError):pass
 phase('rendering' if not complete else 'verifying_frames')
 if complete:pass
 elif workers==1:
  with (out/'capture.log').open('w') as log:subprocess.run(cmd,check=True,stdout=log,stderr=subprocess.STDOUT)
 else:
  logs=[];processes=[]
  try:
   for i in range(workers):
    log=(out/f'capture-{i}.log').open('w');logs.append(log)
    processes.append(subprocess.Popen(cmd+['--shard-index',str(i),'--shard-count',str(workers)],stdout=log,stderr=subprocess.STDOUT))
   failures=[p.wait() for p in processes]
   if any(failures):raise RuntimeError('Blender capture worker failed: '+str(failures))
  finally:
   for p in processes:
    if p.poll() is None:p.terminate();p.wait()
   for log in logs:log.close()
  reports=[json.loads((out/f'capture-audit-{i}.json').read_text()) for i in range(workers)]
  audit=reports[0].copy();audit['frames']=sorted([row for r in reports for row in r['frames']],key=lambda r:r['sourceFrame'])
  if [r['sourceFrame'] for r in audit['frames']]!=list(range(job['startFrame'],job['endFrameExclusive'])):raise ValueError('Missing/duplicate exact source frames')
  for r in reports:
   if not r['interiorGeometryUnchanged'] or not r['cameraFromExactSourceFrames'] or r['resolution']!=audit['resolution'] or r['samples']!=audit['samples'] or r['generatorSha256']!=audit['generatorSha256']:raise ValueError('Capture worker settings differ')
  audit['nearSurfaceWarnings']=sorted({f for r in reports for f in r['nearSurfaceWarnings']});audit['maxProjectionError']=max(r['maxProjectionError'] for r in reports);audit['seconds']=max(r['seconds'] for r in reports);audit['workers']=workers;audit['device']=[r['device'] for r in reports]
  (out/'capture-audit.json').write_text(json.dumps(audit,indent=2))
 # Recheck every source after capture. No mid-job edits can receive a success receipt.
 phase('verifying_frames');audit,frame_digest=verify_frames(out,job)
 validate(job,base,review=review)
 for record in normalized['captureImplementation']:resolve(record,base)
 from tour_pages import probe_video
 phase('encoding');video=out/('review.mp4' if review else 'draft.mp4');encoding=out/'encoding-receipt.json'
 if video.exists():
  r=json.loads(encoding.read_text()) if encoding.exists() else {}
  if r.get('videoSha256')!=bound(video)['sha256'] or r.get('frameDigest')!=frame_digest:raise ValueError('Unbound existing encoded video; preserve and inspect it')
 else:
  temp=out/('encode-'+uuid.uuid4().hex+'.mp4')
  subprocess.run([ffmpeg,'-nostdin','-n','-v','error','-framerate',str(t['fps']),'-i',str(out/'frames/frame-%06d.png'),'-frames:v',str(job['endFrameExclusive']-job['startFrame']),'-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(temp)],check=True)
  probe=probe_video(temp)
  if probe['frames']!=job['endFrameExclusive']-job['startFrame'] or abs(probe['fps']-t['fps'])>1e-6 or probe['hasAudio']:raise ValueError('Encoded draft timebase/audio changed')
  from remote_production import write
  write(encoding,{'videoSha256':bound(temp)['sha256'],'frameDigest':frame_digest,'probe':probe});temp.replace(video)
 probe=probe_video(video)
 report={'schema':'homeowner-blender-review-result/1' if review else 'homeowner-blender-draft-result/1','sources':{k:bound(v) for k,v in refs.items()},'video':bound(video),'probe':probe,'sourceFrames':[job['startFrame'],job['endFrameExclusive']],'capture':json.loads((out/'capture-audit.json').read_text()),'visualReview':'pending','fullAnimationEnabled':bool(review),'purpose':'video_review' if review else 'dynamic_draft','narrationAuthorized':False}
 (out/('review-result.json' if review else 'draft-result.json')).write_text(json.dumps(report,indent=2));return report
