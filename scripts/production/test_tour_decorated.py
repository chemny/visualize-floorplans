"""Synthetic input/graph tests; no remote service or invented user acceptance."""
import copy,json,tempfile,unittest,shutil,subprocess,sys
from pathlib import Path
from tour_decorated import prepare,read,ready,review_image,make_graph,validate_plan,segment_sha,graph_sha,frozen_graph,bound,write,assemble,assembly_receipt
class DecoratedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  self.t=self.p/'tour.json';self.t.write_text(json.dumps({'fps':2,'seconds':4,'frames':[{}]*8,'schemeSha256':'synthetic'}))
  for name in ['bundle.json','config.json']:(self.p/name).write_text('{}')
  for f in range(8):(self.p/f'frame-{f:06d}.png').write_bytes(b'synthetic-only-'+str(f).encode())
  self.job={'tour':str(self.t),'bundle':str(self.p/'bundle.json'),'config':str(self.p/'config.json'),'sourceFramesDir':str(self.p),'authorizationEvidence':'Synthetic test, never an actual approval','maximumSegmentSeconds':2,'keyframeSpacingSeconds':1,'render':{'unet':'test','lora':'test','loraStrength':.8,'clip':'test','vae':'test','shiftVideo':12,'shiftAudio':3,'width':512,'height':288,'steps':8,'seed':1,'prompt':'test'}}
  self.out=self.p/'out';self.plan=self.out/'decoration-plan.json'
 def images(self):
  p=read(self.plan)
  for f in sorted(set(k['sourceFrame'] for s in p['segments'] for k in s['keyframes'])):
   source=self.p/f'frame-{f:06d}.png'
   review_image(self.plan,f,source,{k:True for k in ['layoutPreserved','cameraPreserved','noInventedFixtures','styleConsistent']},'Synthetic validation fixture')
  return read(self.plan)
 def test_no_intermediate_video_required_and_full_timeline(self):
  p=prepare(self.job,self.out);validate_plan(p);self.assertNotIn('sourceVideo',p['sources']);self.assertEqual(p['frames'],8);self.assertFalse(p['narrationAllowed'])
 def test_gap_overlap_duplicate_and_wrong_binding_rejected(self):
  p=prepare(self.job,self.out)
  for key,value in [('startFrame',3),('endFrame',9)]:
   c=copy.deepcopy(p);c['segments'][1][key]=value
   with self.assertRaises(ValueError):validate_plan(c)
  c=copy.deepcopy(p);c['segments'][0]['keyframes'][1]['targetFrame']+=1
  with self.assertRaisesRegex(ValueError,'exact local'):validate_plan(c)
 def test_temporal_guides_are_actual_nodes_not_just_prompt(self):
  prepare(self.job,self.out);p=self.images();s=p['segments'][0];g=make_graph(p,s,{str(k['sourceFrame']):'uploaded.png' for k in s['keyframes']})
  nodes=[v['inputs']['frame_idx'] for v in g.values() if v['class_type']=='MiniMaxH3AddGuide']
  self.assertEqual(nodes,[2,4]);self.assertEqual(g['9']['inputs']['length'],124);self.assertEqual(g['11']['inputs']['conditioning'],['101',0])
  self.assertFalse(any(v['class_type'] in ['LoadVideo','MiniMaxH3FunControlNetApply'] for v in g.values()))
 def test_unreviewed_and_changed_images_block_generation(self):
  p=prepare(self.job,self.out)
  with self.assertRaisesRegex(ValueError,'Unreviewed'):ready(p,p['segments'][0])
  p=self.images();Path(p['segments'][0]['keyframes'][0]['imagePath']).write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'changed'):ready(p,p['segments'][0])
 def test_failed_image_review_is_not_recorded(self):
  prepare(self.job,self.out)
  with self.assertRaisesRegex(ValueError,'review evidence'):review_image(self.plan,0,self.p/'frame-000000.png',{},'')
  self.assertEqual(read(self.plan)['imageReviews'],{})
 def test_native_cli_check_reports_ready_without_approval(self):
  prepare(self.job,self.out);self.images()
  r=subprocess.run([sys.executable,str(Path(__file__).with_name('h5.py')),'decoration-check','--plan',str(self.plan)],capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertIn('ready',r.stdout);self.assertIn('False',r.stdout)
 def test_known_failed_video_cannot_be_assembled(self):
  prepare(self.job,self.out);p=self.images();s=p['segments'][0];d=self.out/'segments'/s['id'];d.mkdir()
  write(d/'receipt.json',{'visualReview':{'status':'failed','evidence':'Synthetic invented fixture'}})
  with self.assertRaisesRegex(ValueError,'Known failed visual'):assemble(self.plan,self.p/'joined','unused','unused')
  self.assertFalse((self.p/'joined').exists())
 def test_changed_source_and_existing_output_rejected(self):
  p=prepare(self.job,self.out);self.t.write_text('{}')
  with self.assertRaisesRegex(ValueError,'changed source'):validate_plan(p)
  with self.assertRaisesRegex(ValueError,'new empty'):prepare(self.job,self.out)
 def test_other_segment_image_review_does_not_invalidate_passed_segment(self):
  prepare(self.job,self.out);p=self.images();before=segment_sha(p,p['segments'][0])
  p['imageReviews']['7']['evidence']='Different review of later frame'
  self.assertEqual(before,segment_sha(p,p['segments'][0]));self.assertNotEqual(segment_sha(p,p['segments'][1]),segment_sha(read(self.plan),p['segments'][1]))
 def test_resume_uses_exact_frozen_upload_names_and_rejects_changed_inputs(self):
  prepare(self.job,self.out);p=self.images();s=p['segments'][0];dest=self.out/'segments'/s['id'];dest.mkdir()
  g=make_graph(p,s,{str(k['sourceFrame']):'original-upload.png' for k in s['keyframes']})
  write(dest/'graph.json',g);write(dest/'intent.json',{'client_id':'fixture','graphSha256':graph_sha(g),'segmentSha256':segment_sha(p,s)})
  actual,_=frozen_graph(p,s,dest,None);self.assertEqual(actual,g)
  p['render']['seed']=2
  with self.assertRaisesRegex(ValueError,'parameters'):frozen_graph(p,s,dest,None)
 def frozen_fixture(self):
  prepare(self.job,self.out);p=self.images();s=p['segments'][0];d=self.out/'segments'/s['id'];d.mkdir();v=d/'silent.mp4';v.write_bytes(b'synthetic frozen clip')
  r=d/'receipt.json';write(r,{'segment':s['id'],'startFrame':s['startFrame'],'endFrame':s['endFrame'],'segmentSha256':segment_sha(p,s),'video':bound(v)})
  q=copy.deepcopy(p);q['frozenSegments']={s['id']:{'plan':bound(self.plan),'segmentId':s['id'],'receipt':bound(r)}}
  return q,s,r,v
 def test_frozen_clip_keeps_its_original_image_identity_at_changed_shared_boundary(self):
  q,s,r,v=self.frozen_fixture();q['imageReviews']['4']['evidence']='Current adjoining segment uses a new actual video boundary guide'
  self.assertNotEqual(segment_sha(q,s),read(r)['segmentSha256'])
  self.assertEqual(assembly_receipt(q,s,self.p/'new')['video'],bound(v))
 def test_frozen_clip_rejects_changed_timing_profile_and_video(self):
  q,s,r,v=self.frozen_fixture();changed=copy.deepcopy(q);changed['render']['seed']=9
  with self.assertRaisesRegex(ValueError,'changed source'):assembly_receipt(changed,s,self.p)
  changed=copy.deepcopy(s);changed['endFrame']-=1
  with self.assertRaisesRegex(ValueError,'segment changed'):assembly_receipt(q,changed,self.p)
  v.write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'changed source'):assembly_receipt(q,s,self.p)
 def test_frozen_status_never_waives_known_visual_failure(self):
  q,s,r,v=self.frozen_fixture();receipt=read(r);receipt['visualReview']={'status':'failed'};write(r,receipt);q['frozenSegments'][s['id']]['receipt']=bound(r)
  with self.assertRaisesRegex(ValueError,'Known failed visual'):assembly_receipt(q,s,self.p)
 def test_real_assembly_keeps_complete_timebase_and_pending_approval(self):
  ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
  if not ffmpeg or not ffprobe:self.skipTest('Existing FFmpeg unavailable')
  prepare(self.job,self.out);p=self.images()
  for s in p['segments']:
   d=self.out/'segments'/s['id'];d.mkdir();v=d/'silent.mp4'
   subprocess.run([ffmpeg,'-v','error','-f','lavfi','-i','color=c=beige:s=512x288:r=2:d=2','-c:v','libx264','-pix_fmt','yuv420p',str(v)],check=True)
   write(d/'receipt.json',{'segmentSha256':segment_sha(p,s),'video':bound(v),'startFrame':s['startFrame'],'endFrame':s['endFrame']})
  r=assemble(self.plan,self.p/'joined',ffmpeg,ffprobe)
  self.assertEqual(r['probe']['frames'],8);self.assertEqual(r['probe']['seconds'],4);self.assertFalse(r['approvalGranted']);self.assertFalse(r['narrationAllowed'])
  self.assertEqual(read(self.p/'joined/video-review.pending.json')['status'],'pending')
if __name__=='__main__':unittest.main()
