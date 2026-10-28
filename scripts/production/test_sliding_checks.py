import unittest
from door_checks import sliding_geometry
from plan_route import Planner
class SlidingChecks(unittest.TestCase):
 def bundle(self,o):
  return {'model':{'rooms':[],'footprint':[[-1000,-1000],[4000,-1000],[4000,4000],[-1000,4000]]},'state':{'furniture':[],'walls':[{'id':'W','a':[0,0],'b':[3000,0],'t':120,'opens':[dict(id='D',kind='sliding',at=300,width=1800,**o)]}]}}
 def test_planner_uses_same_panels(self):
  for n in [2,3]:
   for d in [-1,1]:
    for op in [0,.5,1]:
     b=self.bundle(dict(leaves=n,slideDirection=d,slideOpen=op));w=b['state']['walls'][0];g=sliding_geometry(w,w['opens'][0]);p=Planner(b,{'bodyRadiusMm':100})
     self.assertEqual(len(p.leaves),n)
     for (a,z,r),panel in zip(p.leaves,g['panels']):
      self.assertAlmostEqual((a[0]+z[0])/2,panel['cx']);self.assertEqual(r,17.5)
 def test_closed_is_not_passable(self):
  p=Planner(self.bundle({'slideOpen':0}),{'bodyRadiusMm':100});self.assertTrue(p.blocked([1200,0]))
 def test_open_gap_and_stack(self):
  p=Planner(self.bundle({'slideOpen':1,'slideDirection':1}),{'bodyRadiusMm':100});self.assertFalse(p.blocked([650,0]));self.assertTrue(p.blocked([1900,0]))
 def test_protected_decoration_and_removed(self):
  b=self.bundle({});b['state']['doorStyles']={'D':{'leaves':3,'slideOpen':1,'slideDirection':-1}};self.assertEqual(len(Planner(b,{}).leaves),3)
  b['state']['doorStyles']['D']['leafRemoved']=True;self.assertEqual(Planner(b,{}).leaves,[])
if __name__=='__main__':unittest.main()
