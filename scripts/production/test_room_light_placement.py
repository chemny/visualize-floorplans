import unittest
from room_light_placement import room_center,apply_room_light_defaults
from lighting_checks import inside
class RoomLightDefaults(unittest.TestCase):
 def test_polygon_center_not_label(self):
  self.assertEqual(room_center([[0,0],[2000,0],[2000,1000],[0,1000]]),[1000,500])
 def test_concave_inside(self):
  poly=[[0,0],[3000,0],[3000,500],[500,500],[500,3000],[0,3000]]
  self.assertTrue(inside(room_center(poly),poly))
 def test_default_only_once(self):
  c={'model':{'rooms':[{'id':'r','poly':[[0,0],[1000,0],[1000,1000],[0,1000]]}]},'initialState':{'furniture':[{'id':'manual','type':'ceilinground','cx':50,'cy':80},{'id':'default','type':'ceilinground','roomId':'r','defaultPlacement':'room-center','cx':1,'cy':2}]}}
  apply_room_light_defaults(c);m,f=c['initialState']['furniture'];self.assertEqual([m['cx'],m['cy']],[50,80]);self.assertEqual([f['cx'],f['cy']],[500,500]);f['cx']=650;apply_room_light_defaults(c);self.assertEqual(f['cx'],650)
if __name__=='__main__':unittest.main()
