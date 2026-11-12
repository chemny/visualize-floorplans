"""Independent synthetic fixtures; never changes current user deliverables or grants their approval."""
import copy,json,tempfile,unittest,subprocess,shutil
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
from tour_stage_gate import bound,CHECKS,pending,compose
from remote_production import prepare,checked,endpoint
from blender_test_fixtures import unit_route_refs

def save(p,name,value):
 f=p/name;f.write_text(json.dumps(value));return bound(f)
def capture_fixture(p):
 (p/'scene.blend').write_bytes(b'Independent synthetic scene');(p/'still.png').write_bytes(b'synthetic image')
 refs={'scene':bound(p/'scene.blend'),'tour':save(p,'tour.json',{'schemeSha256':'fixture','fps':2,'seconds':4,'frames':[{'pointMm':[500,500],'eyeMm':1600,'yawRadians':0,'pitchRadians':0}]*8}),'bundle':save(p,'bundle.json',{'schemeSha256':'fixture','model':{'width':2000,'depth':2000}})}
 refs.update(unit_route_refs(p,refs['bundle']))
 refs['staticApproval']=save(p,'static.json',{'status':'user_confirmed','evidence':'SYNTHETIC TEST ONLY','scene':refs['scene'],'image':bound(p/'still.png')})
 refs['executionProfile']=save(p,'device.json',{'schema':'blender-execution-profile/1','backend':'OPTIX','allowCpuFallback':False,'graphicsBackend':'vulkan','requirePackedImages':True})
 refs['authorization']=save(p,'auth.json',{'scope':'blender_dynamic_draft','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'SYNTHETIC TEST ONLY','startFrame':2,'endFrameExclusive':4,'anchorFrame':0,**refs})
 job={'schema':'homeowner-blender-draft-job/1',**refs,'model':{'width':2000,'depth':2000},'startFrame':2,'endFrameExclusive':4,'anchorFrame':0,'width':320,'samples':8}
 return job

class ExecutionTests(unittest.TestCase):
 def setUp(self):
  gate=patch('route_rehearsal.require_route',return_value={});gate.start();self.addCleanup(gate.stop)
  version=patch('runtime_requirements.blender',side_effect=lambda p:p);version.start();self.addCleanup(version.stop)
 def test_explicit_gpu_no_silent_fallback(self):
  from blender_execution import select,validate,arguments
  class Prefs:
   devices=[]
   def get_devices(self):self.devices=[NS(type='OPTIX',name='Synthetic GPU',use=False)] if self.compute_device_type=='OPTIX' else []
  scene=NS(cycles=NS(device='CPU'),render=NS())
  p={'schema':'blender-execution-profile/1','backend':'OPTIX','allowCpuFallback':False,'graphicsBackend':'vulkan'}
  self.assertEqual(select(scene,Prefs(),p)['actual'],'OPTIX');self.assertEqual(arguments(p),['--gpu-backend','vulkan'])
  with self.assertRaises(ValueError):select(scene,Prefs(),{**p,'backend':'METAL'})
  self.assertEqual(select(scene,Prefs(),{**p,'backend':'METAL','allowCpuFallback':True})['actual'],'CPU-fallback')
  for delta in ({'backend':'bad'},{'allowCpuFallback':1},{'requirePackedImages':'yes'},{'graphicsBackend':'bad'}):
   with self.assertRaises(ValueError):validate({**p,**delta})
 def test_quality_explicit_and_unsupported_motion_rejected(self):
  from blender_render_quality import validate
  good={'schema':'blender-render-quality/1','adaptiveSampling':False,'denoiser':'OPENIMAGEDENOISE','denoisingInputPasses':'RGB_ALBEDO_NORMAL','motionBlur':False,'seed':42}
  validate(good,128)
  for delta in ({'motionBlur':True},{'denoiser':'magic'},{'seed':True},{'denoisingInputPasses':'unknown'}):
   with self.assertRaises(ValueError):validate({**good,**delta},128)
 def test_remote_rebase_freeze_and_auth(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);capture=capture_fixture(p);cj=save(p,'capture.json',capture)
   e={'sshTarget':'synthetic-host','root':'D:/Render/test-only','python':'C:/Python/python.exe','blender':'C:/Blender/blender.exe','ffmpeg':'C:/Tools/ffmpeg.exe','ffprobe':'C:/Tools/ffprobe.exe'}
   auth=save(p,'remote-auth.json',{'scope':'remote_production','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'SYNTHETIC TRANSPORT TEST ONLY','job':cj,'kind':'blender','endpoint':e})
   job={'schema':'homeowner-remote-production-job/1','job':cj,'kind':'blender','endpoint':e,'authorization':auth}
   with patch('remote_production.ps') as network:
    result=prepare(job,p,p/'prepared');network.assert_not_called()
   self.assertEqual(result['status'],'prepared_no_remote_calls');checked(p/'prepared')
   mapped=json.loads((p/'prepared/transfer/job.json').read_text());self.assertTrue(mapped['scene']['path'].startswith(e['root']+'/inputs/'))
   self.assertEqual(mapped['scene']['sha256'],capture['scene']['sha256'])
   # Modules that read an asset when imported (the lighting checks) must find it on the worker.
   self.assertTrue((p/'prepared/transfer/assets/h5/source/renovation-components-v12.js').is_file())
   self.assertEqual(mapped['tour']['sha256'],capture['tour']['sha256'])
   (p/'prepared/transfer/scripts/production/blender_execution.py').write_text('tampered')
   with self.assertRaises(ValueError):checked(p/'prepared')
   with self.assertRaises(ValueError):prepare({**job,'kind':'upscale'},p,p/'bad')
   for target in ['-oProxyCommand=bad','host;command','host\ncommand']:
    with self.assertRaises(ValueError):endpoint({**e,'sshTarget':target})
 def test_frame_verification_rejects_corruption_and_duplicates(self):
  from blender_draft import verify_frames
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'frames').mkdir();job={'startFrame':8,'endFrameExclusive':10,'width':320,'samples':8}
   rows=[]
   for i in range(2):
    f=p/'frames'/f'frame-{i:06d}.png';f.write_bytes(bytes([i+1]));rows.append({'frame':i,'sourceFrame':8+i,'sha256':bound(f)['sha256']})
   (p/'frame-receipts.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
   save(p,'capture-audit.json',{'interiorGeometryUnchanged':True,'cameraFromExactSourceFrames':True,'frames':[{'sourceFrame':8},{'sourceFrame':9}],'resolution':[320,180],'samples':8})
   verify_frames(p,job);(p/'frames/frame-000001.png').write_bytes(b'corrupt')
   with self.assertRaises(ValueError):verify_frames(p,job)
 def test_encoding_retry_keeps_completed_capture(self):
  import sys
  from PIL import Image
  from blender_draft import run
  ff=shutil.which('ffmpeg')
  if not ff:self.skipTest('Existing FFmpeg required')
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);job=capture_fixture(p);out=p/'output';calls={'capture':0,'encode':0};actual=subprocess.run
   def fake_capture_or_encode(cmd,**kwargs):
    if cmd[0]==sys.executable:
     calls['capture']+=1;(out/'frames').mkdir()
     rows=[]
     for i in range(2):
      f=out/'frames'/f'frame-{i:06d}.png';Image.new('RGB',(320,180),(i*60,80,90)).save(f);rows.append({'frame':i,'sourceFrame':i+2,'sha256':bound(f)['sha256']})
     (out/'frame-receipts.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
     save(out,'capture-audit.json',{'interiorGeometryUnchanged':True,'cameraFromExactSourceFrames':True,'samples':8,'resolution':[320,180],'frames':[{'sourceFrame':2},{'sourceFrame':3}]})
     return NS(returncode=0)
    if cmd[0]==ff:
     calls['encode']+=1
     if calls['encode']==1:raise subprocess.CalledProcessError(1,cmd)
    return actual(cmd,**kwargs)
   with patch('blender_draft.subprocess.run',side_effect=fake_capture_or_encode):
    with self.assertRaises(subprocess.CalledProcessError):run(job,p,out,sys.executable,ff)
    r=run(job,p,out,sys.executable,ff)
    self.assertEqual(calls,{'capture':1,'encode':2});self.assertEqual(r['probe']['frames'],2)
    with self.assertRaises(ValueError):run({**job,'width':640},p,out,sys.executable,ff)
 def test_remote_worker_uses_utf8_and_json_roundtrip(self):
  import base64,re
  from remote_production import start,write
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);e={'root':'D:/Render/synthetic','python':'C:/Python/python.exe','sshTarget':'test'};r={'manifest':{'path':'fixture','sha256':'fixture'}}
   with patch('remote_production.checked',return_value=(p,r,e)),patch('remote_production.scp'),patch('remote_production.ps',side_effect=['','{"ProcessId":123,"ReturnValue":0}']) as network:
    start(p);script=network.call_args.args[1];encoded=re.search(r'EncodedCommand ([A-Za-z0-9+/=]+)',script)[1]
    self.assertIn("'-X','utf8'",base64.b64decode(encoded).decode('utf-16le'))
   write(p/'unicode.json',{'label':'独立放大测试'})
   self.assertEqual(json.loads((p/'unicode.json').read_text(encoding='utf-8'))['label'],'独立放大测试')
 def test_unknown_remote_submission_is_not_duplicated(self):
  from remote_production import start
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'submission-intent.json').write_text('{}')
   with patch('remote_production.checked',return_value=(p,{},{})),patch('remote_production.ps') as network:
    with self.assertRaises(ValueError):start(p)
    network.assert_not_called()
 def test_remote_failure_keeps_stage_and_frames(self):
  from remote_production_worker import run
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);save(p,'job.json',{'schema':'homeowner-blender-draft-job/1'});save(p,'request.json',{'kind':'blender','job':'job.json','endpoint':{'blender':'unused','ffmpeg':'ffmpeg','ffprobe':'ffprobe'}})
   save(p,'manifest.json',{'files':[]})
   def failure(*args,**kwargs):kwargs['on_phase']('encoding');raise RuntimeError('synthetic encoder error')
   with patch('blender_draft.run',side_effect=failure):
    with self.assertRaises(RuntimeError):run(p)
   state=json.loads((p/'state.json').read_text());self.assertEqual(state['failedStage'],'encoding');self.assertTrue(state['framesPreserved'])

class EnlargementTests(unittest.TestCase):
 def test_alignment_and_no_sampler_graph(self):
  from video_upscale import alignment,graph,temporal_alignment
  a=alignment(1280,720,[1920,1080]);self.assertEqual(a['input'],[1280,768]);self.assertEqual(a['cropOrigin'],[0,36]);self.assertFalse(a['originalContentCropped'])
  self.assertEqual(temporal_alignment(8)['inputFrames'],22);self.assertEqual(temporal_alignment(72)['inputFrames'],73)
  g=graph({'vae':'installed','upscalerModel':'installed','frameCount':72,'target':[1920,1080]},'video.mp4',a,'test')
  self.assertFalse(any('sampl' in n['class_type'].lower() for n in g.values()))
  with self.assertRaises(ValueError):alignment(1280,720,[1920,1200])
 def test_real_ordinary_enlargement_and_resume_rejection(self):
  from video_upscale import execute
  ff=shutil.which('ffmpeg');fp=shutil.which('ffprobe')
  if not ff or not fp:self.skipTest('Existing media tools required')
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);f=p/'source.mp4'
   subprocess.run([ff,'-v','error','-f','lavfi','-i','testsrc2=size=320x180:rate=8:duration=2','-c:v','libx264',str(f)],check=True)
   j={'schema':'homeowner-upscale-comparison-job/1','purpose':'comparison','video':bound(f),'startFrame':2,'frameCount':4,'target':[480,270],'methods':['lanczos'],'diffusionSampling':False,'frameInterpolation':False}
   j['authorization']=save(p,'auth.json',{'scope':'video_upscale_comparison','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'SYNTHETIC MEDIA TEST ONLY','settings':{k:v for k,v in j.items() if k!='schema'}})
   r=execute(j,p,p/'result',ff,fp);self.assertEqual([x['probe']['frames'] for x in r['variants']],[4,4]);self.assertEqual(r['variants'][1]['probe']['width'],480)
   execute(j,p,p/'result',ff,fp)
   (p/'result/frames/frame-000000.png').write_bytes(b'changed')
   with self.assertRaises(ValueError):execute(j,p,p/'result',ff,fp)

class InspectionTests(unittest.TestCase):
 def test_local_flash_not_hidden_by_global_median(self):
  import importlib.util
  if importlib.util.find_spec('cv2') is None:self.skipTest('Existing OpenCV required for optical-flow diagnostic')
  import numpy as np
  from tour_media_quality import analyse
  rng=np.random.default_rng(42);a=rng.integers(40,100,(180,320,3),dtype=np.uint8);b=a.copy();b[45:90,80:160]+=90
  r=analyse([a,b,a],[{'name':'patch','bounds':[.25,.25,.5,.5]}])
  self.assertEqual(r['globalFlashFlags'],[]);self.assertTrue(r['localResidualFlags']);self.assertTrue(r['visualReviewRequired']);self.assertFalse(r['userApprovalGranted'])
 def test_stale_or_incomplete_visual_review_rejected(self):
  from tour_media_quality import require_visual
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'v.mp4').write_bytes(b'fixture')
   v={'schema':'homeowner-media-visual-review/1','status':'engineer_checked','video':bound(p/'v.mp4'),'method':'continuous_playback','reviewer':'synthetic','notes':'Synthetic test only','checks':{k:True for k in ['clarity','edges','localFlicker','occlusion','lighting']}}
   require_visual(save(p,'visual.json',v),p/'v.mp4',p)
   v['method']='screenshots'
   with self.assertRaises(ValueError):require_visual(save(p,'visual.json',v),p/'v.mp4',p)
 def test_real_delivery_keeps_frames_audio_and_pending_status(self):
  from tour_delivery import inspect
  ff=shutil.which('ffmpeg');fp=shutil.which('ffprobe')
  if not ff or not fp:self.skipTest('Existing media tools required')
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);v=p/'v.mp4';voice=p/'voice.wav'
   subprocess.run([ff,'-v','error','-f','lavfi','-i','color=s=320x180:r=2:d=2','-c:v','libx264',str(v)],check=True)
   subprocess.run([ff,'-v','error','-f','lavfi','-i','sine=frequency=440:duration=2',str(voice)],check=True)
   tour=save(p,'tour.json',{'fps':2,'seconds':2,'frames':[{}]*4});a=pending(v,p/'tour.json');a.update(status='approved',confirmedBy='synthetic',evidence='SYNTHETIC TEST ONLY',checks={k:True for k in CHECKS})
   j={'video':bound(v),'tour':tour,'videoReview':save(p,'approval.json',a),'voice':bound(voice),'captions':[]}
   c=compose(j,p,p/'composed',ff);target=resolve_output=Path(c['output']['path'])
   dj={'schema':'homeowner-delivery-check-job/1','video':bound(target),'sourceVideo':bound(v),'compositionReport':bound(p/'composed/composition-report.json')}
   r=inspect(dj,p,p/'check.json',ff,fp);self.assertTrue(r['picturePacketsUnchanged']);self.assertEqual(r['audio']['clippedSamples'],0);self.assertEqual(r['status'],'needs_engineering_review');self.assertIn('continuous_visual_review_required',r['findings']);self.assertFalse(r['approvalGranted'])

if __name__=='__main__':unittest.main()
