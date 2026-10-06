import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'production'))
from plan_route import Planner,plan,apply_camera_cues
class RouteTests(unittest.TestCase):
 def fixture(self,kind='door'):
  return {'schema':'floor-visualization-production/1.0','schemeSha256':'test','confirmations':{'structure':{'status':'confirmed'},'layout':{'status':'confirmed'},'style':{'status':'confirmed'}},'model':{'rooms':[{'id':'A','poly':[[0,0],[2000,0],[2000,2000],[0,2000]]},{'id':'B','poly':[[2000,0],[4000,0],[4000,2000],[2000,2000]]}]},'state':{'furniture':[],'walls':[{'id':'w','a':[2000,0],'b':[2000,2000],'t':120,'opens':[{'kind':kind,'at':500,'width':1000,'swing':1,'angle':90}]}]}}
 def test_windows_never_traversable(self):
  p=Planner(self.fixture('window'),{'bodyRadiusMm':100})
  self.assertTrue(p.blocked([2000,1000]))
  with self.assertRaises(ValueError):p.astar([1000,1000],[3000,1000])
 def test_real_door_traversable_with_clearance(self):
  p=Planner(self.fixture(),{'bodyRadiusMm':100})
  self.assertFalse(p.blocked([2000,1000]));self.assertTrue(p.astar([1000,1000],[3000,1000]))
 def test_unconfirmed_bundle_rejected(self):
  b=self.fixture();b['confirmations']['layout']['status']='stale'
  with self.assertRaisesRegex(ValueError,'Unconfirmed'):plan(b,{'stops':[]})
 def test_open_leaf_is_collision_obstacle(self):
  p=Planner(self.fixture(),{'bodyRadiusMm':100});h,tip,_=p.leaves[0];self.assertTrue(p.blocked([(h[0]+tip[0])/2,(h[1]+tip[1])/2]))
 def test_trim_and_threshold_do_not_block_a_real_door(self):
  b=self.fixture();b['state']['furniture']=[{'type':t,'cx':2000,'cy':1000,'w':1100,'d':160,'h':20,'rot':90,'elevation':0} for t in ['threshold','doortrim','skirting']]
  p=Planner(b,{'bodyRadiusMm':100});self.assertFalse(p.blocked([2000,1000]));self.assertTrue(p.astar([1000,1000],[3000,1000]))
 def test_preview_remains_unaccepted_and_fov_is_retained(self):
  b=self.fixture();b['confirmations']={}
  result=plan(b,{'stops':[{'name':'a','point':[1000,1200]},{'name':'b','point':[3000,1200]}],'seconds':4,'fps':12,'horizontalFovDegrees':82,'bodyRadiusMm':100},preview=True)
  self.assertTrue(result['previewOnly']);self.assertEqual(result['humanAcceptance'],'pending');self.assertTrue(all(f['horizontalFovDegrees']==82 for f in result['frames']))
 def test_sliding_open_half_matches_mesh_pose(self):
  b=self.fixture('sliding');o=b['state']['walls'][0]['opens'][0];o.update(slideOpen=1,slideDirection=-1,leaves=2)
  p=Planner(b,{'bodyRadiusMm':60});self.assertTrue(p.blocked([2000,700]));self.assertFalse(p.blocked([2000,1250]));self.assertTrue(p.astar([1500,1250],[2500,1250]))
  o['slideOpen']=0;p=Planner(b,{'bodyRadiusMm':60})
  with self.assertRaises(ValueError):p.astar([1500,1250],[2500,1250])
 def test_visit_times_follow_route_order_on_return_trip(self):
  b=self.fixture();c={'stops':[{'name':'start','point':[1000,1200],'lookAt':[1800,1200,1000]},{'name':'visit','point':[3000,1200],'lookAt':[3500,1200,1000]},{'name':'return','point':[1000,1200],'lookAt':[1500,1200,1000]},{'name':'end','point':[3000,1200]}],'seconds':12,'fps':12,'bodyRadiusMm':100}
  r=plan(b,c);times=[v['frame'] for v in r['visits']];self.assertEqual(times,sorted(times));self.assertLess(times[1],times[2]);self.assertAlmostEqual(r['frames'][times[1]]['pointMm'][0],3000,delta=100)
 def test_perpendicular_wall_join_padding_is_a_blocker(self):
  b=self.fixture();b['model']['footprint']=[[-1000,-1000],[4000,-1000],[4000,4000],[-1000,4000]]
  b['state']['walls']=[{'id':'h','a':[0,0],'b':[2000,0],'t':240,'opens':[]},{'id':'v','a':[2000,0],'b':[2000,2000],'t':240,'opens':[]}]
  p=Planner(b,{'bodyRadiusMm':100});self.assertTrue(p.blocked([2200,-150]))
 def test_explicit_cues_keep_path_and_show_target(self):
  import copy,math
  fs=[{'pointMm':[i*10,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0} for i in range(60)]
  original=copy.deepcopy(fs);apply_camera_cues(fs,10,[{'startSeconds':1,'endSeconds':5,'targetMm':[0,1000,1000]}],35)
  self.assertEqual([f['pointMm'] for f in fs],[f['pointMm'] for f in original]);self.assertGreater(fs[30]['yawRadians'],math.pi/2);self.assertLess(fs[30]['pitchRadians'],0)
 def test_camera_cue_order_and_targets_rejected(self):
  fs=[{'pointMm':[0,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0} for _ in range(100)]
  for cues in [[{'startSeconds':2,'endSeconds':11,'targetMm':[0,100,900]}],[{'startSeconds':1,'endSeconds':4,'targetMm':[0,100,900]},{'startSeconds':3,'endSeconds':5,'targetMm':[0,100,900]}],[{'startSeconds':1,'endSeconds':4,'targetMm':[0,float('nan'),900]}]]:
   with self.assertRaises(ValueError):apply_camera_cues(fs,10,cues)
 def test_route_cli_utf8_and_unicode_space_paths(self):
  import tempfile,json,subprocess
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp)/'中文 path';root.mkdir();b=root/'模型.json';c=root/'镜头.json';out=root/'输出.json'
   b.write_text(json.dumps(self.fixture(),ensure_ascii=False),encoding='utf-8')
   c.write_text(json.dumps({'stops':[{'name':'开始','point':[1000,1200]},{'name':'第二间','point':[3000,1200]}],'seconds':4,'fps':12,'bodyRadiusMm':100},ensure_ascii=False),encoding='utf-8')
   command=[sys.executable,'-X','warn_default_encoding','-W','error::EncodingWarning',str(Path(__file__).parent/'production/plan_route.py'),'--bundle',str(b),'--config',str(c),'--output',str(out)]
   run=subprocess.run(command,capture_output=True,text=True,encoding='utf-8')
   self.assertEqual(run.returncode,0,run.stderr);self.assertEqual(json.loads(out.read_text(encoding='utf-8'))['visits'][1]['name'],'第二间')
 def test_camera_cue_invalid_rate_and_boolean_values(self):
  fs=[{'pointMm':[0,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0} for _ in range(100)]
  c=[{'startSeconds':1,'endSeconds':4,'targetMm':[0,100,900]}]
  for fps,yaw in [(0,35),(10,0),(True,35),(10,float('nan'))]:
   with self.assertRaises(ValueError):apply_camera_cues(fs,fps,c,yaw)
  for c in [[{'startSeconds':True,'endSeconds':4,'targetMm':[0,100,900]}],[{'startSeconds':1,'endSeconds':4,'targetMm':[False,100,900]}]]:
   with self.assertRaises(ValueError):apply_camera_cues(fs,10,c)
 def test_camera_cues_rate_limit_and_short_rotation(self):
  import math
  fs=[{'pointMm':[0,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0} for _ in range(100)]
  apply_camera_cues(fs,10,[{'startSeconds':0,'endSeconds':3,'targetMm':[-1000,10,1000]},{'startSeconds':5,'endSeconds':10,'targetMm':[-1000,-10,1000]}],30)
  self.assertLess(max(abs(b['yawRadians']-a['yawRadians'])*10 for a,b in zip(fs,fs[1:])),math.radians(30)+1e-8);self.assertLess(abs(fs[-1]['yawRadians']-fs[0]['yawRadians']),.1)
if __name__=='__main__':unittest.main()
