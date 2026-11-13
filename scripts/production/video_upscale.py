"""Optional bounded enlargement comparison; never diffusion, interpolation or automatic full-film work."""
import json,math,subprocess,time,uuid,urllib.request,urllib.parse,hashlib,shutil
from fractions import Fraction
from pathlib import Path
from tour_stage_gate import resolve,bound,sha
from remote_production import write

def validate(job,base):
 if job.get('schema')!='homeowner-upscale-comparison-job/1' or job.get('purpose')!='comparison':raise ValueError('Only explicitly authorized short comparisons are supported')
 source=resolve(job['video'],base);a,n=job.get('startFrame'),job.get('frameCount')
 if type(a)is not int or a<0 or type(n)is not int or n<2:raise ValueError('Invalid source frame interval')
 if not job.get('methods') or set(job['methods'])-{'lanczos','h3_latent'} or len(set(job['methods']))!=len(job['methods']):raise ValueError('Unsupported upscale method')
 if job.get('diffusionSampling') is not False or job.get('frameInterpolation') is not False:raise ValueError('This comparison forbids diffusion and interpolation')
 if 'h3_latent' in job['methods']:
  if not job.get('vae') or not job.get('upscalerModel'):raise ValueError('Explicit installed H3 VAE/upscaler names required')
 auth=json.loads(resolve(job['authorization'],base).read_text())
 settings={k:v for k,v in job.items() if k not in ('schema','authorization')}
 if auth.get('scope')!='video_upscale_comparison' or auth.get('status')!='approved' or auth.get('approvalSource')!='explicit_user_confirmation' or not auth.get('evidence','').strip() or auth.get('settings')!=settings:raise ValueError('Upscale settings lack exact user authorization')
 return source

