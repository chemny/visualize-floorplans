import re,unittest
from tour_playback import prepare_renderer,ASSETS,preview_page
class PlaybackTests(unittest.TestCase):
 def test_capture_function_is_unchanged_and_preparation_is_idempotent(self):
  src=(ASSETS.parent/'runtime/renderer.html').read_text();new=prepare_renderer(src)
  original=re.search(r'window.renderFrame=async f=>\{.*?\n\};',src,re.S)[0]
  self.assertIn(original,new);self.assertIn('window.renderInteractiveFrame',new);self.assertEqual(prepare_renderer(new),new)
 def test_unknown_renderer_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'Unknown renderer'):prepare_renderer('<canvas></canvas>')
 def test_shared_template_uses_continuous_player_and_fractional_seek(self):
  page=preview_page('待确认');self.assertIn('rehearsal-player.js',page);self.assertIn('step="any"',page);self.assertNotIn('Math.round(at',page)
 def test_preview_never_embeds_a_complete_stage_page(self):
  page=preview_page('待确认')
  self.assertIn('src="route-embed.html"',page);self.assertNotIn('src="route.html',page)
  self.assertNotIn('<nav',page);self.assertNotIn('<video',page)
  self.assertIn('href="route.html"',page);self.assertIn('@media(max-width:700px)',page)
if __name__=='__main__':unittest.main()
