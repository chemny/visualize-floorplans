import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from design_contract import digest
from layout_review import review
from layout_use_review import numeric_check


class LayoutUseReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
        self.state={'walls':[],'doorStyles':{},'furniture':[{'id':'unit','type':'vanity','roomId':'room','cx':800,'cy':2500,'w':1600,'d':450,'h':820,'rot':0}]}
        self.case={'initialState':self.state,'model':{'rooms':[{'id':'room'}]}}
        self.write('observed.txt','Synthetic observations, not a real room');self.obs={'status':'observed_clear','observation':'Synthetic assembly and use observed','evidence':[self.ref('observed.txt')]}
        self.record={'schema':'layout-review/1','stateSha256':digest(self.state),'rooms':[{'id':'room','purpose':'synthetic','requirements':[{'types':['vanity'],'minimum':1}],'reasonableness':copy.deepcopy(self.obs)}],'groups':[{'id':'assembly','roomId':'room','members':['unit'],'composition':copy.deepcopy(self.obs),'useStates':[{'name':'normal',**copy.deepcopy(self.obs)}],'relations':[{'kind':'count','ids':['unit'],'expected':1}]}]}
        self.record['assemblyIntents']=[{'groupId':'assembly','functions':[{'name':'washing','memberIds':['unit']},{'name':'storage','memberIds':['unit']}],'requirements':[{'kind':'pose','ids':['unit'],'values':{'cx':800,'w':1600}}]}]
        self.write('delivery.html','<p>Close the room door before using this storage.</p>')
        self.record['operationMatrix']={'actors':{'roomDoor':['open','closed'],'cabinet':['stowed','extended'],'person':['using']},'motionIncludesHandles':True,'scenarios':[]}
        for name,door,cab,blocked in [('normal','closed','stowed',False),('expanded','closed','extended',False),('negative','open','extended',True)]:
            states={'roomDoor':door,'cabinet':cab,'person':'using'}
            checks={'body':[{'kind':'rect_clear','a':[0,0,2,2],'b':[3,3,4,4]}],'motion':[{'kind':'segment_clear','a':[0,0],'b':[0,2],'rect':[3,0,5,2],'padMm':.2}],'use':[{'kind':'rect_clear','a':[10,10,12,12],'b':[11,11,13,13] if blocked else [20,20,22,22]}]}
            self.write(name+'.json',{'stateSha256':digest(self.state),'states':states,'checks':checks})
            scenario={'id':name,'states':states,'snapshot':self.ref(name+'.json'),'expected':'blocked' if blocked else 'usable'}
            if blocked:scenario.update(reason='Door blocks the human standing zone despite clear cabinet bodies',disclosure={'text':'Close the room door before using this storage.','artifact':self.ref('delivery.html')})
            self.record['operationMatrix']['scenarios'].append(scenario)
        measurements={'counterOutline':[[0,0],[900,0],[900,200],[1600,200],[1600,450],[0,450]],'fixtureCenter':[600,280]}
        final={'comparisons':[{'measurement':k,'tolerance':.01}for k in measurements],'expectedScreenshotStates':{'roomDoor':'closed','cabinet':'extended'}}
        for kind in ['plan','mesh','screenshot']:
            self.write(kind+'.artifact','synthetic '+kind)
            receipt={'stateSha256':digest(self.state),'artifact':self.ref(kind+'.artifact'),'measurements':copy.deepcopy(measurements)}
            if kind=='screenshot':receipt.update(renderedStates={'roomDoor':'closed','cabinet':'extended'},animationSamples=[{'actual':0,'target':0,'tolerance':.001}])
            self.write(kind+'.json',receipt);final[kind]={'receipt':self.ref(kind+'.json'),'observation':copy.deepcopy(self.obs)}
        self.record['finalRepresentations']=final
    def ref(self,name):return {'path':name,'sha256':hashlib.sha256((self.base/name).read_bytes()).hexdigest()}
    def write(self,name,value):(self.base/name).write_text(value if isinstance(value,str)else json.dumps(value))
    def mutate_receipt(self,kind,fn):
        name=kind+'.json';d=json.loads((self.base/name).read_text());fn(d);self.write(name,d)
        if kind in ['plan','mesh','screenshot']:self.record['finalRepresentations'][kind]['receipt']=self.ref(name)
        else:next(x for x in self.record['operationMatrix']['scenarios']if x['id']==kind)['snapshot']=self.ref(name)
    def run_review(self):return review(self.case,self.record,self.base)
    def test_valid_conditional_states(self):self.assertEqual(self.run_review()['operationMatrixCheck']['status'],'pass_with_conditions')
    def test_legacy_does_not_claim_extended_coverage(self):
        for key in ['assemblyIntents','operationMatrix','finalRepresentations']:del self.record[key]
        out=self.run_review();self.assertEqual(out['finalRepresentationCheck']['status'],'not_provided')
    def test_required_extension_cannot_be_omitted(self):
        self.record['requiredChecks']=['finalRepresentationCheck'];del self.record['finalRepresentations']
        with self.assertRaisesRegex(ValueError,'Required extended'):self.run_review()
    def test_duplicate_or_unknown_assembly_group(self):
        self.record['assemblyIntents'][0]['groupId']='unknown'
        with self.assertRaisesRegex(ValueError,'assembly group'):self.run_review()
    def test_function_not_mapped(self):
        self.record['assemblyIntents'][0]['functions'][0]['memberIds']=[]
        with self.assertRaisesRegex(ValueError,'missing members'):self.run_review()
    def test_merely_renaming_does_not_meet_assembly_extent(self):
        self.state['furniture'][0]['w']=1000;self.record['stateSha256']=digest(self.state)
        with self.assertRaisesRegex(ValueError,'field differs'):self.run_review()
    def test_body_clear_but_person_blocked_is_not_usable(self):
        self.record['operationMatrix']['scenarios'][-1]['expected']='usable'
        with self.assertRaisesRegex(ValueError,'contradicts'):self.run_review()
    def test_missing_human_domain(self):
        self.mutate_receipt('normal',lambda d:d['checks'].pop('use'))
        with self.assertRaisesRegex(ValueError,'human-use'):self.run_review()
    def test_missing_actor_state(self):
        del self.record['operationMatrix']['scenarios'][0]['states']['person']
        with self.assertRaisesRegex(ValueError,'omits'):self.run_review()
    def test_unexercised_state(self):
        self.record['operationMatrix']['actors']['roomDoor'].append('half')
        with self.assertRaisesRegex(ValueError,'unchecked'):self.run_review()
    def test_handles_not_covered(self):
        self.record['operationMatrix']['motionIncludesHandles']=False
        with self.assertRaisesRegex(ValueError,'handles'):self.run_review()
    def test_stale_operating_snapshot(self):
        self.mutate_receipt('normal',lambda d:d.update(stateSha256='old'))
        with self.assertRaisesRegex(ValueError,'stale'):self.run_review()
    def test_condition_not_in_delivery(self):
        self.write('delivery.html','all clear');self.record['operationMatrix']['scenarios'][-1]['disclosure']['artifact']=self.ref('delivery.html')
        with self.assertRaisesRegex(ValueError,'absent'):self.run_review()
    def test_2d_old_full_depth_symbol(self):
        self.mutate_receipt('plan',lambda d:d['measurements'].update(counterOutline=[[0,0],[1600,0],[1600,450],[0,450]]))
        with self.assertRaisesRegex(ValueError,'2D/3D geometry differs'):self.run_review()
    def test_basin_shift_hidden_by_matching_outer_bounds(self):
        self.mutate_receipt('plan',lambda d:d['measurements'].update(fixtureCenter=[800,280]))
        with self.assertRaisesRegex(ValueError,'fixtureCenter'):self.run_review()
    def test_stale_final_receipt(self):
        self.mutate_receipt('mesh',lambda d:d.update(stateSha256='old'))
        with self.assertRaisesRegex(ValueError,'stale'):self.run_review()
    def test_wrong_screenshot_door_state(self):
        self.mutate_receipt('screenshot',lambda d:d['renderedStates'].update(roomDoor='open'))
        with self.assertRaisesRegex(ValueError,'wrong operating state'):self.run_review()
    def test_animation_in_flight(self):
        self.mutate_receipt('screenshot',lambda d:d['animationSamples'][0].update(actual=.4))
        with self.assertRaisesRegex(ValueError,'before pose settled'):self.run_review()
    def test_changed_actual_artifact(self):
        self.write('mesh.artifact','changed')
        with self.assertRaisesRegex(ValueError,'changed'):self.run_review()
    def test_new_state_failure_blocks_existing_build_entry(self):
        import sys
        from unittest.mock import patch
        sys.path.insert(0,str(Path(__file__).parent/'production'));import h5
        self.record['operationMatrix']['scenarios'][-1]['expected']='usable'
        self.write('review.json',self.record);case={**self.case,'layoutReview':self.ref('review.json')};self.write('case.json',{})
        with patch('floor_boundaries.normalize_floor_boundaries',return_value=(case, {'status':'isolated_fixture'})), patch.object(h5,'validate_case',return_value=case):
            with self.assertRaisesRegex(ValueError,'contradicts'):h5.build(self.base/'case.json',self.base/'out.html')
        self.assertFalse((self.base/'out.html').exists())
    def test_path_check_uses_obstacles(self):
        c={'kind':'path_clear','points':[[0,0],[10,0]],'obstacles':[[4,-1,6,1]],'radiusMm':.2}
        self.assertFalse(numeric_check(c));c['obstacles']=[[4,2,6,3]];self.assertTrue(numeric_check(c))

if __name__=='__main__':unittest.main()
