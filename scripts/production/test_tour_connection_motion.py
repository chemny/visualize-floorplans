import unittest,math
from tour_connection_motion import repair_positions_numpy,project_gaze_numpy
class ConnectionMotionTests(unittest.TestCase):
 def test_gaze_projection_enforces_final_speed_acceleration_and_monotone_window(self):
  values=[0.]*8+[90.]*9+[35.]*8
  result=project_gaze_numpy(values,24,32/24*.999,240/24**2*.98,{i:1 for i in range(8,16)})
  self.assertLessEqual(max(abs(b-a) for a,b in zip(result,result[1:])),32/24)
  self.assertLessEqual(max(abs(c-2*b+a) for a,b,c in zip(result,result[1:],result[2:])),240/24**2)
  self.assertTrue(all(result[i+1]>=result[i]-1e-6 for i in range(8,16)))
 def test_position_projection_keeps_observation_positions_and_frame_count(self):
  class Space:
   walls=[];leaves=[];furniture=[];radius=180
   def blocked(self,p):return False
   def line_free(self,a,b):return True
  frames=[{'pointMm':[i*20.,0.]} for i in range(31)]
  frames[12]['pointMm'][1]=80
  tour={'fps':24,'frames':frames,'visits':[{'name':'a','frame':0},{'name':'b','frame':20},{'name':'c','frame':30}]}
  config={'chapters':[{'phase':'transit','from':'a','to':'b'},{'phase':'observe','from':'b','to':'c'}]}
  result,evidence=repair_positions_numpy(tour,config,Space(),maximum_iterations=4000)
  self.assertTrue(evidence['accepted']);self.assertEqual(result['frames'][20:],frames[20:]);self.assertEqual(len(result['frames']),31)
if __name__=='__main__':unittest.main()
