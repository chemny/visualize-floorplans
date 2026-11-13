"""Diagnostic temporal measurements for a generated draft; not visual approval."""
import json
from pathlib import Path

def inspect(directory,regions=None):
 import cv2,numpy as np
 p=Path(directory);files=sorted((p/'frames').glob('frame-*.png'));rows=[];prev=None
 for i,f in enumerate(files):
  current=cv2.resize(cv2.imread(str(f)),(320,180));gray=cv2.cvtColor(current,cv2.COLOR_BGR2GRAY).astype('float32')/255
  if prev is not None:
   flow=cv2.calcOpticalFlowFarneback((gray*255).astype('uint8'),(prev*255).astype('uint8'),None,.5,3,15,3,5,1.2,0);y,x=np.mgrid[:180,:320];mx=(x+flow[:,:,0]).astype('float32');my=(y+flow[:,:,1]).astype('float32');warped=cv2.remap(prev,mx,my,cv2.INTER_LINEAR);mask=(mx>=3)&(mx<317)&(my>=3)&(my<177);residual=gray-warped
   rows.append({'frame':i,'medianSignedResidual':float(np.median(residual[mask])),'medianAbsoluteResidual':float(np.median(np.abs(residual[mask])))})
  prev=gray
 result={'schema':'blender-draft-temporal-diagnostic/1','frames':len(files),'method':'low-resolution backward optical-flow compensation; disocclusions may cause false positives','suspectedGlobalFlickerFrames':[r['frame'] for r in rows if abs(r['medianSignedResidual'])>.06],'maxMedianSignedResidual':max((abs(r['medianSignedResidual']) for r in rows),default=0),'rows':rows,'visualReviewRequired':True}
 from tour_media_quality import analyse
 local=analyse([cv2.resize(cv2.imread(str(f)),(320,180)) for f in files],regions) if regions else {'localCheckStatus':'not_sampled','localResidualFlags':[],'limitations':['No global flash flags does not establish absence of local flicker. Actual continuous visual review remains required.']}
 result.update(localCheckStatus=local['localCheckStatus'],localResidualFlags=local['localResidualFlags'],limitations=local['limitations'])
 (p/'temporal-check.json').write_text(json.dumps(result,indent=2));return result
if __name__=='__main__':
 import sys
 print(json.dumps(inspect(sys.argv[1])))

def page(directory,plan,bounds):
 import shutil
 from tour_pages import fill,theme,navigation,safe
 from tour_stage_gate import resolve,bound
 import html
 p=Path(directory);job=json.loads((p/'job.json').read_text());tour=json.loads(resolve(job['tour'],p).read_text());a,z=job['startFrame'],job['endFrameExclusive'];frames=[f['pointMm'] for f in tour['frames'][a:z]]
 approval=json.loads(resolve(job['staticApproval'],p).read_text());shutil.copy2(resolve(approval['image'],p),p/'approved-static.png');shutil.copy2(plan,p/'route-plan.png')
 x,y,w,h=bounds;values={'TITLE':html.escape(job.get('title','Blender 动态短样')),'STYLE':theme(),'NAV':navigation(2,False,False,True),'START':f'{a/tour["fps"]:.2f}','END':f'{z/tour["fps"]:.2f}','SECONDS':f'{(z-a)/tour["fps"]:.2f}','VIDEO':'draft.mp4','BOUNDS':' '.join(map(str,bounds)),'X':str(x),'Y':str(y),'W':str(w),'H':str(h),'PATH':' '.join(('M' if i==0 else 'L')+f'{q[0]},{q[1]}' for i,q in enumerate(frames)),'FRAMES':safe(frames),'FPS':str(tour['fps']),'OFFSET':str(a/tour['fps'])}
 template=Path(__file__).resolve().parents[2]/'assets/h5/tour/blender-draft-template.html';(p/'index.html').write_text(fill(template.read_text(),values))
 (p/'page-source.json').write_text(json.dumps({'template':bound(template),'plan':bound(plan),'bounds':bounds,'role':'auxiliary_stage2_dynamic_review','approvalGranted':False},indent=2))

def validation_index(root,rows,comparison_href=None,*,heading=None,intro=None,footer=None,columns=2):
 import html
 from tour_pages import fill,theme,navigation
 from tour_stage_gate import bound,resolve
 if type(columns)!=int or not 1<=columns<=3:raise ValueError('Invalid comparison columns')
 p=Path(root);cards=[];sources=set();report=[]
 for row in rows:
  out=Path(row['out']);result=json.loads((out/'draft-result.json').read_text());sources.add((result['sources']['scene']['sha256'],result['sources']['tour']['sha256']))
  resolve(result['video'],out)
  for key in ('scene','tour'):resolve(result['sources'][key],out)
  relative=out.relative_to(p).as_posix();title=html.escape(row['title']);seconds=result['probe']['seconds']
  cards.append(f'<section class="validation-card"><h2>{title}</h2><p class="validation-note">{seconds:.2f} 秒 · {result["probe"]["width"]} × {result["probe"]["height"]}</p><video controls playsinline preload="metadata" src="{html.escape(relative,quote=True)}/draft.mp4"></video><p class="validation-note">{html.escape(row.get('reviewNote','动态效果待审阅'))}</p><p><a href="{html.escape(relative,quote=True)}/index.html">单段与原路线 →</a></p></section>')
  report.append({'title':row['title'],'result':bound(out/'draft-result.json'),'video':result['video'],'userReview':'pending'})
 if len(sources)!=1:raise ValueError('Validation clips must share exact source scene and route')
 template=Path(__file__).resolve().parents[2]/'assets/h5/tour/blender-validation-template.html'
 (p/'index.html').write_text(fill(template.read_text(),{'STYLE':theme(),'NAV':navigation(2,False,False,True),'CARDS':''.join(cards),'COLUMNS':str(columns),'HEADING':html.escape(heading or 'Blender · 整片前动态短样'),'INTRO':html.escape(intro or '同一场景、同一条原路线。各段独立播放，重点查看门洞遮挡、卫浴镜面和移动窗景。当前为动态验证清晰度，尚未制作整片。'),'FOOTER':html.escape(footer or '短样不自动代表全片通过。窗外仍为远处平面概念背景，长距离移动和其他窗户需要另行核对。'),'EXTRA':('<p><a href="'+html.escape(comparison_href,quote=True)+'">查看调整前后对照 →</a></p>') if comparison_href else ''}))
 (p/'validation-index.json').write_text(json.dumps({'schema':'homeowner-blender-dynamic-validation/1','template':bound(template),'clips':report,'fullAnimationEnabled':False,'approvalGranted':False},ensure_ascii=False,indent=2))
