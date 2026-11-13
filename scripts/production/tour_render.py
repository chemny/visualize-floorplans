"""Shared render preparation. No capture, install, route planning or approval."""
import json, math, shutil, sys
from pathlib import Path
from tour_stage_gate import resolve, bound
ENGINES={'h5':'标准渲染','blender':'高质量渲染 · Blender'}
def engine(job):
 e=job.get('rendering',{}).get('engine','h5')
 if e not in ENGINES:raise ValueError('Unsupported rendering.engine; choose h5 or blender')
 return e

def validate_route(tour,scheme):
 fps=tour.get('fps');frames=tour.get('frames',[])
 if tour.get('schemeSha256')!=scheme:raise ValueError('Route belongs to another scheme')
 if not isinstance(fps,(int,float)) or isinstance(fps,bool) or not math.isfinite(fps) or fps<=0 or not frames:raise ValueError('Invalid route timebase')
 if abs(tour.get('seconds',0)-len(frames)/fps)>1e-5:raise ValueError('Route duration differs from exact frame count')
 for f in frames:
  values=[*f['pointMm'],f['eyeMm'],f['yawRadians'],f['pitchRadians'],f.get('horizontalFovDegrees',76),f.get('shiftY',0)]
  if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values):raise ValueError('Invalid exact camera frame')
 return tour

def prepare(job,base,out):
 if job.get('schema')!='homeowner-render-job/1':raise ValueError('Unsupported render job')
 e=engine(job);base=Path(base);bundle=resolve(job.get('bundle'),base);tour=resolve(job.get('tour'),base)
 b=json.loads(bundle.read_text());t=validate_route(json.loads(tour.read_text()),b['schemeSha256'])
 runtime=Path(job['runtime']);runtime=runtime if runtime.is_absolute() else base/runtime
 scene=json.loads((runtime/'scene.json').read_text())
 if any(scene[k]!=b[k] for k in ('schemeSha256','model','state')):raise ValueError('Runtime differs from confirmed bundle')
 from route_rehearsal import require_route
 review=resolve(job.get('routeReview'),base);require_route(review,tour,runtime)
 out=Path(out)
 if out.exists():raise ValueError('Use a fresh render preparation directory')
 profile=resolve(job['profile'],base) if job.get('profile') else None
 config=resolve(job['config'],base) if e=='blender' else None
 # Distributed review samples plus the greatest direction change; never a new route.
 ids=sorted({0,len(t['frames'])-1,*[round((len(t['frames'])-1)*i/4) for i in range(1,4)]})
 receipt={'schema':'homeowner-render-preparation/1','engine':e,'engineLabel':ENGINES[e],'bundle':bound(bundle),'tour':bound(tour),'routeReview':bound(review),'runtimeScene':bound(runtime/'scene.json'),'runtimeGeometry':bound(runtime/'geometry.bin'),'profile':bound(profile) if profile else None,'fps':t['fps'],'frames':len(t['frames']),'seconds':t['seconds'],'representativeFrames':ids,'routeReplanned':False,'videoGenerated':False,'approvalGranted':False,'nextStage':'standard_capture' if e=='h5' else 'static_samples_then_dynamic_validation','blenderFullAnimationEnabled':False}
 out.mkdir(parents=True);shutil.copy2(tour,out/'tour.json')
 commands=[]
 if e=='blender':
  script=Path(__file__).with_name('run_production.py')
  for i in ids:
   cmd=[sys.executable,str(script),'--engine','blender','--bundle',str(bundle),'--route',str(tour),'--runtime',str(runtime),'--frame',str(i),'--config',str(config),'--out',str((out/f'static-{i}').resolve())]
   if profile:cmd+=['--render-profile',str(profile)]
   commands.append(cmd)
 (out/'render-plan.json').write_text(json.dumps({**receipt,'staticCommands':commands,'dynamicChecks':['same_camera_projection','door_occlusion','material_and_shadow_flicker','denoising_stability','window_parallax','render_cost'],'dynamicStatus':'not_validated'},ensure_ascii=False,indent=2))
 return receipt
