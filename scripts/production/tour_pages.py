"""Portable four-stage tour presentation. Never captures, encodes or grants approval."""
import base64,copy,hashlib,html,json,math,re,shutil,subprocess
from pathlib import Path
from tour_audio import music_gain
ASSETS=Path(__file__).resolve().parents[2]/'assets/h5/tour'
SCHEMA='homeowner-tour-pages/1'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def safe(value):return json.dumps(value,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
def fill(template,values):return re.sub(r'__([A-Z_]+)__',lambda m:values[m[1]],template)
def theme():return (ASSETS/'stage-theme.css').read_text()
def navigation(active=1,video=False,narrated=False,standalone=False):
 rows=[]
 for i,name,file,ready in [(1,'参观路线','route.html',True),(2,'镜头预演','preview.html',True),(3,'视频审阅','video.html',video),(4,'讲解成片','narrated.html',narrated)]:
  label=f'{i:02d}　{name}'+(' · 待生成' if not ready else '')
  attrs=f'class="{"active" if i==active else ""}"'
  rows.append(f'<span {attrs}>{label}</span>' if standalone else f'<a {attrs} href="{file}">{label}</a>')
 return '<nav class="steps">'+''.join(rows)+'</nav>'
def chapter_nodes(chapters,end):
 nodes=[{'name':'开始','seconds':0}]
 for ch in chapters:
  if ch['phase']!='observe':continue
  name=re.sub(r'\s*[·・]\s*观看$', '',ch['name']).strip()
  # Historical transition-labelled observations resolve to their destination.
  name=name.rsplit('→',1)[-1].strip()
  if nodes[-1]['name']==name:continue
  nodes.append({'name':name,'seconds':ch['startSeconds']})
 return nodes+[{'name':'结束','seconds':end}]

def plan_nodes(records,frames,fps):
 """Display-only milestones tied to existing frames; never create camera stops."""
 if not isinstance(records,list) or not 2<=len(records)<=64:raise ValueError('Provide 2..64 route milestones')
 nodes=[];previous=-1
 for row in records:
  if not isinstance(row,dict):raise ValueError('Route milestone must be an object')
  name=row.get('name');frame=row.get('frameIndex')
  if not isinstance(name,str) or not name.strip() or len(name)>80:raise ValueError('Route milestone needs a short name')
  if isinstance(frame,bool) or not isinstance(frame,int) or not previous<frame<len(frames):raise ValueError('Route milestone frames must increase within the exact tour')
  nodes.append({'name':name.strip(),'seconds':frame/fps,'frameIndex':frame});previous=frame
 if records[0]['frameIndex']!=0 or records[-1]['frameIndex']!=len(frames)-1:raise ValueError('Route milestones must include the actual entrance and exit frames')
 return nodes

def ref(manifest,key,base):
 record=manifest['references'][key];p=Path(record['path']);p=p if p.is_absolute() else base/p
 if not p.is_file() or sha(p)!=record['sha256']:raise ValueError('Changed rehearsal input: '+key)
 return p.resolve()
def probe_video(path,ffprobe=None):
 exe=ffprobe or shutil.which('ffprobe')
 if not exe:raise ValueError('Existing ffprobe is required to bind video; no install performed')
 r=subprocess.run([exe,'-v','error','-count_frames','-show_entries','stream=codec_type,width,height,avg_frame_rate,nb_read_frames,duration:format=duration','-of','json',str(path)],check=True,capture_output=True,text=True)
 p=json.loads(r.stdout);s=next(s for s in p['streams'] if s.get('codec_type')=='video');a,b=map(float,s['avg_frame_rate'].split('/'))
 return {'seconds':float(s.get('duration',p['format']['duration'])),'fps':a/b,'frames':int(s['nb_read_frames']),'width':s['width'],'height':s['height'],'hasAudio':any(s.get('codec_type')=='audio' for s in p['streams'])}
def check_media(record,base,label):
 if not isinstance(record,dict) or not record.get('sha256'):raise ValueError(label+' requires path and sha256')
 p=Path(record['path']);p=p if p.is_absolute() else base/p
 if not p.is_file() or sha(p)!=record['sha256']:raise ValueError('Changed '+label)
 return p.resolve()
def map_svg(bounds,label="与视频同步的户型路线"):
 x,y,w,h=bounds
 return f'''<svg class="sync-map" role="img" aria-label="{html.escape(label,quote=True)}" viewBox="{x} {y} {w} {h}" preserveAspectRatio="xMidYMid meet"><image x="{x}" y="{y}" width="{w}" height="{h}" href="route-plan.png"/><g pointer-events="none"><path data-line="full" fill="none" stroke="white" stroke-width="100"/><path data-line="full" fill="none" stroke="#aebbc5" stroke-width="55" stroke-dasharray="130 95" opacity=".8"/><path data-line="done" fill="none" stroke="#94623e" stroke-width="70" stroke-linejoin="round" stroke-linecap="round"/><path data-line="cone" fill="#bc8650" fill-opacity=".23" stroke="#ad7b44" stroke-width="20"/><path data-line="axis" fill="none" stroke="#9b663e" stroke-width="25" stroke-dasharray="90 65"/><circle data-mark="start" r="105" fill="white" stroke="#998366" stroke-width="35"/><g data-mark="camera"><circle r="135" fill="#94623e" stroke="white" stroke-width="40"/><path d="M170,0 L40,-65 L40,65 Z" fill="#734c2b"/></g></g></svg>'''
def build(rehearsal_path,out,job=None,job_base=None,ffprobe=None,existing=False):
 job=job or {};
 from tour_render import engine, ENGINES
 render_engine=engine(job)
 if job.get('schema','homeowner-tour-pages-job/1')!='homeowner-tour-pages-job/1':raise ValueError('Unsupported presentation job')
 base=Path(job_base or '.').resolve();mp=Path(rehearsal_path).resolve();m=read(mp)
 if m.get('schema')!='homeowner-route-rehearsal/1':raise ValueError('Expected a generated rehearsal manifest')
 paths={k:ref(m,k,mp.parent) for k in ('tour','config','plan','animation','timing','bundle')}
 tour=read(paths['tour']);config=read(paths['config']);timing=read(paths['timing'])
 if m['schemeSha256']!=tour['schemeSha256']:raise ValueError('Scheme mismatch')
 frames=tour['frames'];fps=tour['fps'];seconds=tour['seconds'];bounds=m['planBounds']
 if not frames or not math.isfinite(fps) or fps<=0 or abs(seconds-len(frames)/fps)>1e-5:raise ValueError('Invalid final-frame timebase')
 if len(bounds)!=4 or not all(math.isfinite(v) for v in bounds) or min(bounds[2:])<=0:raise ValueError('Invalid explicit plan bounds')
 # A primary route page must contain actual continuous movement, never an editorial substitute.
 if any(f.get('cutBefore') for f in frames):raise ValueError('Route page requires continuous movement; editorial shots need a separate storyboard preview')
 max_speed=config.get('motionReviewLimits',{}).get('maximumSpeedMps',1.2)
 if any(math.dist(a['pointMm'],z['pointMm'])>max_speed*1000/fps+.1 for a,z in zip(frames,frames[1:])):raise ValueError('Discontinuous or teleporting route; rebuild physical room connections before presentation')

 if not paths['plan'].read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Expected bound plan PNG')
 from plan_route import Planner
 planner=Planner(read(paths['bundle']),{});walls=planner.walls+planner.leaves
 chapters=timing['chapters'];nodes=chapter_nodes(chapters,(len(frames)-1)/fps)
 plan_only=job.get('reviewScope')=='plan_only'
 if job.get('reviewScope') not in (None,'plan_only'):raise ValueError('Unsupported presentation review scope')
 if 'routeNodes' in job:nodes=plan_nodes(job['routeNodes'],frames,fps)
 if plan_only and any(job.get(key) for key in ('preview','video','narration')):raise ValueError('Plan-only review must not present camera or media stages')
 compressed={'fps':fps,'seconds':seconds,'bounds':bounds,'frames':[{'p':f['pointMm'],'yaw':f['yawRadians'],'fov':f.get('horizontalFovDegrees',76),'cutBefore':bool(f.get('cutBefore',False))} for f in frames],'walls':walls,'chapters':chapters,'tourSha256':sha(paths['tour'])}
 if 'routeNodes' in job:compressed['routeNodes']=nodes
 video_record=job.get('video');video_path=None;probe=None
 if video_record:
  if video_record.get('kind') in ('h5','blender') and video_record['kind']!=render_engine:raise ValueError('Video kind differs from selected rendering engine')
  video_path=check_media(video_record,base,'video')
  if video_record.get('tourSha256')!=sha(paths['tour']):raise ValueError('Video belongs to a different tour')
  probe=probe_video(video_path,ffprobe)
  if abs(probe['fps']-fps)>1e-5 or probe['frames']!=len(frames) or abs(probe['seconds']-seconds)>1/fps:raise ValueError('Video timebase differs from full route; partial/retimed videos need their own rehearsal')
 if video_record and video_record.get('kind')=='decorated':
  decoration=read(check_media(job.get('decorationResult'),base,'decoration result'))
  if decoration.get('schema')!='homeowner-decoration-result/1' or decoration.get('tourSha256')!=sha(paths['tour']) or decoration.get('video',{}).get('sha256')!=sha(video_path):raise ValueError('Decorated video must match exact assembly result and route')
 decoration_plan=None
 if job.get('decorationPlan'):
  from tour_decorated import validate_plan
  decoration_plan=read(check_media(job['decorationPlan'],base,'decoration plan'));validate_plan(decoration_plan)
  if decoration_plan['sources']['tour']['sha256']!=sha(paths['tour']):raise ValueError('Decoration images belong to another route')
 narration=job.get('narration');audio={};captions=[];gain=music_gain((narration or {}).get('musicGain',1))
 if narration:
  if not video_path:raise ValueError('Narration page needs its bound video first')
  if probe.get('hasAudio'):raise ValueError('External narration requires a silent video to avoid duplicate soundtracks')
  if narration.get('videoSha256')!=sha(video_path):raise ValueError('Narration belongs to a different video')
  if job.get('sample') is not True:
   from tour_stage_gate import require_video
   require_video(check_media(job.get('videoReview'),base,'video review'),video_path,paths['tour'])
  audio['voice']=check_media(narration.get('voice'),base,'voice')
  if narration.get('music'):audio['music']=check_media(narration['music'],base,'music')
  end=0
  for c in narration.get('captions',[]):
   a,z=c.get('start'),c.get('end')
   if not all(isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x) for x in (a,z)) or not 0<=a<z<=seconds+1e-6 or a<end or not isinstance(c.get('text'),str):raise ValueError('Invalid aligned captions')
   captions.append({'start':a,'end':z,'text':c['text']});end=z
 preview=job.get('preview')
 preview_runtime=Path(preview['runtime']).resolve() if preview else (Path(out)/'runtime' if (Path(out)/'runtime/renderer.html').is_file() else None)
 if preview_runtime:
  if preview and preview.get('tourSha256')!=sha(paths['tour']):raise ValueError('Preview belongs to a different tour')
  scene=read(preview_runtime/'scene.json')
  if scene.get('schemeSha256')!=tour['schemeSha256'] or sha(preview_runtime/'geometry.bin')!=m['geometrySha256']:raise ValueError('Preview scene or geometry differs from bound rehearsal')
  # Existing pipeline runtime is already copied. New jobs bind the actual scene as well.
  baseline=read(ref(m,'scene',mp.parent));current=copy.deepcopy(scene)
  for v in (baseline,current):v.get('renderSettings',{}).pop('size',None)
  if baseline!=current:raise ValueError('Preview scene changed; regenerate rehearsal binding')
 out=Path(out).resolve()
 if out.exists() and not existing and any(out.iterdir()):raise ValueError('Use a new empty presentation output')
 targets=['route.html','preview.html','video.html','narrated.html','tour-pages.json','tour-media.js','tour-map.js','route-data.json','route-plan.png','route-embed.html','route-embed.js','route-panel.js']
 if any((out/k).exists() for k in targets):raise ValueError('Presentation targets already exist; use a fresh revision')
 # All source/media validation occurs before writing files. No source case is modified.
 out.mkdir(parents=True,exist_ok=True);media=out/'media';media.mkdir(exist_ok=True)
 video_url=''
 if video_path:
  target=media/('tour'+video_path.suffix.lower());shutil.copy2(video_path,target)
  if sha(target)!=video_record['sha256']:raise ValueError('Video changed during packaging')
  video_url='media/'+target.name+'?v='+video_record['sha256'][:16]
 urls={}
 for kind,path in audio.items():
  target=media/(kind+path.suffix.lower());shutil.copy2(path,target)
  if sha(target)!=narration[kind]['sha256']:raise ValueError('Audio changed during packaging')
  urls[kind]='media/'+target.name
 gallery=''
 if decoration_plan:
  tiles=[]
  for frame,row in sorted(decoration_plan['imageReviews'].items(),key=lambda x:int(x[0])):
   source=check_media(row['image'],base,'decoration image');target=media/('keyframe-'+frame+source.suffix.lower());shutil.copy2(source,target)
   tiles.append(f'<a href="media/{target.name}"><img loading="lazy" src="media/{target.name}" alt="{int(frame)/fps:.2f}秒装修关键帧"><span>{int(frame)/fps:.2f}秒</span></a>')
  if tiles:gallery='<details class="render-keyframes"><summary>装修关键帧</summary><div class="keyframe-grid">'+''.join(tiles)+'</div></details>'
 shutil.copy2(paths['plan'],out/'route-plan.png')
 for file in ('tour-map.js','tour-media.js','route-embed.js','route-panel.js'):shutil.copy2(ASSETS/file,out/file)
 for module in ('tour-media.js','route-embed.js'):
  path=out/module;text=path.read_text()
  for dependency in ('tour-map.js','route-panel.js'):
   text=text.replace("'./"+dependency+"'","'./"+dependency+"?v="+sha(out/dependency)[:16]+"'")
  path.write_text(text)
 (out/'route-data.json').write_text(safe(compressed),encoding='utf-8')
 # Always render current shared template, including when upgrading a historical rehearsal.
 x,y,w,h=bounds;points=[f['pointMm'] for f in frames];line=' '.join(('M' if i==0 or frames[i].get('cutBefore') else 'L')+f'{a},{b}' for i,(a,b) in enumerate(points))
 image=base64.b64encode(paths['plan'].read_bytes()).decode()
 svg=f'<svg id="plan" xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}"><image x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/png;base64,{image}"/><g pointer-events="none"><path d="{line}" fill="none" stroke="white" stroke-width="42"/><path d="{line}" fill="none" stroke="#69849b" stroke-width="26" opacity=".7"/><path id="cone" fill="#bc8650" fill-opacity=".23"/><path id="axis" fill="none" stroke="#9b663e" stroke-width="20" stroke-dasharray="90 65"/><g id="travel"><path d="M150,0 L-70,-85 L-70,85 Z" fill="#69849b"/></g><g id="camera"><circle r="90" fill="#94623e" stroke="white" stroke-width="25"/><path d="M130,0 L-20,-45 L-20,45 Z" fill="white"/></g></g></svg>'
 cards=''.join(f'<button class="chapter" data-time="{n["seconds"]}"><span>{i+1:02}　{html.escape(n["name"])}</span><small>{n["seconds"]:.1f}s</small></button>' for i,n in enumerate(nodes))
 values={'STYLE':theme(),'NAV':navigation(1,bool(video_path),bool(narration)),'INTRO':('分镜路线：房间间切换机位，断开的线段不代表连续行走。' if any(f.get('cutBefore') for f in frames) else '在已确认路线上核对朝向与节奏。'),'BADGE':('镜头待确认' if m.get('spatialGate')=='approved' else '路线未确认') if m.get('status')=='pending_user_review' else '待调整','PLAN':svg,'CARDS':cards,'END':str((len(frames)-1)/fps),'STEP':str(1/fps),'DURATION':f'全程约 {seconds:.1f} 秒','TOUR':safe(tour),'WALLS':safe(walls),'VISITS':safe(nodes),'CHAPTERS':safe(chapters)}
 if plan_only:
  values.update(INTRO='先看参观顺序和行走路径；时间与朝向为草案，镜头后续细化。',BADGE='平面路线待确认',DURATION=f'草案约 {seconds:.1f} 秒')
 if job.get('sample') is True:
  values['INTRO']='流程样例 · 使用历史素材演示页面，非当前方案成片。'
  values['BADGE']='样例预览'
 values['ACTIONS']='' if job.get('sample') is True else '<span class="pill">'+values['BADGE']+'</span>'
 original=fill((ASSETS/'rehearsal-template.html').read_text(),values)
 embedded=fill((ASSETS/'route-embed-template.html').read_text(),{'MAP':map_svg(bounds,'与三维预演同步的户型路线')})
 (out/'route-embed.html').write_text(embedded,encoding='utf-8')
 (out/'route.html').write_text(original,encoding='utf-8')
 (out/'index.html').write_text(original,encoding='utf-8')
 if preview_runtime:
  from tour_playback import prepare_renderer
  dest=out/'runtime';dest.mkdir(exist_ok=True)
  for name in ('scene.json','geometry.bin','renderer.html','three.module.js','three.core.js','THREE-LICENSE.txt'):
   src=preview_runtime/name
   if src.resolve()!=(dest/name).resolve():shutil.copy2(src,dest/name)
  renderer=dest/'renderer.html';renderer.write_text(prepare_renderer(renderer.read_text()))
  shutil.copy2(paths['tour'],out/'replay.json')
  shutil.copy2(ASSETS/'rehearsal-player.js',out/'rehearsal-player.js')
  preview_body=(ASSETS/'preview-stage-template.html').read_text()
  preview_scripts='<script type="module">import{initPreview}from "./rehearsal-player.js?v='+sha(out/'rehearsal-player.js')[:16]+'";initPreview();</script>'
 else:
  preview_body='<section class="stage-empty"><h2>镜头预演待准备</h2><p>路线确认后，加载当前方案的三维镜头。</p></section>';preview_scripts=''
 preview_values={'TITLE':'镜头预演','STYLE':theme(),'CASE_TITLE':html.escape(str(job.get('title','全屋参观'))),'NAV':navigation(2,bool(video_path),bool(narration)),'INTRO':'查看实际构图与运镜，确认后制作装修效果视频。','STATUS':('待审阅' if m.get('status')=='pending_user_review' else '工程检查未通过 · 仅供诊断') if preview_runtime else '待准备','BODY':preview_body,'SCRIPTS':preview_scripts}
 (out/'preview.html').write_text(fill((ASSETS/'stage-template.html').read_text(),preview_values),encoding='utf-8')
 chapters_html=''.join(f'<button data-time="{n["seconds"]}"><span>{html.escape(n["name"])}</span><small>{int(n["seconds"])//60:02}:{int(n["seconds"])%60:02}</small></button>' for n in nodes)
 for stage,file,title,intro in [(3,'video.html','视频审阅','检查画面质感、布局一致性与镜头连接。'),(4,'narrated.html','讲解成片','画面、讲解与音乐，一起呈现完整参观。')]:
  if stage==3:intro=ENGINES[render_engine]+' · '+intro
  available=bool(video_path) if stage==3 else bool(narration)
  status='待审阅' if stage==3 else '讲解试听'
  if not available:
   status='待生成';message=('镜头确认后，使用标准渲染制作参观视频。' if render_engine=='h5' else '先确认静态样板和动态短样，再制作完整参观视频。') if stage==3 else '视频确认后，再加入讲解、音乐和字幕。'
   body=f'<section class="stage-empty"><h2>{title}待生成</h2><p>{message}</p><a href="{"preview.html" if stage==3 else "video.html"}">返回{"镜头预演" if stage==3 else "视频审阅"} →</a></section>';scripts=''
  else:
   svg=map_svg(bounds);position='<div class="route-position"><strong data-route-room>正在加载路线…</strong><time data-route-time></time></div>'
   controls=''
   if stage==4:
    controls='<div class="toggles"><label><input id="voiceOn" type="checkbox" checked>讲解</label>'
    if 'music'in urls:controls+='<label><input id="musicOn" type="checkbox" checked>背景音乐</label>'
    controls+='<label><input id="subsOn" type="checkbox" checked>字幕</label></div><details class="script"><summary>查看讲解文稿</summary><div id="script"></div></details>'
   body=f'<div class="video-layout"><div class="video-main"><div class="player"><video id="video" aria-label="参观视频" controls playsinline preload="metadata" src="{video_url}"></video>'
   if stage==4:body+='<div id="subtitle" class="subtitle"></div>'
   body+='</div>'+controls+'</div>'
   body+='<aside class="route-reference"><div class="route-reference-header"><h2>参观路线</h2></div><div class="route-tabs" role="tablist" aria-label="参观路线显示方式"><button id="routeMapTab" type="button" role="tab" aria-selected="true" aria-controls="routeMapPanel">路线图</button><button id="roomListTab" type="button" role="tab" aria-selected="false" aria-controls="roomListPanel" tabindex="-1">房间列表</button></div><div class="route-view" id="routeMapPanel" role="tabpanel" aria-labelledby="routeMapTab"><div class="route-key"><span><i class="done"></i>已走</span><span><i class="later"></i>未走</span><span>● 当前机位</span></div>'+svg+'</div><div class="route-view" id="roomListPanel" role="tabpanel" aria-labelledby="roomListTab" hidden><div class="chapters room-list">'+chapters_html+'</div></div>'+position+'</aside></div>'
   from tour_subtitles import phrase_cues
   payload={'subtitleCues':phrase_cues(captions) if stage==4 else [],'subtitleTiming':'phrase_estimate_within_source_intervals','stage':stage,'routeData':'route-data.json','seconds':seconds,'audio':urls if stage==4 else {},'musicGain':gain,'captions':captions if stage==4 else []}
   scripts='<script type="application/json" id="tour-page-data">'+safe(payload)+'</script><script type="module" src="tour-media.js?v='+sha(out/'tour-media.js')[:16]+'"></script>'
  if stage==3:
   body+=gallery
   if video_record and video_record.get('kind')=='blender':status='待审阅';intro='Blender 渲染 · 检查完整画面、光照一致性与镜头连接。'
   elif video_record and video_record.get('kind')!='decorated':status='三维参考';intro='当前是三维参考视频，尚未绑定装修渲染成片。'
  values={'TITLE':html.escape(title),'STYLE':theme(),'CASE_TITLE':html.escape(str(job.get('title','全屋参观'))),'NAV':navigation(stage,bool(video_path),bool(narration)),'INTRO':html.escape(intro),'STATUS':status,'BODY':body,'SCRIPTS':scripts}
  (out/file).write_text(fill((ASSETS/'stage-template.html').read_text(),values),encoding='utf-8')
 for k in paths:ref(m,k,mp.parent)
 inputs={k:{'path':str(v),'sha256':m['references'][k]['sha256']} for k,v in paths.items()};inputs['rehearsal']={'path':str(mp),'sha256':sha(mp)}
 for key in ('decorationResult','decorationPlan'):
  if job.get(key):inputs[key]={'path':str(check_media(job[key],base,key)),'sha256':job[key]['sha256']}
 if narration and job.get('sample') is not True:
  inputs['videoReview']={'path':str(check_media(job.get('videoReview'),base,'video review')),'sha256':job['videoReview']['sha256']}
 for k,path in {'video':video_path,**audio}.items():
  if path:inputs[k]={'path':str(path),'sha256':sha(path)}
 if not existing:
  rebound=copy.deepcopy(m);rebound['references']={k:{'path':str(ref(m,k,mp.parent)),'sha256':v['sha256']} for k,v in m['references'].items()}
  rebound['references']['planAnimation']=rebound['references']['animation']
  rebound['references']['animation']={'path':str(out/'index.html'),'sha256':sha(out/'index.html')}
  rebound['references']['routePage']={'path':str(out/'route.html'),'sha256':sha(out/'route.html')}
  if plan_only:rebound['reviewScope']='plan_only'
  (out/'rehearsal.json').write_text(json.dumps(rebound,ensure_ascii=False,indent=2),encoding='utf-8')
  pending={'schema':'homeowner-route-approval/1','status':'pending','approvalSource':'explicit_user_confirmation','confirmedBy':'','evidence':'','presentedAnimationSha256':None,'rehearsal':{'path':str(out/'rehearsal.json'),'sha256':sha(out/'rehearsal.json')},'checks':{k:False for k in ['animationViewed','pathAndFacingApproved','durationAndRhythmApproved']}}
  if plan_only:pending['reviewScope']='plan_only'
  (out/'route-review.pending.json').write_text(json.dumps(pending,ensure_ascii=False,indent=2),encoding='utf-8')
 assets={str(f.relative_to(out)):{'sha256':sha(f)} for f in [*(out/k for k in targets+['index.html','rehearsal.json','route-review.pending.json']),*media.iterdir()] if f.is_file()}

 if video_path:
  from tour_stage_gate import pending
  review_pending=pending(video_path,paths['tour'])
  if job.get('sample') is True:review_pending['purpose']='sample'
  (out/'video-review.pending.json').write_text(json.dumps(review_pending,ensure_ascii=False,indent=2),encoding='utf-8')
  assets['video-review.pending.json']={'sha256':sha(out/'video-review.pending.json')}
 validate_presentation(out)
 for name in ('preview.html','camera-preview.html','rehearsal-player.js','replay.json','runtime/renderer.html','runtime/scene.json','runtime/geometry.bin','runtime/three.module.js','runtime/three.core.js','runtime/THREE-LICENSE.txt'):
  if (out/name).is_file():assets[name]={'sha256':sha(out/name)}
 report={'purpose':'sample' if job.get('sample') is True else 'review','presentationContract':'four-stage-presentation/1','schema':SCHEMA,'generatorSha256':sha(__file__),'inputs':inputs,'artifacts':assets,'templateSha256':{n:sha(ASSETS/n) for n in ['preview-stage-template.html','stage-template.html','rehearsal-template.html','stage-theme.css','tour-map.js','tour-media.js','route-embed-template.html','route-embed.js','route-panel.js']},'stages':{'route':'approved' if m.get('spatialGate')=='approved' else 'pending_user_confirmation','preview':('blocked_route_unconfirmed' if m.get('spatialGate')!='approved' else 'ready_for_review' if m.get('status')=='pending_user_review' else 'diagnostic_needs_revision') if preview_runtime else 'not_prepared','video':('approved_for_narration' if narration and job.get('sample') is not True else 'ready_for_review') if video_path else 'not_generated','narrated':'ready_for_review' if narration else 'not_generated'},'rendering':{'engine':render_engine,'label':ENGINES[render_engine]},'videoProbe':probe,'videoGenerated':False,'approvalGranted':False,'videoReviewAccepted':bool(narration) and job.get('sample') is not True,'presentationPolicy':{'navigation':'top-horizontal-four-stage','mediaAspectRatio':'16:9','routeSidebar':'map-or-vertical-list','defaultRouteView':'map','musicGain':gain,'musicVolumePolicy':'constant-no-speech-ducking','chapterPlacement':'route-sidebar','routeAuxiliaryEntry':False,'sampleStatePill':False,'subtitles':'phrase-cuts','captionTiming':'estimated-within-source-intervals','resourceCache':'content-hash-urls'}}
 if plan_only:report.update(reviewScope='plan_only',cameraAcceptanceEligible=False)
 (out/'tour-pages.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');return report


