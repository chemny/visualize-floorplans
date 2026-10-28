import unittest
from tour_subtitles import phrase_cues

class SubtitleTests(unittest.TestCase):
 def test_phrase_cuts_preserve_source_interval_and_remove_pause_marks(self):
  rows=[{'start':1.,'end':6.,'text':'主卧连接衣帽间，重点看采光、床位和收纳。'}]
  out=phrase_cues(rows)
  self.assertEqual([r['text'] for r in out],['主卧连接衣帽间','重点看采光','床位和收纳'])
  self.assertEqual(out[0]['start'],1.);self.assertEqual(out[-1]['end'],6.)
  self.assertTrue(all(a['end']==b['start'] for a,b in zip(out,out[1:])))
  self.assertEqual(rows[0]['text'],'主卧连接衣帽间，重点看采光、床位和收纳。')
 def test_digits_and_gaps_survive_and_cues_do_not_flash(self):
  out=phrase_cues([{'start':0.,'end':3.,'text':'保持1.6米，使用16:9。'},{'start':5.,'end':6.,'text':'明亮、清爽。'}])
  self.assertIn('1.6',out[0]['text']);self.assertTrue(any('16:9' in x['text'] for x in out))
  self.assertTrue(all(x['end']-x['start']>=.7 for x in out));self.assertEqual(out[-1]['start'],5.)
 def test_long_text_is_split_and_timeline_never_overruns(self):
  out=phrase_cues([{'start':0,'end':8,'text':'卧室采用浅橡木地板和柔和的奶油白墙面搭配暖光照明'}])
  self.assertTrue(len(out)>1);self.assertTrue(all(len(x['text'])<=14 for x in out));self.assertEqual(out[-1]['end'],8)
if __name__=='__main__':unittest.main()
