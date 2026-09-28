import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from platform_support import font_candidates, load_font
from vector_tools import atomic_write, load_json


class PortabilityTests(unittest.TestCase):
    def test_unicode_space_paths(self):
        with tempfile.TemporaryDirectory(prefix="floorplan ") as directory:
            target = Path(directory) / "中文 空间" / "布局.json"
            atomic_write(target, '{"label":"书房"}')
            self.assertEqual(load_json(target)["label"], "书房")
            atomic_write(target, '{"label":"客厅"}')
            self.assertEqual(load_json(target)["label"], "客厅")

    def test_windows_font_discovery(self):
        with patch.dict(os.environ, {"WINDIR": "X:/Windows", "FLOORPLAN_FONT": "custom font.ttc"}):
            candidates = list(font_candidates())
            self.assertEqual(candidates[0], Path("custom font.ttc"))
            self.assertIn(Path("X:/Windows/Fonts/msyh.ttc"), candidates)

    def test_missing_font_is_reported(self):
        with patch("platform_support.find_font", return_value=None):
            with self.assertWarns(RuntimeWarning):
                self.assertIsNotNone(load_font(18))


if __name__ == "__main__":
    unittest.main()
