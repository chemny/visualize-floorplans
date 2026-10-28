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
