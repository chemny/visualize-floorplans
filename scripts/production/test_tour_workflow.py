import copy,json,math,tempfile,unittest
from pathlib import Path
from tour_workflow import metrics,retime,refine,intent_check,require_preview,sha,scene_review_sha
from camera_gaze import PROFILE

class TourWorkflowTests(unittest.TestCase):
 def setUp(self):
  self.t={'fps':24,'seconds':1,'schemeSha256':'case','frames':[{'frame':i,'pointMm':[i*100,0],'eyeMm':1600,'yawRadians':i*.03,'pitchRadians':0} for i in range(24)],'visits':[{'name':'entry','frame':0},{'name':'room','frame':12},{'name':'exit','frame':23}]}
  self.c={'chapters':[{'name':'view','from':'entry','to':'room','phase':'observe','subjects':['cabinet'],'minimumSeconds':2},{'name':'return','from':'room','to':'exit','phase':'transit'}]};self.l={'maximumSpeedMps':1.2,'maxYawDegreesPerSecond':32,'maxPitchDegreesPerSecond':14}
 def test_retime_limits_and_endpoints(self):
  o=retime(self.t,self.c,self.l);m=metrics(o)
  self.assertGreater(o['seconds'],self.t['seconds']);self.assertLessEqual(m['maximumSpeedMps'],1.200001);self.assertLessEqual(m['maxYawDegreesPerSecond'],32.000001)
  self.assertEqual(o['frames'][0]['pointMm'],self.t['frames'][0]['pointMm']);self.assertEqual(o['frames'][-1]['pointMm'],self.t['frames'][-1]['pointMm']);self.assertEqual(o['visits'][-1]['frame'],len(o['frames'])-1)
  self.assertFalse(o['cameraMethod']['positionsAndFrameTimingUnchanged']);self.assertTrue(o['timingMethod']['requiresNewMeshAndSubjectAudit'])
 def test_observation_pace_and_faster_connections(self):
  for f in self.t['frames']:f['yawRadians']=0
  self.c['chapters'][0].update(minimumSeconds=0,timingLimits={'maximumSpeedMps':.4})
  out=retime(self.t,self.c,self.l);at=out['visits'][1]['frame']
  self.assertLessEqual(metrics({'fps':24,'frames':out['frames'][:at]})['maximumSpeedMps'],.400001)
  self.assertGreater(metrics({'fps':24,'frames':out['frames'][at+2:]})['maximumSpeedMps'],.8)
  self.c['chapters'][0]['timingLimits']['maximumSpeedMps']=1.3
  with self.assertRaises(ValueError):retime(self.t,self.c,self.l)
 def test_repeat_observation_needs_reason(self):
  self.c['chapters'][1].update(phase='observe',subjects=['cabinet']);self.assertTrue(intent_check(self.t,self.c)['failures'])
  self.c['chapters'][1]['repeatReason']='exit detail';self.assertFalse(intent_check(self.t,self.c)['failures'])
 def test_sway_report_and_local_baseline(self):
  baseline=copy.deepcopy(self.t);o=refine(self.t,[{'startSeconds':.2,'endSeconds':.7,'yawBumpDegrees':4}]);self.assertEqual(self.t,baseline)
  for i,(a,b) in enumerate(zip(self.t['frames'],o['frames'])):
   self.assertEqual(a['pointMm'],b['pointMm']);self.assertEqual(a['eyeMm'],b['eyeMm'])
   if i/24<.2 or i/24>.7:self.assertEqual(a,b)
  self.assertIn('positiveYawTravelDegrees',metrics(o));self.assertEqual(o['seconds'],self.t['seconds'])
 def test_preview_gate_missing_stale_and_resolution_transfer(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'tour.json').write_text(json.dumps(self.t));scene={'renderSettings':{'size':[1280,720]},'materials':['pearl']};(p/'scene.json').write_text(json.dumps(scene));(p/'geometry.bin').write_bytes(b'geometry');(p/'renderer.html').write_text('renderer')
   with self.assertRaises(ValueError):require_preview(None,p/'tour.json',p)
   checks={k:True for k in ['turnSamplesViewed','wholePreviewViewed','subjectsReadable','paceComfortable','noBlankCaptureEdges']};arts={}
   for k in ['turnSamples','wholePreview','subjectAudit','meshAudit']:
    q=p/(k+'.json');q.write_text(json.dumps({'tourSha256':sha(p/'tour.json'),'schemeSha256':'case','status':'pass','meshAudit':{'hits':[]},'errors':[]}));arts[k]={'path':q.name,'sha256':sha(q)}
   r={'schema':'homeowner-preview-review/1','status':'passed','reviewedBy':'actual reviewer','tourSha256':sha(p/'tour.json'),'schemeSha256':'case','sceneReviewSha256':scene_review_sha(p),'geometrySha256':sha(p/'geometry.bin'),'rendererSha256':sha(p/'renderer.html'),'checks':checks,'artifacts':arts};q=p/'review.json';q.write_text(json.dumps(r));require_preview(q,p/'tour.json',p)
   scene['renderSettings']['size']=[1920,1080];(p/'scene.json').write_text(json.dumps(scene));require_preview(q,p/'tour.json',p)
   scene['materials']=['changed'];(p/'scene.json').write_text(json.dumps(scene))
   with self.assertRaises(ValueError):require_preview(q,p/'tour.json',p)
   (p/'scene.json').write_text(json.dumps({'renderSettings':{'size':[1280,720]},'materials':['pearl']}));r['tourSha256']='stale';q.write_text(json.dumps(r))
   with self.assertRaises(ValueError):require_preview(q,p/'tour.json',p)
if __name__=='__main__':unittest.main()
