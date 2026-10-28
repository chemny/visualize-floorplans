"""Validate the component capability index; this is not runtime/site acceptance."""
import argparse
import json
import re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
RESIZE_MODES = {'renderer_defined_envelope', 'cabinet_envelope', 'fixed_leaf_variable_enclosure',
                'fixed_bowl_variable_cabinet', 'fixed_body_variable_surround',
                'manual_or_owner_derived_finish', 'legacy_proxy_envelope'}
OPERATION_SUPPORT = {'static_representation', 'declared_use_envelope_only', 'model_selection_required',
                     'conditional_hinged_mechanism', 'fixture_light_and_visibility',
                     'schematic_only', 'legacy_shape_only'}
SPECIAL = {'shower': ('shower-fixed-leaf', 'fixed_leaf_variable_enclosure', {'showerDoor.width'}),
           'vanity': ('vanity-fixed-basin', 'fixed_bowl_variable_cabinet',
                      {'basinLayout.width', 'basinLayout.depth', 'basinLayout.gap',
                       'basinLayout.backGap', 'basinLayout.faucetInset'}),
           'bathtub': ('bathtub-fixed-body', 'fixed_body_variable_surround',
                       {'bathtubBody.width', 'bathtubBody.depth'})}
MECHANISMS = {'hinged': 'hinged_geometry', 'wallslide': 'single_wall_slide_geometry',
              'sliding': 'multi_panel_slide_geometry', 'double': 'two_hinge_leaves_geometry',
              'hidden': 'hinged_finish_variant', 'passage': 'aperture_only',
              'window': 'aperture_only', 'folding': 'unsupported', 'pocket': 'unsupported'}


def references(refs, label):
    assert isinstance(refs, list), label + ': evidence must be a list'
    for ref in refs:
        path = Path(ref)
        assert not path.is_absolute() and '..' not in path.parts, label + ': invalid evidence path'
        assert (ROOT / path).is_file(), label + ': missing evidence ' + ref


