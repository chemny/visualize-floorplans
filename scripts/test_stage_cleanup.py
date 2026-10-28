import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from stage_cleanup import scan, apply, restore, write


class StageCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'project'
        self.root.mkdir()
        (self.root / 'old.mp4').write_bytes(b'old video')
        self.inventory = self.base / 'inventory.json'
        self.set_inventory()
        self.plan = self.base / 'plan.json'
        self.backup = self.base / 'backups'

    def set_inventory(self, **extra):
        item = {'path': 'old.mp4', 'role': 'obsolete', 'reason': 'Superseded by accepted final', 'evidence': 'Final reviewed; dependency inspection found no consumers'}
        item.update(extra)
        self.inventory.write_text(json.dumps({'stage': 'delivery-confirmed', 'stageEvidence': 'User accepted final output', 'items': [item]}))

    def prepare(self):
        result = scan(self.root, self.inventory)
        write(self.plan, result)
        return result

    def execute(self, result):
        return apply(self.root, self.inventory, self.plan, result['planSha256'], self.backup)

    def test_backup_quarantine_restore_round_trip(self):
        result = self.prepare()
        self.assertEqual(result['candidateBytes'], 9)
        record = self.execute(result)
        self.assertFalse((self.root / 'old.mp4').exists())
        self.assertTrue(Path(record['backup']).is_file())
        restored = restore(self.root, record['batch'])
        self.assertEqual(restored['status'], 'restored')
        self.assertEqual((self.root / 'old.mp4').read_bytes(), b'old video')

    def test_reference_and_encoded_url_protect(self):
        (self.root / 'index.html').write_text('<video src="%6fld.mp4"></video>')
        result = scan(self.root, self.inventory)
        self.assertFalse(result['candidates'])
        self.assertIn('index.html', result['protected'][0]['references'])

    def test_unicode_json_reference_protects(self):
        (self.root / '旧图.png').write_bytes(b'png')
        self.set_inventory(path='旧图.png')
        (self.root / 'scheme.json').write_text(json.dumps({'reference': '旧图.png'}))
        self.assertFalse(scan(self.root, self.inventory)['candidates'])

    def test_accepted_and_unknown_files_not_eligible(self):
        self.set_inventory(role='final')
        (self.root / 'unknown.png').write_bytes(b'png')
        result = scan(self.root, self.inventory)
        self.assertFalse(result['candidates'])
        self.assertIn('unknown.png', result['unclassified'])

    def test_missing_evidence_protects(self):
        self.set_inventory(evidence='')
        self.assertFalse(scan(self.root, self.inventory)['candidates'])

    def test_new_reference_invalidates_approval(self):
        result = self.prepare()
        (self.root / 'new.json').write_text('{"input":"old.mp4"}')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            self.execute(result)
        self.assertTrue((self.root / 'old.mp4').exists())

    def test_modified_candidate_invalidates_approval(self):
        result = self.prepare()
        (self.root / 'old.mp4').write_bytes(b'new edit')
        with self.assertRaisesRegex(ValueError, 'Stale'):
            self.execute(result)

    def test_bad_approval_and_tampered_plan_rejected(self):
        result = self.prepare()
        with self.assertRaises(ValueError):
            apply(self.root, self.inventory, self.plan, 'wrong', self.backup)
        result['candidateBytes'] = 0
        self.plan.write_text(json.dumps(result))
        with self.assertRaises(ValueError):
            self.execute(result)

    def test_backup_failure_leaves_original(self):
        result = self.prepare()
        with patch('stage_cleanup.zipfile.ZipFile', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.execute(result)
        self.assertTrue((self.root / 'old.mp4').exists())

    def test_partial_quarantine_can_restore(self):
        (self.root / 'second.png').write_bytes(b'second')
        inv = json.loads(self.inventory.read_text())
        inv['items'].append({**inv['items'][0], 'path': 'second.png'})
        self.inventory.write_text(json.dumps(inv))
        result = self.prepare()
        original = Path.rename
        def fail_second(src, dst):
            if src == self.root / 'second.png':
                raise OSError('Interrupted move')
            return original(src, dst)
        with patch.object(Path, 'rename', fail_second):
            with self.assertRaises(OSError):
                self.execute(result)
        batches = [p for p in (self.root / '.cleanup').iterdir() if p.is_dir()]
        self.assertEqual(len(batches), 1)
        restore(self.root, batches[0].name)
        self.assertEqual((self.root / 'old.mp4').read_bytes(), b'old video')
        self.assertEqual((self.root / 'second.png').read_bytes(), b'second')

    def test_no_stage_confirmation_rejected(self):
        inv = json.loads(self.inventory.read_text())
        inv['stageEvidence'] = ''
        self.inventory.write_text(json.dumps(inv))
        with self.assertRaises(ValueError):
            scan(self.root, self.inventory)

    def test_large_json_validated_and_unicode_reference_protected(self):
        (self.root / '旧图.png').write_bytes(b'png')
        self.set_inventory(path='旧图.png')
        doc = self.root / 'large.json'
        doc.write_text(json.dumps({'padding': 'x' * (17 * 1024 * 1024), 'nested': [{'path': '旧图.png'}]}))
        result = scan(self.root, self.inventory)
        self.assertFalse(result['candidates'])
        self.assertIn('large.json', result['protected'][0]['references'])

    def test_large_invalid_json_is_not_skipped(self):
        (self.root / 'large.json').write_text('{"padding":"' + 'x' * (17 * 1024 * 1024) + '"')
        with self.assertRaises(json.JSONDecodeError):
            scan(self.root, self.inventory)

    def test_duplicate_json_cannot_hide_reference(self):
        (self.root / 'duplicate.json').write_text('{"a":"old.mp4","a":"no-reference"}')
        with self.assertRaisesRegex(ValueError, 'Duplicate JSON'):
            scan(self.root, self.inventory)

    def test_backup_inside_project_rejected(self):
        result = self.prepare()
        self.backup = self.root / 'backups'
        with self.assertRaises(ValueError):
            self.execute(result)

    def test_paths_and_symlinks_rejected(self):
        for name in ('../outside.mp4', '/outside.mp4', 'C:/outside.mp4', '.cleanup/old.mp4'):
            self.set_inventory(path=name)
            with self.assertRaises(ValueError):
                scan(self.root, self.inventory)
        link = self.root / 'link.mp4'
        link.symlink_to(self.root / 'old.mp4')
        self.set_inventory(path='link.mp4')
        with self.assertRaises(ValueError):
            scan(self.root, self.inventory)

    def test_restore_never_overwrites(self):
        result = self.prepare()
        record = self.execute(result)
        (self.root / 'old.mp4').write_bytes(b'user replacement')
        with self.assertRaises(ValueError):
            restore(self.root, record['batch'])
        self.assertEqual((self.root / 'old.mp4').read_bytes(), b'user replacement')

    def test_restore_rejects_modified_quarantine(self):
        record = self.execute(self.prepare())
        (self.root / '.cleanup' / record['batch'] / 'files' / 'old.mp4').write_bytes(b'damaged')
        with self.assertRaises(ValueError):
            restore(self.root, record['batch'])

    def test_reserved_sources_even_if_misclassified(self):
        (self.root / 'inputs').mkdir()
        (self.root / 'inputs' / 'source.png').write_bytes(b'original')
        self.set_inventory(path='inputs/source.png')
        self.assertFalse(scan(self.root, self.inventory)['candidates'])


if __name__ == '__main__':
    unittest.main()
