import copy
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent/'production'))
from workbench_regression_cases import regression_cases
from floor_boundaries import normalize_floor_boundaries
from workbench_cross_layout import inspect_case_result, summarize
from workbench_browser_suite import prerequisite, selected_checks


class CrossLayoutTests(unittest.TestCase):
    def test_independent_cases_have_distinct_shapes_ids_and_component_sets(self):
        cases=regression_cases()
        self.assertEqual(len(cases),3)
        self.assertEqual(len({json.dumps(c['case']['model']['footprint']) for c in cases}),3)
        self.assertEqual(len({c['case']['caseId'] for c in cases}),3)
        self.assertEqual([len(c['case']['model']['rooms']) for c in cases],[2,3,1])
        legacy={'living','dining','primary','bed_nw','bed_ne','suite-vanity'}
        for spec in cases:
            c=spec['case']
            self.assertTrue(c['syntheticFixture']['notApprovedLayout'])
            self.assertTrue(c['caseId'].startswith('synthetic-cross-layout-'))
            self.assertFalse(legacy&{r['id'] for r in c['model']['rooms']})
            self.assertTrue(all(len(r['name'])<=3 for r in c['model']['rooms']))
        first,second=cases[:2]
        for kind in ['shower','vanity','bathtub']:
            a=next(f for f in first['case']['initialState']['furniture'] if f['type']==kind)
            b=next(f for f in second['case']['initialState']['furniture'] if f['type']==kind)
            self.assertNotEqual(a['id'],b['id']);self.assertNotEqual(a['rot'],b['rot'])
        self.assertEqual(cases[2]['case']['initialState']['furniture'],[])
        cases[0]['case']['initialState']['furniture'].clear()
        self.assertTrue(regression_cases()[0]['case']['initialState']['furniture'])

    def test_all_shapes_normalize_without_moving_any_furniture(self):
        for spec in regression_cases():
            c=spec['case'];before=copy.deepcopy(c['initialState'])
            normalized,report=normalize_floor_boundaries(c)
            self.assertEqual(report['status'],'pass')
            self.assertEqual(c['initialState'],before)
            self.assertEqual(normalized['initialState'],before)
            self.assertEqual(normalize_floor_boundaries(normalized)[0],normalized)

    def test_core_targets_do_not_require_legacy_room_or_furniture_ids(self):
        self.assertIn('components',selected_checks('core,components,floors'))
        for spec in regression_cases():
            self.assertTrue(prerequisite(spec['case'],'any_room')[0])
        self.assertFalse(prerequisite(regression_cases()[2]['case'],'components')[0])

    def test_required_pass_cannot_be_replaced_with_skipped(self):
        spec=regression_cases()[0]
        report={'status':'pass','caseUnchanged':True,'serverStopped':True,
                'checks':[{'name':'copy','status':'not_applicable'}]}
        self.assertEqual(inspect_case_result(spec,report,['copy'])[0],'fail')

    def test_component_aggregate_pass_cannot_hide_missing_mechanisms(self):
        spec=regression_cases()[0]
        report={'status':'pass','caseUnchanged':True,'serverStopped':True,
                'checks':[{'name':'components','status':'pass'}]}
        partial={'checks':[{'kind':'door','status':'pass'},{'kind':'shower','status':'not_applicable'}]}
        self.assertEqual(inspect_case_result(spec,report,['components'],partial)[0],'fail')
        full={'checks':[{'kind':kind,'status':'pass'} for kind in spec['requiredMechanisms']]}
        self.assertEqual(inspect_case_result(spec,report,['components'],full)[0],'pass')

    def test_missing_environment_and_incomplete_results_do_not_pass(self):
        spec=regression_cases()[0]
        self.assertEqual(inspect_case_result(spec,{},['copy'])[0],'blocked')
        blocked={'status':'blocked','checks':[{'name':'copy','status':'blocked'}]}
        self.assertEqual(inspect_case_result(spec,blocked,['copy'])[0],'blocked')
        self.assertEqual(summarize([{'status':'pass'},{'status':'fail'}]),'fail')
        self.assertEqual(summarize([{'status':'pass'},{'status':'blocked'}]),'blocked')
        self.assertEqual(summarize([{'status':'not_applicable'}]),'not_applicable')

    def test_absent_features_in_empty_case_are_explicit_not_applicable(self):
        spec=regression_cases()[2]
        r={'status':'pass','caseUnchanged':True,'serverStopped':True,
           'checks':[{'name':'copy','status':'pass'},
                     {'name':'generated','status':'not_applicable'},
                     {'name':'components','status':'not_applicable'}]}
        self.assertEqual(inspect_case_result(spec,r,['copy','generated','components'])[0],'pass')
        r['checks'][2]['status']='pass'
        self.assertEqual(inspect_case_result(spec,r,['copy','generated','components'])[0],'fail')


if __name__=='__main__':unittest.main()
