"""Synthetic confirmations only; verifies stopping before any media work."""
import copy,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from tour_stage_gate import CHECKS,pending,bound,require_video,prepare,compose
import test_tour_pages

class StageGateTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  self.video=self.p/'v.mp4';self.video.write_bytes(b'video');self.tour=self.p/'tour.json';self.tour.write_text(json.dumps({'fps':2,'seconds':2,'frames':[{}]*4}))
  self.review=self.p/'review.json';self.r=pending(self.video,self.tour)
  self.voice=self.p/'voice.wav';self.voice.write_bytes(b'voice')
 def approved(self):
  self.r.update(status='approved',confirmedBy='synthetic-user',evidence='Synthetic test only');self.r['checks']={k:True for k in CHECKS};self.save()
 def save(self):self.review.write_text(json.dumps(self.r))
 def job(self):return {'video':bound(self.video),'tour':bound(self.tour),'videoReview':bound(self.review),'voice':bound(self.voice),'captions':[{'start':0,'end':1.5,'text':'欢迎参观。'}]}
 def probe(self):return patch('tour_pages.probe_video',return_value={'fps':2,'seconds':2,'frames':4,'width':320,'height':180,'hasAudio':False})
 def test_pending_rejected_before_probe_processing_or_output(self):
  self.save()
  for fn in (prepare,compose):
   with patch('tour_pages.probe_video') as probe,patch('tour_stage_gate.subprocess.run') as run:
    with self.assertRaisesRegex(ValueError,'approved'):fn(self.job(),self.p,self.p/'blocked')
    probe.assert_not_called();run.assert_not_called();self.assertFalse((self.p/'blocked').exists())
 def test_capture_release_sample_failed_and_missing_evidence_not_acceptance(self):
  self.approved();original=copy.deepcopy(self.r)
  for delta in ({'status':'failed'},{'schema':'homeowner-review-release/1'},{'purpose':'sample'},{'reviewCaptureOnly':True},{'evidence':''},{'approvalSource':'automatic'},{'checks':{}}):
   self.r={**original,**delta};self.save()
   with self.assertRaises(ValueError):require_video(self.review,self.video,self.tour)
 def test_video_and_tour_changes_invalidate(self):
  self.approved()
  for p in (self.video,self.tour):
   old=p.read_bytes();p.write_bytes(old+b' ')
   with self.assertRaises(ValueError):require_video(self.review,self.video,self.tour)
   p.write_bytes(old)
 def test_different_target_same_duration_is_rejected(self):
  self.approved();other=self.p/'other.mp4';other.write_bytes(b'other')
  with self.assertRaisesRegex(ValueError,'different video'):require_video(self.review,other,self.tour)
 def test_prepare_checks_exact_acceptance_and_never_produces_audio(self):
  self.approved()
  with self.probe(),patch('tour_stage_gate.subprocess.run') as run:r=prepare(self.job(),self.p,self.p/'prepared')
  run.assert_not_called();self.assertFalse(r['approvalGranted']);self.assertIsNone(json.loads((self.p/'prepared/composition-job.json').read_text())['voice'])
 def test_sample_cannot_authorize_production(self):
  self.approved()
  with self.assertRaisesRegex(ValueError,'Sample jobs'):prepare({**self.job(),'sample':True},self.p,self.p/'blocked')
 def test_packaging_rejects_unreviewed_narration_but_video_page_stops(self):
  fixture=test_tour_pages.TourPagesTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
  from tour_pages import build,read
  job=fixture.job();job.pop('videoReview')
  with fixture.probe():
   with self.assertRaisesRegex(ValueError,'video review'):build(fixture.manifest,fixture.p/'blocked',job)
   self.assertFalse((fixture.p/'blocked').exists())
   r=build(fixture.manifest,fixture.p/'video-only',{'video':fixture.video()})
  self.assertEqual(r['stages']['narrated'],'not_generated');self.assertEqual(read(fixture.p/'video-only/video-review.pending.json')['status'],'pending')
 def test_real_compose_keeps_video_and_timebase(self):
  ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
  if not ffmpeg or not ffprobe:self.skipTest('Existing FFmpeg tools unavailable')
  subprocess.run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=c=beige:s=320x180:r=2:d=2','-c:v','libx264','-pix_fmt','yuv420p',str(self.video)],check=True)
  subprocess.run([ffmpeg,'-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=1.8',str(self.voice)],check=True)
  self.r=pending(self.video,self.tour);self.approved();j=self.job();j['ffprobe']=ffprobe
  r=compose(j,self.p,self.p/'composed',ffmpeg)
  self.assertEqual(r['status'],'pending_narrated_review');self.assertTrue(r['videoFramesCopied']);self.assertFalse(r['approvalGranted'])
  trace=r['reproduction'];self.assertEqual(trace['inputs']['voice'],bound(self.voice));self.assertIsNone(trace['inputs']['music'])
  self.assertEqual(json.loads((self.p/'composed/captions-source.json').read_text()),j['captions']);self.assertIn('-c:v',trace['ffmpeg']['argv']);self.assertIn('ffmpeg version',trace['ffmpeg']['version'])
  self.assertEqual(trace['inputs']['originalCaptions'],bound(self.p/'composed/captions-source.json'));self.assertIn('tour_subtitles.py',trace['generators'])
  p=subprocess.run([ffprobe,'-v','error','-show_entries','stream=codec_type','-of','json',str(self.p/'composed/narrated.mp4')],check=True,capture_output=True,text=True)
  self.assertEqual({s['codec_type'] for s in json.loads(p.stdout)['streams']},{'video','audio','subtitle'})

 def test_real_mix_with_music_keeps_timing_and_selectable_subtitles(self):
  ffmpeg=shutil.which('ffmpeg');ffprobe=shutil.which('ffprobe')
  if not ffmpeg or not ffprobe:self.skipTest('Existing FFmpeg tools unavailable')
  subprocess.run([ffmpeg,'-v','error','-y','-f','lavfi','-i','color=c=beige:s=320x180:r=2:d=2','-c:v','libx264','-pix_fmt','yuv420p',str(self.video)],check=True)
  subprocess.run([ffmpeg,'-v','error','-y','-f','lavfi','-i','sine=frequency=440:duration=2',str(self.voice)],check=True)
  self.r=pending(self.video,self.tour);self.approved();j=self.job();j.update(ffprobe=ffprobe,music=bound(self.voice),musicGain=.35)
  r=compose(j,self.p,self.p/'mix',ffmpeg)
  self.assertEqual(r['captionsMode'],'selectable_mp4_and_sidecar');self.assertEqual(r['status'],'pending_narrated_review')
  self.assertEqual(r['reproduction']['inputs']['music'],bound(self.voice));self.assertNotIn('sidechaincompress',str(r['reproduction']['ffmpeg']['argv']));self.assertIn('volume=0.35',str(r['reproduction']['ffmpeg']['argv']));self.assertEqual(r['reproduction']['musicGain'],.35)
 def test_cli_pending_review_cannot_start_composition(self):
  import sys
  self.save();job=self.p/'job.json';job.write_text(json.dumps(self.job()))
  r=subprocess.run([sys.executable,str(Path(__file__).with_name('h5.py')),'narration-compose','--job',str(job),'--out',str(self.p/'blocked')],capture_output=True,text=True)
  self.assertNotEqual(r.returncode,0);self.assertIn('explicitly approved',r.stderr);self.assertFalse((self.p/'blocked').exists())
