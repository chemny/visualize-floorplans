import hashlib
import json
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import patch

from engine_provenance import (SCHEMA, file_sha, require_current_engine,
                               source_fingerprint, source_inputs)


class EngineProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.assets = self.root / 'assets/h5'
        (self.assets / 'source').mkdir(parents=True)
        for name, content in {'source/app.js': 'console.log(1)',
                              'source/style.css': 'body{}',
                              'source/package.json': '{"type":"module"}',
                              'version.json': '{"version":"test"}',
                              'engine.js': 'compiled-engine',
                              'component-types.json': '{"types":[]}',
                              'template.html': '<html>template</html>'}.items():
            (self.assets / name).write_text(content, encoding='utf-8')
        self.stamp_fixture()

    def stamp_fixture(self):
        inputs = source_inputs(self.root)
        # Synthetic evidence, only for rejection tests. Production has no stamp API.
        self.evidence = {'schema': SCHEMA, 'inputs': inputs,
                         'sourceSha256': source_fingerprint(inputs),
                         'engineSha256': file_sha(self.assets / 'engine.js'),
                         'registrySha256': file_sha(self.assets / 'component-types.json')}
        (self.assets / 'engine.provenance.json').write_text(json.dumps(self.evidence))

    def test_current_and_relocatable(self):
        self.assertEqual(require_current_engine(self.root)['status'], 'pass')
        self.assertTrue(all(not Path(r['path']).is_absolute() for r in self.evidence['inputs']))

    def test_changed_source_css_json_and_version_rejected(self):
        for name in ['source/app.js', 'source/style.css', 'source/package.json', 'version.json']:
            p = self.assets / name
            before = p.read_bytes()
            p.write_bytes(before + b' ')
            with self.assertRaisesRegex(ValueError, 'source changed'):
                require_current_engine(self.root)
            p.write_bytes(before)

    def test_added_and_removed_source_rejected(self):
        p = self.assets / 'source/new.mjs'
        p.write_text('export const a=1')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            require_current_engine(self.root)
        self.stamp_fixture()
        p.unlink()
        with self.assertRaisesRegex(ValueError, 'source changed'):
            require_current_engine(self.root)

    def test_bundle_and_registry_tampering_rejected(self):
        for name in ['engine.js', 'component-types.json']:
            p = self.assets / name
            before = p.read_bytes()
            p.write_bytes(before + b' ')
            with self.assertRaisesRegex(ValueError, 'differs from its provenance'):
                require_current_engine(self.root)
            p.write_bytes(before)

    def test_missing_or_invalid_manifest_rejected(self):
        p = self.assets / 'engine.provenance.json'
        for content in [None, '{bad', '{}']:
            if content is None:
                p.unlink()
            else:
                p.write_text(content)
            with self.assertRaisesRegex(ValueError, 'provenance'):
                require_current_engine(self.root)

    def test_forged_combined_hash_without_matching_list_rejected(self):
        self.evidence['sourceSha256'] = 'a' * 64
        (self.assets / 'engine.provenance.json').write_text(json.dumps(self.evidence))
        with self.assertRaisesRegex(ValueError, 'source changed'):
            require_current_engine(self.root)

    def test_template_is_independent_from_bundle(self):
        (self.assets / 'template.html').write_text('New product copy')
        self.assertEqual(require_current_engine(self.root)['status'], 'pass')

    def test_node_modules_are_not_shipped_source(self):
        p = self.assets / 'source/node_modules/test/index.js'
        p.parent.mkdir(parents=True)
        p.write_text('external')
        self.assertEqual(require_current_engine(self.root)['status'], 'pass')

    def test_build_rejects_stale_bundle_before_writing_html(self):
        import h5
        case = {'initialState': {'walls': [], 'furniture': []}, 'model': {'rooms': []}}
        (self.assets / 'source/app.js').write_text('changed source')
        out = self.root / 'out.html'
        with patch.object(h5, 'ROOT', self.root), patch.object(h5, 'ASSETS', self.assets), \
                patch.object(h5, 'read_snapshot', return_value=(case, 'test-input')), \
                patch.object(h5, 'validate_case', return_value=case), \
                patch('floor_boundaries.normalize_floor_boundaries', return_value=(case, {})), \
                patch('room_light_placement.apply_room_light_defaults', return_value=case):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                h5.build('unused-fixture.json', out)
        self.assertFalse(out.exists())

    def build_fixture(self, validator=None):
        import h5
        case = {'caseId': 'fixture', 'initialState': {'walls': [], 'furniture': []},
                'model': {'rooms': [], 'height': 2800}}
        p = self.root / 'case.json'
        p.write_text(json.dumps(case))
        stack = ExitStack()
        self.addCleanup(stack.close)
        for target, value in [('ROOT', self.root), ('ASSETS', self.assets)]:
            stack.enter_context(patch.object(h5, target, value))
        stack.enter_context(patch.object(h5, 'validate_case', side_effect=validator or (lambda c: c)))
        stack.enter_context(patch('floor_boundaries.normalize_floor_boundaries', side_effect=lambda c: (c, {})))
        stack.enter_context(patch('room_light_placement.apply_room_light_defaults', side_effect=lambda c: c))
        return h5, p

    def test_engine_replaced_after_gate_is_rejected(self):
        h5, case = self.build_fixture()
        def replaced(root):
            record = require_current_engine(root)
            (self.assets / 'engine.js').write_text('changed during build')
            return record
        out = self.root / 'race.html'
        with patch('engine_provenance.require_current_engine', side_effect=replaced):
            with self.assertRaisesRegex(ValueError, 'engine changed during generation'):
                h5.build(case, out)
        self.assertFalse(out.exists())

    def test_case_replaced_during_build_is_rejected(self):
        def changed(c):
            (self.root / 'case.json').write_text('{"different":true}')
            return c
        h5, case = self.build_fixture(changed)
        out = self.root / 'case-race.html'
        with self.assertRaisesRegex(ValueError, 'input changed during generation'):
            h5.build(case, out)
        self.assertFalse(out.exists())

    def test_metadata_uses_read_template_bytes_not_later_file(self):
        h5, case = self.build_fixture()
        before = (self.assets / 'template.html').read_bytes()
        calls = []
        def replaced_template(root):
            record = require_current_engine(root)
            calls.append(1)
            if len(calls) == 2:
                (self.assets / 'template.html').write_text('next template revision')
            return record
        out = self.root / 'snapshot.html'
        with patch('engine_provenance.require_current_engine', side_effect=replaced_template):
            h5.build(case, out)
        meta = json.loads(out.with_suffix('.build.json').read_text())
        self.assertEqual(meta['templateSha256'], hashlib.sha256(before).hexdigest())
        self.assertEqual(meta['caseSha256'], file_sha(case))
        self.assertEqual(out.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
