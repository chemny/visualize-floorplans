import math,unittest
from tour_stop_smoothness import inspect as stops
from tour_workflow import shaped_distance_times,retime
from plan_route import Planner

def path(speeds,fps=24):
 """Frames whose per-step speed (m/s) follows the list."""
 x=0.;frames=[{'pointMm':[0.,0.]}]
 for v in speeds:x+=v*1000/fps;frames.append({'pointMm':[x,0.]})
 return {'fps':fps,'frames':frames}

class StopSmoothness(unittest.TestCase):
 def test_a_hard_stop_from_walking_pace_is_refused(self):
  report=stops(path([1.2]*12+[0]*12),{});self.assertEqual([i['code'] for i in report['issues']],['abrupt_stop']);self.assertEqual(report['issues'][0]['edge'],'stop')
 def test_a_hard_start_is_refused_too(self):
  self.assertEqual([i['edge'] for i in stops(path([0]*12+[1.2]*12),{})['issues']],['start'])
 def test_an_eased_stop_passes(self):
  ramp=[0.9*(1-i/20) for i in range(1,20)]  # 0.8 s down to a stop at 24 fps
  self.assertEqual(stops(path([0.9]*12+ramp+[0]*12),{})['issues'],[])
 def test_a_short_pause_is_not_a_stop(self):
  self.assertEqual(stops(path([1.2]*10+[0]*2+[1.2]*10),{})['issues'],[])
 def test_policy_must_be_explicit_and_positive(self):
  with self.assertRaises(ValueError):stops(path([1.0]*10),{'stopPolicy':{'dropMps':-1}})
  self.assertEqual(stops(path([1.2]*12+[0]*12),{'stopPolicy':{'dropMps':2.0}})['issues'],[])

