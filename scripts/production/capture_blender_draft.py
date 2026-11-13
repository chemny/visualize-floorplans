"""Executed only inside existing Blender, for bounded review capture."""
import bpy,sys,json,hashlib,struct,math,time,argparse
from pathlib import Path
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent))
from import_blender import set_camera
from blender_draft import validate
GENERATOR_SHA256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--job',required=True);p.add_argument('--out',required=True);p.add_argument('--shard-index',type=int,default=0);p.add_argument('--shard-count',type=int,default=1);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);job=json.loads(Path(a.job).read_text());refs,tour=validate(job,Path(a.job).parent,review=job.get('schema')=='homeowner-blender-review-job/1');out=Path(a.out)
if not 1<=a.shard_count<=job.get('captureWorkers',1) or not 0<=a.shard_index<a.shard_count:raise ValueError('Invalid capture shard')
from tour_stage_gate import resolve
for record in job.get('captureImplementation',[]):resolve(record,Path(a.job).parent)
s=bpy.context.scene;cam=s.camera;cam.rotation_mode='QUATERNION';anchor=tour['frames'][job['anchorFrame']]
# Reject a scene from another house even if a job provides a different model size.
ids={o.get('schemeSha256') for o in s.objects if o.type=='MESH' and o.get('schemeSha256')}
if ids!={tour['schemeSha256']}:raise ValueError('Scene source scheme differs from route')
def fingerprint():
 h=hashlib.sha256()
 for o in sorted(s.objects,key=lambda o:o.name):
  if o.type=='MESH' and o.name!='Exterior-reference-backdrop' and o.get('presentationRole')!='exterior':
   h.update(o.name.encode());h.update(str([v for r in o.matrix_world for v in r]).encode())
   for v in o.data.vertices:h.update(struct.pack('fff',*v.co))
   for f in o.data.polygons:h.update(str(list(f.vertices)).encode())
 return h.hexdigest()
expected=Vector(((anchor['pointMm'][0]-job['model']['width']/2)/1000,-(anchor['pointMm'][1]-job['model']['depth']/2)/1000,anchor['eyeMm']/1000))
if (cam.location-expected).length>1e-5:raise ValueError('Saved static scene camera is not the declared anchor')
before=fingerprint();back=s.objects.get('Exterior-reference-backdrop');backdrop=None
if back:
 # Homothety preserves every anchor-camera ray while moving the background into the distance.
 c=Vector(((anchor['pointMm'][0]-job['model']['width']/2)/1000,-(anchor['pointMm'][1]-job['model']['depth']/2)/1000,anchor['eyeMm']/1000))
 scale=job.get('exteriorDistanceScale',5)
 if not isinstance(scale,(int,float)) or not 1<=scale<=6:raise ValueError('Invalid background depth')
 err=0
 for v in back.data.vertices:
  original=back.matrix_world@v.co;new=c+(original-c)*scale
  err=max(err,(new-c).normalized().cross((original-c).normalized()).length);v.co=back.matrix_world.inverted()@new
 back.data.update();backdrop={'depthScale':scale,'anchorRayDirectionMaxError':err,'representation':'distant planar concept background; not surveyed outdoor geometry'}
 if err>1e-6:raise ValueError('Background anchor projection changed')
room_changes=[];window_coverage=[]
if refs.get('roomPresentation'):
 from blender_room_presentation import apply,coverage
 profile=json.loads(refs['roomPresentation'].read_text());room_changes=apply(s,profile);window_coverage=coverage(s,profile,tour,job['model'])
 if any(not row['fullCoverage'] for row in window_coverage):raise ValueError('Window background does not cover moving source viewpoints')
s.render.use_persistent_data=True;s.render.use_motion_blur=False
s.render.engine='CYCLES';s.render.resolution_x=job.get('width',960);s.render.resolution_y=round(s.render.resolution_x*9/16);s.render.resolution_percentage=100;s.render.use_border=False;s.render.use_crop_to_border=False;s.cycles.samples=job.get('samples',48);s.cycles.adaptive_threshold=.015;s.cycles.seed=42;s.cycles.use_animated_seed=False;s.cycles.use_denoising=True
from blender_render_quality import apply as apply_quality,diagnostic_path,save_passes
quality={'schema':'blender-render-quality/1'};raw_node=apply_quality(s,quality,s.cycles.samples)
if refs.get('qualityProfile'):
 from blender_render_quality import apply as apply_quality,diagnostic_path,save_passes
 quality=json.loads(refs['qualityProfile'].read_text());raw_node=apply_quality(s,quality,s.cycles.samples)
from blender_execution import select,LEGACY_PROFILE
execution=json.loads(refs['executionProfile'].read_text()) if 'executionProfile' in refs else LEGACY_PROFILE
if execution.get('requirePackedImages'):
 for image in bpy.data.images:
  if image.source in ('FILE','TILED') and not image.packed_file and not getattr(image,'packed_files',[]):raise ValueError('Remote render requires packed image: '+image.name)
device_receipt=select(s,bpy.context.preferences.addons['cycles'].preferences,execution);device=device_receipt['actual']
if s.cycles.denoiser=='OPTIX' and device not in ('OPTIX','CUDA'):raise ValueError('OptiX denoiser requires an explicitly available NVIDIA GPU')
timings=[]
frames=out/'frames';frames.mkdir(exist_ok=True);
suffix=f'-{a.shard_index}' if a.shard_count>1 else ''
receipts_path=out/f'frame-receipts{suffix}.jsonl';receipts={}
if receipts_path.exists():
 for line in receipts_path.read_text().splitlines():
  try:
   row=json.loads(line);receipts[row['frame']]=row
  except (ValueError,KeyError):pass
