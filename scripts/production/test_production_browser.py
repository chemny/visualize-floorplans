"""Real synthetic media + freshly generated four-stage pages; no current case writes."""
import functools,http.server,json,subprocess,sys,threading,re
from pathlib import Path
import test_tour_pages as page_fixtures
from tour_stage_gate import bound,CHECKS,pending,compose
from tour_pages import build
from tour_delivery import inspect

def run(out,node,browser,playwright,ffmpeg,ffprobe):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=False)
 fixture=page_fixtures.TourPagesTests();fixture.setUp();p=fixture.p
 try:
  def media(args):subprocess.run([ffmpeg,'-nostdin','-y','-v','error',*map(str,args)],check=True)
  media(['-f','lavfi','-i','testsrc2=s=640x360:r=2:d=4','-an','-c:v','libx264','-pix_fmt','yuv420p',p/'film.mp4'])
  for name,freq,volume in [('voice',440,.2),('music',220,.05)]:media(['-f','lavfi','-i',f'sine=frequency={freq}:duration=4','-af',f'volume={volume}','-c:a','aac',p/(name+'.m4a')])
  approval=pending(p/'film.mp4',p/'tour.json');approval.update(status='approved',confirmedBy='synthetic-test',evidence='SYNTHETIC REGRESSION ONLY',checks={k:True for k in CHECKS})
  (p/'video-review.json').write_text(json.dumps(approval))
  job={'video':bound(p/'film.mp4'),'tour':bound(p/'tour.json'),'videoReview':bound(p/'video-review.json'),'voice':bound(p/'voice.m4a'),'music':bound(p/'music.m4a'),'musicGain':.6,'captions':[{'start':.1,'end':2.8,'text':'独立测试字幕'}]}
  result=compose(job,p,p/'composed',ffmpeg)
  pages=build(fixture.manifest,p/'pages',{'video':fixture.video(),'videoReview':job['videoReview'],'narration':{'videoSha256':job['video']['sha256'],'voice':job['voice'],'music':job['music'],'musicGain':.6,'captions':job['captions']}})
  class RangeHandler(http.server.SimpleHTTPRequestHandler):
   def do_GET(self):
    header=self.headers.get('Range');f=Path(self.translate_path(self.path))
    if not header or not f.is_file():return super().do_GET()
    m=re.fullmatch(r'bytes=(\d+)-(\d*)',header)
    if not m:return self.send_error(416)
    a=int(m[1]);z=min(int(m[2]) if m[2] else f.stat().st_size-1,f.stat().st_size-1)
    if a>z:return self.send_error(416)
    self.send_response(206);self.send_header('Content-Type',self.guess_type(str(f)));self.send_header('Accept-Ranges','bytes');self.send_header('Content-Range',f'bytes {a}-{z}/{f.stat().st_size}');self.send_header('Content-Length',str(z-a+1));self.end_headers()
    with f.open('rb') as stream:stream.seek(a);self.wfile.write(stream.read(z-a+1))
  handler=functools.partial(RangeHandler,directory=str(p));server=http.server.ThreadingHTTPServer(('127.0.0.1',0),handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();url=f'http://127.0.0.1:{server.server_port}'
  try:
   subprocess.run([node,str(Path(__file__).with_name('tour_delivery_browser.mjs')),'--url',url+'/composed/narrated.mp4','--video',result['output']['path'],'--out',str(out/'playback.json'),'--browser',browser,'--playwright-module',playwright,'--page-url',url+'/pages/narrated.html','--page-video',str(p/'film.mp4'),'--composition-job',str(p/'composed/composition-job.json')],check=True,timeout=90)
  finally:server.shutdown();server.server_close()
  # Synthetic scene visual record exercises bindings only; not user-case approval.
  visual={'schema':'homeowner-media-visual-review/1','status':'engineer_checked','video':result['output'],'method':'continuous_playback','reviewer':'synthetic-regression','notes':'SYNTHETIC REGRESSION ONLY; not visual acceptance of any house','checks':{k:True for k in ['clarity','edges','localFlicker','occlusion','lighting']}}
  (out/'visual.json').write_text(json.dumps(visual))
  delivery={'schema':'homeowner-delivery-check-job/1','video':result['output'],'sourceVideo':job['video'],'compositionReport':bound(p/'composed/composition-report.json'),'playback':bound(out/'playback.json'),'visualReview':bound(out/'visual.json'),'pageReport':bound(p/'pages/tour-pages.json')}
  checked=inspect(delivery,p,out/'delivery.json',ffmpeg,ffprobe)
  assert checked['status']=='ready_for_user_review' and checked['approvalGranted'] is False,checked
  # Same-length wrong-version evidence must fail.
  wrong=json.loads((out/'playback.json').read_text());wrong['video']=job['video'];(out/'stale-playback.json').write_text(json.dumps(wrong))
  try:inspect({**delivery,'playback':bound(out/'stale-playback.json')},p,out/'bad.json',ffmpeg,ffprobe)
  except ValueError:pass
  else:raise AssertionError('Stale playback was accepted')
  pagefile=p/'pages/narrated.html';pagefile.write_text(pagefile.read_text()+'<!-- synthetic tamper -->')
  try:inspect(delivery,p,out/'bad-page.json',ffmpeg,ffprobe)
  except ValueError:pass
  else:raise AssertionError('Changed page was accepted')
  (out/'result.json').write_text(json.dumps({'status':'passed','syntheticOnly':True,'pageControls':json.loads((out/'playback.json').read_text())['pageControls'],'delivery':checked['status'],'stalePlaybackRejected':True,'changedPageRejected':True,'approvalGranted':False},indent=2))
 finally:fixture.doCleanups()

if __name__=='__main__':run(*sys.argv[1:])
