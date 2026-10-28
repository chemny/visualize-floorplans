import copy,math,unittest
from tour_motion_comfort import regularize,gaze_windows,position_window,cubic_path,creep_arc_window
from tour_speed_profile import profile
class ComfortTests(unittest.TestCase):
 def fixture(self):
  fs=[{'frame':i,'pointMm':[i*10,0],'yawRadians':i*.003+(.08 if i==30 else 0),'pitchRadians':-.1,'eyeMm':1600,'horizontalFovDegrees':76,'shiftY':0} for i in range(65)]
  return {'fps':24,'seconds':65/24,'frames':fs,'visits':[{'name':'a','frame':0},{'name':'b','frame':64}]},{'chapters':[{'name':'move','phase':'transit','from':'a','to':'b','subjects':[]}]}
 def test_regularization_reduces_angular_jerk_and_preserves_context(self):
  import numpy as np
  x=np.arange(65)*.1;x[30]+=.8;y=regularize(x)
  self.assertLess(np.max(np.abs(np.diff(y,n=3))),np.max(np.abs(np.diff(x,n=3))))
  self.assertTrue(np.array_equal(x[:3],y[:3]));self.assertTrue(np.array_equal(x[-3:],y[-3:]))
 def test_gaze_patch_preserves_position_time_and_outside_frames(self):
  t,c=self.fixture();before=copy.deepcopy(t);new,r=gaze_windows(t,c,[(5,59)])
  self.assertEqual(t,before);self.assertEqual(t['seconds'],new['seconds']);self.assertEqual([f['pointMm'] for f in t['frames']],[f['pointMm'] for f in new['frames']]);self.assertEqual(new['frames'][:6],t['frames'][:6]);self.assertEqual(new['frames'][59:],t['frames'][59:])
 def test_overlapping_gaze_windows_are_rejected(self):
  t,c=self.fixture()
  with self.assertRaisesRegex(ValueError,'overlap'):gaze_windows(t,c,[(5,30),(20,40)])
 def test_unsafe_position_proposal_is_rejected(self):
  class Blocked:
   def blocked(self,p):return True
   def line_free(self,a,z):return False
  t,c=self.fixture();new,r=position_window(t,Blocked(),5,59);self.assertFalse(r['accepted']);self.assertEqual(new,t)
 def test_bezier_uses_actual_endpoints(self):
  pts=cubic_path([[0,0],[100,0],[100,100],[200,100]],24);self.assertEqual(pts[0],[0,0]);self.assertEqual(pts[-1],[200,100]);self.assertEqual(len(pts),25)
 def test_nonzero_boundary_speeds_are_preserved_by_arc_profile(self):
  p=profile([[0,0],[2000,0]],start_speed=300,end_speed=400);self.assertEqual(p['speed'][0],300);self.assertEqual(p['speed'][-1],400)
  with self.assertRaisesRegex(ValueError,'Endpoint speed'):profile([[0,0],[1000,0]],end_speed=1400)
 def test_gentle_approach_preserves_time_arc_end_and_checks_obstacles(self):
  class Clear:
   def blocked(self,p):return False
   def line_free(self,a,z):return True
  class Blocked(Clear):
   def blocked(self,p):return p[0]>0
  fs=[{'frame':i,'pointMm':[max(0,i-60)*20,0]} for i in range(102)]
  t={'frames':fs,'fps':24,'seconds':102/24};original=copy.deepcopy(t)
  new,report=creep_arc_window(t,Clear(),2,95,40,.4)
  self.assertEqual(t,original);self.assertEqual(new['frames'][:3],t['frames'][:3]);self.assertEqual(new['frames'][95:],t['frames'][95:]);self.assertEqual(new['seconds'],t['seconds'])
  self.assertTrue(all(x['pointMm'][1]==0 for x in new['frames']));self.assertGreater(new['frames'][20]['pointMm'][0],0)
  with self.assertRaisesRegex(ValueError,'obstacle'):creep_arc_window(t,Blocked(),2,95,40,.4)
  with self.assertRaisesRegex(ValueError,'walking cap'):creep_arc_window(t,Clear(),2,95,40,.4,{'motionReviewLimits':{'maximumSpeedMps':.1}})
if __name__=='__main__':unittest.main()