s.render.image_settings.file_format='PNG';s.render.image_settings.color_mode='RGB';audit=[];start=time.monotonic()
for local,i in enumerate(range(job['startFrame'],job['endFrameExclusive'])):
 if local%a.shard_count!=a.shard_index:continue
 f=tour['frames'][i];r=set_camera(s,cam,f,job['model']);cam.data.clip_end=100
 # Stable visibility audit in actual scene coordinates, including door/wall occluders.
 deps=bpy.context.evaluated_depsgraph_get();near=0;hits=0;distances=[];tan=math.tan(math.radians(f.get('horizontalFovDegrees',76))/2);aspect=s.render.resolution_x/s.render.resolution_y
 for y in [-.6,-.3,0,.3,.6]:
  for x in [-.8,-.4,0,.4,.8]:
   direction=cam.rotation_quaternion@Vector((x*tan,(y-f.get('shiftY',0))*tan/aspect,-1)).normalized();hit,loc,n,idx,obj,matrix=s.ray_cast(deps,cam.location,direction,distance=100)
   if hit:
    distance=(loc-cam.location).length;near+=distance<.35;hits+=1;distances.append(distance)
 path=frames/f'frame-{local:06d}.png';s.render.filepath=str(path)
 reuse=local in receipts and receipts[local].get('sourceFrame')==i and path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest()==receipts[local]['sha256']
 if reuse and raw_node is not None:
  reuse=len(receipts[local].get('auxiliary',[]))==2 and all(Path(q['path']).is_file() and hashlib.sha256(Path(q['path']).read_bytes()).hexdigest()==q['sha256'] for q in receipts[local]['auxiliary'])
 if not reuse:
  if raw_node is not None:diagnostic_path(raw_node,out,local)
  render_start=time.monotonic()
  try:bpy.ops.render.render(write_still=True)
  except RuntimeError:
   if device not in ('METAL','OPTIX','CUDA') or not execution.get('allowCpuFallback',False):raise
   if s.cycles.denoiser=='OPTIX':raise
   s.cycles.device='CPU';device='CPU-fallback';bpy.ops.render.render(write_still=True)
  timings.append({'sourceFrame':i,'seconds':time.monotonic()-render_start})
  auxiliary=[]
  if raw_node is not None:
   exr=save_passes(s,out,local);auxiliary.append({'role':'multilayer-raw-and-light-passes','path':str(exr),'sha256':hashlib.sha256(exr.read_bytes()).hexdigest()})
   raw=list((out/'raw-frames').glob(f'frame-{local:06d}*.png'))
   if len(raw)!=1:raise ValueError('Expected exactly one raw image output')
   auxiliary.append({'role':'raw-before-denoising','path':str(raw[0]),'sha256':hashlib.sha256(raw[0].read_bytes()).hexdigest()})
  with receipts_path.open('a') as log:log.write(json.dumps({'frame':local,'sourceFrame':i,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'auxiliary':auxiliary})+'\n')
 audit.append({'sourceFrame':i,'projectionError':r['projectionNdcMaxError'],'location':r['location'],'nearSurfaceFraction':near/25,'centralRayHitCount':hits})
 if local%12==0 or i==job['endFrameExclusive']-1:
  temp=out/f'capture-progress{suffix}.partial';temp.write_text(json.dumps({'schema':'blender-capture-progress/1','completedFrames':len(audit),'expectedFrames':len(range(job['startFrame']+a.shard_index,job['endFrameExclusive'],a.shard_count)),'lastSourceFrame':i,'elapsedSeconds':time.monotonic()-start,'device':device,'samples':s.cycles.samples}));temp.replace(out/f'capture-progress{suffix}.json')
 print('DRAFT_FRAME',local,i,flush=True)
if fingerprint()!=before:raise ValueError('Interior meshes changed')
(out/f'frame-timing{suffix}.json').write_text(json.dumps(timings,indent=2))
(out/f'execution{suffix}.json').write_text(json.dumps({**device_receipt,'actual':device,'motionBlur':s.render.use_motion_blur,'denoiser':s.cycles.denoiser,'denoisingInputPasses':s.cycles.denoising_input_passes,'seed':s.cycles.seed},indent=2))
(out/f'capture-audit{suffix}.json').write_text(json.dumps({'generatorSha256':GENERATOR_SHA256,'interiorGeometryUnchanged':True,'cameraFromExactSourceFrames':True,'maxProjectionError':max(r['projectionError'] for r in audit),'nearSurfaceWarnings':[r['sourceFrame'] for r in audit if r['nearSurfaceFraction']>.6],'frames':audit,'exterior':backdrop,'roomPresentationChanges':room_changes,'windowCoverage':window_coverage,'device':device,'seconds':time.monotonic()-start,'samples':s.cycles.samples,'qualityProfile':quality,'actualQuality':{'adaptiveSampling':s.cycles.use_adaptive_sampling,'minimumSamples':s.cycles.adaptive_min_samples,'noiseThreshold':s.cycles.adaptive_threshold,'denoiser':s.cycles.denoiser,'denoisingPasses':s.cycles.denoising_input_passes,'causticsReflective':s.cycles.caustics_reflective,'causticsRefractive':s.cycles.caustics_refractive,'diagnosticPassesSaved':raw_node is not None},'resolution':[s.render.resolution_x,s.render.resolution_y]},indent=2));print('BLENDER_DRAFT_PASS',flush=True)
