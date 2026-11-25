"""Case-neutral regressions for rooms the user passes through (walk in, walk out) and for the faster back-out."""
import unittest
from tour_core_targets import excused_rooms
from design_homeowner_tour import mark_speed_limits
from tour_workflow import shaped_distance_times

class OpenFloor:
 def gap_at(self,p):return 5000.

POLICY={'cruiseMps':1.1,'narrowCruiseMps':.95,'rampSeconds':.5,'floorMps':.15}

def line(n,back_from=None):
 frames=[{'pointMm':[i*40.,0.]} for i in range(n)]
 for f in frames[back_from:] if back_from is not None else []:f['backOut']=True
 return frames

class PassThroughRooms(unittest.TestCase):
 def test_core_target_exclusion_needs_a_non_empty_user_reason(self):
  rows=[{'roomId':'a','reason':'Synthetic user reason'},{'roomId':'b','reason':''},{'roomId':'c','reason':'  '},{'roomId':'d'},'e']
  self.assertEqual(excused_rooms({'coreTargetPolicy':{'excludedRooms':rows}}),{'a'})
  self.assertEqual(excused_rooms({}),set())
 def test_back_out_factor_only_speeds_up_marked_frames(self):
  frames=line(40,back_from=20);mark_speed_limits(frames,OpenFloor(),dict(POLICY,backOutSpeedFactor=1.5))
  self.assertAlmostEqual(frames[5]['speedLimitMps'],1.1);self.assertAlmostEqual(frames[30]['speedLimitMps'],1.65)
  plain=line(40,back_from=20);mark_speed_limits(plain,OpenFloor(),POLICY);self.assertAlmostEqual(plain[30]['speedLimitMps'],1.1)
 def test_back_out_intervals_are_quicker_than_going_in_but_never_above_the_factor(self):
  frames=line(80,back_from=40);mark_speed_limits(frames,OpenFloor(),dict(POLICY,backOutSpeedFactor=1.5))
  times=shaped_distance_times(frames,dict(POLICY,backOutSpeedFactor=1.5))
  inward=times[20];outward=times[60];self.assertLess(outward,inward)
  self.assertGreaterEqual(outward,.04/1.65-1e-9)  # 40 mm per frame, never faster than 1.5 x cruise
if __name__=='__main__':unittest.main()
