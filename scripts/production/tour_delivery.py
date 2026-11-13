"""Reusable final-delivery inspection. Does not approve a video or edit any media."""
import array,json,math,subprocess,sys
from pathlib import Path
from tour_stage_gate import resolve,bound
from tour_pages import probe_video
from remote_production import write

def packet_hash(video,ffmpeg):
 return subprocess.check_output([ffmpeg,'-nostdin','-v','error','-i',str(video),'-map','0:v:0','-c:v','copy','-f','hash','-hash','sha256','-'],text=True).strip()
def audio_check(video,ffmpeg):
 data=subprocess.check_output([ffmpeg,'-nostdin','-v','error','-i',str(video),'-vn','-ar','48000','-ac','2','-f','f32le','pipe:1']);samples=array.array('f');samples.frombytes(data)
 if sys.byteorder!='little':samples.byteswap()
 if not samples or any(not math.isfinite(x) for x in samples):raise ValueError('Invalid/missing audio samples')
 peak=max(abs(x) for x in samples);clipped=sum(abs(x)>=1 for x in samples)
 return {'seconds':len(samples)/96000,'analysisChannels':2,'peakDbFS':20*math.log10(peak) if peak else None,'clippedSamples':clipped,'silence':peak==0}

def inspect(job,base,out,ffmpeg,ffprobe):
 if job.get('schema')!='homeowner-delivery-check-job/1':raise ValueError('Unsupported delivery job')
 video=resolve(job['video'],base);probe=probe_video(video,ffprobe);findings=[];report={'schema':'homeowner-delivery-check/1','video':bound(video),'probe':probe,'userAcceptance':'pending','approvalGranted':False}
 if job.get('sourceVideo'):
  source=resolve(job['sourceVideo'],base);sp=probe_video(source,ffprobe)
  if any(probe[k]!=sp[k] for k in ('width','height','frames','fps','seconds')):raise ValueError('Composition changed source picture/timebase')
  report['picturePacketsUnchanged']=packet_hash(video,ffmpeg)==packet_hash(source,ffmpeg)
  if not report['picturePacketsUnchanged']:raise ValueError('Narration reencoded/changed accepted video frames')
 if probe['hasAudio']:
  report['audio']=audio_check(video,ffmpeg)
  if report['audio']['clippedSamples'] or report['audio']['silence']:findings.append('audio_clipping_or_silence')
  if abs(report['audio']['seconds']-probe['seconds'])>1/probe['fps']:findings.append('audio_duration_mismatch')
 if job.get('compositionReport'):
  cp=resolve(job['compositionReport'],base);c=json.loads(cp.read_text())
  if resolve(c['output'],cp.parent)!=video or c.get('videoReviewAccepted') is not True:raise ValueError('Wrong/unapproved composition report')
  trace=c['reproduction'];report['musicGain']=trace['musicGain'];report['audioPolicy']=trace['audioPolicy']
  if 'sidechaincompress' in ' '.join(trace['ffmpeg']['argv']):raise ValueError('Speech-dependent music ducking forbidden')
  for v in trace['inputs'].values():
   if isinstance(v,dict) and 'sha256' in v:resolve(v,cp.parent)
 if job.get('playback'):
  pp=resolve(job['playback'],base);p=json.loads(pp.read_text())
  if p.get('schema')!='homeowner-playback-check/1' or resolve(p['video'],pp.parent)!=video:raise ValueError('Stale/wrong playback evidence')
  if p.get('status')!='passed' or p.get('errors') or p.get('droppedFrames',0)>0 or p.get('stalls') or not p.get('ended') or p.get('rate')!=1 or abs(p.get('seconds',0)-probe['seconds'])>1/probe['fps']:findings.append('incomplete_normal_speed_playback')
  report['playback']=p
 else:findings.append('normal_speed_playback_required')
 if job.get('visualReview'):
  from tour_media_quality import require_visual
  report['visualReview']=require_visual(job['visualReview'],video,base)
 else:findings.append('continuous_visual_review_required')
 if job.get('pageReport'):
  pr=resolve(job['pageReport'],base);page=json.loads(pr.read_text())
  if page.get('inputs',{}).get('video',{}).get('sha256') not in (bound(video)['sha256'],job.get('sourceVideo',{}).get('sha256')):raise ValueError('Page shows a different version')
  if page.get('presentationContract')!='four-stage-presentation/1':raise ValueError('Wrong presentation SOP')
  if job.get('compositionReport'):
   for kind in ('voice','music'):
    if page.get('inputs',{}).get(kind,{}).get('sha256')!=(trace['inputs'].get(kind) or {}).get('sha256'):raise ValueError('Page uses a different '+kind+' track')
   if page.get('presentationPolicy',{}).get('musicGain')!=trace['musicGain']:raise ValueError('Page music gain differs from composed video')
  for name,row in page.get('artifacts',{}).items():
   target=(pr.parent/name).resolve()
   if not target.is_relative_to(pr.parent.resolve()) or bound(target)['sha256']!=row['sha256']:raise ValueError('Page artifact changed')
  report['pageReport']=bound(pr)
 else:findings.append('same_version_page_report_required')
 report.update(findings=findings,status='ready_for_user_review' if not findings else 'needs_engineering_review')
 write(out,report);return report
