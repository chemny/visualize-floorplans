import copy,unittest
from compact_tour_visits import compact,safe_path
from design_homeowner_tour import design
from tour_workflow import markers

class CompactTests(unittest.TestCase):
 def test_exact_endpoint_does_not_snap_through_a_thin_wall(self):
  from plan_route import Planner
  b={'model':{'footprint':[[-500,-500],[500,-500],[500,500],[-500,500]],'rooms':[]},'state':{'walls':[{'id':'thin','a':[25,-400],'b':[25,400],'t':2,'opens':[]}],'furniture':[]}}
  p=Planner(b,{'bodyRadiusMm':0,'gridMm':100})
  self.assertFalse(p.line_free([49,0],[0,0]))
  self.assertEqual(p.nearest([49,0]),(1,0))
  path=safe_path(p,[49,0],[150,100])
  self.assertEqual(path[0],[49,0]);self.assertEqual(path[-1],[150,100])
  self.assertTrue(all(p.line_free(a,z) for a,z in zip(path,path[1:])))
 def test_blocked_exact_endpoint_is_not_silently_moved(self):
  from plan_route import Planner
  b={'model':{'footprint':[[0,0],[1000,0],[1000,1000],[0,1000]],'rooms':[]},'state':{'walls':[],'furniture':[{'id':'cabinet','type':'cabinet','cx':500,'cy':500,'w':200,'d':200}]}}
  p=Planner(b,{'bodyRadiusMm':100,'gridMm':50})
  with self.assertRaisesRegex(ValueError,'Exact endpoint is not walkable'):p.astar([500,500],[900,900])
 def fixture(self):
  b={'schemeSha256':'compact-test','model':{'footprint':[[0,0],[4000,0],[4000,4000],[0,4000]],'rooms':[{'id':'room','poly':[[100,100],[3900,100],[3900,3900],[100,3900]]}]},'state':{'walls':[{'id':'w','a':[4000,0],'b':[4000,4000],'t':100,'opens':[{'id':'entry','kind':'door','at':1500,'width':1000,'swing':-1,'angle':90,'hingeEnd':'start'}]}],'furniture':[{'id':'sofa','type':'sofa','cx':1200,'cy':2000,'w':1000,'d':600,'rot':0}]}}
  brief={'schema':'homeowner-design-brief/1','coveragePolicy':{'enabled':False},'tourMode':'full_tour','entranceOpeningId':'entry','startPoint':[4500,2000],'maximumSeconds':60,'rooms':[{'roomId':'room','name':'Room','subjectId':'sofa','targetMm':[1200,2000,1000],'candidatePoints':[[2800,2000]],'viewSeconds':2,'viewPurpose':'View room','tourRole':'public','observationPanDegrees':10}],'choreographyPolicy':{'maximumTransitFraction':1}}
  t,c,_=design(b,brief);return b,t,c
 def test_preserve_viewing_duration_and_input_data(self):
  b,t,c=self.fixture();old_t=copy.deepcopy(t);old_c=copy.deepcopy(c)
  new,nc,r=compact(b,t,c,{'entranceOpeningId':'entry','driftMm':500,'exteriorPoint':[4450,2000],'navigationPolicy':{'interpolation':'linear','excessTurnPerStepWeight':30}})
  self.assertEqual(t,old_t);self.assertEqual(c,old_c)
  self.assertTrue(r['viewingFrameCountsPreserved']);self.assertFalse(r['collisions']);self.assertFalse(r['motionFailures'])
  self.assertEqual(new['frames'][0]['pointMm'],[4450,2000]);self.assertEqual(new['frames'][-1]['pointMm'],[4450,2000])
  self.assertTrue(all(x['afterFrames']>=x['beforeFrames'] for x in r['observationFrameCounts']))
  self.assertEqual(len([ch for ch in nc['chapters'] if ch['phase']=='observe']),1)
 def test_movement_speed_cannot_exceed_existing_ceiling(self):
  b,t,c=self.fixture()
  with self.assertRaisesRegex(ValueError,'existing speed ceiling'):compact(b,t,c,{'entranceOpeningId':'entry','observationSpeedMps':1.3})
if __name__=='__main__':unittest.main()
