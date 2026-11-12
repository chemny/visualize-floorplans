"""Portable timed route rehearsal. Produces no video and grants no approval."""
import argparse,base64,copy,html,json,math,shutil
from pathlib import Path
from plan_route import Planner
from tour_workflow import sha
TEMPLATE=Path(__file__).resolve().parents[2]/'assets/h5/tour/rehearsal-template.html'
CHECKS=('animationViewed','pathAndFacingApproved','durationAndRhythmApproved')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def build(tour_path,config_path,bundle_path,plan_path,bounds,out,budget_seconds,runtime,label=None,spatial=None):
 out=Path(out).resolve()
 if out.exists():raise ValueError('Use a fresh rehearsal directory')
 t,c,b=read(tour_path),read(config_path),read(bundle_path);fs=t['frames'];fps=t['fps']
 if t['schemeSha256']!=b['schemeSha256']:raise ValueError('Scheme mismatch')
 if not fs or not math.isfinite(fps) or fps<=0 or not math.isfinite(budget_seconds) or budget_seconds<=0:raise ValueError('Positive finite time data required')
 if abs(t['seconds']-len(fs)/fps)>1/fps+.0001:raise ValueError('Tour duration differs from frames')
 if len(bounds)!=4 or not all(math.isfinite(v) for v in bounds) or min(bounds[2:])<=0:raise ValueError('Explicit plan-coordinate bounds required')
 image=Path(plan_path).read_bytes()
 if not image.startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('Use the current approved PNG plan; bounds map its full canvas to model coordinates')
 marks={s['name']:s.get('frameIndex',s.get('frame')) for s in (t.get('stopFrames') or t.get('visits',[]))};chapters=[];visits=[{'name':'开始','seconds':0}];seen=set();occupied=set()
 for ch in c['chapters']:
  a,z=marks[ch['from']],marks[ch['to']]
  if not isinstance(a,int) or not isinstance(z,int) or not 0<=a<z<len(fs) or ch['phase'] not in ('observe','transit'):raise ValueError('Invalid chapter')
  indices=set(range(a,z))
  if occupied&indices:raise ValueError('Overlapping time chapters')
  occupied|=indices
  row={**ch,'startSeconds':a/fps,'endSeconds':z/fps,'allocatedSeconds':(z-a)/fps};chapters.append(row)
  if ch['phase']=='observe':visits.append({'name':ch['name'],'seconds':a/fps})
 if occupied!=set(range(len(fs)-1)):raise ValueError('Chapters must cover the full timeline')
 visits.append({'name':'结束','seconds':(len(fs)-1)/fps})
 observe=sum(x['allocatedSeconds'] for x in chapters if x['phase']=='observe');transit=t['seconds']-observe;yaw=sum(abs(z['yawRadians']-a['yawRadians']) for a,z in zip(fs,fs[1:]))*180/math.pi
 from tour_choreography import inspect
 choreography=inspect(t,c)
 ledger={'totalSeconds':t['seconds'],'maximumSeconds':budget_seconds,'observeSeconds':observe,'transitSeconds':transit,'transitFraction':transit/t['seconds'],'accumulatedYawDegrees':yaw,'overBudget':t['seconds']>budget_seconds+1e-6,'chapters':chapters,'choreography':choreography,'note':'Case-specific proposed budget, not a universal duration or comfort rule. Transit includes entering, turning, backtracking and final frame hold.'}
 planner=Planner(b,{});walls=planner.walls+planner.leaves
 if c.get('roomBudgetPolicy'):
  from tour_room_budgets import inspect as inspect_budgets
  ledger['roomBudgets']=inspect_budgets(b,t,c,c['roomBudgetPolicy'])
 from tour_observation_points import inspect as inspect_points
 ledger['observationPoints']=inspect_points(t,c)
 points_failed=bool(ledger['observationPoints']['issues'])
 coverage=None
 if c.get('coveragePolicy',{}).get('enabled'):
  from tour_coverage import inspect as inspect_coverage
  coverage=inspect_coverage(b,t,planner,c['coveragePolicy'].get('minimumPercent'),config=c);ledger['coverage']=coverage
 from tour_contract import inspect as inspect_contract
 contract_report=inspect_contract(b,t,c)
 ledger['tourContract']=contract_report
 contract_failed=bool(contract_report['issues'])
 coverage_failed=coverage is not None and coverage['status']=='needs_revision'
 budgets_failed=ledger.get('roomBudgets',{}).get('status')=='needs_revision'
 pts=[f['pointMm'] for f in fs];route='M'+' L'.join(f'{x},{y}' for x,y in pts)
 x,y,w,h=bounds
 svg=f'<svg id="plan" xmlns="http://www.w3.org/2000/svg" viewBox="{x} {y} {w} {h}"><image x="{x}" y="{y}" width="{w}" height="{h}" href="data:image/png;base64,{base64.b64encode(image).decode()}"/><g pointer-events="none"><path d="{route}" fill="none" stroke="white" stroke-width="42"/><path d="{route}" fill="none" stroke="#27788b" stroke-width="22" stroke-linejoin="round"/><path id="cone" fill="#cd984a" fill-opacity=".22" stroke="#b77c39" stroke-width="12"/><path id="axis" stroke="#ac682e" stroke-width="20" stroke-dasharray="50 25"/><g id="travel"><path d="M0,0 L230,0 M175,-45 L230,0 L175,45" fill="none" stroke="#26788b" stroke-width="20"/></g><g id="camera"><circle r="65" fill="#aa6433" stroke="white" stroke-width="18"/><path d="M90,0 L-20,-35 L-20,35 Z" fill="white"/></g></g></svg>'
 cards=''.join(f'<button class="chapter" data-time="{v["seconds"]}"><span>{i+1:02}　{html.escape(v["name"])}</span><small>{v["seconds"]:.1f}s</small></button>' for i,v in enumerate(visits))
 table='<h2 style="margin-top:18px">观看时间 · 进出另计</h2><table style="width:100%;font-size:12px">'+''.join(f'<tr><td>{html.escape(ch["name"])}<small style="display:block;color:#81776a">{html.escape(ch.get("viewPurpose",""))}</small></td><td>{ch["allocatedSeconds"]:.1f}秒</td></tr>' for ch in chapters if ch['phase']=='observe')+'</table>'
 issue_html=''.join('<li>'+html.escape(i.get('chapter','整体节奏')+'：'+i['message'])+'</li>' for i in choreography['issues'])
 summary=f'总计 {t["seconds"]:.1f} 秒 / 提议上限 {budget_seconds:.1f} 秒<br>观看 {observe:.1f} 秒 · 连接 {transit:.1f} 秒（{transit/t["seconds"]:.0%}）<br>累计转头 {yaw:.0f}°<br>'+('超出时长预算：先调整路线与节奏，不可直接渲染。' if ledger['overBudget'] else '时长在预算内，仍须观看动画确认节奏。')
 if issue_html:summary+='<br>需调整：<ul>'+issue_html+'</ul>'
 if coverage is not None:summary+='<br>每房覆盖最低 '+str(coverage['minimumPercent'])+'%（二维筛查，三维待核验）<ul>'+''.join('<li>'+html.escape(r['roomId'])+'：'+str(r['horizontalAreaPercent'])+'%'+(' · 未达标' if not r['meetsProxyMinimum'] else '')+'</li>' for r in coverage['rooms'])+'</ul>'
 safe=lambda v:json.dumps(v,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
 from tour_pages import theme,navigation
 values={'PREVIEW':'','STYLE':theme(),'NAV':navigation(standalone=True),'DURATION':f'全程约 {t["seconds"]:.1f} 秒','INTRO':html.escape(label or '先确认走位、视线与时间分配，再生成视频。'),'PLAN':svg,'CARDS':cards,'BUDGET':table,'SUMMARY':summary,'BADGE':'待调整' if ledger['overBudget'] or choreography['issues'] or coverage_failed or budgets_failed or points_failed or contract_failed else '待用户确认','TOUR':safe(t),'WALLS':safe(walls),'VISITS':safe(visits),'CHAPTERS':safe(chapters),'END':str((len(fs)-1)/fps),'STEP':str(1/fps)}
 values['ACTIONS']='<span class="pill">'+values['BADGE']+'</span>'
 page=TEMPLATE.read_text(encoding='utf-8')
 import re
 page=re.sub(r'__([A-Z]+)__',lambda m:values[m[1]],page)
 out.mkdir(parents=True);shutil.copy2(Path(runtime)/'scene.json',out/'scene-reference.json');(out/'index.html').write_text(page,encoding='utf-8');dump(out/'timing.json',ledger)
 if c.get('tourContract'):dump(out/'tour-contract-report.json',{**contract_report,'tourSha256':sha(tour_path),'configSha256':sha(config_path),'bundleSha256':sha(bundle_path),'schemeSha256':t['schemeSha256']})  # review-capture releases verify these bindings
 refs={k:{'path':str(Path(v).resolve()),'sha256':sha(v)} for k,v in {'tour':tour_path,'config':config_path,'bundle':bundle_path,'plan':plan_path,'animation':out/'index.html','timing':out/'timing.json','scene':out/'scene-reference.json'}.items()}
 if c.get('tourContract'):refs['contractReport']={'path':str(out/'tour-contract-report.json'),'sha256':sha(out/'tour-contract-report.json')}
 if spatial:
  from tour_spatial_plan import conformance
  dump(out/'spatial-conformance.json',{**conformance(spatial['value'],t),'tourSha256':sha(tour_path)})
  refs.update(spatialPlan={'path':str(Path(spatial['plan']).resolve()),'sha256':sha(spatial['plan'])},spatialReview={'path':str(Path(spatial['review']).resolve()),'sha256':sha(spatial['review'])},spatialConformance={'path':str(out/'spatial-conformance.json'),'sha256':sha(out/'spatial-conformance.json')})
 manifest={'schema':'homeowner-route-rehearsal/1','stage':'camera_rehearsal','spatialGate':'approved' if spatial else 'missing','schemeSha256':t['schemeSha256'],'references':refs,'geometrySha256':sha(Path(runtime)/'geometry.bin'),'label':label,'planBounds':bounds,'status':'over_budget' if ledger['overBudget'] else 'needs_revision' if choreography['issues'] or coverage_failed or budgets_failed or points_failed or contract_failed else 'pending_user_review','timing':ledger};dump(out/'rehearsal.json',manifest)
 review={'schema':'homeowner-route-approval/1','status':'pending','approvalSource':'explicit_user_confirmation','confirmedBy':'','evidence':'','rehearsal':{'path':str(out/'rehearsal.json'),'sha256':sha(out/'rehearsal.json')},'presentedAnimationSha256':None,'checks':{k:False for k in CHECKS}}
 dump(out/'route-review.pending.json',review)
 return manifest

def require_route(review_path,tour_path,runtime=None,*,runtime_scene=None,runtime_geometry=None):
 # Bound file inputs also work after remote transport; no untracked runtime directory.
 scene_path=Path(runtime_scene) if runtime_scene is not None else Path(runtime)/'scene.json'
 geometry_path=Path(runtime_geometry) if runtime_geometry is not None else Path(runtime)/'geometry.bin'
 if not review_path:raise ValueError('Video capture requires --route-review: show and confirm the timed route animation first (including --preview/--range)')
 r=read(review_path);base=Path(review_path).resolve().parent
 resolve=lambda s:Path(s) if Path(s).is_absolute() else base/s
 if r.get('schema')!='homeowner-route-approval/1' or r.get('status')!='approved' or r.get('approvalSource')!='explicit_user_confirmation' or not str(r.get('confirmedBy','')).strip() or not str(r.get('evidence','')).strip():raise ValueError('Explicit user approval of displayed rehearsal is required; text itinerary/internal review is insufficient')
 if any(r.get('checks',{}).get(k) is not True for k in CHECKS):raise ValueError('Animation, facing, duration and rhythm must all be approved')
 a=r.get('rehearsal',{});mp=resolve(a.get('path',''))
 if not mp.is_file() or sha(mp)!=a.get('sha256'):raise ValueError('Rehearsal manifest missing/changed')
 m=read(mp)
 if m.get('schema')!='homeowner-route-rehearsal/1':raise ValueError('Invalid rehearsal')
 if m.get('reviewScope')=='plan_only' or r.get('reviewScope')=='plan_only':raise ValueError('Plan-only route review does not authorize camera/video capture')
 for a in m['references'].values():
  q=Path(a['path']) if Path(a['path']).is_absolute() else mp.parent/a['path']
  if not q.is_file() or sha(q)!=a['sha256']:raise ValueError('Rehearsal source or displayed animation changed')
 if m['references']['tour']['sha256']!=sha(tour_path) or m['schemeSha256']!=read(tour_path)['schemeSha256'] or m['schemeSha256']!=read(scene_path)['schemeSha256']:raise ValueError('Route or scheme changed; show a new animation')
 if r.get('presentedAnimationSha256')!=m['references']['animation']['sha256']:raise ValueError('Approval does not identify displayed animation')
 from tour_stage_chain import require_rehearsal_chain
 require_rehearsal_chain(m,mp.parent,tour_path)
 if m.get('geometrySha256')!=sha(geometry_path):raise ValueError('Runtime geometry changed')
 baseline=read(m['references']['scene']['path']);current=read(scene_path)
 for v in (baseline,current):v.get('renderSettings',{}).pop('size',None)
 if baseline!=current:raise ValueError('Runtime scene changed; resolution-only transfer is allowed')
 from tour_choreography import inspect
 diagnostic=inspect(read(tour_path),read(m['references']['config']['path']))
 config=read(m['references']['config']['path'])
 from tour_contract import inspect as inspect_contract
 contract_report=inspect_contract(read(m['references']['bundle']['path']),read(tour_path),config)
 if contract_report['issues']:raise ValueError('Tour contract requires revision before capture: '+', '.join(x['code'] for x in contract_report['issues']))
 from tour_rules import require_visual_evidence
 require_visual_evidence(m,tour_path)
 if config.get('coveragePolicy',{}).get('enabled'):
  from tour_coverage import inspect as inspect_coverage
  coverage=inspect_coverage(read(m['references']['bundle']['path']),read(tour_path),Planner(read(m['references']['bundle']['path']),{}),config['coveragePolicy'].get('minimumPercent'),config=config)
  if coverage['status']=='needs_revision':raise ValueError('Room coverage below minimum; revise route before capture')
 if diagnostic['issues']:raise ValueError('Tour choreography requires revision before capture: '+', '.join(i['code'] for i in diagnostic['issues']))
 from tour_observation_points import inspect as inspect_points
 if inspect_points(read(tour_path),config)['issues']:raise ValueError('Observation point count/time requires revision before capture')
 if config.get('roomBudgetPolicy'):
  from tour_room_budgets import inspect as inspect_budgets
  budget_report=inspect_budgets(read(m['references']['bundle']['path']),read(tour_path),config,config['roomBudgetPolicy'])
  if budget_report['issues']:raise ValueError('Room visit budget exceeded; replan and reconfirm before capture')
 if m['timing']['overBudget'] or m['timing']['totalSeconds']>m['timing']['maximumSeconds']+1e-6:raise ValueError('Over-budget route: replan and reconfirm timing; do not accelerate or silently extend')
 return r

def bind_quality(manifest_path,screen_path,visual_path):
 """Explicitly bind review evidence; invalidates old approvals, never creates acceptance."""
 from tour_rules import require_visual_evidence,review_state,RULESET,fingerprint
 mp=Path(manifest_path).resolve();m=read(mp)
 for key,path in [('screenAudit',screen_path),('visualReview',visual_path)]:
  q=Path(path).resolve();m['references'][key]={'path':str(q),'sha256':sha(q)}
 screen=read(screen_path);visual=read(visual_path)
 # Identity is required even for a pending or failed review.
 for value in (screen,visual):
  if value.get('tourSha256')!=m['references']['tour']['sha256'] or value.get('configSha256')!=m['references']['config']['sha256'] or value.get('geometrySha256')!=m['geometrySha256']:raise ValueError('Stale quality evidence')
 screen_pass=screen.get('status')=='pass' and screen.get('rulesetVersion')==RULESET and screen.get('ruleFingerprint')==fingerprint() and screen.get('screenQuality',{}).get('status')=='pass'
 failed=not screen_pass or visual.get('result')=='needs_revision' or bool(m['timing']['tourContract']['issues'])
 if visual.get('result')=='pass':require_visual_evidence(m,m['references']['tour']['path'])
 m['status']='needs_revision' if failed or m['timing']['tourContract']['issues'] else 'pending_user_review'
 dump(mp,m)
 pending=mp.with_name('route-review.pending.json');r=read(pending);r.update(status='pending',confirmedBy='',evidence='',presentedAnimationSha256=None);r['checks']={k:False for k in CHECKS};r['rehearsal']['sha256']=sha(mp);dump(pending,r)
 root=mp.parent.parent
 state={**review_state(m['timing']['tourContract']['status'],'pass' if screen_pass else 'fail',visual.get('result','pending')),'actualPlayback':visual.get('observationMode','not_performed')}
 dump(root/'self-check.json',state)
 if (root/'workflow-state.json').exists():
  workflow=read(root/'workflow-state.json');workflow.update(stage='repair_required' if failed else 'rehearsal_pending',visualReview=visual.get('result','pending'),dynamicPlayback=state['actualPlayback'],routeApproval='pending',humanAcceptance='pending',readyForVisualReview=state['readyForVisualReview'],blockedStages=['video_capture'],nextAllowedStage='repair_and_recheck' if failed else 'explicit_route_review');workflow.setdefault('events',[]).append({'stage':'visual_evidence_bound','result':visual.get('result','pending')});dump(root/'workflow-state.json',workflow)
 return m

def main():
 import sys
 if len(sys.argv)>1 and sys.argv[1]=='bind-quality':
  ap=argparse.ArgumentParser(description='Bind same-tour mesh and real-playback review; reset approval to pending')
  for key in ('manifest','screen-audit','visual-review'):ap.add_argument('--'+key,required=True)
  a=ap.parse_args(sys.argv[2:]);m=bind_quality(a.manifest,a.screen_audit,a.visual_review);print(json.dumps({'status':m['status'],'approval':'pending'}));return
 ap=argparse.ArgumentParser(description=__doc__)
 for k in ('tour','config','bundle','plan','out','runtime'):ap.add_argument('--'+k,required=True)
 ap.add_argument('--label',help='Optional explicit purpose, e.g. rejected-route diagnosis; never imply approval');ap.add_argument('--spatial-plan');ap.add_argument('--spatial-review');ap.add_argument('--bounds',type=float,nargs=4,required=True,metavar=('X','Y','WIDTH','HEIGHT'));ap.add_argument('--budget-seconds',type=float,required=True);a=ap.parse_args()
 from tour_stage_chain import require_camera_entry
 spatial=require_camera_entry({'bundle':a.bundle,'spatialPlan':a.spatial_plan,'spatialReview':a.spatial_review})
 m=build(a.tour,a.config,a.bundle,a.plan,a.bounds,a.out,a.budget_seconds,a.runtime,a.label,spatial);print(json.dumps({'status':m['status'],'output':a.out,'seconds':m['timing']['totalSeconds']},ensure_ascii=False))
if __name__=='__main__':main()
