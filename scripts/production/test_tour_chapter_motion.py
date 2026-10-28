"""Phase-specific ceilings must constrain real chords, not just UI labels."""
import copy,math,unittest
from tour_workflow import chapter_limits,edge_limits,markers
from tour_connection_motion import project_gaze_numpy
from tour_pipeline import constrained_angles

class ChapterMotionTests(unittest.TestCase):
 def fixture(self):
  base={'maxYawDegreesPerSecond':45,'maxPitchDegreesPerSecond':14,'maximumSpeedMps':1.2}
  tour={'fps':24,'frames':[{'frame':i,'pointMm':[0,0],'yawRadians':math.radians(i*1.6),'pitchRadians':0} for i in range(9)],'visits':[{'name':'a','frame':0},{'name':'b','frame':4},{'name':'c','frame':8}]}
  config={'motionReviewLimits':base,'chapters':[{'name':'walk','from':'a','to':'b','phase':'transit'}, {'name':'view','from':'b','to':'c','phase':'observe','singleSweepDegrees':10,'motionReviewLimits':{'maxYawDegreesPerSecond':32}}]}
  return base,tour,config
 def test_boundary_chords_have_one_exact_owner(self):
  b,t,c=self.fixture();self.assertEqual(edge_limits(t,c,'maxYawDegreesPerSecond',b),[45]*4+[32]*4)
 def test_unconfigured_case_keeps_original_scalar_ceiling(self):
  b,t,c=self.fixture();c['chapters'][1].pop('motionReviewLimits');b['maxYawDegreesPerSecond']=32
  self.assertEqual(edge_limits(t,c,'maxYawDegreesPerSecond',b),[32]*8)
 def test_chapter_cannot_raise_or_disable_its_ceiling(self):
  b,t,c=self.fixture()
  for value in [46,0,-1,True,float('nan'),'32']:
   with self.subTest(value=value),self.assertRaises(ValueError):chapter_limits(b,{'motionReviewLimits':{'maxYawDegreesPerSecond':value}})
  with self.assertRaises(ValueError):chapter_limits(b,{'motionReviewLimits':{'unknown':1}})
 def test_final_projection_enforces_observation_cap_after_fast_navigation(self):
  b,t,c=self.fixture();v=constrained_angles([f['yawRadians'] for f in t['frames']],c,t,'yawRadians')
  rates=[math.degrees(z-a)*t['fps'] for a,z in zip(v,v[1:])]
  self.assertLessEqual(max(rates[:4]),45.00001);self.assertLessEqual(max(rates[4:]),32.00001)
  self.assertTrue(all(v>=-1e-6 for v in rates[4:]))
 def test_fixed_endpoint_feasibility_uses_sum_of_local_caps(self):
  with self.assertRaisesRegex(ValueError,'within speed limit'):
   project_gaze_numpy([0,1,2],24,[1,.5],10,{},fixed_values={0:0,2:2})
 def test_final_contract_rejects_viewing_rate_below_global_but_above_local_cap(self):
  from test_tour_contract import ContractTests
  from tour_contract import inspect
  x=ContractTests();x.setUp();c=copy.deepcopy(x.c);t=copy.deepcopy(x.t);c['motionReviewLimits']={'maxYawDegreesPerSecond':45};c['ruleExceptions'].append({'code':'motion_limit_override','reason':'Synthetic explicit navigation approval'})
  ch=next(v for v in c['chapters'] if v['phase']=='observe');ch['motionReviewLimits']={'maxYawDegreesPerSecond':32};m=markers(t);a,z=m[ch['from']],m[ch['to']]
  for i in range(a,z+1):t['frames'][i]['yawRadians']=math.pi+math.radians(35)*(i-a)/t['fps']
  r=inspect(x.b,t,c);issues=[v for v in r['issues'] if v['code']=='chapter_motion_limit']
  self.assertTrue(any(v['chapter']==ch['name'] and v['metric']=='maxYawDegreesPerSecond' for v in issues))

if __name__=='__main__':unittest.main()
