"""Independent synthetic cases; no real user approval or video capture."""
import copy,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from route_rehearsal import build as rehearsal
from tour_pages import build,sha,read,ASSETS
class TourPagesTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name);p=self.p
  self.t={'schemeSha256':'independent-layout','fps':2,'seconds':4,'frames':[{'pointMm':[600+i*60,700+i*20],'eyeMm':1600,'yawRadians':i*.01,'pitchRadians':-.05,'horizontalFovDegrees':73} for i in range(8)],'visits':[{'name':'front','frame':0},{'name':'inside','frame':3},{'name':'leave','frame':7}]}
  self.c={'chapters':[{'name':'入口 → 东室','from':'front','to':'inside','phase':'transit'},{'name':'东室 · 观看','from':'inside','to':'leave','phase':'observe','subjects':[]}]}
  self.b={'schemeSha256':'independent-layout','model':{'rooms':[{'id':'east-new-id','poly':[[0,0],[3000,0],[3000,2000],[0,2000]]}]},'state':{'walls':[],'furniture':[]}}
  for name,v in [('tour.json',self.t),('config.json',self.c),('bundle.json',self.b),('scene.json',{'schemeSha256':self.t['schemeSha256']})]:(p/name).write_text(json.dumps(v))
  (p/'geometry.bin').write_bytes(b'fixture');Image.new('RGB',(300,200),'ivory').save(p/'plan.png')
  rehearsal(p/'tour.json',p/'config.json',p/'bundle.json',p/'plan.png',[-100,-200,3400,2400],p/'rehearsal',5,p)
  self.manifest=p/'rehearsal/rehearsal.json';(p/'film.mp4').write_bytes(b'test video, probe mocked');(p/'voice.m4a').write_bytes(b'aligned test voice');(p/'music.m4a').write_bytes(b'test music')
  from tour_stage_gate import pending,CHECKS
  approval=pending(p/'film.mp4',p/'tour.json');approval.update(status='approved',confirmedBy='synthetic-test-user',evidence='Synthetic fixture only');approval['checks']={k:True for k in CHECKS}
  (p/'video-review.json').write_text(json.dumps(approval))
 def video(self):return {'path':str(self.p/'film.mp4'),'sha256':sha(self.p/'film.mp4'),'tourSha256':sha(self.p/'tour.json')}
 def probe(self):return patch('tour_pages.probe_video',return_value={'seconds':4,'fps':2,'frames':8,'width':640,'height':360,'hasAudio':False})
 def job(self):return {'videoReview':{'path':str(self.p/'video-review.json'),'sha256':sha(self.p/'video-review.json')},'video':self.video(),'narration':{'videoSha256':sha(self.p/'film.mp4'),'voice':{'path':str(self.p/'voice.m4a'),'sha256':sha(self.p/'voice.m4a')},'music':{'path':str(self.p/'music.m4a'),'sha256':sha(self.p/'music.m4a')},'captions':[{'start':.1,'end':1.5,'text':'这是另一套户型。'}]}}
 def test_route_only_has_start_end_nodes_no_video_and_no_empty_players(self):
  result=build(self.manifest,self.p/'out');out=self.p/'out';route=(out/'route.html').read_text()
  for text in ['开始','结束','东室','rehearsalPlayback','路线与镜头']:self.assertIn(text,route)
  self.assertNotIn('<iframe',route);self.assertNotIn('<video',route)
  for file in ['video.html','narrated.html']:self.assertIn('待生成',(out/file).read_text());self.assertNotIn('<video',(out/file).read_text())
  self.assertEqual(read(out/'rehearsal.json')['references']['routePage']['sha256'],sha(out/'route.html'))
  self.assertFalse(result['approvalGranted']);self.assertFalse(result['videoGenerated']);self.assertEqual(read(out/'route-review.pending.json')['status'],'pending')
 def test_preview_is_auxiliary_and_embedded_map_cannot_contain_stage_navigation(self):
  from tour_playback import preview_page
  from tour_pages import validate_presentation
  out=self.p/'out';out.mkdir();(out/'camera-preview.html').write_text(preview_page('待确认'))
  result=build(self.manifest,out,existing=True)
  self.assertNotIn('href="camera-preview.html"',(out/'route.html').read_text());self.assertIn('route-embed.html',(out/'camera-preview.html').read_text())
  self.assertEqual(validate_presentation(out)['status'],'pass')
  self.assertEqual(result['presentationContract'],'three-stage-presentation/2')
  self.assertIn('route-embed.html',result['artifacts']);self.assertIn('route-embed.js',result['artifacts'])
  (out/'route-embed.html').write_text((out/'route.html').read_text())
  with self.assertRaisesRegex(ValueError,'pure map'):validate_presentation(out)
 def test_generated_guard_rejects_full_route_inside_camera_frame(self):
  from tour_playback import preview_page
  from tour_pages import validate_presentation
  out=self.p/'out';build(self.manifest,out)
  (out/'camera-preview.html').write_text(preview_page('待确认').replace('src="route-embed.html"','src="route.html"'))
  with self.assertRaisesRegex(ValueError,'pure route map'):validate_presentation(out)
 def test_stage_navigation_stays_horizontal_and_empty_media_stays_empty(self):
  build(self.manifest,self.p/'out')
  for name in ('route.html','video.html','narrated.html'):
   text=(self.p/'out'/name).read_text();self.assertEqual(text.count('<nav class="steps">'),1)
   self.assertIn('.steps{flex-direction:row;',text)
  self.assertNotIn('preview-entry" href=',(self.p/'out/route.html').read_text())
 def test_sample_pages_label_historical_media_without_granting_approval(self):
  with self.probe():result=build(self.manifest,self.p/'sample',{**self.job(),'sample':True,'title':'流程样例 · 历史素材'})
  route=(self.p/'sample/route.html').read_text();self.assertIn('非当前方案成片',route);self.assertNotIn('样例预览',route)
  self.assertEqual(result['purpose'],'sample');self.assertFalse(result['approvalGranted'])
 def test_clean_chapter_chain_preserves_visit_times_and_adds_arrows(self):
  from tour_pages import chapter_nodes
  nodes=chapter_nodes([{'phase':'observe','name':'客厅 · 观看','startSeconds':2},{'phase':'observe','name':'客厅 → 阳台','startSeconds':4},{'phase':'observe','name':'阳台 · 观看','startSeconds':5},{'phase':'transit','name':'经过走廊','startSeconds':6}],8)
  self.assertEqual(nodes,[{'name':'开始','seconds':0},{'name':'客厅','seconds':2},{'name':'阳台','seconds':4},{'name':'结束','seconds':8}])
  with self.probe():build(self.manifest,self.p/'out',self.job())
  s=(self.p/'out/narrated.html').read_text();self.assertIn('class="chapters room-list"',s);self.assertNotIn('东室 · 观看</span>',s)
 def test_final_artifact_guard_rejects_presentation_regressions(self):
  from tour_pages import validate_presentation
  with self.probe():build(self.manifest,self.p/'out',self.job())
  p=self.p/'out/video.html';original=p.read_text()
  cases=[(original.replace('<nav class="steps">','<aside><nav class="steps">').replace('</nav>','</nav></aside>'),'outside content'),(original.replace('<div class="chapters room-list">','</div><div class="chapters room-list">'),'inside the route list'),(original.replace('class="route-reference"','class="other"'),'one route sidebar')]
  for changed,reason in cases:
   p.write_text(changed)
   with self.assertRaisesRegex(ValueError,reason):validate_presentation(self.p/'out')
  p.write_text(original)
  route=self.p/'out/route.html';route.write_text(route.read_text().replace('<main class="main">','<a href="camera-preview.html">三维预演</a><main class="main">'))
  with self.assertRaisesRegex(ValueError,'auxiliary'):validate_presentation(self.p/'out')
 def test_resource_urls_are_bound_to_packaged_modules(self):
  with self.probe():r=build(self.manifest,self.p/'out',self.job())
  out=self.p/'out';self.assertIn('tour-media.js?v='+sha(out/'tour-media.js')[:16],(out/'video.html').read_text())
  self.assertIn('route-panel.js?v='+sha(out/'route-panel.js')[:16],(out/'tour-media.js').read_text())
  self.assertEqual(r['presentationPolicy']['mediaAspectRatio'],'16:9');self.assertFalse(r['approvalGranted'])
 def test_storyboard_and_unflagged_teleports_cannot_be_presented_as_full_route(self):
  for name in ['cut','jump']:
   t=copy.deepcopy(self.t)
   if name=='cut':t['frames'][4]['cutBefore']=True
   else:t['frames'][4]['pointMm']=[2700,1500]
   (self.p/'tour.json').write_text(json.dumps(t))
   rehearsal(self.p/'tour.json',self.p/'config.json',self.p/'bundle.json',self.p/'plan.png',[0,0,3000,2000],self.p/name,5,self.p)
   with self.assertRaisesRegex(ValueError,'continuous|Discontinuous'):build(self.p/name/'rehearsal.json',self.p/(name+'-out'))
   self.assertFalse((self.p/(name+'-out')).exists())
 def test_new_case_bounds_and_fps_are_not_apartment_constants(self):
  build(self.manifest,self.p/'out');data=read(self.p/'out/route-data.json');self.assertEqual(data['bounds'],[-100,-200,3400,2400]);self.assertEqual(data['fps'],2);self.assertEqual(data['frames'][5]['p'],[900,800]);self.assertNotIn('7750',(self.p/'out/route.html').read_text())
 def test_concave_renamed_layout_keeps_own_bounds_and_timebase(self):
  b=copy.deepcopy(self.b);b['model']['rooms'][0]['poly']=[[0,0],[3000,0],[3000,1000],[2200,1000],[2200,2000],[0,2000]]
  (self.p/'bundle.json').write_text(json.dumps(b));self.t['fps']=3;self.t['seconds']=len(self.t['frames'])/3;(self.p/'tour.json').write_text(json.dumps(self.t))
  rehearsal(self.p/'tour.json',self.p/'config.json',self.p/'bundle.json',self.p/'plan.png',[-300,100,3600,2300],self.p/'concave',4,self.p)
  build(self.p/'concave/rehearsal.json',self.p/'out');d=read(self.p/'out/route-data.json');self.assertEqual(d['fps'],3);self.assertEqual(d['bounds'],[-300,100,3600,2300]);self.assertEqual(d['frames'][0]['p'],self.t['frames'][0]['pointMm'])
 def test_video_and_narration_enable_three_pages_and_use_same_route(self):
  with self.probe():r=build(self.manifest,self.p/'out',self.job())
  out=self.p/'out';self.assertEqual(r['stages']['video'],'approved_for_narration');self.assertEqual(r['stages']['narrated'],'ready_for_review')
  for file in ['video.html','narrated.html']:
   s=(out/file).read_text();self.assertIn('sync-map',s);self.assertIn('tour-media.js?v=',s);self.assertIn('roomListPanel',s);self.assertNotIn('id="routeDialog"',s);self.assertNotIn('<section class="chapter-strip"',s);self.assertLess(s.index('<aside class="route-reference"'),s.index('id="roomListPanel"'))
   self.assertEqual(s.count('<video '),1);self.assertNotIn('route-thumb',s[s.index('<main'):])
  self.assertEqual((out/'media/tour.mp4').read_bytes(),(self.p/'film.mp4').read_bytes());self.assertIn('voiceOn',(out/'narrated.html').read_text());self.assertIn('musicOn',(out/'narrated.html').read_text())
 def test_changed_video_hash_is_rejected_before_output(self):
  job={'video':{**self.video(),'sha256':'old'}}
  with self.assertRaisesRegex(ValueError,'Changed video'):build(self.manifest,self.p/'out',job)
  self.assertFalse((self.p/'out').exists())
 def test_same_duration_video_with_wrong_route_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'different tour'):build(self.manifest,self.p/'out',{'video':{**self.video(),'tourSha256':'another-layout'}})
  self.assertFalse((self.p/'out').exists())
 def test_partial_or_retimed_video_is_rejected(self):
  for change in [{'seconds':3},{'fps':3},{'frames':7}]:
   with patch('tour_pages.probe_video',return_value={**{'seconds':4,'fps':2,'frames':8},**change}):
    with self.assertRaisesRegex(ValueError,'timebase'):build(self.manifest,self.p/'out',{'video':self.video()})
  self.assertFalse((self.p/'out').exists())
 def test_voice_is_bound_to_exact_video_and_captions_cannot_overrun(self):
  for action in ['video','captions']:
   job=self.job()
   if action=='video':job['narration']['videoSha256']='old'
   else:job['narration']['captions'][0]['end']=9
   with self.probe(),self.assertRaises(ValueError):build(self.manifest,self.p/'out',job)
  self.assertFalse((self.p/'out').exists())
 def test_media_with_existing_audio_requires_separate_silent_source(self):
  with patch('tour_pages.probe_video',return_value={'seconds':4,'fps':2,'frames':8,'hasAudio':True}),self.assertRaisesRegex(ValueError,'silent video'):build(self.manifest,self.p/'out',self.job())
 def test_changed_plan_and_occupied_output_are_protected(self):
  build(self.manifest,self.p/'out')
  with self.assertRaisesRegex(ValueError,'empty'):build(self.manifest,self.p/'out')
  (self.p/'plan.png').write_bytes(b'changed')
  with self.assertRaisesRegex(ValueError,'plan'):build(self.manifest,self.p/'other')
  self.assertFalse((self.p/'other').exists())
 def test_html_text_is_escaped_and_package_is_relocatable(self):
  job=self.job();job['title']='<script>bad()</script>';job['narration']['captions'][0]['text']='</script><script>bad()</script>'
  with self.probe():r=build(self.manifest,self.p/'out',job)
  s=(self.p/'out/narrated.html').read_text();self.assertNotIn('<script>bad()',s);self.assertIn('\\u003c/script>',s);self.assertNotIn('file://',s)
  for name,row in r['artifacts'].items():self.assertEqual(sha(self.p/'out'/name),row['sha256'])
 def test_cli_without_media_uses_no_video_dependencies(self):
  r=subprocess.run([sys.executable,str(Path(__file__).with_name('h5.py')),'tour-pages','--rehearsal',str(self.manifest),'--out',str(self.p/'cli')],capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertTrue((self.p/'cli/route.html').is_file())
if __name__=='__main__':unittest.main()
