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
    def test_python_and_js_reconstruct_same_inventory_and_readability(self):
        data={'bundle':self.b,'config':bind(self.b,self.c),'chapters':self.samples(),'policy':self.policy,'fps':24}
        script="import fs from 'node:fs';import{coreReadability}from './tour_core_targets.mjs';const d=JSON.parse(fs.readFileSync(0,'utf8'));console.log(JSON.stringify(coreReadability(d.bundle,d.config,d.chapters,d.policy,d.fps)));"
        node=shutil.which('node')
        if not node:self.skipTest('Existing Node unavailable; parity check not performed')
        r=subprocess.run([node,'--input-type=module','-e',script],input=json.dumps(data),text=True,capture_output=True,cwd=Path(__file__).parent,check=True);self.assertEqual(json.loads(r.stdout),readability(self.b,data['config'],data['chapters'],data['policy'],24))
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
