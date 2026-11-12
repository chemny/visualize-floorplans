import math,unittest
from design_homeowner_tour import flow_sweep,flow_candidates,forward_plan,navigation_gaze,delta
class Open:
 walls=[];vision_leaves=[];leaves=[]
 def blocked(self,p):return False
class FlowCamera(unittest.TestCase):
 def angle(self,d):return math.radians(d)
 def test_sweep_keeps_subject_framed_and_turns_toward_exit(self):
  subject=self.angle(180);start,pan=flow_sweep(Open(),[0,0],self.angle(180),self.angle(90),[subject],self.angle(30),limits=(12,64))
  sweep=[start+pan*i/8 for i in range(9)]
  self.assertGreaterEqual(sum(abs(delta(y,subject))<=self.angle(30) for y in sweep),4)
  self.assertLess(abs(delta(start+pan,self.angle(90))),self.angle(90))
 def test_sweep_respects_limit_and_episode_direction(self):
  start,pan=flow_sweep(Open(),[0,0],0,self.angle(90),[0],self.angle(30),limits=(12,40),signs=(-1,))
  self.assertLess(pan,0);self.assertLessEqual(abs(pan),self.angle(40)+1e-9)
 def test_impossible_subject_group_is_refused_not_dropped(self):
  with self.assertRaisesRegex(ValueError,'share one sweep'):flow_sweep(Open(),[0,0],0,0,[0,self.angle(180)],self.angle(10),limits=(12,30))
 def test_forward_gaze_follows_path_and_meets_both_views(self):
  dense=[[i*50.,0.] for i in range(60)];distances=[p[0] for p in dense]
  out=navigation_gaze(Open(),dense,distances,self.angle(40),self.angle(-40),{'mode':'forward'})
  self.assertAlmostEqual(out[0],self.angle(40),places=6);self.assertAlmostEqual(delta(out[-1],self.angle(-40)),0,places=6)
  self.assertLess(abs(delta(out[30],0)),self.angle(5))

def track(points,step=35.):
 dense=[points[0]];
 for a,b in zip(points,points[1:]):
  n=max(1,int(math.dist(a,b)//step))
  dense+= [[a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n] for i in range(1,n+1)]
 run=[0]
 for a,b in zip(dense,dense[1:]):run.append(run[-1]+math.dist(a,b))
 return dense,run
class MinimalTurning(unittest.TestCase):
 def total(self,plan,start):
  ys=[start]+plan['startPivot']+plan['yaws']+plan['endPivot'];return sum(abs(math.degrees(delta(a,b))) for a,b in zip(ys,ys[1:]))
 def test_pivot_stops_at_the_band_edge_instead_of_following_the_heading(self):
  dense,run=track([[0,0],[3000,0]]);start=math.radians(90);plan=forward_plan(dense,run,start,start,band=60)
  self.assertLessEqual(self.total(plan,start),75);self.assertTrue(plan['startPivot'] and plan['endPivot'])
 def test_heading_across_the_wrap_never_spins(self):
  dense,run=track([[0,0],[1500,0],[1500,-1500]]);start=math.radians(10);end=math.radians(-95)
  plan=forward_plan(dense,run,start,end,band=60);spin=self.total(plan,start)
  self.assertLessEqual(spin,140);ys=plan['startPivot']+plan['yaws']+plan['endPivot']
  self.assertLess(max(abs(math.degrees(y-start)) for y in ys),200)
 def test_walking_stays_within_band_and_steps_are_small(self):
  dense,run=track([[0,0],[2000,0],[2000,2000]]);plan=forward_plan(dense,run,0,math.radians(90),band=60)
  for y in plan['yaws']:self.assertLess(abs(math.degrees(y)),150)
  steps=[abs(math.degrees(b-a)) for a,b in zip(plan['yaws'],plan['yaws'][1:])];self.assertLess(max(steps),5)
 def test_pivot_cost_is_counted_so_dead_end_exit_turns_once(self):
  dense,run=track([[0,0],[2000,0]]);start=math.radians(180);plan=forward_plan(dense,run,start,0,band=60)
  self.assertLessEqual(self.total(plan,start),185)
 def test_candidates_keep_subjects_framed_and_are_diverse(self):
  rows=flow_candidates(Open(),[0,0],[math.radians(40)],math.radians(30),(24,60))
  self.assertGreater(len(rows),3);self.assertEqual(len({(round(math.degrees(a)),round(math.degrees(b))) for _,a,b in rows}),len(rows))
  for _,s0,pan in rows:
   sweep=[s0+pan*i/8 for i in range(9)];self.assertGreaterEqual(sum(abs(delta(y,math.radians(40)))<=math.radians(30) for y in sweep),1)
  self.assertTrue(all(abs(math.degrees(p))>=24 for _,_,p in rows))
if __name__=='__main__':unittest.main()
