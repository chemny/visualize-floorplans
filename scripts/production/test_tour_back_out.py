import math,unittest
from design_homeowner_tour import back_out_hold
from tour_forward_motion import inspect,verify_policy,polygon_area_m2

FPS=10
def rig(back_meters,seconds,face=0.,chapter='浴室 → 客厅',area=3.):
 """Camera faces +x the whole time while walking toward -x: pure backing out."""
 n=max(2,round(seconds*FPS));step=back_meters*1000/n
 frames=[{'pointMm':[3000-i*step,0],'yawRadians':face} for i in range(n+1)]
 frames+= [{'pointMm':[frames[-1]['pointMm'][0],0],'yawRadians':face} for _ in range(2)]
 tour={'fps':FPS,'frames':frames,'visits':[{'name':'a','frame':0},{'name':'b','frame':len(frames)-1}]}
 config={'chapters':[{'name':chapter,'from':'a','to':'b','phase':'transit'}],'smallRoomBackOut':{'rooms':[{'roomId':'bath','areaM2':area,'chapter':chapter}]}}
 return tour,config
class BackOut(unittest.TestCase):
 def codes(self,tour,config):return [i['code'] for i in inspect(tour,config)['issues']]
 def test_short_back_out_of_a_small_room_is_allowed_and_labelled(self):
  tour,config=rig(1.0,2.0);report=inspect(tour,config)
  self.assertEqual(report['issues'],[]);self.assertEqual(report['backwardSpans'][0]['allowance'],'small_room_back_out')
 def test_without_the_case_option_the_same_motion_is_refused(self):
  tour,config=rig(1.0,2.0);config.pop('smallRoomBackOut');self.assertEqual(self.codes(tour,config),['sustained_backward_walking'])
 def test_too_far_too_long_or_wrong_chapter_is_refused(self):
  self.assertEqual(self.codes(*rig(1.6,2.4)),['sustained_backward_walking'])
  self.assertEqual(self.codes(*rig(0.9,2.9)),['sustained_backward_walking'])
  tour,config=rig(1.0,2.0);config['smallRoomBackOut']['rooms'][0]['chapter']='别处 → 客厅';self.assertEqual(self.codes(tour,config),['sustained_backward_walking'])
 def test_config_cannot_loosen_the_limits_or_the_room_size(self):
  tour,config=rig(1.6,2.4);config['smallRoomBackOut'].update(maximumMeters=5,maximumSeconds=9);self.assertEqual(self.codes(tour,config),['sustained_backward_walking'])
  tour,config=rig(1.0,2.0,area=14.);self.assertEqual(self.codes(tour,config),['sustained_backward_walking'])
 def test_walking_forward_or_turning_in_place_is_unaffected(self):
  tour,config=rig(1.0,2.0,face=math.pi);self.assertEqual(self.codes(tour,config),[])
 def test_scheme_must_confirm_the_declared_small_room(self):
  bundle={'model':{'rooms':[{'id':'bath','poly':[[0,0],[1800,0],[1800,1700],[0,1700]]},{'id':'big','poly':[[0,0],[4000,0],[4000,4000],[0,4000]]}]}}
  ok={'smallRoomBackOut':{'rooms':[{'roomId':'bath','areaM2':3.06,'chapter':'x'}]}};self.assertEqual(verify_policy(bundle,ok)['issues'],[])
  big={'smallRoomBackOut':{'rooms':[{'roomId':'big','areaM2':16.,'chapter':'x'}]}};self.assertEqual(verify_policy(bundle,big)['issues'][0]['code'],'small_room_back_out_invalid')
  lie={'smallRoomBackOut':{'rooms':[{'roomId':'big','areaM2':3.,'chapter':'x'}]}};self.assertEqual(verify_policy(bundle,lie)['issues'][0]['code'],'small_room_back_out_invalid')
  self.assertEqual(verify_policy(bundle,{})['status'],'not_requested');self.assertAlmostEqual(polygon_area_m2(bundle['model']['rooms'][0]['poly']),3.06,places=2)
 def test_hold_stops_clear_of_the_room_and_inside_the_limit(self):
  dense=[[i*35.,0.] for i in range(80)];run=[p[0] for p in dense];room=[[-100,-500],[600,-500],[600,500],[-100,500]]
  hold=back_out_hold(dense,run,room);self.assertGreater(run[hold],600);self.assertLessEqual(run[hold],1200-60)
  far=[[-100,-500],[3000,-500],[3000,500],[-100,500]];self.assertLessEqual(run[back_out_hold(dense,run,far)],1200-60)
if __name__=='__main__':unittest.main()
