import unittest
from wall_anchor_layout import anchor,audit
class WallAnchorTest(unittest.TestCase):
 def setUp(self):
  self.f={'id':'cab','cx':1500,'cy':1500,'w':1000,'d':600,'rot':0}
 def test_four_faces_and_reversed_endpoints(self):
  for side,a,b,coord,rot in [('south',[0,0],[3000,0],400,0),('north',[3000,3000],[0,3000],2600,180),('east',[0,3000],[0,0],400,-90),('west',[3000,0],[3000,3000],2600,90)]:
   with self.subTest(side=side):
    f=dict(self.f);w={'id':'w','a':a,'b':b,'t':200};anchor(f,w,side)
    self.assertEqual(f['cy' if side in ('north','south') else 'cx'],coord);self.assertEqual(f['rot'],rot)
 def test_real_wall_thickness_and_install_gap(self):
  w={'id':'w','a':[0,0],'b':[3000,0],'t':240};f=dict(self.f);anchor(f,w,'south',20)
  self.assertEqual(f['cy'],440);self.assertEqual(audit(f,w,'south',20)['backGapMm'],20)
 def test_opening_and_partial_demolition_rejected_atomically(self):
  for extras in [{'opens':[{'at':1000,'width':800}]},{'removedIntervals':[[1000,1800]]}]:
   f=dict(self.f);w={'id':'w','a':[0,0],'b':[3000,0],'t':200,**extras}
   with self.assertRaises(ValueError):anchor(f,w,'south')
   self.assertEqual(f,self.f)
 def test_stale_relationship_after_manual_movement(self):
  w={'id':'w','a':[0,0],'b':[3000,0],'t':200};f=dict(self.f);anchor(f,w,'south');f['cy']+=100
  with self.assertRaises(ValueError):audit(f,w,'south')
 def test_short_or_missing_support_rejected(self):
  for w in [{'id':'w','a':[0,0],'b':[1700,0],'t':200},{'id':'w','a':[0,0],'b':[3000,0],'t':200,'demolished':True}]:
   with self.assertRaises(ValueError):anchor(dict(self.f),w,'south')
if __name__=='__main__':unittest.main()
