"""Behavior regressions for the repair failures found in real rehearsals."""
import copy
import math
import unittest
import json
import tempfile
from pathlib import Path

from tour_candidate_quality import (attach_screen_evidence,framing_cost,pitch_candidates,
                                    smooth_position_seams,protect_satisfied_constraints)
from tour_pipeline import JointPlanner,rank,apply_timing_locks
from tour_workflow import markers,metrics
from tour_rules import trajectory


class ClearPlanner:
    def blocked(self,p):return False
    def line_free(self,a,b):return True


class CandidateQualityTests(unittest.TestCase):
    def fixture(self):
        from test_tour_contract import ContractTests
        c=ContractTests();c.setUp();return c.b,c.t,c.c

    def screen(self,passed=False):
        return {'status':'pass' if passed else 'fail','chapters':[],
                'screenQuality':{'status':'pass' if passed else 'needs_revision',
                                 'issues':[] if passed else [{'code':'screen_near_surface_occlusion'}]}}

    def test_numeric_failure_still_keeps_screen_issues(self):
        r=attach_screen_evidence({'issues':[{'code':'room_coverage_below_case_minimum'}]},self.screen())
        self.assertEqual(r['checks']['screenEvidence']['status'],'checked')
        self.assertEqual({x['code'] for x in r['issues']},{'room_coverage_below_case_minimum','screen_near_surface_occlusion'})

    def test_unchecked_candidate_cannot_win_by_hiding_visual_errors(self):
        checked=attach_screen_evidence({'issues':[]},self.screen())
        unchecked=attach_screen_evidence({'issues':[]},None)
        self.assertLess(rank(checked,{'seconds':60}),rank(unchecked,{'seconds':50}))

    def test_fewer_visual_flags_cannot_introduce_a_new_room_time_failure(self):
        baseline={'issues':[{'code':'screen_near_surface_occlusion'}]*4,'checks':{}}
        repaired={'issues':[{'code':'room_visit_over_budget','name':'Child room'}],'checks':{}}
        repaired=protect_satisfied_constraints(repaired,baseline)
        self.assertGreater(rank(repaired,{'seconds':59}),rank(baseline,{'seconds':59}))

    def test_existing_failure_in_one_room_does_not_allow_breaking_another(self):
        base={'issues':[{'code':'room_coverage_below_case_minimum','roomId':'kitchen'}]}
        new={'issues':[{'code':'room_coverage_below_case_minimum','roomId':'dining'}]}
        r=protect_satisfied_constraints(new,base)
        self.assertEqual(r['checks']['introducedConstraintRegressions'][0]['roomId'],'dining')

    def test_changed_angles_do_not_discharge_historical_failure(self):
        for evidence in (None,self.screen()):
            r=attach_screen_evidence({'issues':[]},evidence,['Kitchen exit'])
            self.assertIn('known_visual_failure_unverified',{x['code'] for x in r['issues']})
            self.assertFalse(r['checks']['historicalVisualFindings']['geometryCleared'])
        r=attach_screen_evidence({'issues':[]},self.screen(True),['Kitchen exit'])
        self.assertEqual(r['issues'],[])
        self.assertEqual(r['checks']['historicalVisualFindings']['actualPlayback'],'pending')

    def split_fixture(self):
        b,t,c=self.fixture();ch=c['chapters'][1];m=markers(t);cut=(m[ch['from']]+m[ch['to']])//2
        t['visits'].append({'name':'continuous-view','frame':cut})
        c['chapters'][1:2]=[{**ch,'to':'continuous-view'},
            {**ch,'name':'Moving continuation','from':'continuous-view','movingView':True}]
        return b,t,c

    def test_moving_view_is_a_real_search_window(self):
        b,t,c=self.split_fixture();engine=JointPlanner(b,t,c,{})
        self.assertIn('Moving continuation',{ch['name'] for _,ch in engine.obs})
        from tour_pipeline import affected_chapters
        names=affected_chapters(t,c,{'issues':[{'chapter':'Moving continuation','code':'screen_near_surface_occlusion'}]})
        self.assertIn('Moving continuation',names)

    def test_adjacent_view_binding_preserves_shared_pose_and_no_extra_time(self):
        b,t,c=self.split_fixture();e=JointPlanner(b,t,c,{})
        first,second=[ch for _,ch in e.obs];choices={ch['name']:e.baseline(ch) for _,ch in e.obs}
        choices[first['name']].update(endPoint=[2800,2050],source='joint_search')
        item=e.bind_adjacent(first,second,choices[second['name']],choices)
        self.assertIsNotNone(item);self.assertEqual(item['point'],[2800,2050])
        self.assertAlmostEqual(item['yaw'],choices[first['name']]['yaw']+choices[first['name']]['pan'])
        choices[second['name']]=item
        # Observations are generated using their original frame counts, not
        # the connection allocator which previously lengthened movingView.
        u,cc=e.rebuild(choices,{})
        old,new=markers(t),markers(u)
        for ch in c['chapters']:
            if ch['phase']=='observe':self.assertEqual(old[ch['to']]-old[ch['from']],new[ch['to']]-new[ch['from']])

    def test_connection_slack_is_reclaimed_without_shortening_view(self):
        b,t,c=self.fixture();m=markers(t)
        c['timingLocks']={'totalFrames':len(t['frames'])-2,
            'viewingFrames':{ch['name']:m[ch['to']]-m[ch['from']] for ch in c['chapters'] if ch['phase']=='observe'}}
        u=apply_timing_locks(t,c);n=markers(u)
        self.assertEqual(len(u['frames']),len(t['frames'])-2)
        for ch in c['chapters']:
            if ch['phase']=='observe':
                self.assertEqual(t['frames'][m[ch['from']]:m[ch['to']]+1][0]['pointMm'],u['frames'][n[ch['from']]:n[ch['to']]+1][0]['pointMm'])
                self.assertEqual(m[ch['to']]-m[ch['from']],n[ch['to']]-n[ch['from']])
        self.assertLessEqual(metrics(u)['maximumSpeedMps'],1.2+1e-6)

    def test_early_budget_rejects_impossible_connection(self):
        b,t,c=self.fixture();m=markers(t)
        c['timingLocks']={'totalFrames':1+sum(m[ch['to']]-m[ch['from']] for ch in c['chapters'] if ch['phase']=='observe')}
        e=JointPlanner(b,t,c,{});choices={ch['name']:e.baseline(ch) for _,ch in e.obs}
        self.assertFalse(e.budget_feasible(choices));self.assertTrue(e.budget_rejections)

    def test_pitch_edit_reuses_safe_spatial_connections_without_replanning(self):
        from unittest.mock import patch
        b,t,c=self.fixture();e=JointPlanner(b,t,c,{})
        choices={ch['name']:{**e.baseline(ch),'pitch':math.radians(-10),'source':'joint_search'} for _,ch in e.obs}
        with patch.object(e,'path',side_effect=AssertionError('A safe unchanged path should not be discarded for pitch')):
            result,_=e.rebuild(choices,{})
        self.assertEqual(result['frames'][0]['pointMm'],t['frames'][0]['pointMm'])
        self.assertEqual(result['frames'][-1]['pointMm'],t['frames'][-1]['pointMm'])

    def test_room_after_failed_beam_still_gets_a_local_repair_pool(self):
        from unittest.mock import patch
        b,t,c=self.split_fixture();e=JointPlanner(b,t,c,{})
        names=[ch['name'] for _,ch in e.obs];seen=[]
        def propose(ch,*args):
            seen.append(ch['name'])
            if ch['name']==names[0]:raise ValueError('Synthetic blocked early room')
            e.pool[ch['name']]={'retained':[e.baseline(ch)]}
        with patch.object(e,'candidates',side_effect=propose):errors=e.prepare_local_repairs(set(names),0)
        self.assertEqual(seen,names);self.assertEqual(len(errors),1)
        self.assertIn(names[1],e.pool)

    def test_failed_single_connection_does_not_abort_other_beam_candidates(self):
        from unittest.mock import patch
        b,t,c=self.fixture();e=JointPlanner(b,t,c,{'beamWidth':2})
        ch=e.obs[0][1];base=e.baseline(ch)
        with patch.object(e,'candidates',return_value=[base,copy.deepcopy(base)]),patch.object(e,'budget_feasible',side_effect=[ValueError('Synthetic unsafe corner'),True]):
            result=e.joint_beam({ch['name']},0)
        self.assertEqual(len(result),1)
        self.assertIn('unsafe corner',e.budget_rejections[0]['reason'])

    def test_cheap_early_poses_cannot_prune_the_only_complete_seed_chain(self):
        from unittest.mock import patch
        b,t,c=self.split_fixture();e=JointPlanner(b,t,c,{'beamWidth':2})
        names=[ch['name'] for _,ch in e.obs]
        def propose(ch,*args):
            base=e.baseline(ch);base['localCost']=100
            return [{**base,'source':'dead_end','localCost':0},{**base,'source':'dead_end','localCost':1},base] if ch['name']==names[0] else [base]
        def bind(previous,current,item,choices):
            if previous and choices[previous['name']]['source']=='dead_end':return None
            return item
        with patch.object(e,'candidates',side_effect=propose),patch.object(e,'bind_adjacent',side_effect=bind),patch.object(e,'budget_feasible',return_value=True):
            rows=e.joint_beam(set(names),0)
        self.assertTrue(rows)
        self.assertTrue(all(v['source']=='seed' for v in rows[0][1].values()))

    def test_closing_pose_faces_outward_without_moving_confirmed_endpoint(self):
        b,t,c=self.fixture();e=JointPlanner(b,t,c,{})
        # The real gate lies west of this exterior endpoint. Forward departure
        # faces east; looking back at the gate would produce backward walking.
        t['frames'][-1]['yawRadians']=math.pi
        end=e.closing_pose()
        self.assertEqual(end['pointMm'],t['frames'][-1]['pointMm'])
        self.assertEqual(end['eyeMm'],1600)
        self.assertEqual(end['closingTargetOpeningId'],c['tourContract']['entranceOpeningId'])
        self.assertAlmostEqual(end['yawRadians'],0)

    def test_room_repair_does_not_require_an_extra_closing_turn(self):
        from unittest.mock import patch
        b,t,c=self.fixture();e=JointPlanner(b,t,c,{})
        choices={ch['name']:e.baseline(ch) for _,ch in e.obs}
        with patch.object(e,'closing_pose',side_effect=AssertionError('Unselected closing turn should not block a room repair')):
            self.assertTrue(e.budget_feasible(choices))
            u,_=e.rebuild(choices,{'closingView':'seed'})
        self.assertAlmostEqual(math.cos(u['frames'][-1]['yawRadians']),math.cos(t['frames'][-1]['yawRadians']))
        # Deferring the turn does not clear the blank-ending failure.
        r=attach_screen_evidence({'issues':[]},self.screen(),['Exit'])
        self.assertIn('known_visual_failure_unverified',{i['code'] for i in r['issues']})

    def test_rejected_local_build_does_not_consume_the_only_evaluable_alternative(self):
        from unittest.mock import patch
        from tour_pipeline import run
        b,t,c=self.fixture();c['maximumSeconds']=1;c['roomBudgetPolicy']['rooms'][0]['maximumSeconds']=.1
        name=c['chapters'][1]['name'];seen=[]
        def pools(engine,*args):
            base=engine.baseline(engine.obs[0][1])
            engine.pool[name]={'retained':[{**base,'source':'bad'},{**base,'source':'good'}]};return []
        def rebuild(engine,choices,policy):
            source=choices[name]['source'];seen.append(source)
            if source=='bad':raise ValueError('Synthetic locally cheap candidate cannot fit')
            return copy.deepcopy(t),copy.deepcopy(c)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);runtime=p/'runtime';runtime.mkdir()
            (runtime/'scene.json').write_text(json.dumps({'schemeSha256':b['schemeSha256']}))
            for file,value in [('bundle.json',b),('tour.json',t),('config.json',c)]:(p/file).write_text(json.dumps(value))
            job={'schema':'homeowner-production-job/1','bundle':str(p/'bundle.json'),'seedTour':str(p/'tour.json'),
                 'seedConfig':str(p/'config.json'),'runtime':str(runtime),'searchOnly':True,'meshPreflight':False,
                 'search':{'maximumRounds':1,'maximumFullEvaluations':3,'localAlternatives':1,'strictRepairRounds':True}}
            with patch.object(JointPlanner,'joint_beam',return_value=[]),patch.object(JointPlanner,'prepare_local_repairs',new=pools),patch.object(JointPlanner,'rebuild',new=rebuild):
                result=run(job,p/'out')
            self.assertIn('good',seen);self.assertEqual(seen.count('good'),1)
            self.assertFalse(result['rehearsalGenerated']);self.assertFalse((p/'out/index.html').exists())

    def reversal(self):
        fps=24
        t={'fps':fps,'frames':[{'frame':i,'pointMm':[min(i,48-i)*20.,0.],
            'yawRadians':0.,'pitchRadians':-.1,'eyeMm':1600} for i in range(49)],
            'visits':[{'name':'a','frame':0},{'name':'b','frame':24},{'name':'z','frame':48}]}
        c={'chapters':[{'from':'a','to':'b'},{'from':'b','to':'z'}]}
        return t,c

    def test_seam_repairs_real_position_reversal_without_time_or_boundary_changes(self):
        t,c=self.reversal();before=copy.deepcopy(t)
        u=smooth_position_seams(t,c,ClearPlanner())
        self.assertEqual(t,before);self.assertEqual(len(u['frames']),len(t['frames']))
        self.assertEqual(u['frames'][24]['pointMm'],t['frames'][24]['pointMm'])
        self.assertIn(24,u['positionSeamRepair']['boundaryFrames'])
        a,z=trajectory(t,c),trajectory(u,c)
        self.assertLess(z['maximumPlanarAccelerationMps2'],a['maximumPlanarAccelerationMps2'])
        self.assertNotIn('path_tangent_discontinuity',{x['code'] for x in z['issues']})

    def test_unsafe_seam_curve_is_rejected_instead_of_marked_fixed(self):
        class GridOnly(ClearPlanner):
            def blocked(self,p):return abs(p[0]/20-round(p[0]/20))>1e-7
        t,c=self.reversal();u=smooth_position_seams(t,c,GridOnly())
        self.assertEqual([f['pointMm'] for f in t['frames']],[f['pointMm'] for f in u['frames']])
        self.assertIn('path_tangent_discontinuity',{x['code'] for x in trajectory(u,c)['issues']})

    def test_pitch_search_can_raise_an_overly_downward_old_view(self):
        b={'state':{'furniture':[{'id':'bed','cx':2800,'cy':0,'w':500,'d':500,'h':600}]}}
        ch={'subjects':['bed']};p=pitch_candidates(b,ch,[0,0],0,math.radians(-25),1600)
        self.assertGreater(p[0],math.radians(-25))
        self.assertTrue(any(abs(x-math.radians(-8))<1e-7 for x in p))

    def test_projected_lower_bound_penalizes_cutoff_instead_of_lowering_eye(self):
        b={'state':{'furniture':[{'id':'bed','cx':2300,'cy':0,'w':200,'d':400,'h':600}]}}
        ch={'subjects':['bed']}
        self.assertLess(framing_cost(b,ch,[0,0],0,math.radians(-10),1600),framing_cost(b,ch,[0,0],0,math.radians(-5),1600))



    def test_case_station_proposals_are_checked_and_do_not_bypass_motion_or_domain(self):
        b,t,c=self.fixture();ch=c['chapters'][1]
        ch['candidatePoses']=[
            {'point':[-1000,2000],'yawDegrees':180,'panDegrees':10,'pitchDegrees':-10},
            {'point':[2800,2000],'yawDegrees':180,'panDegrees':300,'pitchDegrees':-10},
            {'point':[2800,2000],'yawDegrees':180,'panDegrees':10,'pitchDegrees':-10}]
        e=JointPlanner(b,t,c,{});pool=e.candidates(ch,0,True)
        self.assertEqual(len(pool),2)
        self.assertEqual(pool[1]['source'],'case_station_proposal')
        self.assertEqual(pool[1]['point'],[2800,2000])
        self.assertAlmostEqual(pool[1]['pan'],math.radians(10))
        self.assertEqual(e.pool[ch['name']]['tested'],3)

    def test_entry_intent_changes_only_heading_not_entrance_or_eye_height(self):
        b,t,c=self.fixture();before=copy.deepcopy(t)
        c['entryView']={'targetMm':[1000,2200,1300]}
        e=JointPlanner(b,t,c,{})
        self.assertEqual(e.entry['pointMm'],t['frames'][0]['pointMm'])
        self.assertEqual(e.entry['eyeMm'],1600)
        self.assertNotEqual(e.entry['yawRadians'],t['frames'][0]['yawRadians'])
        self.assertEqual(t,before)

    def test_final_angle_projection_certifies_the_whole_vector(self):
        from tour_pipeline import constrained_angles
        from tour_camera_evidence import DEFAULTS
        n=180;t={'fps':24,'frames':[{} for _ in range(n)],'visits':[]}
        values=constrained_angles([0. if i<n//2 else .8 for i in range(n)],{'chapters':[]},t,'yawRadians')
        speeds=[math.degrees(b-a)*24 for a,b in zip(values,values[1:])]
        self.assertLessEqual(max(map(abs,speeds)),32)
        self.assertLessEqual(max(abs(b-a)*24 for a,b in zip(speeds,speeds[1:])),DEFAULTS['maximumYawAccelerationDegreesPerSecondSquared'])

    def test_seed_duplicates_do_not_consume_distinct_station_alternatives(self):
        b,t,c=self.fixture();ch=c['chapters'][1];e=JointPlanner(b,t,c,{})
        base=e.baseline(ch)
        ch['candidatePoses']=[{'point':base['point'],'endPoint':base['endPoint'],
            'yawDegrees':math.degrees(base['yaw']),'panDegrees':math.degrees(base['pan']),
            'pitchDegrees':math.degrees(base['pitch'])}]*3
        self.assertEqual(len(e.candidates(ch,0,True)),1)

    def test_case_connection_waypoint_is_preserved_and_cannot_cross_furniture(self):
        b,t,c=self.fixture();e=JointPlanner(b,t,c,{})
        path=e.connection_path(t['frames'][0]['pointMm'],[2800,2000],{'pathWaypoints':[[3300,2500]]})
        self.assertGreater(max(q[1] for q in path),2250)
        self.assertTrue(all(e.p.line_free(a,b) for a,b in zip(path,path[1:])))
        with self.assertRaisesRegex(ValueError,'collides'):
            e.connection_path(t['frames'][0]['pointMm'],[2800,2000],{'pathWaypoints':[[1200,2000]]})

if __name__=='__main__':unittest.main()

class ConnectionWorkTests(unittest.TestCase):
 def test_curve_subdivisions_do_not_invent_extra_time(self):
  from tour_candidate_quality import connection_effort
  limits={'maximumSpeedMps':1.2,'maxYawDegreesPerSecond':32,'maxPitchDegreesPerSecond':14}
  values=[]
  for count in (1,10,1000):
   points=[[2000*i/count,0] for i in range(count+1)];ys=[math.pi/2*i/count for i in range(count+1)]
   values.append(sum(connection_effort(points,ys,0,math.radians(-30),limits)))
  for value in values:self.assertAlmostEqual(value,90/32,places=9)
 def test_zero_length_vertices_have_no_implicit_pause_but_real_turns_still_take_time(self):
  from tour_candidate_quality import connection_effort
  limits={'maximumSpeedMps':1.2,'maxYawDegreesPerSecond':32,'maxPitchDegreesPerSecond':14}
  self.assertEqual(sum(connection_effort([[0,0]]*100,[0.]*100,0,0,limits)),0)
  self.assertAlmostEqual(sum(connection_effort([[0,0]]*3,[0,math.pi/4,math.pi/2],0,0,limits)),90/32)
  self.assertAlmostEqual(sum(connection_effort([[0,0]]*3,[0,0,0],0,math.radians(-28),limits)),2)

class WrappedConnectionTests(unittest.TestCase):
 def test_exact_endpoint_copy_does_not_insert_a_full_turn_at_angle_wrap(self):
  from test_tour_contract import ContractTests
  x=ContractTests();x.setUp();p=JointPlanner(x.b,x.t,x.c,{})
  p.entry['yawRadians']=3.0
  choices={ch['name']:{**p.baseline(ch),'yaw':-3.0,'pan':0.,'source':'synthetic_wrap_candidate'} for _,ch in p.obs}
  new,c=p.rebuild(choices,{'closingView':'seed'})
  self.assertLess(max(abs(z['yawRadians']-a['yawRadians']) for a,z in zip(new['frames'],new['frames'][1:])),.2)
  self.assertEqual(new['frames'][-1]['pointMm'],x.t['frames'][-1]['pointMm'])
