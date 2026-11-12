"""Hash-bound SSH/Windows execution. No installs, service edits, global interrupts or archives."""
import base64,hashlib,json,re,shutil,subprocess
from pathlib import Path
from tour_stage_gate import resolve,bound,sha

def write(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.partial');t.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8');t.replace(p)
def endpoint(e):
 if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.@:-]*',e.get('sshTarget','')):raise ValueError('Use an existing SSH alias/target')
 for k in ('root','python'):
  if not re.fullmatch(r'[A-Za-z]:/[A-Za-z0-9 _./-]+',e.get(k,'')) or '..' in e[k].split('/'):raise ValueError('Invalid remote '+k)
 if ' ' in e['root']:raise ValueError('Use a remote work directory without spaces for SCP portability')
 return e
def ps(e,script):
 encoded=base64.b64encode(("$ErrorActionPreference='Stop';[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false);"+script).encode('utf-16le')).decode()
 r=subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=10',e['sshTarget'],'powershell.exe -NoProfile -NonInteractive -EncodedCommand '+encoded],check=True,capture_output=True,timeout=60)
 return r.stdout.decode('utf-8-sig').strip()
def scp(e,src,dst,recursive=False):
 subprocess.run(['scp','-q','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',*(['-r'] if recursive else []),str(src),str(dst)],check=True,timeout=1800)

def prepare(job,base,out):
 if job.get('schema')!='homeowner-remote-production-job/1' or job.get('kind') not in ('blender','upscale'):raise ValueError('Unsupported remote job')
 e=endpoint(job['endpoint']);source=resolve(job['job'],base);task=json.loads(source.read_text())
 if job['kind']=='blender':
  from blender_draft import validate
  refs,_=validate(task,source.parent,review=task['schema']=='homeowner-blender-review-job/1')
  if 'executionProfile' not in refs:raise ValueError('Remote Blender requires bound executionProfile')
  execution=json.loads(refs['executionProfile'].read_text())
  if execution['backend'] not in ('OPTIX','CUDA','CPU') or execution.get('allowCpuFallback',False):raise ValueError('Remote backend must be explicit; no silent CPU fallback')
  if not execution.get('requirePackedImages'):raise ValueError('Remote scene must require packed texture images')
  for k in ('blender','ffmpeg','ffprobe'):
   if not e.get(k):raise ValueError('Missing existing remote '+k)
 else:
  from video_upscale import validate
  validate(task,source.parent)
  if not e.get('ffmpeg') or not e.get('ffprobe'):raise ValueError('Remote media tools required')
 auth_path=resolve(job['authorization'],base);auth=json.loads(auth_path.read_text())
 if auth.get('scope')!='remote_production' or auth.get('status')!='approved' or auth.get('approvalSource')!='explicit_user_confirmation' or not auth.get('evidence','').strip() or auth.get('job')!=job['job'] or auth.get('endpoint')!=e or auth.get('kind')!=job['kind']:raise ValueError('Remote task/endpoint lacks matching explicit authorization')
 out=Path(out).resolve()
 if out.exists():raise ValueError('Use fresh remote preparation output')
 stage=out/'transfer';(stage/'inputs').mkdir(parents=True);memo={};visiting=set();mapping=[]
 def copy_ref(record,parent):
  src=resolve(record,parent)
  if src in memo:return memo[src]
  if src in visiting:raise ValueError('Cyclic input references')
  visiting.add(src);name=sha(src)[:20]+'-'+re.sub(r'[^A-Za-z0-9_.-]','_',src.name);dest=stage/'inputs'/name
  if src.suffix.lower()=='.json':
   original=json.loads(src.read_text());rebased=walk(original,src.parent)
   if rebased==original:shutil.copy2(src,dest)
   else:dest.write_text(json.dumps(rebased,ensure_ascii=False,indent=2),encoding='utf-8')
  else:shutil.copy2(src,dest)
  result={'path':e['root']+'/inputs/'+name,'sha256':sha(dest)};memo[src]=result;visiting.remove(src)
  mapping.append({'original':bound(src),'remote':result,'relative':'inputs/'+name});return result
 def walk(v,parent):
  if isinstance(v,dict):
   if set(('path','sha256')).issubset(v):return {**v,**copy_ref(v,parent)}
   return {k:walk(x,parent) for k,x in v.items()}
  if isinstance(v,list):return [walk(x,parent) for x in v]
  return v
 task_remote=walk(task,source.parent);write(stage/'job.json',task_remote)
 scripts=stage/'scripts/production';scripts.mkdir(parents=True)
 root=Path(__file__).resolve().parents[2]
 for f in Path(__file__).parent.iterdir():
  if f.is_file() and f.suffix in ('.py','.json','.mjs'):shutil.copy2(f,scripts/f.name)
 # Keep the source layout and every file in the route-rule fingerprint, including templates.
 names=json.loads((Path(__file__).parent/'tour_rules_sources.json').read_text())
 for name in names:
  f=(Path(__file__).parent/name).resolve()
  if not f.is_relative_to(root):raise ValueError('Rule source outside skill root')
  target=stage/f.relative_to(root);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
 # Modules that read an asset when imported on the worker; the rule-source list does not cover them.
 for relative in ('assets/h5/source/renovation-components-v12.js',):
  f=root/relative;target=stage/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,target)
 request={'schema':'homeowner-remote-request/1','kind':job['kind'],'endpoint':e,'sourceJob':job['job'],'job':'job.json'};write(stage/'request.json',request)
 manifest={'schema':'homeowner-remote-input-manifest/1','files':[{'path':f.relative_to(stage).as_posix(),'sha256':sha(f)} for f in sorted(stage.rglob('*')) if f.is_file()],'sourceMapping':mapping}
 write(stage/'manifest.json',manifest)
 write(out/'remote-job.json',job);write(out/'preparation.json',{'sourceJob':bound(source),'authorization':bound(auth_path),'manifest':bound(stage/'manifest.json'),'endpoint':e,'kind':job['kind']})
 return {'status':'prepared_no_remote_calls','inputs':len(manifest['files']),'approvalGranted':False}

