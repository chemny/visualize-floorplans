import copy, json, shutil, subprocess, unittest
from pathlib import Path
from tour_core_targets import inventory, inspect, bind, readability, targets

class CoreTargetTests(unittest.TestCase):
    def setUp(self):
        self.b={'model':{'rooms':[{'id':'renamed-zone','poly':[[0,0],[4000,0],[4000,4000],[0,4000]]}]},'state':{'furniture':[
            {'id':ident,'type':kind,'cx':x,'cy':2000,'roomId':'renamed-zone'}
            for ident,kind,x in [('one','vanity',1000),('two','shower',2000),('three','toilet',3000)]]}}
        self.c={'chapters':[{'name':'presentation','phase':'observe','roomId':'renamed-zone','from':'a','to':'b','subjects':['one','two']}]}
        self.policy={'sampleHz':4,'minVisibleSamples':2,'minVisibleFraction':.03,'minScreenAreaFraction':.005}
    def samples(self,ids=('one','two','three')):
        return [{'id':'presentation','samples':[{'seconds':s,'subjects':{i:{'unoccludedSamples':10,'totalSamples':20,'screenAreaFraction':.1} for i in ids}} for s in [0,.25,.5,.75]]}]
    def test_missing_actual_toilet_is_reported(self):
        self.assertEqual(inspect(self.b,self.c)['issues'],[{'code':'missing_core_view_target','roomId':'renamed-zone','subjectId':'three'}])
    def test_binding_is_scene_based_and_does_not_mutate_input(self):
        old=copy.deepcopy(self.c);c=bind(self.b,self.c)
        self.assertEqual(old,self.c);self.assertIn('three',c['chapters'][0]['subjects']);self.assertEqual(inspect(self.b,c)['status'],'pass')
    def test_nonexistent_bathtub_not_invented_and_detail_parts_not_required(self):
        self.b['state']['furniture'] += [{'id':'part','type':'toilet','cx':1000,'cy':1000,'assemblyOwner':{'kind':'object'}}, {'id':'decor','type':'plant','cx':1000,'cy':1000}]
        self.assertEqual(len(inventory(self.b)['renamed-zone']),3)
    def test_room_assignment_uses_real_geometry_when_metadata_is_stale(self):
        self.b['state']['furniture'][2]['roomId']='old-name';self.assertIn('three',[r['subjectId'] for r in inventory(self.b)['renamed-zone']])
    def test_ordered_list_does_not_hide_additional_unordered_subjects(self):
        ch=self.c['chapters'][0];ch['orderedViewTargets']=['one'];ch['subjects'].append('three');self.assertEqual(targets(ch),['one','two','three'])
    def test_same_frame_can_show_all_main_fixtures(self):
        r=readability(self.b,bind(self.b,self.c),self.samples(),self.policy,24);self.assertEqual(r['status'],'pass');self.assertTrue(all(v['pass'] for v in r['readability']))
    def test_unlisted_fixture_is_still_tested_in_actual_sample_check(self):
        r=readability(self.b,self.c,self.samples(('one','two')),self.policy,24);self.assertIn('three',[i['subjectId'] for i in r['issues'] if i['code']=='core_facility_unreadable'])
    def test_occluded_or_only_tiny_visible_patch_cannot_pass(self):
        for visible,area in [(0,.1),(10,.0001)]:
            rows=self.samples()
            for s in rows[0]['samples']:s['subjects']['three'].update(unoccludedSamples=visible,screenAreaFraction=area)
            self.assertEqual(readability(self.b,bind(self.b,self.c),rows,self.policy,24)['status'],'needs_revision')
    def test_brief_flash_not_enough(self):
        rows=self.samples()
        for s in rows[0]['samples'][1:]:s['subjects'].pop('three')
        self.assertEqual(readability(self.b,bind(self.b,self.c),rows,self.policy,24)['status'],'needs_revision')
    def test_later_revisit_cannot_make_up_first_visit_omission(self):
        c=bind(self.b,self.c);c['chapters'] += [{'name':'other','phase':'observe','roomId':'other','subjects':[]}, {**c['chapters'][0],'name':'later'}]
        rows=self.samples(('one','two'));late=self.samples()[0];late['id']='later';self.assertEqual(readability(self.b,c,rows+[late],self.policy,24)['status'],'needs_revision')
    def test_two_complementary_stations_share_complete_room_target_set(self):
        c=copy.deepcopy(self.c);c['chapters'].append({**c['chapters'][0],'name':'second','subjects':['three']});self.assertEqual(bind(self.b,c),c);self.assertEqual(inspect(self.b,c)['status'],'pass')
    def multi_config(self):
        return {'roomViewingPolicy':{'singleEpisode':False},
                'tourContract':{'singleEpisodeExceptionReason':'User explicitly presents the wash area before the main room.'},
                'chapters':[{'name':'wash','phase':'observe','roomId':'renamed-zone','subjects':['one']},
                            {'name':'other','phase':'observe','roomId':'other','subjects':[]},
                            {'name':'main','phase':'observe','roomId':'renamed-zone','subjects':['two','three']}]}
    def episode_samples(self,name,ids,start):
        row=self.samples(ids)[0];row['id']=name
        for sample in row['samples']:sample['seconds']+=start
        return row
    def test_explicit_multiple_introductions_keep_each_subject_first_declared_episode(self):
        c=self.multi_config();report=inspect(self.b,c)
        self.assertEqual(report['status'],'pass');self.assertEqual(bind(self.b,c),c)
        room=next(row for row in report['rooms'] if row['roomId']=='renamed-zone')
        self.assertEqual(room['subjectChapters'],{'one':['wash'],'three':['main'],'two':['main']})
        result=readability(self.b,c,[self.episode_samples('wash',['one'],0),self.episode_samples('main',['two','three'],4)],self.policy,24)
        self.assertEqual(result['status'],'pass')
        self.assertEqual(next(row['chapters'] for row in result['readability'] if row['subjectId']=='one'),['wash'])
    def test_exception_requires_explicit_false_and_nonempty_string_reason(self):
        for policy,reason in [({},'fixed order'),({'singleEpisode':True},'fixed order'),({'singleEpisode':False},''),({'singleEpisode':False},'  '),({'singleEpisode':False},None),({'singleEpisode':False},True)]:
            c=self.multi_config();c['roomViewingPolicy']=policy;c['tourContract']['singleEpisodeExceptionReason']=reason
            self.assertEqual({issue['subjectId'] for issue in inspect(self.b,c)['issues']},{'two','three'})
    def test_missing_explicit_introduction_is_not_silently_assigned_by_bind(self):
        c=self.multi_config();c['chapters'][-1]['subjects']=['two'];old=copy.deepcopy(c)
        self.assertEqual(bind(self.b,c),old)
        report=inspect(self.b,c);self.assertIn({'code':'missing_core_view_target','roomId':'renamed-zone','subjectId':'three'},report['issues'])
        self.assertEqual(next(row for row in report['rooms'] if row['roomId']=='renamed-zone')['subjectChapters']['three'],[])
    def test_later_repeat_or_transit_cannot_repair_failed_first_declared_introduction(self):
        c=self.multi_config();c['chapters'] += [{'name':'pass-through','phase':'transit','roomId':'renamed-zone','subjects':['one']},
                                               {'name':'later-other','phase':'observe','roomId':'other','subjects':[]},
                                               {'name':'wash-repeat','phase':'observe','roomId':'renamed-zone','subjects':['one']}]
        rows=[self.episode_samples('wash',[],0),self.episode_samples('main',['two','three'],4),
              self.episode_samples('pass-through',['one'],7),self.episode_samples('wash-repeat',['one'],10)]
        result=readability(self.b,c,rows,self.policy,24)
        self.assertEqual({issue['subjectId'] for issue in result['issues'] if issue['code']=='core_facility_unreadable'},{'one'})
        self.assertEqual(next(row for row in result['readability'] if row['subjectId']=='one')['chapters'],['wash'])
    def test_incidental_earlier_visibility_cannot_replace_declared_introduction(self):
        c=self.multi_config();rows=[self.episode_samples('wash',['one','two','three'],0),self.episode_samples('main',[],4)]
        result=readability(self.b,c,rows,self.policy,24)
        self.assertEqual({issue['subjectId'] for issue in result['issues'] if issue['code']=='core_facility_unreadable'},{'two','three'})
    def test_explicit_episode_ids_separate_adjacent_introductions(self):
        c=self.multi_config();c['chapters'].pop(1);c['chapters'][0]['episodeId']='wash-introduction';c['chapters'][1]['episodeId']='main-introduction'
        report=inspect(self.b,c);room=report['rooms'][0]
        self.assertEqual(room['subjectChapters']['one'],['wash']);self.assertEqual(room['subjectChapters']['two'],['main'])
    def test_adjacent_vanity_view_keeps_covered_physical_room_inventory(self):
        c=self.multi_config();wash=c['chapters'][0];wash.update(roomId='wet-zone',observationRegionId='renamed-zone',coveredRoomIds=['renamed-zone'],adjacentViewReason='The actual external wash basin is in the adjacent public room.')
        self.b['model']['rooms'].append({'id':'wet-zone','poly':[[5000,0],[6000,0],[6000,1000],[5000,1000]]})
        report=inspect(self.b,c);room=next(row for row in report['rooms'] if row['roomId']=='renamed-zone')
        self.assertEqual({f['subjectId'] for f in room['required']},{'one','two','three'});self.assertEqual(room['subjectChapters']['one'],['wash'])
        rows=[self.episode_samples('wash',['one'],0),self.episode_samples('main',['two','three'],4)]
        self.assertEqual(readability(self.b,c,rows,self.policy,24)['status'],'pass')
        self.assert_js_parity(c,rows)
    def assert_js_parity(self,config,chapters):
        data={'bundle':self.b,'config':config,'chapters':chapters,'policy':self.policy,'fps':24}
        script="import fs from 'node:fs';import{coreReadability}from './tour_core_targets.mjs';const d=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(coreReadability(d.bundle,d.config,d.chapters,d.policy,d.fps)));"
        node=shutil.which('node')
        if not node:self.skipTest('Existing Node unavailable; parity check not performed')
        r=subprocess.run([node,'--input-type=module','-e',script],input=json.dumps(data),text=True,capture_output=True,cwd=Path(__file__).parent,check=True)
        self.assertEqual(json.loads(r.stdout),readability(self.b,config,chapters,self.policy,24))
    def test_python_and_js_reconstruct_same_inventory_and_readability(self):
        self.assert_js_parity(bind(self.b,self.c),self.samples())
    def test_python_js_parity_for_multiple_episodes_and_rejected_late_repair(self):
        c=self.multi_config();c['chapters'].append({'name':'wash-repeat','phase':'observe','roomId':'renamed-zone','episodeId':'new','subjects':['one']})
        rows=[self.episode_samples('wash',[],0),self.episode_samples('main',['two','three'],4),self.episode_samples('wash-repeat',['one'],8)]
        self.assert_js_parity(c,rows)
        c['tourContract']['singleEpisodeExceptionReason']='';self.assert_js_parity(c,rows)
    def test_scan_proposals_adapt_to_whole_function_set_within_angular_budget(self):
        from tour_core_targets import scan_angles
        c=bind(self.b,self.c);proposals=scan_angles(self.b,c['chapters'][0],[2500,3500],3,32)
        self.assertTrue(proposals);self.assertTrue(any(pan<0 for yaw,pan in proposals));self.assertTrue(any(pan>0 for yaw,pan in proposals))
        self.assertTrue(all(abs(pan)*180/3.141592653589793<=3*32 for yaw,pan in proposals))
    def test_joint_planner_binds_missing_functions_from_its_actual_bundle(self):
        from test_tour_contract import ContractTests
        from tour_pipeline import JointPlanner
        x=ContractTests();x.setUp();original=copy.deepcopy(x.c)
        x.b['state']['furniture'].append({'id':'wc-new-id','type':'toilet','cx':600,'cy':600,'w':400,'d':700,'rot':0,'roomId':'room'})
        planner=JointPlanner(x.b,x.t,x.c,{})
        self.assertIn('wc-new-id',next(c for c in planner.c['chapters'] if c['phase']=='observe')['subjects'])
        self.assertEqual(x.c,original)

if __name__=='__main__':unittest.main()
