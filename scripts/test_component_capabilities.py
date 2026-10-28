import copy
import json
import unittest
from check_component_capabilities import ROOT, check


class CapabilityInventoryTests(unittest.TestCase):
    def setUp(self):
        self.data = json.loads((ROOT / 'assets/component-capabilities.json').read_text())
        self.ids = json.loads((ROOT / 'assets/h5/component-types.json').read_text())['types']

    def rejects(self, change):
        data = copy.deepcopy(self.data)
        change(data)
        with self.assertRaises(AssertionError):
            check(data, self.ids)

    def row(self, data, id):
        return next(row for row in data['components'] if row['id'] == id)

    def test_inventory(self):
        r = check(self.data, self.ids)
        self.assertEqual(r['registeredComponents'], len(self.ids))
        self.assertEqual(r['behaviorProfiles'], 13)
        self.assertEqual(r['architecturalMechanisms'], 9)

    def test_missing_or_duplicate(self):
        for rows in [self.data['components'][:-1], self.data['components'] + [self.data['components'][0]]]:
            self.rejects(lambda d: d.update(components=rows))

    def test_false_mechanism_claim(self):
        for key in ['folding', 'pocket', 'wall_mounted_sliding']:
            self.rejects(lambda d: d['doorMechanisms'].update({key: 'supported'}))
        self.rejects(lambda d: d['architecturalMechanismProfiles']['pocket'].update(support='single_wall_slide_geometry'))
        self.rejects(lambda d: d['architecturalMechanismProfiles']['folding'].update(implemented=['animated']))

    def test_alias_and_operation(self):
        for key, value in [('alias', 'unknown'), ('operation', 'fully_animated')]:
            self.rejects(lambda d: d['components'][0].update({key: value}))

    def test_missing_profile_or_dimensions(self):
        self.rejects(lambda d: self.row(d, 'chair').pop('behaviorProfile'))
        self.rejects(lambda d: self.row(d, 'chair').update(behaviorProfile='unknown'))
        self.rejects(lambda d: d['behaviorProfiles']['nominal-envelope'].pop('resize'))
        self.rejects(lambda d: d['behaviorProfiles']['nominal-envelope']['resize'].pop('limits'))

    def test_fixed_leaf_basin_and_body_contracts_are_required(self):
        for profile in ['shower-fixed-leaf', 'vanity-fixed-basin', 'bathtub-fixed-body']:
            self.rejects(lambda d: d['behaviorProfiles'][profile]['resize'].update(fixed=[]))
            self.rejects(lambda d: d['behaviorProfiles'][profile]['resize'].update(mode='renderer_defined_envelope'))

    def test_alias_inherits_target_and_matches_actual_runtime_alias(self):
        self.rejects(lambda d: self.row(d, 'basin').update(behaviorProfile='bathtub-fixed-body'))
        self.rejects(lambda d: self.row(d, 'basin').update(runtimeType='bathtub'))
        self.rejects(lambda d: self.row(d, 'basin').update(alias='bathtub', runtimeType='bathtub', behaviorProfile='bathtub-fixed-body'))
        self.rejects(lambda d: self.row(d, 'sink').update(behaviorProfile='vanity-fixed-basin'))

    def test_source_and_test_evidence_are_required_and_local(self):
        self.rejects(lambda d: d['behaviorProfiles']['shower-fixed-leaf']['evidence'].update(source=[]))
        self.rejects(lambda d: d['behaviorProfiles']['vanity-fixed-basin']['evidence'].update(validation=[]))
        self.rejects(lambda d: d['behaviorProfiles']['bathtub-fixed-body']['evidence'].update(validation=['scripts/missing_test.py']))
        self.rejects(lambda d: d['behaviorProfiles']['bathtub-fixed-body']['evidence'].update(validation=['../elsewhere.py']))

    def test_storage_and_lighting_boundaries_cannot_be_silently_replaced(self):
        self.rejects(lambda d: self.row(d, 'wardrobe').update(behaviorProfile='nominal-envelope'))
        self.rejects(lambda d: self.row(d, 'pendant').update(behaviorProfile='nominal-envelope'))
        self.rejects(lambda d: d['behaviorProfiles']['storage-envelope']['operation'].update(support='static_representation'))
        self.rejects(lambda d: d['behaviorProfiles']['shower-fixed-leaf']['operation'].update(support='static_representation'))

    def test_geometry_is_not_runtime_product_or_site_acceptance(self):
        self.rejects(lambda d: d['behaviorProfiles']['vanity-fixed-basin']['representation'].update(acceptance='passed'))
        self.rejects(lambda d: d['behaviorProfiles']['storage-envelope']['operation'].update(support='fully_animated'))
        self.rejects(lambda d: d['architecturalMechanismProfiles']['window'].update(acceptance='passed'))

    def test_material_does_not_add_a_door_mechanism(self):
        self.rejects(lambda d: d['architecturalCatalog']['panelFinishes'].update(independentOfMechanism=False))
        self.rejects(lambda d: d['architecturalMechanismProfiles']['window'].update(support='hinged_geometry'))

    def test_cross_layout_and_component_check_entries_are_required(self):
        self.rejects(lambda d: d.pop('regressionEntry'))
        self.rejects(lambda d: d['regressionEntry'].update(componentBrowser='scripts/missing.mjs'))

    def test_old_schema_is_rejected(self):
        self.rejects(lambda d: d.update(schemaVersion=1))


if __name__ == '__main__':
    unittest.main()
