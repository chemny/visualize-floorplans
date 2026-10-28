import math,unittest
from unittest.mock import patch
from tour_navigation_coverage import gaze

class PassageCoverageTests(unittest.TestCase):
 def test_side_passage_coverage_is_an_objective_without_changing_path(self):
  points=[[0,y] for y in range(0,2001,100)];dist=list(range(0,2001,100))
  policy={'coveragePolygons':[[[-1600,-200],[1600,-200],[1600,2400],[-1600,2400]]],'minimumCoveragePercent':80,'maximumEffortSeconds':12}
  original=[p[:] for p in points]
  with patch('design_homeowner_tour.clear_distance',return_value=100000):
   ys=gaze(None,points,dist,math.pi/2,math.pi/2,policy)
  self.assertEqual(points,original);self.assertEqual(len(ys),len(points));self.assertAlmostEqual(ys[0],math.pi/2);self.assertAlmostEqual(ys[-1],math.pi/2)
  self.assertGreater(max(ys)-min(ys),math.radians(30))
 def test_insufficient_budget_rejects_without_relaxing_limits(self):
  with patch('design_homeowner_tour.clear_distance',return_value=100000):
   with self.assertRaisesRegex(ValueError,'bounded connection effort'):
    gaze(None,[[0,0],[1000,0]],[0,1000],0,0,{'coveragePolygons':[[[-100,-100],[1100,-100],[1100,100],[-100,100]]],'minimumCoveragePercent':80,'coverageGridMm':100,'maximumEffortSeconds':.1})
 def test_requires_explicit_nonempty_geometry_and_percentage(self):
  with self.assertRaises(ValueError):gaze(None,[[0,0],[100,0]],[0,100],0,0,{'coveragePolygons':[],'minimumCoveragePercent':80})

if __name__=='__main__':unittest.main()
