"""Sequential video-to-narration gate. Never creates user approval."""
import hashlib,json,math,re,shutil,subprocess
from pathlib import Path
CHECKS=('fullVideoViewed','compositionApproved','motionAndTransitionsApproved','readyForNarration')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
def bound(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def resolve(record,base):
 if not isinstance(record,dict) or not record.get('path') or not record.get('sha256'):raise ValueError('Missing bound review/input reference')
 p=Path(record['path']);p=p if p.is_absolute() else Path(base)/p
 if not p.is_file() or sha(p)!=record['sha256']:raise ValueError('Changed bound review/input')
 return p.resolve()
def pending(video,tour):
 return {'schema':'homeowner-video-approval/1','status':'pending','approvalSource':'explicit_user_confirmation','confirmedBy':'','evidence':'','video':bound(video),'tour':bound(tour),'checks':{k:False for k in CHECKS}}
def require_video(review,video,tour):
 p=Path(review).resolve();r=read(p)
 if r.get('schema')!='homeowner-video-approval/1' or r.get('status')!='approved':raise ValueError('Video review must be explicitly approved before narration')
 if r.get('approvalSource')!='explicit_user_confirmation' or not all(isinstance(r.get(k),str) and r[k].strip() for k in ('confirmedBy','evidence')):raise ValueError('Video approval needs explicit user confirmation evidence')
 if r.get('sample') or r.get('purpose')=='sample' or r.get('reviewCaptureOnly'):raise ValueError('Sample/capture authorization is not video acceptance')
 if any(r.get('checks',{}).get(k) is not True for k in CHECKS):raise ValueError('Video acceptance checks remain incomplete')
 for key,target in [('video',video),('tour',tour)]:
  source=resolve(r.get(key),p.parent)
  if sha(source)!=sha(target):raise ValueError('Video approval belongs to a different '+key)
 return {'schema':'homeowner-narration-authorization/1','videoReview':bound(p),'video':bound(video),'tour':bound(tour),'approvalGranted':False}
def require_job(job,base):
 if job.get('schema','homeowner-narration-job/1')!='homeowner-narration-job/1':raise ValueError('Unsupported narration job')
 if job.get('sample') is True:raise ValueError('Sample jobs cannot authorize narration production')
 video=resolve(job.get('video'),base);tour=resolve(job.get('tour'),base)
 review=resolve(job.get('videoReview'),base)
 receipt=require_video(review,video,tour)
 from tour_pages import probe_video
 probe=probe_video(video,job.get('ffprobe'));t=read(tour)
 if probe['hasAudio']:raise ValueError('Narration production requires a silent source video')
 if probe['frames']!=len(t['frames']) or abs(probe['fps']-t['fps'])>1e-5 or abs(probe['seconds']-t['seconds'])>1/t['fps']:raise ValueError('Video and approved tour timebase differ')
 return video,tour,receipt,probe

def prepare(job,base,out):
 # Call before synthesis, subtitle alignment or any media processing.
 video,tour,receipt,probe=require_job(job,base)
 out=Path(out)
 if out.exists():raise ValueError('Use a new narration preparation output')
 out.mkdir(parents=True)
 (out/'authorization.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 (out/'composition-job.json').write_text(json.dumps({**job,'video':bound(video),'tour':bound(tour),'videoReview':receipt['videoReview'],'voice':None,'music':None,'captions':[]},ensure_ascii=False,indent=2))
 return receipt

def compose(job,base,out,ffmpeg=None):
 video,tour,receipt,probe=require_job(job,base)
 voice=resolve(job.get('voice'),base);music=resolve(job['music'],base) if job.get('music') else None
 captions=job.get('captions',[]);end=0
 for c in captions:
  a,z=c.get('start'),c.get('end')
  if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (a,z)) or not 0<=a<z<=probe['seconds'] or a<end or not isinstance(c.get('text'),str):raise ValueError('Invalid aligned captions')
  end=z
 exe=ffmpeg or shutil.which('ffmpeg')
 if not exe:raise ValueError('Existing ffmpeg required; no installation performed')
 out=Path(out)
 if out.exists():raise ValueError('Use a new composition output')
 out.mkdir(parents=True)
 from tour_subtitles import phrase_cues
 def stamp(t):
  ms=round(t*1000);return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
 cues=phrase_cues(captions)
 (out/'captions.srt').write_text('\n\n'.join(f"{i+1}\n{stamp(c['start'])} --> {stamp(c['end'])}\n{c['text']}" for i,c in enumerate(cues)),encoding='utf-8')
 seconds=str(probe['seconds']);cmd=[exe,'-nostdin','-n','-i',str(video),'-i',str(voice)]
 if music:cmd+=['-i',str(music)]
 if cues:cmd+=['-i',str(out/'captions.srt')]
 if music:
  cmd+=['-filter_complex','[1:a]apad,asplit=2[v][sc];[2:a]apad[m];[m][sc]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=450[duck];[v][duck]amix=inputs=2:duration=longest:normalize=0[a]','-map','0:v:0','-map','[a]']
 else:cmd+=['-map','0:v:0','-map','1:a:0','-af','apad']
 if cues:cmd+=['-map',('3' if music else '2')+':s:0','-c:s','mov_text','-metadata:s:s:0','language=zho']
 cmd+=['-c:v','copy','-c:a','aac','-t',seconds,'-movflags','+faststart',str(out/'narrated.mp4')]
 # Recheck approval and all bound bytes immediately before processing.
 require_job(job,base);resolve(job['voice'],base)
 if music:resolve(job['music'],base)
 tool_version=subprocess.run([exe,'-version'],check=True,capture_output=True,text=True).stdout.splitlines()[0]
 subprocess.run(cmd,check=True,capture_output=True)
 # Refuse a successful receipt if any input changed during processing.
 require_job(job,base);resolve(job['voice'],base)
 if music:resolve(job['music'],base)
 # Selectable MP4 subtitles plus portable sidecar, never claimed as burned-in.
 from tour_pages import probe_video
 result=probe_video(out/'narrated.mp4',job.get('ffprobe'))
 if result['frames']!=probe['frames'] or abs(result['seconds']-probe['seconds'])>1/probe['fps']:raise ValueError('Composition changed approved video timing')
 receipt.update({'output':bound(out/'narrated.mp4'),'captions':bound(out/'captions.srt'),'status':'pending_narrated_review','videoFramesCopied':True,'captionsMode':'selectable_mp4_and_sidecar' if cues else 'none','videoReviewAccepted':True})
 # Preserve both the original transcript intervals and emitted phrase cues.
 (out/'captions-source.json').write_text(json.dumps(captions,ensure_ascii=False,indent=2),encoding='utf-8')
 (out/'subtitle-cues.json').write_text(json.dumps(cues,ensure_ascii=False,indent=2),encoding='utf-8')
 root=Path(__file__).resolve().parents[2]
 version=re.search(r'version:\s*"([^"\n]+)"',(root/'SKILL.md').read_text(encoding='utf-8')).group(1)
 source_job={**job,'video':bound(video),'tour':bound(tour),'videoReview':receipt['videoReview'],'voice':bound(voice),'music':bound(music) if music else None,'captions':captions}
 (out/'composition-job.json').write_text(json.dumps(source_job,ensure_ascii=False,indent=2),encoding='utf-8')
 receipt['reproduction']={'schema':'homeowner-composition-trace/1','skillVersion':version,'inputs':{'voice':bound(voice),'music':bound(music) if music else None,'originalCaptions':bound(out/'captions-source.json'),'job':bound(out/'composition-job.json')},'generatedSubtitleCues':bound(out/'subtitle-cues.json'),'ffmpeg':{'path':str(Path(exe).resolve()),'version':tool_version,'argv':cmd},'sourceProbe':probe,'outputProbe':result,'generators':{name:bound(Path(__file__).with_name(name)) for name in ('tour_stage_gate.py','tour_subtitles.py','tour_pages.py')},'reproducibility':'Same bound inputs, tool build and arguments; byte identity across hardware/tool builds is not guaranteed','audioPolicy':'Inputs already aligned/leveled; optional music ducked by voice; no TTS invoked'}
 (out/'composition-report.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
 return receipt
