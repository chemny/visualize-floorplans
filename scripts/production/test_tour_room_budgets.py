import unittest
from tour_room_budgets import inspect
class RoomBudgetTests(unittest.TestCase):
 def setUp(self):
  self.bundle={'model':{'rooms':[{'id':'room','poly':[[0,0],[1000,0],[1000,1000],[0,1000]]}]}}
  self.tour={'fps':10,'seconds':1.1,'frames':[{'pointMm':[x,500]} for x in [-100,100,200,300,600,900,1100,1200,1300,900,800]],'visits':[{'name':'arrive','frame':2},{'name':'done','frame':4}]}
  self.config={'chapters':[{'phase':'observe','roomId':'room','from':'arrive','to':'done'}]}
 def policy(self,limit):return {'maximumTotalSeconds':10,'rooms':[{'name':'Room','roomIds':['room'],'maximumSeconds':limit}]}
 def test_counts_entry_and_exit_and_excludes_later_pass(self):
  r=inspect(self.bundle,self.tour,self.config,self.policy(.5));row=r['rooms'][0]
  self.assertAlmostEqual(row['seconds'],.4);self.assertEqual(row['endSeconds'],.5);self.assertFalse(r['issues'])
 def test_observation_only_pass_cannot_hide_long_visit(self):
  r=inspect(self.bundle,self.tour,self.config,self.policy(.2))
  self.assertEqual(r['issues'][0]['code'],'room_visit_over_budget')
 def test_unknown_room_and_invalid_limit_are_rejected(self):
  p=self.policy(1);p['rooms'][0]['roomIds']=['unknown']
  with self.assertRaises(ValueError):inspect(self.bundle,self.tour,self.config,p)
  with self.assertRaises(ValueError):inspect(self.bundle,self.tour,self.config,self.policy(float('nan')))

 def separate_fixture(self):
  bundle={'model':{'rooms':self.bundle['model']['rooms']+[{'id':'other','poly':[[1200,0],[1800,0],[1800,1000],[1200,1000]]}]}}
  xs=[-100]+[500]*5+[1500]*7+[500]*5+[1500]*3+[500]*3
  tour={'fps':10,'seconds':len(xs)/10,'frames':[{'pointMm':[x,500]} for x in xs],
   'visits':[{'name':name,'frame':frame} for name,frame in [('a',2),('b',4),('c',8),('d',10),('e',14),('f',16)]]}
  config={'roomViewingPolicy':{'singleEpisode':False},'tourContract':{'singleEpisodeExceptionReason':'The user explicitly requests separate public-area introductions.'},'chapters':[
   {'phase':'observe','roomId':'room','episodeId':'first','from':'a','to':'b'},
   {'phase':'observe','roomId':'other','from':'c','to':'d'},
   {'phase':'observe','roomId':'room','episodeId':'later','from':'e','to':'f'}]}
  return bundle,tour,config
 def test_justified_separate_visits_sum_local_entry_view_exit_and_exclude_return_pass(self):
  b,t,c=self.separate_fixture();r=inspect(b,t,c,self.policy(1));row=r['rooms'][0]
  self.assertEqual([(w['startFrame'],w['endFrame']) for w in row['visitWindows']],[(1,5),(13,17)])
  self.assertAlmostEqual(row['seconds'],.8);self.assertAlmostEqual(row['endSeconds']-row['startSeconds'],1.6)
  self.assertFalse(r['issues'])
 def test_unjustified_disabled_single_episode_keeps_existing_budget_measurement(self):
  b,t,c=self.separate_fixture();c['tourContract']['singleEpisodeExceptionReason']='  '
  r=inspect(b,t,c,self.policy(1));row=r['rooms'][0]
  self.assertAlmostEqual(row['seconds'],1.6);self.assertNotIn('visitWindows',row)
  self.assertEqual(r['issues'][0]['code'],'room_visit_over_budget')
 def test_explicit_covered_room_anchor_counts_its_own_local_visit(self):
  b,t,c=self.separate_fixture();c['chapters'][0].update(roomId='other',coveredRoomIds=['room'],observationRegionId='room')
  row=inspect(b,t,c,self.policy(1))['rooms'][0]
  self.assertAlmostEqual(row['seconds'],.8)
  self.assertEqual([(w['startFrame'],w['endFrame']) for w in row['visitWindows']],[(1,5),(13,17)])
 def test_overlapping_local_visits_are_counted_once(self):
  b,t,c=self.separate_fixture();t['frames']=[{'pointMm':[500,500]} for _ in range(10)];t['seconds']=1
  t['visits']=[{'name':name,'frame':frame} for name,frame in [('a',2),('b',4),('e',6),('f',8)]]
  c['chapters']=[c['chapters'][0],c['chapters'][2]]
  row=inspect(b,t,c,self.policy(1))['rooms'][0]
  self.assertAlmostEqual(row['seconds'],.9);self.assertEqual(len(row['visitWindows']),1)
 def test_other_room_introduction_is_not_a_shared_region_budget_gap(self):
  b,t,c=self.separate_fixture();t['frames']=[{'pointMm':[500,500]} for _ in range(13)];t['seconds']=1.3
  t['visits']=[{'name':name,'frame':frame} for name,frame in [('a',1),('b',2),('c',4),('d',6),('e',10),('f',11)]]
  c['chapters'][1]['observationRegionId']='room'
  row=inspect(b,t,c,self.policy(1))['rooms'][0]
  self.assertEqual([(w['startFrame'],w['endFrame']) for w in row['visitWindows']],[(0,3),(7,12)])
  self.assertAlmostEqual(row['seconds'],.8)
