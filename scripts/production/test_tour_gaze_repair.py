import copy,math,unittest
from tour_connection_motion import project_gaze_numpy
from tour_gaze_repair import revise

class GazeRepairTests(unittest.TestCase):
 def test_expired_deadline_rejects_instead_of_running_projection(self):
  from unittest.mock import patch
  with patch('tour_connection_motion.time.monotonic',return_value=2):
   with self.assertRaises(TimeoutError):project_gaze_numpy([0,1,0],24,1,1,{},deadline=1)
  with patch('tour_connection_motion.time.monotonic',side_effect=[0,2]):
   with self.assertRaises(TimeoutError):project_gaze_numpy([0,100,0],24,.1,.1,{},deadline=1)
  for deadline in (True,float('nan'),'tomorrow'):
   with self.assertRaises(ValueError):project_gaze_numpy([0,1,0],24,1,1,{},deadline=deadline)
 def fixture(self):
  frames=[{'frame':i,'pointMm':[i*10.,0.],'yawRadians':math.radians(350+i*.2),'pitchRadians':math.radians(-5),'eyeMm':1600} for i in range(81)]
  tour={'fps':24,'seconds':81/24,'frames':frames,'visits':[{'name':str(i),'frame':i} for i in (0,20,40,60,80)]}
  config={'chapters':[{'name':name,'from':str(a),'to':str(z),'phase':phase,**({'singleSweepDegrees':1} if phase=='observe' else {})} for name,a,z,phase in [('before',0,20,'transit'),('view',20,40,'observe'),('after',40,60,'transit'),('last',60,80,'transit')]]}
  return tour,config
 def test_fixed_projection_retains_values_and_rejects_infeasible_endpoints(self):
  result=project_gaze_numpy([0,2,2,2,0],24,1,1,{},fixed_values={0:0,4:0})
  self.assertEqual(result[0],0);self.assertEqual(result[4],0)
  self.assertLessEqual(max(abs(b-a) for a,b in zip(result,result[1:])),1.000001)
  with self.assertRaisesRegex(ValueError,'connect'):project_gaze_numpy([0,0,0],24,1,1,{},fixed_values={0:0,2:10})
 def test_revise_keeps_other_axes_positions_markers_and_unpatched_frames_exact(self):
  tour,config=self.fixture();original=copy.deepcopy(tour)
  patch={'chapter':'view','axes':['yawRadians'],'keys':[{'offsetFrame':0,'yawDegrees':-6},{'offsetFrame':10,'yawDegrees':-2},{'offsetFrame':20,'yawDegrees':-2}]}
  out,evidence=revise(tour,config,[patch]);self.assertEqual(tour,original)
  for i,(a,z) in enumerate(zip(tour['frames'],out['frames'])):
   self.assertEqual(a['pointMm'],z['pointMm']);self.assertEqual(a['pitchRadians'],z['pitchRadians'])
   if i<20 or i>40:self.assertEqual(a,z)
  self.assertTrue(all(evidence[k] for k in ('positionsPreserved','frameCountPreserved','visitsPreserved','timingPreserved')))
  self.assertTrue(all(out['frames'][i+1]['yawRadians']>=out['frames'][i]['yawRadians']-1e-8 for i in range(20,40)))
  self.assertGreater(min(f['yawRadians'] for f in out['frames']),math.radians(340))
 def test_multichapter_pitch_repair_does_not_touch_yaw(self):
  tour,config=self.fixture();patch={'chapter':'view','endChapter':'after','axes':['pitchRadians'],'keys':[{'offsetFrame':0,'pitchDegrees':-5},{'offsetFrame':20,'pitchDegrees':-7},{'offsetFrame':40,'pitchDegrees':-5}]}
  out,evidence=revise(tour,config,[patch]);self.assertEqual([f['yawRadians'] for f in tour['frames']],[f['yawRadians'] for f in out['frames']]);self.assertEqual(evidence['patches'][0]['endFrame'],60)
 def test_subrange_cannot_modify_remainder_of_selected_chapter(self):
  tour,config=self.fixture()
  patch={'chapter':'after','startOffsetFrame':5,'endOffsetFrame':15,'axes':['yawRadians'],'keys':[{'offsetFrame':0,'yawDegrees':359},{'offsetFrame':5,'yawDegrees':361},{'offsetFrame':10,'yawDegrees':361}]}
  out,evidence=revise(tour,config,[patch])
  self.assertEqual(out['frames'][:45],tour['frames'][:45])
  self.assertEqual(out['frames'][56:],tour['frames'][56:])
  self.assertEqual(evidence['patches'][0]['startFrame'],45)
  self.assertEqual(evidence['patches'][0]['endFrame'],55)
  bad={**patch,'endOffsetFrame':21}
  with self.assertRaisesRegex(ValueError,'subrange'):revise(tour,config,[bad])
 def test_valid_frozen_frames_at_original_speed_ceiling_stay_feasible(self):
  tour,config=self.fixture()
  for i,f in enumerate(tour['frames']):f['yawRadians']=math.radians(i*32/24)
  patch={'chapter':'view','axes':['yawRadians'],'keys':[{'offsetFrame':0,'yawDegrees':20*32/24},{'offsetFrame':20,'yawDegrees':40*32/24}]}
  out,evidence=revise(tour,config,[patch])
  self.assertEqual(out['frames'][:20],tour['frames'][:20]);self.assertEqual(out['frames'][41:],tour['frames'][41:])
  self.assertLessEqual(evidence['axes']['yawRadians']['maximumDegreesPerSecond'],32.000001)
 def test_impossible_frozen_boundary_is_rejected_instead_of_expanding_patch(self):
  tour,config=self.fixture();tour['frames'][0]['yawRadians']=0;tour['frames'][1]['yawRadians']=math.radians(90)
  patch={'chapter':'view','axes':['yawRadians'],'keys':[{'offsetFrame':0,'yawDegrees':354},{'offsetFrame':20,'yawDegrees':358}]}
  with self.assertRaisesRegex(ValueError,'Fixed gaze'):revise(tour,config,[patch])

if __name__=='__main__':unittest.main()