def check(data, registry):
    assert data.get('schemaVersion') == 2, 'capability schema version must be 2'
    profiles = data.get('behaviorProfiles')
    assert isinstance(profiles, dict) and profiles, 'behavior profiles missing'
    for key, p in profiles.items():
        assert p.get('label'), key + ': label missing'
        resize, operation, evidence = p.get('resize', {}), p.get('operation', {}), p.get('evidence', {})
        assert resize.get('mode') in RESIZE_MODES, key + ': unknown resize behavior'
        for field in ['mutable', 'fixed', 'exceptions']:
            assert isinstance(resize.get(field), list), key + ': resize ' + field + ' missing'
        assert resize['mutable'] and resize.get('initialization') and resize.get('limits'), key + ': incomplete resize contract'
        assert not set(resize['mutable']) & set(resize['fixed']), key + ': fixed and mutable fields overlap'
        assert operation.get('support') in OPERATION_SUPPORT, key + ': unsupported operational claim'
        for field in ['implemented', 'notImplemented', 'requires']:
            assert isinstance(operation.get(field), list) and operation[field], key + ': operation ' + field + ' missing'
        assert p.get('representation', {}).get('acceptance') == 'not_implied_by_index', key + ': false runtime acceptance'
        assert p['representation'].get('planMeshRelation'), key + ': representation contract missing'
        for field in ['source', 'validation', 'browser']:
            references(evidence.get(field), key)
        assert evidence['source'] and evidence['validation'], key + ': implementation and test evidence required'
    rows = data['components']; ids = [x['id'] for x in rows]; by_id = {x['id']: x for x in rows}
    source = (ROOT / 'assets/h5/source/app.js').read_text()
    alias_literal = re.search(r'const typeMap=\{([^}]+)\}', source)
    assert alias_literal, 'runtime alias declaration missing'
    runtime_aliases = {a: b for a, b in re.findall(r"(\w+):'([^']+)'", alias_literal.group(1)) if a != b}
    assert len(ids) == len(set(ids)), 'duplicate component ID'
    assert set(ids) == set(registry), 'registry coverage mismatch'
    for row in rows:
        key = row['id']
        assert row.get('alias') == runtime_aliases.get(key), key + ': alias differs from runtime source'
        assert row['family'] in data['families'], 'unknown family'
        assert row['use'] and row['checks'] and row['optional']
        assert row.get('behaviorProfile') in profiles, key + ': unknown behavior profile'
        assert row.get('runtimeType') in registry, key + ': unknown runtime type'
        if row.get('alias'):
            assert row['alias'] in registry, 'unknown alias'
            assert row['runtimeType'] == row['alias'], key + ': alias runtime mismatch'
            target = by_id[row['alias']]
            assert not target.get('alias'), key + ': chained aliases need explicit resolution'
            assert row['behaviorProfile'] == target['behaviorProfile'], key + ': alias behavior differs from target'
        else:
            assert row['runtimeType'] == key, key + ': non-alias runtime mismatch'
        references(row['evidence'], key)
        # Preserve the conservative historical boundary: an indexed model is not a verified product action.
        assert row['operation'] == 'manual_envelope_or_model_selection_required', 'unsupported operational claim'
        if row['family'] == 'storage':
            assert row['behaviorProfile'] == 'storage-envelope', key + ': cabinet resize behavior missing'
        if row['family'] == 'lighting':
            assert row['behaviorProfile'] == 'lighting-fixture', key + ': light visibility/illumination split missing'
    for component, (profile, mode, fixed) in SPECIAL.items():
        assert by_id[component]['behaviorProfile'] == profile, component + ': required behavior profile missing'
        resize = profiles[profile]['resize']
        assert resize['mode'] == mode and set(resize['fixed']) == fixed, component + ': fixed subpart contract missing'
    assert by_id['ksink']['behaviorProfile'] == 'kitchen-sink-envelope', 'kitchen sink must not borrow fixed vanity behavior'
    assert profiles['shower-fixed-leaf']['operation']['support'] == 'conditional_hinged_mechanism', 'shower must require an explicit mechanism'
    assert profiles['lighting-fixture']['operation']['support'] == 'fixture_light_and_visibility', 'lighting contract missing'
    assert profiles['storage-envelope']['operation']['support'] == 'declared_use_envelope_only', 'cabinet must not imply animated doors'
    for key in ('folding', 'pocket'):
        assert data['doorMechanisms'][key] == 'unsupported', key
    assert 'single wall-side panel' in data['doorMechanisms']['wall_mounted_sliding']
    assert data['architecturalCatalog']['common'] == ['hinged', 'wallslide', 'sliding', 'window', 'passage']
    assert 'hinged' in data['doorMechanisms']['hidden']
    assert 'advanced UI available' in data['doorMechanisms']['sliding']
    mechanisms = data.get('architecturalMechanismProfiles', {})
    assert set(mechanisms) == set(MECHANISMS), 'architectural mechanism coverage mismatch'
    for key, support in MECHANISMS.items():
        p = mechanisms[key]
        assert p.get('support') == support, key + ': false mechanism support claim'
        for field in ['requires', 'implemented', 'notImplemented']:
            assert isinstance(p.get(field), list), key + ': mechanism boundary missing'
        assert p['notImplemented'], key + ': mechanism limits missing'
        if support == 'unsupported':
            assert not p['implemented'], key + ': unsupported mechanism cannot have implemented actions'
        else:
            assert p['requires'] and p['implemented'], key + ': mechanism requirements missing'
        assert p.get('acceptance') == 'case_operation_paths_and_product_conditions_required', key + ': false mechanism acceptance'
        for field in ['source', 'validation']:
            references(p.get('evidence', {}).get(field), key)
            assert p['evidence'][field], key + ': evidence missing'
    finishes = data['architecturalCatalog'].get('panelFinishes', {})
    assert finishes.get('values') == ['solid', 'clear', 'frosted'] and finishes.get('independentOfMechanism') is True, 'door finishes must remain independent from mechanisms'
    references(finishes.get('evidence'), 'panel finishes')
    regression = data.get('regressionEntry', {})
    assert regression.get('scope'), 'regression scope missing'
    for key in ['crossLayout', 'fixtures', 'componentBrowser']:
        assert regression.get(key), 'regression entry missing: ' + key
        references([regression[key]], 'regression entry')
    assert data['caseOnly'], 'case-specific extension boundary missing'
    return {'status': 'pass', 'registeredComponents': len(ids), 'families': len(data['families']),
            'behaviorProfiles': len(profiles), 'architecturalMechanisms': len(mechanisms),
            'scope': 'registry/implementation contract/evidence-path consistency only; no per-component or current-case runtime, product, site or visual acceptance'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--component', help='Show a registered component and its shared behavior contract')
    args = parser.parse_args()
    data = json.loads((ROOT / 'assets/component-capabilities.json').read_text())
    registry = json.loads((ROOT / 'assets/h5/component-types.json').read_text())['types']
    result = check(data, registry)
    if args.component:
        rows = {row['id']: row for row in data['components']}
        if args.component not in rows:
            parser.error('Unknown component: ' + args.component)
        row = rows[args.component]
        result['component'] = row
        result['behavior'] = data['behaviorProfiles'][row['behaviorProfile']]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
