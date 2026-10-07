import unittest
from layout_access_checks import check_routes,chair_envelope
from wall_anchor_layout import anchor_corner,audit_corner
class AccessAndCornerTests(unittest.TestCase):
 def test_clear_table_can_have_blocking_pulled_chair(self):
  chair={'cx':1000,'cy':1000,'w':450,'d':450,'rot':180}
  route=[{'id':'entry','rect':[0,1350,2000,2250],'targetWidthMm':900}]
  self.assertEqual(check_routes(route,[{'id':'chair','rect':chair_envelope(chair,0)}]),[])
  self.assertEqual(check_routes(route,[{'id':'chair-pulled','rect':chair_envelope(chair,300)}])[0]['routeId'],'entry')
 def test_corner_on_split_back_wall_and_real_faces(self):
  walls=[{'id':'west1','a':[0,0],'b':[0,600],'t':200},{'id':'west2','a':[0,600],'b':[0,3000],'t':200}]
  north={'id':'north','a':[0,0],'b':[3000,0],'t':200}
  f={'id':'book','cx':1500,'cy':1500,'w':1000,'d':350,'rot':0}
  anchor_corner(f,walls,'east',north,'south',1,1)
  self.assertEqual((f['cx'],f['cy'],f['rot']),(276,601,-90));self.assertEqual(audit_corner(f,walls,'east',north,'south',1,1)['endGapMm'],1)
  f['cy']+=100
  with self.assertRaises(ValueError):audit_corner(f,walls,'east',north,'south',1,1)
 def test_corner_with_window_is_rejected_atomically(self):
  wall={'id':'west','a':[0,0],'b':[0,3000],'t':200}
  top={'id':'top','a':[0,0],'b':[3000,0],'t':200,'opens':[{'at':100,'width':600}]}
  f={'id':'cab','cx':1500,'cy':1500,'w':1000,'d':600,'rot':0};old=dict(f)
  with self.assertRaises(ValueError):anchor_corner(f,[wall],'east',top,'south')
  self.assertEqual(f,old)
if __name__=='__main__':unittest.main()
