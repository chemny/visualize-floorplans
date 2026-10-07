#!/usr/bin/env python3
"""Regression checks for skipped visual selection and unauthorized fallbacks."""
import base64
import copy
import hashlib
import tempfile
import unittest
from pathlib import Path
from check_style_selection import check


class StyleSelectionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        data = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jC1sAAAAASUVORK5CYII=')
        (self.base / 'image.png').write_bytes(data)
        self.image = {'path': 'image.png', 'sha256': hashlib.sha256(data).hexdigest()}
        self.record = {
            'mode': 'visual', 'options': ['a', 'b', 'c'], 'layout': self.image,
            'boards': [{**self.image, 'style_ids': ['a', 'b', 'c'], 'shown_to_user': True}],
            'tool_check': {'checked': True, 'evidence': 'Host image tool returned a board.'},
            'comparison_review': {'fixed_layout_camera_light': True,
                'visually_distinct_styles': True,
                'evidence': 'Synthetic test review, not real case acceptance.'}}

    def test_visual_evidence_can_reach_selection(self):
        self.assertTrue(check(self.record, self.base)['passed'])

    def test_text_shortlist_cannot_replace_board(self):
        del self.record['boards']
        self.assertFalse(check(self.record, self.base)['passed'])

    def test_generated_but_unshown_board_blocks_selection(self):
        self.record['boards'][0]['shown_to_user'] = False
        self.assertFalse(check(self.record, self.base)['passed'])

    def test_stale_layout_or_board_blocks_selection(self):
        (self.base / 'image.png').write_bytes(b'changed')
        self.assertFalse(check(self.record, self.base)['passed'])

    def test_missing_style_or_review_blocks_selection(self):
        for change in ('coverage', 'review', 'tool'):
            record = copy.deepcopy(self.record)
            if change == 'coverage':
                record['boards'][0]['style_ids'] = ['a', 'b']
            elif change == 'review':
                record['comparison_review']['fixed_layout_camera_light'] = False
            else:
                record.pop('tool_check')
            self.assertFalse(check(record, self.base)['passed'])

    def test_access_blocker_alone_does_not_allow_text_choice(self):
        record = {'mode': 'text_fallback', 'options': ['a', 'b'],
                  'blocker': 'Current saved-state access blocked.',
                  'tool_check': {'checked': True, 'evidence': 'Generation reference unavailable.'}}
        self.assertFalse(check(record, self.base)['passed'])
        record['user_evidence'] = 'User explicitly requested text selection.'
        self.assertTrue(check(record, self.base)['passed'])

    def test_preset_does_not_authorize_production(self):
        self.record['selection'] = {'style_id': 'a'}
        self.assertFalse(check(self.record, self.base, production=True)['passed'])
        self.record['selection']['user_evidence'] = 'User chose panel a.'
        self.assertTrue(check(self.record, self.base, production=True)['passed'])

    def test_explicit_direct_choice_skips_board(self):
        record = {'mode': 'direct_choice', 'options': ['a'],
                  'user_evidence': 'User specifically requested style a.',
                  'selection': {'style_id': 'a', 'user_evidence': 'User specifically requested style a.'}}
        self.assertTrue(check(record, self.base, production=True)['passed'])


if __name__ == '__main__':
    unittest.main()
