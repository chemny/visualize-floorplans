"""Read-only legacy-case and demo-source review. Never rewrites input or approves it."""
import hashlib,json
from pathlib import Path
from floor_boundaries import normalize_floor_boundaries

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))

def require_media(manifest,base,case_id,case_sha,scheme_sha=None):
 if manifest.get('schema')!='case-media-manifest/1':raise ValueError('Unsupported case media manifest')
 if manifest.get('caseId')!=case_id or manifest.get('caseSha256')!=case_sha:raise ValueError('Media manifest belongs to another case revision')
 if scheme_sha and manifest.get('schemeSha256')!=scheme_sha:raise ValueError('Media manifest scheme differs from actual export')
 seen=set();rows=[]
 for item in manifest.get('items',[]):
  ident=item.get('id');status=item.get('status')
  if not ident or ident in seen or status not in ('current','historical','pending'):raise ValueError('Media needs unique IDs and explicit status')
  seen.add(ident)
  if status=='pending':
   if item.get('artifact'):raise ValueError('Pending media cannot advertise a current artifact')
   rows.append({'id':ident,'status':'pending'});continue
  ref=item.get('artifact',{});p=Path(base)/ref.get('path','')
  if not p.is_file() or digest(p)!=ref.get('sha256'):raise ValueError('Media missing or changed: '+ident)
  if status=='current':
   if item.get('caseId')!=case_id or item.get('caseSha256')!=case_sha:raise ValueError('Mixed case or stale media: '+ident)
   if item.get('kind') in ('tour','video','narrated','render') and (not scheme_sha or item.get('schemeSha256')!=scheme_sha):raise ValueError('Rendered media lacks current exported scheme: '+ident)
   if item.get('kind') in ('video','narrated') and not item.get('tourSha256'):raise ValueError('Video needs exact route binding: '+ident)
  elif not item.get('sourceCaseSha256') or not item.get('representationNote'):
   raise ValueError('Historical reference needs source identity and representation note: '+ident)
  rows.append({'id':ident,'status':status,'kind':item.get('kind'),'sha256':ref['sha256']})
 return rows

def inspect(case_path,source_path,build_path=None,manifest_path=None,scheme_sha=None):
 c=load(case_path);old=load(source_path);blockers=[];pending=[]
 s=c['initialState'];original=old['initialState']
 # Explicit room ownership is migration metadata, not a changed furniture body.
 old_by_id={f['id']:f for f in original['furniture']}
 selected=old.get('presentation',{}).get('finishOverrides',{}).get('furnitureColors',{})
 def bodies(rows):
  result=[]
  for f in rows:
   body={k:v for k,v in f.items() if k!='roomId'};prior=old_by_id.get(f['id'],{})
   if 'colorStyleMode' not in prior and body.get('colorStyleMode')=='fixed' and selected.get(f['id'])==prior.get('color')==body.get('color'):body.pop('colorStyleMode')
   result.append(body)
  return result
 protection={
  'wallsAndOpenings':s['walls']==original['walls'],
  'furniture':bodies(s['furniture'])==bodies(original['furniture']),
  'doorStyles':s.get('doorStyles',{})==original.get('doorStyles',{}),
  'footprint':c['model']['footprint']==old['model']['footprint'],
  'roomIds':{r['id'] for r in c['model']['rooms']}=={r['id'] for r in old['model']['rooms']},
  'style':s.get('style')==original.get('style'),
  'presentation':c.get('presentation',{})==old.get('presentation',{}),
 }
 for key,value in protection.items():
  if not value:blockers.append('Frozen source scope changed: '+key)
 try:_,floor=normalize_floor_boundaries(c)
 except ValueError as e:floor=getattr(e,'report',{'status':'failed','error':str(e)});blockers.append(str(e))
 build=None
 if build_path:
  build=load(build_path);html=Path(build_path).with_suffix('.html')
  # foo.build.json is emitted beside foo.html.
  if str(build_path).endswith('.build.json'):html=Path(str(build_path)[:-11]+'.html')
  if build.get('caseId')!=c['caseId'] or build.get('caseSha256')!=digest(case_path) or not html.is_file() or build.get('htmlSha256')!=digest(html):blockers.append('Build receipt differs from actual case or HTML')
  for field in ('doorSourceCheck','layoutReviewCheck','facilityUseCheck'):
   row=build.get(field,{})
   if row.get('status')!='pass':pending.append({'scope':field,'status':row.get('status','not_provided')})
  d=build.get('doorOperationCheck',{})
  if d.get('status')!='pass':pending.append({'scope':'doorOperationCheck','status':d.get('status','not_provided'),'doors':[v['openingId'] for v in d.get('doors',[]) if v['status']!='pass']})
  if d.get('pathStatus')!='checked':pending.append({'scope':'doorPaths','status':'not_provided'})
 else:pending.append({'scope':'latestGeneratedWorkbench','status':'not_provided'})
 missing=[f['id'] for f in s['furniture'] if f['type']=='shower' and not f.get('showerDoor')]
 if missing:pending.append({'scope':'operableShowerMechanisms','status':'not_provided','ids':missing})
 if not c.get('deskPlacementPolicy'):pending.append({'scope':'deskPlacementPolicy','status':'not_provided'})
 media=[]
 if manifest_path:
  try:media=require_media(load(manifest_path),Path(manifest_path).parent,c['caseId'],digest(case_path),scheme_sha)
  except ValueError as e:blockers.append(str(e))
 else:pending.append({'scope':'boundDemoMedia','status':'not_provided'})
 return {'schema':'case-upgrade-review/1','caseId':c['caseId'],'caseSha256':digest(case_path),'sourceCaseId':old['caseId'],'sourceCaseSha256':digest(source_path),'status':'blocked' if blockers else 'needs_review','frozenSource':protection,'floor':floor,'buildVersion':build.get('workbenchVersion') if build else None,'pending':pending,'blockers':blockers,'media':media,'humanAcceptance':'pending; not inferred from migration or tests','routeAndVideo':'Old media remain historical until current exact route, preview and silent-video approval'}