def checked(out):
 out=Path(out);receipt=json.loads((out/'preparation.json').read_text());manifest_path=resolve(receipt['manifest'],out)
 resolve(receipt['sourceJob'],out);resolve(receipt['authorization'],out)
 for row in json.loads(manifest_path.read_text())['files']:
  if sha(out/'transfer'/row['path'])!=row['sha256']:raise ValueError('Prepared input/producer changed')
 return out,receipt,receipt['endpoint']
def start(out,resume=False):
 out,r,e=checked(out);intent=out/'submission-intent.json'
 if intent.exists() and not resume:raise ValueError('Submission already attempted; use status, never resubmit blindly')
 if resume:
  state=json.loads(ps(e,"Get-Content -LiteralPath '"+e['root']+"/state.json' -Raw"))
  if state['stage']!='failed':raise ValueError('Only a failed, stopped task can resume')
  if ps(e,"@(Get-CimInstance Win32_Process | Where-Object {$_.CommandLine -like '*"+e['root']+"*' -and $_.Name -match 'python|blender'}).Count")!='0':raise ValueError('Remote worker still running')
 else:
  ps(e,"if(Test-Path -LiteralPath '"+e['root']+"'){throw 'Remote output already exists'};New-Item -ItemType Directory -Path '"+e['root']+"'|Out-Null")
  scp(e,str(out/'transfer')+'/.',e['sshTarget']+':'+e['root']+'/',recursive=True)
 write(intent,{'manifest':r['manifest'],'endpoint':e,'resume':resume,'submissionOutcome':'pending_or_unknown'})
 entry="$p=Start-Process -FilePath '"+e['python']+"' -ArgumentList @('-X','utf8','-u','\""+e['root']+"/scripts/production/remote_production_worker.py\"','--root','\""+e['root']+"\"') -WorkingDirectory '"+e['root']+"' -RedirectStandardOutput '"+e['root']+"/worker.log' -RedirectStandardError '"+e['root']+"/worker-error.log' -PassThru"
 encoded=base64.b64encode(entry.encode('utf-16le')).decode()
 launch=ps(e,"$r=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine='powershell.exe -NoProfile -NonInteractive -EncodedCommand "+encoded+"';CurrentDirectory='"+e['root']+"'};if($r.ReturnValue -ne 0){throw 'Worker launch failed'};$r|Select-Object ProcessId,ReturnValue|ConvertTo-Json -Compress")
 write(out/'launch.json',json.loads(launch));return {'status':'submitted_pending_execution','launch':json.loads(launch)}
def status(out):
 out,r,e=checked(out)
 script="$s=Get-Content -LiteralPath '"+e['root']+"/state.json' -Raw|ConvertFrom-Json;$p='"+e['root']+"/output/capture-progress.json';if(Test-Path $p){$s|Add-Member -NotePropertyName capture -NotePropertyValue (Get-Content $p -Raw|ConvertFrom-Json)};$s|ConvertTo-Json -Depth 8 -Compress"
 value=json.loads(ps(e,script));write(out/'last-remote-state.json',value);return value
def collect(out):
 out,r,e=checked(out);s=status(out)
 if s['stage']!='ready_for_review':raise ValueError('Remote task not complete')
 dest=out/'collected';dest.mkdir(exist_ok=True)
 scp(e,e['sshTarget']+':'+e['root']+'/result.json',dest/'remote-result.json')
 result=json.loads((dest/'remote-result.json').read_text())
 if result['manifestSha256']!=r['manifest']['sha256']:raise ValueError('Remote result belongs to another frozen job')
 for row in result['artifacts']:
  rel=Path(row['path'])
  if rel.is_absolute() or '..' in rel.parts or ':' in row['path']:raise ValueError('Unsafe remote artifact path')
  target=dest/rel;target.parent.mkdir(parents=True,exist_ok=True)
  scp(e,e['sshTarget']+':'+e['root']+'/'+rel.as_posix(),target)
  if sha(target)!=row['sha256']:raise ValueError('Downloaded output hash mismatch')
 task=json.loads(resolve(r['sourceJob'],out).read_text())
 if r['kind']=='blender':
  native=json.loads((dest/'output/review-result.json' if task['schema']=='homeowner-blender-review-job/1' else dest/'output/draft-result.json').read_text())
  native['sources']={k:v for k,v in task.items() if isinstance(v,dict) and 'path' in v and 'sha256' in v};native['video']=bound(dest/result['videoPath']);native['remoteExecution']=bound(dest/'remote-result.json');native['visualReview']='pending';write(dest/'review-result.json',native)
 else:
  native=json.loads((dest/'output/upscale-result.json').read_text());native['source']=task['video']
  for row in native['variants']:
   remote_path=row['video']['path'].replace('\\','/');prefix=e['root'].rstrip('/')+'/'
   if not remote_path.startswith(prefix):raise ValueError('Upscale output outside frozen remote job')
   row['video']=bound(dest/remote_path[len(prefix):])
  native['video']=bound(dest/result['videoPath']);write(dest/'upscale-result.json',native)
 write(out/'collection.json',{'status':'ready_for_review','remoteResult':bound(dest/'remote-result.json'),'video':bound(dest/result['videoPath']),'sourceFramesRetainedRemote':True,'narrationAuthorized':False})
 return json.loads((out/'collection.json').read_text())
