import copy, json, math, unittest
from pathlib import Path
from camera_gaze import generate, PROFILE

class CameraGazeTests(unittest.TestCase):
 def setUp(self):
  self.profile=json.loads(PROFILE.read_text());self.tour={'fps':24,'seconds':4,'frames':[{'frame':i,'pointMm':[i*10,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0} for i in range(96)],'visits':[{'name':'in','frame':0},{'name':'out','frame':95}]}
  self.config={'cameraKeys':[{'atStop':'in','targetMm':[-1000,30,1400]},{'atStop':'out','targetMm':[-1000,-30,1400]}]}
 def test_short_arc_and_path_identity(self):
  original=copy.deepcopy(self.tour);out=generate(self.tour,self.config,self.profile)
  self.assertEqual(original,self.tour)
  self.assertEqual([f['pointMm'] for f in original['frames']],[f['pointMm'] for f in out['frames']])
  self.assertEqual(out['seconds'],original['seconds']);self.assertEqual(len(out['frames']),96)
  ys=[f['yawRadians'] for f in out['frames']]
  self.assertLess(max(ys)-min(ys),.15) # crosses ±π without a full spin
  self.assertTrue(all(f['horizontalFovDegrees']==76 for f in out['frames']))
 def test_bad_marker_not_silent(self):
  self.config['cameraKeys'][0]['atStop']='unknown'
  with self.assertRaises(ValueError):generate(self.tour,self.config,self.profile)
 def test_duplicate_key_rejected(self):
  self.config['cameraKeys'][1]['atStop']='in'
  with self.assertRaises(ValueError):generate(self.tour,self.config,self.profile)
 def test_motion_failure_kept_diagnostic(self):
  self.tour['frames'][50]['pointMm']=[90000,0]
  out=generate(self.tour,self.config,self.profile)
  self.assertIn('maximumSpeedMps',out['cameraMethod']['thresholdFailures'])
  self.assertTrue(out['previewOnly']);self.assertEqual(out['humanAcceptance'],'pending')
 def test_reference_config_loads_without_case_specific_code(self):
  b=PROFILE.parents[2]/'reference-cases/jujian-champagne-pearl/tour'
  tour=json.loads((b/'tour.json').read_text());config=json.loads((b/'route-config.json').read_text())
  out=generate(tour,config,self.profile)
  self.assertEqual([f['pointMm'] for f in tour['frames']],[f['pointMm'] for f in out['frames']])
  self.assertTrue(math.isfinite(out['audit']['maxYawDegreesPerSecond']))

if __name__=='__main__':unittest.main()
