import math,unittest
from types import SimpleNamespace
from design_homeowner_tour import clear_distance
from plan_route import Planner
class VisibilityGeometryTests(unittest.TestCase):
 def test_oblique_leaf_does_not_fill_its_axis_aligned_bounding_box(self):
  p=SimpleNamespace(walls=[],leaves=[([0,0],[1000,1000],10)])
  self.assertEqual(clear_distance(p,[100,800],math.pi,500),500)
 def test_real_oblique_panel_is_still_opaque(self):
  p=SimpleNamespace(walls=[],leaves=[([0,0],[1000,1000],10)])
  self.assertAlmostEqual(clear_distance(p,[0,500],0,1000),500-10*math.sqrt(2))
 def test_legacy_opaque_point_obstacle_remains_visible(self):
  p=SimpleNamespace(walls=[],leaves=[([500,0],[500,0],9)])
  self.assertEqual(clear_distance(p,[0,0],0,1000),491)
 def test_flat_doorway_jamb_does_not_invent_an_along_wall_cap(self):
  p=SimpleNamespace(walls=[([0,0],[1000,0],50)],leaves=[])
  self.assertEqual(clear_distance(p,[1020,-100],math.pi/2,500),500)
  self.assertAlmostEqual(clear_distance(p,[980,-100],math.pi/2,500),50)
 def test_ray_inside_real_strip_returns_zero(self):
  p=SimpleNamespace(walls=[([0,0],[1000,0],50)],leaves=[])
  self.assertEqual(clear_distance(p,[500,0],0,500),0)
 def test_rotated_world_keeps_intersection_distance(self):
  for a in (.3,1.2,2.1):
   rot=lambda p:[p[0]*math.cos(a)-p[1]*math.sin(a),p[0]*math.sin(a)+p[1]*math.cos(a)]
   p=SimpleNamespace(walls=[(rot([0,0]),rot([1000,0]),50)],leaves=[])
   self.assertAlmostEqual(clear_distance(p,rot([500,-200]),a+math.pi/2,1000),150)
 def test_shower_glass_remains_physical_but_is_not_an_opaque_view_wall(self):
  f={'id':'s','type':'shower','cx':2000,'cy':2000,'w':900,'d':900,'h':2100,'rot':0,'showerDoor':{'type':'hinged','hinge':'left','angle':90,'open':0}}
  poly=[[0,0],[5000,0],[5000,5000],[0,5000]]
  p=Planner({'model':{'footprint':poly,'rooms':[{'id':'r','poly':poly}]},'state':{'walls':[],'furniture':[f]}},{'bodyRadiusMm':180})
  self.assertGreater(len(p.leaves),0);self.assertTrue(p.blocked([1555,2000]));self.assertFalse(p.vision_leaves)
  self.assertEqual(clear_distance(p,[2000,3000],-math.pi/2,2000),2000)
if __name__=='__main__':unittest.main()
