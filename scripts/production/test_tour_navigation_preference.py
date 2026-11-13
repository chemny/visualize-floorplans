import math,unittest
from plan_route import Planner
from design_homeowner_tour import navigation_gaze
from camera_gaze import delta
class NavigationPreferenceTests(unittest.TestCase):
 def setUp(self):
  self.p=Planner({'model':{'footprint':[[0,0],[6000,0],[6000,6000],[0,6000]],'rooms':[]},'state':{'walls':[],'furniture':[]}}, {})
 def test_tighter_case_preference_keeps_travel_in_view_without_changing_end_framing(self):
  for rotation in (0,math.pi/2):
   points=[[1000+4000*u*math.cos(rotation),1000+4000*u*math.sin(rotation)] for u in [i/40 for i in range(41)]];ds=[i*100 for i in range(41)];end=rotation+math.pi/4
   default=navigation_gaze(self.p,points,ds,end,end)
   strict=navigation_gaze(self.p,points,ds,end,end,{'preferredHeadingDegrees':20,'forwardWeight':150})
   self.assertAlmostEqual(abs(delta(default[20],rotation)),math.pi/4)
   self.assertLess(abs(delta(strict[20],rotation)),math.radians(21))
   self.assertAlmostEqual(delta(strict[0],end),0);self.assertAlmostEqual(delta(strict[-1],end),0)
 def test_invalid_preference_is_rejected_instead_of_relaxing_forward_motion(self):
  for bad in (-1,61,True,float('nan')):
   with self.assertRaisesRegex(ValueError,'Preferred navigation heading'):
    navigation_gaze(self.p,[[1000,1000],[2000,1000]],[0,1000],0,0,{'preferredHeadingDegrees':bad})
if __name__=='__main__':unittest.main()
