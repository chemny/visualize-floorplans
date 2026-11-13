import unittest,math
from tour_audio import music_gain
class MusicGainTests(unittest.TestCase):
 def test_fixed_gain(self):
  self.assertEqual(music_gain(),1);self.assertEqual(music_gain(.35),.35);self.assertEqual(music_gain(0),0)
 def test_reject_invalid(self):
  for v in [True,-.1,1.1,'0.3',None,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):music_gain(v)
