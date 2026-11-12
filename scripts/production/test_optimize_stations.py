import json,math,unittest
import optimize_stations as o

class Stub:
 def __init__(self,blocked=()):self.blocked_points=blocked
 def blocked(self,p):return tuple(p) in self.blocked_points
 def line_free(self,a,b):return True
SQUARE=[[0,0],[4000,0],[4000,4000],[0,4000]]

class Candidates(unittest.TestCase):
 def test_station_leads_and_candidates_stay_inside_room_tolerance_and_clear(self):
  rows=o.candidates_for(Stub(blocked={(2300,2000)}),SQUARE,[2000,2000],tolerance=800)
  self.assertEqual(rows[0],[2000,2000]);self.assertNotIn([2300,2000],rows)
  self.assertTrue(all(math.dist(p,[2000,2000])<=800 for p in rows));self.assertEqual(rows,sorted(rows,key=lambda p:(math.dist(p,[2000,2000]),p)))
  self.assertTrue(all(0<p[0]<4000 and 0<p[1]<4000 for p in o.candidates_for(Stub(),SQUARE,[200,200],tolerance=1500)))
 def test_candidate_list_is_bounded(self):self.assertLessEqual(len(o.candidates_for(Stub(),SQUARE,[2000,2000],tolerance=1500,limit=5)),5)

class Scoring(unittest.TestCase):
 def audit(self,passes,issues=()):
  return {'chapters':[{'subjects':{i:{'pass':ok} for i,ok in passes.items()}}],'screenQuality':{'issues':[{'code':c} for c in issues]}}
 def test_unreadable_subjects_and_close_walls_cost_more_than_distance(self):
  clean=o.score_audit(self.audit({'a':True}),['a'],0);far=o.score_audit(self.audit({'a':True}),['a'],1000)
  bad=o.score_audit(self.audit({'a':False},['screen_near_surface_occlusion']),['a'],0)
  self.assertLess(clean['score'],far['score']);self.assertLess(far['score'],bad['score'])
  self.assertEqual(bad['unreadable'],['a']);self.assertEqual(bad['screenIssues'],['screen_near_surface_occlusion'])
 def test_a_subject_missing_from_the_audit_counts_as_unreadable(self):
  self.assertEqual(o.score_audit(self.audit({}),['x'],0)['unreadable'],['x'])

class MiniTour(unittest.TestCase):
 def test_window_matches_view_time_sweep_pitch_and_eye(self):
  item={'viewSeconds':2.5,'roomId':'r','subjectId':'s','subjects':[]};furniture={'s':{}}
  tour,config=o.mini_tour(item,[1000,1000],(0.5,0.4,-0.05,-0.2,['s']),{'eyeMm':1300,'cameraProfile':{'horizontalFovDegrees':90}},'h'*64,furniture)
  frames=tour['frames'];self.assertEqual(len(frames),round(2.5*o.FPS)+1);self.assertAlmostEqual(frames[0]['yawRadians'],0.5);self.assertAlmostEqual(frames[-1]['yawRadians'],0.9)
  self.assertAlmostEqual(frames[0]['pitchRadians'],-0.05);self.assertAlmostEqual(frames[-1]['pitchRadians'],-0.2);self.assertEqual({f['eyeMm'] for f in frames},{1300})
  self.assertEqual(config['chapters'][0]['subjects'],['s']);self.assertEqual(tour['schemeSha256'],'h'*64)

class Repair(unittest.TestCase):
 def briefs(self):
  base={'rooms':[{'observationId':'a','name':'甲','candidatePoints':[[0,0]]},{'observationId':'b','name':'乙','candidatePoints':[[10,0]]}]}
  moved={'rooms':[{'observationId':'a','name':'甲','candidatePoints':[[0,300]]},{'observationId':'b','name':'乙','candidatePoints':[[10,300]]}]}
  return base,moved
 def test_a_move_that_adds_a_turn_failure_is_undone_nearest_the_failure(self):
  base,moved=self.briefs();calls=[]
  def fake(bundle,brief):
   calls.append(1);shifted=[r['name'] for r in brief['rooms'] if r['candidatePoints'][0][1]]
   return [{'code':'excessive_transit_turn','chapter':'甲 → 乙'}] if '乙' in shifted else []
  original=o.protected_issues;o.protected_issues=fake
  try:result,steps=o.repair({},base,moved,progress=lambda *a:None)
  finally:o.protected_issues=original
  self.assertEqual([s['undid'] for s in steps],['乙']);self.assertEqual(result['rooms'][1]['candidatePoints'],[[10,0]]);self.assertEqual(result['rooms'][0]['candidatePoints'],[[0,300]])
 def test_a_failure_the_baseline_already_had_is_not_blamed_on_the_move(self):
  base,moved=self.briefs();original=o.protected_issues;o.protected_issues=lambda b,br:[{'code':'excessive_transit_turn','chapter':'甲 → 乙'}]
  try:result,steps=o.repair({},base,moved,progress=lambda *a:None)
  finally:o.protected_issues=original
  self.assertEqual(steps,[]);self.assertEqual(result,moved)
 def test_a_new_failure_with_nothing_to_undo_is_reported_not_hidden(self):
  base,_=self.briefs();original=o.protected_issues
  o.protected_issues=lambda b,br:[] if br is base else [{'code':'sustained_backward_walking','chapter':'甲 → 乙'}]
  try:
   with self.assertRaisesRegex(ValueError,'no moved station'):o.repair({},base,json.loads(json.dumps(base)),progress=lambda *a:None)
  finally:o.protected_issues=original
if __name__=='__main__':unittest.main()
