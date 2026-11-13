"""Optional decorated-tour branch: local planning/checks, explicit remote rendering.

Native Codex image generation is performed by the agent, not simulated by this CLI.
No installation, implicit approval, narration, or publication is performed here.
"""
from pathlib import Path
import argparse,copy,hashlib,json,math,shutil,subprocess,time,urllib.request,uuid

SCHEMA='homeowner-decorated-tour/1'
def read(p):return json.loads(Path(p).read_text())
def write(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bound(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def checked(v):
 p=Path(v['path'])
 if not p.is_file() or sha(p)!=v['sha256']:raise ValueError('Missing or changed source: '+str(p))
 return p
def int_value(v):return isinstance(v,int) and not isinstance(v,bool)
def validate_plan(p):
 if p.get('schema')!=SCHEMA:raise ValueError('Unsupported decorated tour plan')
 for ref in p['sources'].values():checked(ref)
 t=read(checked(p['sources']['tour']));fps=t['fps'];n=len(t['frames'])
 if p['fps']!=fps or p['frames']!=n or abs(p['seconds']-n/fps)>1e-7:raise ValueError('Changed timebase')
 at=0;ids=set()
 for seg in p['segments']:
  a,z=seg['startFrame'],seg['endFrame']
  if not all(int_value(v) for v in [a,z]) or a!=at or not a<z<=n:raise ValueError('Gap, overlap, or invalid segment range')
  if seg['id'] in ids:raise ValueError('Duplicate segment id')
  ids.add(seg['id']);at=z
  k=seg['keyframes']
  if len(k)<2 or k[0]['sourceFrame']!=a or k[-1]['sourceFrame']!=min(z,n-1):raise ValueError('Missing segment endpoint guides')
  order=[x['sourceFrame'] for x in k]
  if order!=sorted(set(order)) or not all(a<=f<=min(z,n-1) for f in order):raise ValueError('Invalid guide order')
  if any(x['targetFrame']!=x['sourceFrame']-a for x in k):raise ValueError('Guide must bind exact local frame')
  for x in k:checked(x['source'])
 if at!=n:raise ValueError('Incomplete route')
 return t
def prepare(job,out):
 out=Path(out)
 if out.exists() and any(out.iterdir()):raise ValueError('Use a new empty output directory')
 if not str(job.get('authorizationEvidence','')).strip():raise ValueError('Explicit execution scope required')
 tour=Path(job['tour']).resolve();t=read(tour);fps=t['fps'];n=len(t['frames'])
 if abs(n/fps-t['seconds'])>1e-7:raise ValueError('Invalid source timeline')
 for k in ('maximumSegmentSeconds','keyframeSpacingSeconds'):
  if not isinstance(job.get(k),(int,float)) or not math.isfinite(job[k]) or job[k]<=0:raise ValueError('Explicit positive '+k+' required')
 cuts=job.get('cutFrames') or list(range(0,n,max(1,round(job['maximumSegmentSeconds']*fps))))+[n]
 if cuts[0]!=0 or cuts[-1]!=n or cuts!=sorted(set(cuts)) or not all(int_value(f) for f in cuts):raise ValueError('Invalid explicit segment boundaries')
 if any(z-a>job['maximumSegmentSeconds']*fps+1e-6 for a,z in zip(cuts,cuts[1:])):raise ValueError('Segment exceeds declared model budget')
 source_dir=Path(job['sourceFramesDir']);pattern=job.get('framePattern','frame-%06d.png')
 sources={'tour':bound(tour),'bundle':bound(job['bundle']),'config':bound(job['config'])}
 if job.get('sourceVideo'):sources['sourceVideo']=bound(job['sourceVideo'])
 if job.get('styleReference'):sources['styleReference']=bound(job['styleReference'])
 out.mkdir(parents=True);(out/'anchors').mkdir();(out/'images').mkdir();(out/'segments').mkdir()
 segments=[];extra=job.get('extraKeyframes',[]);spacing=max(1,round(job['keyframeSpacingSeconds']*fps));cache={}
 for i,(a,z) in enumerate(zip(cuts,cuts[1:])):
  frames=sorted(set([a,min(z,n-1)]+list(range(a+spacing,z,spacing))+[f for f in extra if a<f<z]))
  keys=[]
  for f in frames:
   if f not in cache:
    src=source_dir/(pattern%f)
    if not src.is_file():raise ValueError('Missing source frame '+str(f))
    dst=out/'anchors'/f'{f:06d}.png';shutil.copy2(src,dst);cache[f]=bound(dst)
   keys.append({'sourceFrame':f,'targetFrame':f-a,'source':cache[f],'imagePath':str(out/'images'/f'{f:06d}.png')})
  segments.append({'id':f's{i+1:02d}','startFrame':a,'endFrame':z,'keyframes':keys})
 p={'schema':SCHEMA,'sources':sources,'schemeSha256':t['schemeSha256'],'fps':fps,'frames':n,'seconds':n/fps,
    'authorizationEvidence':job['authorizationEvidence'],'render':job['render'],'segments':segments,
    'imageReviews':{},'status':'awaiting_native_images','controlPolicy':'optional_after_matched_test',
    'approvalGranted':False,'narrationAllowed':False}
 validate_plan(p);write(out/'decoration-plan.json',p);return p
def review_image(plan,frame,image,checks,evidence):
 p=read(plan);validate_plan(p)
 if any(checks.get(k) is not True for k in ('layoutPreserved','cameraPreserved','noInventedFixtures','styleConsistent')) or not evidence.strip():raise ValueError('Geometry and visual review evidence required')
 keys=[k for s in p['segments'] for k in s['keyframes'] if k['sourceFrame']==frame]
 if not keys:raise ValueError('Unknown source frame')
 dst=Path(keys[0]['imagePath'])
 if Path(image).resolve()!=dst.resolve():shutil.copy2(image,dst)
 p['imageReviews'][str(frame)]={'image':bound(dst),'source':keys[0]['source'],'checks':checks,'evidence':evidence,'reviewedBy':'agent','userAcceptance':'not_inferred'}
 write(plan,p)
def ready(p,seg):
 validate_plan(p)
 for k in seg['keyframes']:
  review=p['imageReviews'].get(str(k['sourceFrame']))
  if not review or any(review.get('checks',{}).get(x) is not True for x in ('layoutPreserved','cameraPreserved','noInventedFixtures','styleConsistent')):raise ValueError('Unreviewed image at frame '+str(k['sourceFrame']))
  if review['source']!=k['source'] or checked(review['image']).resolve()!=Path(k['imagePath']).resolve():raise ValueError('Image review belongs to a different frame')
 return True
def segment_sha(p,seg):
 return hashlib.sha256(json.dumps({'sources':p['sources'],'fps':p['fps'],'render':p['render'],'segment':seg,'images':[p['imageReviews'][str(k['sourceFrame'])] for k in seg['keyframes']]},sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def graph_sha(graph):return hashlib.sha256(json.dumps(graph,sort_keys=True).encode()).hexdigest()
def frozen_graph(p,seg,dest,u):
 """Resume the exact submitted graph; upload filenames are not image identities."""
 intent=read(dest/'intent.json');g=read(dest/'graph.json')
 if graph_sha(g)!=intent['graphSha256']:raise ValueError('Stored submitted graph changed')
 refs={str(k['sourceFrame']):g['21' if i==0 else str(39+i)]['inputs']['image'] for i,k in enumerate(seg['keyframes'])}
 if graph_sha(make_graph(p,seg,refs))!=graph_sha(g):raise ValueError('Submitted graph parameters or frame bindings changed')
 identity=segment_sha(p,seg)
 if intent.get('segmentSha256'):
  if intent['segmentSha256']!=identity:raise ValueError('Submitted segment source images changed')
 else:
  # Migrate earlier intent only after proving the actual uploaded bytes match.
  import urllib.parse
  proofs=[]
  for k in seg['keyframes']:
   name=refs[str(k['sourceFrame'])];query=urllib.parse.urlencode({'filename':Path(name).name,'subfolder':str(Path(name).parent) if '/' in name else '', 'type':'input'})
   with u.http.open(u.base+'/view?'+query,timeout=30) as response:actual=hashlib.sha256(response.read()).hexdigest()
   expected=p['imageReviews'][str(k['sourceFrame'])]['image']['sha256']
   if actual!=expected:raise ValueError('Remote original image bytes differ from reviewed input')
   proofs.append({'sourceFrame':k['sourceFrame'],'sha256':actual,'remoteName':name})
  intent.update(segmentSha256=identity,remoteImageProof=proofs);write(dest/'intent.json',intent)
 return g,intent
def make_graph(p,seg,uploaded):
 """Exact frame conditioning, no mandatory source-video input or ControlNet."""
 ready(p,seg);r=p['render'];length=seg['endFrame']-seg['startFrame'];native=max(124,5+17*math.ceil((length-5)/17))
 def node(kind,**inputs):return {'class_type':kind,'inputs':inputs}
 g={'1':node('UNETLoader',unet_name=r['unet'],weight_dtype='default'),
    '23':node('LoraLoaderModelOnly',model=['1',0],lora_name=r['lora'],strength_model=r['loraStrength']),
    '2':node('MiniMaxH3SigmaShift',model=['23',0],shift_video=r['shiftVideo'],shift_audio=r['shiftAudio']),
    '3':node('PathchSageAttentionKJ',model=['2',0],sage_attention='sageattn_qk_int8_pv_fp16_cuda',allow_compile=False),
    '4':node('CLIPLoader',clip_name=r['clip'],type='minimax',device='default'),
    '5':node('VAELoader',vae_name=r['vae']),
    '21':node('LoadImage',image=uploaded[str(seg['keyframes'][0]['sourceFrame'])]),
    '9':node('MiniMaxH3ImageToVideo',clip=['4',0],vae=['5',0],prompt=seg.get('promptOverride',r['prompt']),width=r['width'],height=r['height'],length=native,first_frame=['21',0]),
    '10':node('RandomNoise',noise_seed=r['seed']),
    '12':node('KSamplerSelect',sampler_name='res_multistep'),
    '13':node('BasicScheduler',model=['3',0],scheduler='simple',steps=r['steps'],denoise=1),
    '14':node('SamplerCustomAdvanced',noise=['10',0],guider=['11',0],sampler=['12',0],sigmas=['13',0],latent_image=['9',1]),
    '15':node('VAEDecode',samples=['14',0],vae=['5',0]),
    '16':node('CreateVideo',images=['15',0],fps=p['fps'],bit_depth=8,color_space='sRGB',codec='none'),
    '17':node('SaveVideo',video=['16',0],filename_prefix='Agent_API/decorated-tour/'+seg['id'],format='mp4',**{'format.codec':'h264'})}
 previous=['9',0]
 for i,k in enumerate(seg['keyframes'][1:]):
  load=str(40+i);guide=str(100+i);g[load]=node('LoadImage',image=uploaded[str(k['sourceFrame'])])
  g[guide]=node('MiniMaxH3AddGuide',positive=previous,latent=['9',1],vae=['5',0],image=[load,0],frame_idx=k['targetFrame']);previous=[guide,0]
 g['11']=node('BasicGuider',model=['3',0],conditioning=previous)
 return g
def remote_render(plan,remote,client_module,ffmpeg,only=None):
 """Explicit opt-in remote call. Persist intent before submission; never blind retry."""
 import sys
 sys.path.insert(0,str(Path(client_module).parent));from core import Upstream
 p=read(plan);validate_plan(p);root=Path(plan).parent;u=Upstream(remote)
 for seg in p['segments']:
  if only and seg['id'] not in only:continue
  # Input receipts are per segment; later case-local repairs must not stale passed segments.
  p=read(plan);seg=next(s for s in p['segments'] if s['id']==seg['id'])
  if seg['id'] in p.get('frozenSegments',{}):assembly_receipt(p,seg,root);continue
  ready(p,seg);dest=root/'segments'/seg['id'];dest.mkdir(exist_ok=True)
  if (dest/'receipt.json').exists():
   receipt=read(dest/'receipt.json')
   if receipt.get('segmentSha256')!=segment_sha(p,seg):raise ValueError('Completed segment belongs to changed plan; use a fresh revision')
   checked(receipt['video']);continue
  q=u.request('/queue')
  if q['queue_running'] or q['queue_pending']:
   print('Remote queue occupied; enqueue only this task, never interrupt other jobs',flush=True)
  submit=dest/'submission.json';intent=dest/'intent.json'
  if intent.exists():graph,prior_intent=frozen_graph(p,seg,dest,u)
  else:
   upload_file=dest/'uploads.json';uploaded=read(upload_file) if upload_file.exists() else {}
   for k in seg['keyframes']:
    image=checked(p['imageReviews'][str(k['sourceFrame'])]['image']);key=sha(image)
    if key not in uploaded:uploaded[key]=u.upload(image);write(upload_file,uploaded)
   refs={str(k['sourceFrame']):uploaded[sha(k['imagePath'])] for k in seg['keyframes']}
   graph=make_graph(p,seg,refs)
  graph_hash=graph_sha(graph)
  if submit.exists():
   j=read(submit)
   if j['graphSha256']!=graph_hash:raise ValueError('Submitted graph changed; use fresh revision')
  else:
   client='decorated-'+segment_sha(p,seg)[:12]+'-'+seg['id']
   if intent.exists():
    pid=u.find_task(prior_intent['client_id'])
    if not pid:raise ValueError('Unknown prior submission outcome; inspect remote history before retry')
    j={'prompt_id':pid,'graphSha256':graph_hash}
   else:
    info=u.request('/object_info')
    for n in graph.values():
     if n['class_type'] not in info:raise ValueError('Required remote node unavailable: '+n['class_type'])
    write(dest/'graph.json',graph);write(intent,{'client_id':client,'graphSha256':graph_hash,'planSha256':sha(plan),'segmentSha256':segment_sha(p,seg)})
    j={**u.request('/prompt',{'prompt':graph,'client_id':client},timeout=60),'graphSha256':graph_hash}
   write(submit,j)
  pid=j['prompt_id'];print(seg['id'],'submitted',pid,flush=True)
  while True:
   h=u.request('/history/'+pid)
   if pid in h:
    h=h[pid];write(dest/'history.json',h)
    if h['status']['status_str']!='success':raise ValueError('Remote render failed; inspect '+str(dest/'history.json'))
    refs=[v for vs in h['outputs']['17'].values() if isinstance(vs,list) for v in vs if isinstance(v,dict) and v.get('type')=='output' and 'filename'in v]
    if len(refs)!=1:raise ValueError('Unexpected remote outputs')
    raw=dest/'raw.mp4';u.download(refs[0],raw);video=dest/'silent.mp4'
    subprocess.run([ffmpeg,'-v','error','-y','-i',str(raw),'-frames:v',str(seg['endFrame']-seg['startFrame']),'-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
    write(dest/'receipt.json',{'planSha256':sha(plan),'segmentSha256':segment_sha(p,seg),'segment':seg['id'],'startFrame':seg['startFrame'],'endFrame':seg['endFrame'],'video':bound(video),'graphSha256':graph_hash,'status':'pending_visual_review','approvalGranted':False})
    print(seg['id'],'complete',flush=True);break
   time.sleep(5)
def assembly_receipt(p,seg,root):
 """Frozen clips retain their original guide identity, not a fabricated new render."""
 frozen=p.get('frozenSegments',{}).get(seg['id'])
 if frozen:
  original=read(checked(frozen['plan']));validate_plan(original)
  if original['sources']!=p['sources'] or any(original[k]!=p[k] for k in ('fps','frames','seconds','schemeSha256','render')):raise ValueError('Frozen clip belongs to changed source or render profile')
  prior=next((s for s in original['segments'] if s['id']==frozen['segmentId']),None)
  if prior is None or prior!=seg:raise ValueError('Frozen clip timing or segment changed')
  ready(original,prior);receipt=read(checked(frozen['receipt']))
  if receipt.get('segment')!=prior['id'] or receipt.get('segmentSha256')!=segment_sha(original,prior):raise ValueError('Frozen clip receipt has wrong origin identity')
 else:
  ready(p,seg);receipt=read(root/'segments'/seg['id']/'receipt.json')
  if receipt.get('visualReview',{}).get('status')=='failed':raise ValueError('Known failed visual segment must be repaired before assembly: '+seg['id'])
  if receipt.get('segmentSha256')!=segment_sha(p,seg):raise ValueError('Stale segment receipt')
 if receipt.get('visualReview',{}).get('status')=='failed':raise ValueError('Known failed visual segment must be repaired before assembly: '+seg['id'])
 if receipt['startFrame']!=seg['startFrame'] or receipt['endFrame']!=seg['endFrame']:raise ValueError('Stale segment receipt')
 checked(receipt['video']);return receipt

def assemble(plan,out,ffmpeg,ffprobe):
 from tour_pages import probe_video
 p=read(plan);validate_plan(p);root=Path(plan).parent;paths=[]
 for seg in p['segments']:
  receipt=assembly_receipt(p,seg,root)
  v=checked(receipt['video']);probe=probe_video(v,ffprobe)
  if probe['frames']!=seg['endFrame']-seg['startFrame'] or probe['fps']!=p['fps'] or probe['hasAudio']:raise ValueError('Wrong segment timebase/audio')
  if [probe['width'],probe['height']]!=[p['render']['width'],p['render']['height']]:raise ValueError('Segment resolution mismatch')
  paths.append(v)
 out=Path(out)
 if out.exists():raise ValueError('Use a new assembled output')
 out.mkdir();lst=out/'segments.txt'
 lst.write_text(''.join("file '"+str(v).replace("'","'\\''")+"'\n" for v in paths))
 final=out/'decorated-review.mp4';subprocess.run([ffmpeg,'-v','error','-f','concat','-safe','0','-i',str(lst),'-an','-c:v','copy','-movflags','+faststart',str(final)],check=True)
 probe=probe_video(final,ffprobe)
 if probe['frames']!=p['frames'] or probe['fps']!=p['fps'] or abs(probe['seconds']-p['seconds'])>1/p['fps']:raise ValueError('Final assembly timebase mismatch')
 report={'schema':'homeowner-decoration-result/1','plan':bound(plan),'tourSha256':p['sources']['tour']['sha256'],'video':bound(final),'probe':probe,'frozenSegments':p.get('frozenSegments',{}),'status':'pending_video_review','approvalGranted':False,'narrationAllowed':False}
 write(out/'decoration-result.json',report)
 from tour_stage_gate import pending
 write(out/'video-review.pending.json',pending(final,checked(p['sources']['tour'])))
 return report
def main():
 ap=argparse.ArgumentParser();sub=ap.add_subparsers(dest='command',required=True)
 p=sub.add_parser('prepare');p.add_argument('--job',required=True);p.add_argument('--out',required=True)
 p=sub.add_parser('check');p.add_argument('--plan',required=True)
 p=sub.add_parser('render');p.add_argument('--plan',required=True);p.add_argument('--remote',required=True);p.add_argument('--client-module',required=True);p.add_argument('--ffmpeg',required=True);p.add_argument('--segment',action='append')
 p=sub.add_parser('assemble');p.add_argument('--plan',required=True);p.add_argument('--out',required=True);p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True)
 a=ap.parse_args()
 if a.command=='prepare':prepare(read(a.job),a.out)
 elif a.command=='check':
  p=read(a.plan);validate_plan(p)
  for s in p['segments']:
   if s['id'] in p.get('frozenSegments',{}):assembly_receipt(p,s,Path(a.plan).parent)
   else:ready(p,s)
 elif a.command=='render':remote_render(a.plan,a.remote,a.client_module,a.ffmpeg,a.segment)
 else:assemble(a.plan,a.out,a.ffmpeg,a.ffprobe)
if __name__=='__main__':main()
