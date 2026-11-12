import math,unittest
from tour_choreography import inspect,path_turning

def tour(camera_degrees,corner_degrees=0):
 """30 frames of walking; the path bends once by corner_degrees, the camera turns steadily by camera_degrees."""
 frames=[];x=y=0.;heading=0.
 for i in range(30):
  if i==15:heading=math.radians(corner_degrees)
  x+=40*math.cos(heading);y+=40*math.sin(heading)
  frames.append({'pointMm':[x,y],'yawRadians':math.radians(camera_degrees*i/29),'pitchRadians':0,'eyeMm':1300})
 return {'fps':10,'seconds':3.0,'frames':frames,'visits':[{'name':'a','frame':0},{'name':'b','frame':29}]}
CONFIG={'chapters':[{'name':'a → b','from':'a','to':'b','phase':'transit'}]}
def codes(*a):return sorted(i['code'] for i in inspect(tour(*a),CONFIG)['issues'] if i['code'] in ('excessive_transit_turn','transit_turn_beyond_path'))

class TurnLimits(unittest.TestCase):
 def test_turning_the_path_forces_is_free_up_to_the_absolute_limit(self):
  self.assertEqual(codes(150,90),[]);self.assertEqual(codes(80,0),[]);self.assertEqual(codes(170,90),[])
 def test_extra_turning_on_a_straight_walk_is_refused_even_below_the_absolute_limit(self):
  self.assertEqual(codes(120,0),['transit_turn_beyond_path'])
 def test_extra_over_ninety_degrees_is_refused_where_the_path_also_bends(self):
  self.assertEqual(codes(200,90),['excessive_transit_turn','transit_turn_beyond_path'])
 def test_absolute_limit_still_applies_when_the_path_bends_a_lot(self):
  self.assertEqual(codes(200,160),['excessive_transit_turn'])
 def test_both_are_reported_for_a_big_unneeded_turn(self):
  self.assertEqual(codes(270,30),['excessive_transit_turn','transit_turn_beyond_path'])
 def test_chapter_rows_carry_path_and_excess_numbers(self):
  row=inspect(tour(120,60),CONFIG)['chapters'][0];self.assertAlmostEqual(row['pathTurnDegrees'],60,delta=1);self.assertAlmostEqual(row['excessDegrees'],row['yawTravelDegrees']-row['pathTurnDegrees'])
 def test_case_may_state_a_different_extra_limit_explicitly(self):
  config={**CONFIG,'choreographyPolicy':{'maximumTransitExcessDegrees':150}};self.assertEqual([i['code'] for i in inspect(tour(120,0),config)['issues'] if i['code']=='transit_turn_beyond_path'],[])
  with self.assertRaises(ValueError):inspect(tour(120,0),{**CONFIG,'choreographyPolicy':{'maximumTransitExcessDegrees':-1}})
 def test_path_turning_ignores_tiny_jitter_and_a_stationary_pivot(self):
  frames=[{'pointMm':[0,0]},{'pointMm':[0,0]},{'pointMm':[40,0]},{'pointMm':[80,0]}];self.assertEqual(path_turning(frames),0)
if __name__=='__main__':unittest.main()