def validate_presentation(out,embed=True):
 from html.parser import HTMLParser
 class Surface(HTMLParser):
  def __init__(self,text):
   super().__init__();self.tags=[];self.nodes=[];self.stack=[];self.nav=0;self.stage_labels=[];self.in_steps=False;self.feed(text)
  def handle_starttag(self,tag,attrs):
   a=dict(attrs);self.tags.append((tag,a));self.nodes.append((tag,a,list(self.stack)))
   if tag not in {'meta','link','input','img','br','hr','source','area','embed','wbr'}:self.stack.append((tag,a))
   if tag=='nav' and a.get('class')=='steps':self.nav+=1;self.in_steps=True
   if self.in_steps and tag in ('a','span'):self.stage_labels.append(a.get('href'))
  def handle_startendtag(self,tag,attrs):
   self.handle_starttag(tag,attrs);self.handle_endtag(tag)
  def handle_endtag(self,tag):
   if tag=='nav':self.in_steps=False
   for i in range(len(self.stack)-1,-1,-1):
    if self.stack[i][0]==tag:self.stack=self.stack[:i];break
 out=Path(out)
 for file in ('route.html','preview.html','video.html','narrated.html'):
  s=Surface((out/file).read_text());tags=[t for t,a in s.tags]
  if s.nav!=1 or s.stage_labels!=['route.html','preview.html','video.html','narrated.html'] or ('iframe' in tags and file!='preview.html'):raise ValueError('Presentation requires one top-level four-stage navigation without embedded pages: '+file)
  if any(t=='nav' and a.get('class')=='steps' and any(pt in ('main','aside','section','div') for pt,pa in parents) for t,a,parents in s.nodes):raise ValueError('Stage navigation must remain outside content panels')
  if file=='route.html' and any(t=='a' and a.get('href','').split('?')[0]=='camera-preview.html' for t,a in s.tags):raise ValueError('Route page must not expose the auxiliary camera preview entry')
  count=tags.count('video')
  if (file=='route.html' and count) or count>1:raise ValueError('Invalid stage video surface: '+file)
  if file not in ('route.html','preview.html') and not count and not any(a.get('class')=='stage-empty' for t,a in s.tags):raise ValueError('Missing media must have an explicit empty stage')
  if file=='preview.html':
   if count:raise ValueError('Mirror preview must use actual 3D, not a mandatory intermediate video')
   frames=[a.get('src') for t,a in s.tags if t=='iframe']
   if frames and frames!=['runtime/renderer.html','route-embed.html']:raise ValueError('Preview must use live renderer and pure route map')
  if count:
   if sum(t=='aside' and a.get('class')=='route-reference' for t,a in s.tags)!=1:raise ValueError('Expected exactly one route sidebar')
   if any('data-time' in a and not any(pa.get('id')=='roomListPanel' for pt,pa in parents) for t,a,parents in s.nodes):raise ValueError('Room chapters must stay inside the route list panel')
   ids=[a.get('id') for t,a in s.tags]
   if any(ids.count(x)!=1 for x in ('routeMapTab','roomListTab','routeMapPanel','roomListPanel')) or 'dialog' in tags or any(a.get('class')=='chapter-strip' for t,a in s.tags):raise ValueError('Media route must use one map/list panel without duplicate chapters or expansion dialog')
 if not embed:return {'status':'pass','contract':'four-stage-presentation/1'}
 embed=Surface((out/'route-embed.html').read_text())
 if embed.nav or any(t in ('iframe','video','header','footer','button') for t,a in embed.tags) or sum(t=='svg' for t,a in embed.tags)!=1:raise ValueError('Embedded route must be a pure map component')
 if (out/'camera-preview.html').exists():
  view=Surface((out/'camera-preview.html').read_text());frames=[a.get('src') for t,a in view.tags if t=='iframe']
  if view.nav or frames!=['route-embed.html','runtime/renderer.html'] or any(t=='video' for t,a in view.tags):raise ValueError('3D preview must use pure route map and live renderer')
 return {'status':'pass','contract':'four-stage-presentation/1'}

def for_encoded_video(video,tour,route_review,out,ffprobe=None):
 """Called only after the existing capture/encoding gates; not a new capture entry."""
 review_path=Path(route_review).resolve();record=read(review_path)['rehearsal'];manifest=Path(record['path']);manifest=manifest if manifest.is_absolute() else review_path.parent/manifest
 if sha(manifest)!=record['sha256']:raise ValueError('Changed route approval manifest')
 job={'video':{'path':str(Path(video).resolve()),'sha256':sha(video),'tourSha256':sha(tour)}}
 return build(manifest,out,job,ffprobe=ffprobe)