class ShapedTimes(unittest.TestCase):
 def frames(self,n=120,spacing=35.):
  f=[{'pointMm':[i*spacing,0.]} for i in range(n)]
  for i in range(50,56):f[i]['pointMm']=list(f[50]['pointMm'])
  for i in range(56,n):f[i]['pointMm']=[f[50]['pointMm'][0]+(i-55)*spacing,0.]
  return f
 POLICY={'cruiseMps':.9,'narrowCruiseMps':.65,'rampSeconds':.8,'startRampSeconds':.4}
 def test_speed_never_exceeds_cruise_and_eases_toward_a_stop(self):
  f=self.frames();times=shaped_distance_times(f,self.POLICY);speeds=[math.dist(a['pointMm'],b['pointMm'])/1000/t for a,b,t in zip(f,f[1:],times) if t>0]
  self.assertLessEqual(max(speeds),.9+1e-6);before=[math.dist(a['pointMm'],b['pointMm'])/1000/t for a,b,t in zip(f[:50],f[1:51],times[:50]) if t>0]
  self.assertLess(before[-1],before[len(before)//2]);self.assertTrue(all(b<=a+1e-9 for a,b in zip(before[30:],before[31:])))
 def test_leaving_a_stop_is_quicker_than_arriving(self):
  f=self.frames();times=shaped_distance_times(f,self.POLICY)
  self.assertLess(sum(times[56:62]),sum(times[44:50]))
 def test_a_frame_limit_slows_that_stretch(self):
  f=self.frames()
  for g in f[10:20]:g['speedLimitMps']=.4
  slow=shaped_distance_times(f,self.POLICY);plain=shaped_distance_times(self.frames(),self.POLICY);self.assertGreater(sum(slow[10:19]),sum(plain[10:19]))
 def test_retime_only_lengthens(self):
  f=self.frames();fr=[{**x,'yawRadians':0,'pitchRadians':0,'eyeMm':1300} for x in f]
  tour={'fps':24,'seconds':len(fr)/24,'frames':fr,'visits':[{'name':'a','frame':0},{'name':'b','frame':len(fr)-1}]};limits={'maximumSpeedMps':1.2,'maxYawDegreesPerSecond':32,'maxPitchDegreesPerSecond':14}
  config={'chapters':[{'name':'c','from':'a','to':'b','phase':'transit'}]}
  fast=retime(tour,config,limits);slow=retime(tour,{**config,'speedPolicy':self.POLICY},limits);self.assertGreater(slow['seconds'],fast['seconds'])

class ComfortClearance(unittest.TestCase):
 def planner(self,comfort):
  b={'model':{'footprint':[[0,0],[6000,0],[6000,3000],[0,3000]],'rooms':[{'id':'r','poly':[[50,50],[5950,50],[5950,2950],[50,2950]]}]},'state':{'walls':[{'id':'W','a':[0,0],'b':[6000,0],'t':100,'opens':[]},{'id':'S','a':[0,3000],'b':[6000,3000],'t':100,'opens':[]},{'id':'L','a':[0,0],'b':[0,3000],'t':100,'opens':[]},{'id':'R','a':[6000,0],'b':[6000,3000],'t':100,'opens':[]}],'furniture':[]}}
  return Planner(b,{'bodyRadiusMm':180,'gridMm':50,'comfortClearanceMm':comfort,'comfortWeight':3})
 def test_a_comfort_path_stays_away_from_walls_and_only_costs_a_little_length(self):
  plain,comfort=self.planner(0),self.planner(450);a,b=[300,300],[5700,300]
  p0=plain.astar(a,b);p1=comfort.astar(a,b)
  g0=min(plain.gap_at(q) for q in p0[1:-1]);g1=min(comfort.gap_at(q) for q in p1[1:-1])
  self.assertGreater(g1,g0);length=lambda p:sum(math.dist(x,y) for x,y in zip(p,p[1:]));self.assertLess(length(p1),1.25*length(p0))
 def test_hard_clearance_never_loosens(self):
  p=self.planner(450);self.assertTrue(p.blocked([100,100]));self.assertFalse(p.blocked([1500,1500]))
if __name__=='__main__':unittest.main()


class AccelerationLimiter(unittest.TestCase):
 def test_a_lone_slow_interval_between_fast_ones_is_eased(self):
  from tour_workflow import limit_acceleration
  f=[{'pointMm':[i*40.,0.]} for i in range(40)];times=[1/24]*39;times[20]=1/24*3
  out=limit_acceleration(f,times,{'cruiseMps':1.0,'rampSeconds':1.0});sp=[40/1000/t for t in out]
  accel=[abs(b-a)/((x+y)/2) for a,b,x,y in zip(sp,sp[1:],out,out[1:])]
  self.assertLess(max(accel),1.2,max(accel))
  self.assertTrue(all(o>=t-1e-12 for o,t in zip(out,times)))

class SmallRoomDepth(unittest.TestCase):
 def bundle(self):
  room=lambda i,x0,x1:{'id':i,'name':i,'poly':[[x0,0],[x1,0],[x1,2000],[x0,2000]]}
  return {'model':{'rooms':[room('hall',-3000,0),room('wc',0,2000)],'walls':[],'openings':[]}}
 def test_depth_counts_only_the_small_room_that_is_not_the_entrance(self):
  import tour_small_room_depth as m
  from unittest.mock import patch
  door={'kind':'door','id':'D','a':[0,800],'b':[0,1400],'halfThicknessMm':60}
  tour={'fps':10,'frames':[{'pointMm':[-2500+i*300,1100]} for i in range(15)]}
  with patch.object(m,'gates',return_value=[door]):
   shallow=m.inspect(self.bundle(),tour,{'smallRoomShallow':{'maximumDepthMm':2000}})
   deep=m.inspect(self.bundle(),tour,{'smallRoomShallow':{'maximumDepthMm':500}})
   off=m.inspect(self.bundle(),tour,{})
  self.assertEqual(shallow['status'],'pass');self.assertEqual([i['code'] for i in deep['issues']],['small_room_too_deep']);self.assertEqual(off['status'],'not_requested')