def alignment(width,height,target):
 if any(type(v)is not int or v<16 for v in [width,height,*target]):raise ValueError('Invalid upscale dimensions')
 scale=Fraction(target[0],width)
 if Fraction(target[1],height)!=scale or not 1<scale<=4:raise ValueError('Enlargement must preserve aspect ratio')
 grain=32*scale.denominator//math.gcd(scale.numerator,32*scale.denominator)
 pw=math.ceil(width/grain)*grain;ph=math.ceil(height/grain)*grain
 left=((pw-width)//2//scale.denominator)*scale.denominator;top=((ph-height)//2//scale.denominator)*scale.denominator
 if (Fraction(left)*scale).denominator!=1 or (Fraction(top)*scale).denominator!=1:raise ValueError('Cannot retain an exact picture alignment')
 return {'input':[pw,ph],'pad':[left,top,pw-width-left,ph-height-top],'upscaled':[int(pw*scale),int(ph*scale)],'cropOrigin':[int(left*scale),int(top*scale)],'target':target,'originalContentCropped':False}

def temporal_alignment(count):
 # Installed MiniMax H3 video VAE: frames17k+5 <-> latents5k+2.
 if type(count)is not int or count<2:raise ValueError('Invalid temporal count')
 aligned=max(0,math.ceil((count-5)/17))*17+5
 return {'inputFrames':aligned,'repeatLastFrames':aligned-count,'keptFrames':count,'boundary':'17k+5'}

def graph(job,uploaded,align,prefix):
 def node(c,**i):return {'class_type':c,'inputs':i}
 g={'1':node('LoadVideo',file=uploaded),'2':node('GetVideoComponents',video=['1',0]),'3':node('VAELoader',vae_name=job['vae']),
 '4':node('VAEEncodeTiled',pixels=['2',0],vae=['3',0],tile_size=512,overlap=64,temporal_size=16,temporal_overlap=4),
 '5':node('MinimaxH3LatentUpscaler3D',latent=['4',0],model_name=job['upscalerModel'],mode='target dimensions',**{'mode.width':align['upscaled'][0],'mode.height':align['upscaled'][1]},align=32,enable_temporal_chunking=True,force_unload=True,device='cuda',precision='bf16'),
 '6':node('VAEDecodeTiled',samples=['5',0],vae=['3',0],tile_size=512,overlap=64,temporal_size=16,temporal_overlap=4),
 '7':node('ImageCrop',image=['6',0],width=job['target'][0],height=job['target'][1],x=align['cropOrigin'][0],y=align['cropOrigin'][1]),
 '8':node('ImageFromBatch',image=['7',0],batch_index=0,length=job['frameCount']),
 '9':node('SaveImage',images=['8',0],filename_prefix=prefix)}
 allowed={'LoadVideo','GetVideoComponents','VAELoader','VAEEncodeTiled','MinimaxH3LatentUpscaler3D','VAEDecodeTiled','ImageCrop','ImageFromBatch','SaveImage'}
 if {v['class_type'] for v in g.values()}!=allowed:raise ValueError('Unexpected processing nodes')
 return g

class Comfy:
 def __init__(self,url):
  if urllib.parse.urlparse(url).scheme not in ('http','https'):raise ValueError('Explicit existing ComfyUI URL required')
  self.url=url.rstrip('/');self.http=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 def request(self,path,data=None,content_type='application/json'):
  payload=json.dumps(data).encode() if isinstance(data,dict) else data
  with self.http.open(urllib.request.Request(self.url+path,data=payload,headers={'Content-Type':content_type}),timeout=120) as r:return json.load(r)
 def download(self,ref,path):
  query=urllib.parse.urlencode({k:ref[k] for k in ('filename','subfolder','type') if k in ref})
  with self.http.open(self.url+'/view?'+query,timeout=300) as r:Path(path).write_bytes(r.read())
 def upload(self,path):
  boundary=uuid.uuid4().hex;name=sha(path)+'.mp4'
  data=(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: video/mp4\r\n\r\n').encode()+Path(path).read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
  v=self.request('/upload/image',data,'multipart/form-data; boundary='+boundary);ref={'filename':v['name'],'subfolder':v.get('subfolder',''),'type':'input'}
  query=urllib.parse.urlencode(ref)
  with self.http.open(self.url+'/view?'+query,timeout=300) as r:
   if hashlib.sha256(r.read()).hexdigest()!=sha(path):raise ValueError('Uploaded video bytes differ')
  return '/'.join(x for x in [v.get('subfolder',''),v['name']] if x)
 def find(self,client):
  q=self.request('/queue')
  for row in q['queue_running']+q['queue_pending']:
   if len(row)>3 and row[3].get('client_id')==client:return row[1]
  for pid,r in self.request('/history?max_items=100').items():
   if len(r.get('prompt',[]))>3 and r['prompt'][3].get('client_id')==client:return pid

def execute(job,base,out,ffmpeg,ffprobe,comfy=None):
 from tour_pages import probe_video
 source=validate(job,base);probe=probe_video(source,ffprobe);fps=probe['fps'];count=job['frameCount'];start=job['startFrame']
 if count/fps>5 or count>=probe['frames'] or start+count>probe['frames']:raise ValueError('Use a sample up to5seconds, not the complete film')
 align=alignment(probe['width'],probe['height'],job['target']);out=Path(out)
 if out.exists():
  if not (out/'job.json').exists() or json.loads((out/'job.json').read_text())!=job:raise ValueError('Existing comparison has different inputs')
 else:out.mkdir(parents=True)
 write(out/'job.json',job)
 def cmd(args):subprocess.run([ffmpeg,'-nostdin','-n','-v','error',*map(str,args)],check=True)
 frames=out/'frames';frames.mkdir(exist_ok=True)
 if not list(frames.glob('frame-*.png')):cmd(['-ss',start/fps,'-i',source,'-frames:v',count,'-an','-vsync','0','-start_number','0',frames/'frame-%06d.png'])
 if len(list(frames.glob('frame-*.png')))!=count:raise ValueError('Incomplete source extraction')
 extraction=[{'name':p.name,'sha256':sha(p)} for p in sorted(frames.glob('frame-*.png'))];er=out/'source-frames.json'
 if er.exists() and json.loads(er.read_text())!=extraction:raise ValueError('Extracted source frames changed')
 write(er,extraction)
 def encode(name,images,filter_=None):
  target=out/(name+'.mp4');receipt=out/(name+'-encoding.json')
  if target.exists():
   if not receipt.exists() or json.loads(receipt.read_text())['video']!=bound(target):raise ValueError('Unbound existing comparison video')
   return target
  args=['-framerate',fps,'-i',images,'-frames:v',count]
  if filter_:args+=['-vf',filter_]
  temp=out/(name+'-'+uuid.uuid4().hex+'.mp4')
  cmd([*args,'-an','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',temp]);temp.replace(target);write(receipt,{'video':bound(target)});return target
 variants=[{'method':'original','video':bound(encode('A-original',frames/'frame-%06d.png')),'label':'原片'}]
 if 'lanczos' in job['methods']:variants.append({'method':'lanczos','video':bound(encode('B-lanczos',frames/'frame-%06d.png',f"scale={job['target'][0]}:{job['target'][1]}:flags=lanczos")),'label':'普通插值放大 · 不补真实细节'})
 if 'h3_latent' in job['methods']:
  if comfy!=job.get('comfyUrl'):raise ValueError('ComfyUI endpoint differs from authorized settings')
  u=Comfy(comfy);padded=out/'padded.mp4';l,t,r,b=align['pad'];temporal=temporal_alignment(count)
  if not padded.exists():cmd(['-framerate',fps,'-i',frames/'frame-%06d.png','-frames:v',temporal['inputFrames'],'-vf',f"tpad=stop_mode=clone:stop={temporal['repeatLastFrames']},pad={align['input'][0]}:{align['input'][1]}:{l}:{t},fillborders=left={l}:right={r}:top={t}:bottom={b}:mode=smear",'-an','-c:v','libx264rgb','-crf','0','-pix_fmt','rgb24',padded])
  pad_receipt=out/'padded-source.json'
  if pad_receipt.exists() and json.loads(pad_receipt.read_text())!=bound(padded):raise ValueError('Padded source changed')
  write(pad_receipt,bound(padded))
  intent=out/'intent.json';submission=out/'submission.json'
  if not intent.exists():
   uploaded=u.upload(padded);g=graph(job,uploaded,align,'Agent_API/upscale-'+sha(source)[:12]+'-'+str(start));info=u.request('/object_info')
   if any(v['class_type'] not in info for v in g.values()):raise ValueError('Required H3 node missing')
   write(out/'graph.json',g);write(intent,{'client_id':'pure-upscale-'+uuid.uuid4().hex,'graph':bound(out/'graph.json'),'paddedVideo':bound(padded)})
   i=json.loads(intent.read_text());response=u.request('/prompt',{'prompt':g,'client_id':i['client_id']});write(submission,response)
  else:
   i=json.loads(intent.read_text());resolve(i['graph'],out);resolve(i['paddedVideo'],out)
   if not submission.exists():
    pid=u.find(i['client_id'])
    if not pid:raise ValueError('Unknown submission outcome; inspect server before retry, never duplicate')
    write(submission,{'prompt_id':pid})
  pid=json.loads(submission.read_text())['prompt_id'];began=time.monotonic()
  while True:
   h=u.request('/history/'+pid)
   if pid in h:
    h=h[pid];write(out/'history.json',h)
    if h['status']['status_str']!='success':raise ValueError('H3 processing failed; inspect bound history')
    break
   if time.monotonic()-began>3600:raise TimeoutError('Still running; task not cancelled, resume same ID')
   time.sleep(3)
  refs=h['outputs']['9']['images']
  if len(refs)!=count:raise ValueError('H3 decoded frame count changed')
  c=out/'h3-frames';c.mkdir(exist_ok=True)
  for n,ref in enumerate(refs):u.download(ref,c/f'frame-{n:06d}.png')
  variants.append({'method':'h3_latent','video':bound(encode('C-h3-latent',c/'frame-%06d.png')),'label':'H3潜空间放大 · 无扩散重绘，画质待比较'})
 for row in variants:
  pr=probe_video(row['video']['path'],ffprobe)
  if pr['frames']!=count or abs(pr['fps']-fps)>1e-6 or abs(pr['seconds']-count/fps)>1e-6:raise ValueError('Enlargement changed frame/timebase')
  expected=[probe['width'],probe['height']] if row['method']=='original' else job['target']
  if [pr['width'],pr['height']]!=expected or pr['hasAudio']:raise ValueError('Enlargement changed expected dimensions/audio')
  row['probe']=pr
 result={'schema':'homeowner-upscale-comparison-result/1','source':bound(source),'sourceFrames':[start,start+count],'variants':variants,'video':variants[-1]['video'],'alignment':align,'temporalPadding':temporal_alignment(count) if 'h3_latent' in job['methods'] else None,'diffusionSampling':False,'frameInterpolation':False,'visualReview':'pending','fullFilmAuthorized':False,'qualityClaim':'Output dimensions do not establish recovered detail or native resolution.'}
 write(out/'upscale-result.json',result);return result

def page(result,base,out):
 import html
 from tour_pages import fill,theme
 p=Path(out)
 if p.exists():raise ValueError('Use fresh comparison page output')
 rows=result['variants'];sources=[resolve(r['video'],base) for r in rows];p.mkdir(parents=True);cards=[]
 for n,(row,f) in enumerate(zip(rows,sources)):
  dest=p/(str(n)+'.mp4');shutil.copy2(f,dest)
  cards.append(f'<section class="validation-card"><h2>{html.escape(row["label"])}</h2><p class="validation-note">{row["probe"]["width"]} × {row["probe"]["height"]} · {row["probe"]["fps"]:g}帧</p><video controls playsinline preload="metadata" src="{dest.name}"></video></section>')
 template=Path(__file__).resolve().parents[2]/'assets/h5/tour/blender-validation-template.html'
 (p/'index.html').write_text(fill(template.read_text(),{'STYLE':theme(),'COLUMNS':str(len(rows)),'NAV':'','HEADING':'视频放大对照','INTRO':'相同源帧、相同时间轴。请逐版播放，检查清晰度、家具边缘、颜色与闪烁。','EXTRA':'','CARDS':''.join(cards),'FOOTER':'分辨率达标不代表细节提升。当前仅为短样，未处理整片。'}))
 write(p/'comparison-source.json',{'result':result,'template':bound(template),'userAcceptance':'pending'})
