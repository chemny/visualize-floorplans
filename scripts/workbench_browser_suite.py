"""Generated-artifact browser acceptance with existing local tools; loopback only."""
import argparse, functools, hashlib, http.server, json, os, shutil, signal, subprocess, sys, threading
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit

ROOT=Path(__file__).resolve().parent.parent
SCRIPTS=ROOT/'scripts'
REGISTRY={
 'generated':('test_generated_workbench_browser.mjs','labels_lamps'),
 'copy':('test_product_copy_browser.mjs','any_room'),
 'sidebars':('test_persistent_sidebars_browser.mjs',None),
 'lighting':('test_simple_lighting_browser.mjs',None),
 'view':('test_view_dropdown_browser.mjs',None),
 'header':('test_header_icon_actions_browser.mjs','any_room'),
 'components':('test_component_contracts_browser.mjs','components'),
 'doors':('test_door_dropdown_browser.mjs','door_pair'),
 'library':('test_clean_library_browser.mjs','protected'),
 'walls':('test_orbit_wall_inert_browser.mjs','walls'),
 'sidebar-icons':('test_sidebar_toggles_browser.mjs',None),
 'floors':('test_floor_boundaries_browser.mjs',None),
 'shower':('test_shower_browser.mjs','shower'),
 'shower-resize':('test_shower_resize_browser.mjs','shower_zero'),
 'vanity-resize':('test_vanity_resize_browser.mjs','suite_vanity'),
 'bathtub-resize':('test_bathtub_resize_browser.mjs','bathtub_fixture'),
 'styles':('test_style_linkage_browser.mjs','styled'),
 'style-locks':('test_style_manual_locks_browser.mjs','style_locks'),
 'wet-walls':('test_wet_wall_browser.mjs','wet_rooms'),
 'furniture-styles':('test_furniture_style_browser.mjs','furniture_styles'),
 'plan-order':('test_plan_furniture_order_browser.mjs','plan_pair'),
}
CORE=['generated','copy','sidebars','lighting','view','header']

def selected_checks(value):
 if value=='core':return CORE[:]
 if value=='full':return list(REGISTRY)
 checks=[name for part in value.split(',') for name in (CORE if part=='core' else list(REGISTRY) if part=='full' else [part])]
 if not checks or any(c not in REGISTRY for c in checks):raise ValueError('Unknown checks; use core/full or '+','.join(REGISTRY))
 return list(dict.fromkeys(checks))

def point_inside(point,poly):
 x,y=point;inside=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return inside

def prerequisite(case,name):
 s=case['initialState'];f=s['furniture'];types={v['type'] for v in f};walls=s['walls'];opens=[o for w in walls for o in w.get('opens',[])];kinds={o['kind'] for o in opens};rooms={r['id'] for r in case['model']['rooms']}
 conditions={
  'any_room':(any(r in s.get('rooms',{}) for r in rooms),'needs at least one matching model/state room'),
  'components':(bool(types&{'vanity','bathtub'}) or any(v['type']=='shower' and v.get('showerDoor') for v in f) or 'door' in kinds,'needs a resizable fixture or real hinged opening'),
  'labels_lamps':(len(rooms)>=2 and any(v.get('mount')=='ceiling' or v['type'] in {'ceilinground','ceilingsquare','pendant','downlight','tracklight','lightpanel','spotlight','linearlight','ledstrip'} for v in f),'needs two rooms and a ceiling fixture'),
  'copy':('sofa' in types and 'living' in rooms,'existing copy regression requires a sofa and room id living'),
  'wardrobe':('wardrobe' in types,'existing header regression requires a wardrobe'),
  'door_pair':({'door','sliding'}<=kinds,'existing door regression requires hinged and sliding openings'),
  'protected':(any(w.get('bearing') for w in walls),'needs a protected wall'),
  'walls':(any(w.get('bearing') for w in walls) and any(not w.get('bearing') for w in walls),'needs protected and ordinary walls'),
  'shower':(any(v['type']=='shower' and v.get('showerDoor') for v in f),'needs an explicitly operable shower'),
  'shower_zero':(any(v['type']=='shower' and v.get('rot')==0 and v.get('showerDoor') for v in f),'existing resize regression requires an operable shower at rotation zero'),
  'suite_vanity':(any(v['id']=='suite-vanity' for v in f),'existing vanity regression requires suite-vanity'),
  'bathtub':('bathtub' in types,'needs a bathtub'),
  'bathtub_fixture':('bathtub' not in types and point_inside([5800,14200],case['model'].get('footprint',[])),'existing bathtub regression adds a temporary fixture at [5800,14200] and requires no original bathtub'),
  'styled':({'living','dining','hall','primary','bed_nw','bed_ne','closet','kitchen','bath_public'}<=rooms and 'shower' in types and not any(v.get('floorStyleMode')=='fixed' for v in s.get('rooms',{}).values()),'existing style regression requires the declared reference room ids'),
  'wet_rooms':(any((r.get('function') or r.get('usage') or r.get('role')) in {'kitchen','bathroom','bath','toilet'} or any(v in (str(r.get('id',''))+str(r.get('name',''))).lower() for v in ['kitchen','bath','toilet','厨','卫','浴']) for r in case['model']['rooms']),'needs a kitchen or bathroom'),
  'furniture_styles':({'sofa','chair','tvstand'}<=types and case.get('readLocalStorage') is not False,'needs core furniture and enabled browser persistence'),
  'plan_pair':(bool(types&{'chair','officechair','barstool'}) and bool(types&{'desk','dresser','table'}),'needs a tucked seat/table pair; no silent empty-target pass'),
  'style_locks':('wardrobe' in types and bool(s.get('wallFinishes')) and 'living' in rooms,'existing style-lock regression requires wardrobe, living and wall finishes'),
 }
 return conditions.get(name,(True,''))

class QuietHandler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def stop_test_process(process):
 # Playwright may detach Chrome into its own process group. Follow only this test's
 # descendants, then stop the isolated Node group; never kill unrelated browsers.
 if os.name=='nt':
  subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True)
  return
 try:
  rows=subprocess.check_output(['ps','-axo','pid,ppid'],text=True).splitlines()[1:]
  children={}
  for row in rows:
   pid,ppid=map(int,row.split());children.setdefault(ppid,[]).append(pid)
  def descendants(pid):
   found=[]
   for child in children.get(pid,[]):found.extend(descendants(child));found.append(child)
   return found
  for pid in descendants(process.pid):
   try:os.kill(pid,signal.SIGKILL)
   except ProcessLookupError:pass
 except (OSError,ValueError,subprocess.SubprocessError):pass
 try:os.killpg(process.pid,signal.SIGKILL)
 except ProcessLookupError:pass

def run_process(command,*,timeout,**kwargs):
 flags={'start_new_session':True} if os.name!='nt' else {'creationflags':subprocess.CREATE_NEW_PROCESS_GROUP}
 capture=kwargs.pop('capture_output',False)
 if capture:kwargs.update(stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 process=subprocess.Popen(command,**flags,**kwargs)
 try:
  stdout,stderr=process.communicate(timeout=timeout)
  return subprocess.CompletedProcess(command,process.returncode,stdout,stderr)
 except BaseException:
  stop_test_process(process)
  process.communicate()
  raise

def verify_binding(binding,name,base_url,out):
 if binding.get('status')!='passed':raise ValueError('Actual loaded-artifact evidence did not pass')
 receipts=[]
 for page in binding.get('pages',[]):
  if page.get('status')!='passed':raise ValueError('A captured page did not pass artifact verification')
  receipts.extend(page.get('artifacts',[]))
 for filename in (['before.html','after.html'] if name=='copy' else ['after.html']):
  expected=base_url+filename;manifest=json.loads((out/filename.replace('.html','.build.json')).read_text())
  def normalized(url):
   parts=urlsplit(url);return urlunsplit(parts._replace(query='',fragment=''))
  matches=[r for r in receipts if normalized(r.get('url',''))==expected]
  if not matches:raise ValueError('No actual receipt for this run artifact: '+filename)
  for receipt in matches:
   for key in ['htmlSha256','engineSha256','templateSha256','caseSha256']:
    if receipt.get(key)!=manifest.get(key) or not manifest.get(key):raise ValueError('Receipt mismatch for this run '+filename+': '+key)
   for receipt_key,manifest_key in [('sourceSha256','sourceSha256'),('provenanceManifestSha256','manifestSha256'),('registrySha256','registrySha256')]:
    value=manifest.get('engineProvenance',{}).get(manifest_key)
    if value and receipt.get(receipt_key)!=value:raise ValueError('Source receipt mismatch for this run '+filename+': '+receipt_key)
 return True

def run_one(name,base_url,out,env,node,timeout,run=run_process):
 script,_=REGISTRY[name];dest=out/name;dest.mkdir();report=dest/'result.json';evidence=dest/'artifact-evidence.json'
 command=[str(node),str(SCRIPTS/script)]
 if name=='copy':command+=[base_url+'before.html',base_url+'after.html']
 else:command+=[base_url+'after.html'+('?view=3d' if name in {'styles','style-locks'} else '')]
 command.append(str(report))
 taskenv={**env,'INTERIOR_ARTIFACT_EVIDENCE':str(evidence)}
 try:
  result=run(command,cwd=ROOT,env=taskenv,capture_output=True,text=True,timeout=timeout)
  (dest/'output.log').write_text(result.stdout+result.stderr,encoding='utf-8')
  details=json.loads(report.read_text()) if report.exists() else {}
  binding=json.loads(evidence.read_text()) if evidence.exists() else {}
  ok=result.returncode==0 and details.get('status') in {'passed','pass'}
  if ok:verify_binding(binding,name,base_url,out)
  return {'name':name,'status':'pass' if ok else 'fail','exitCode':result.returncode,'report':str(report.relative_to(out)),'artifactEvidence':str(evidence.relative_to(out)),'reason':None if ok else 'Test, loaded-artifact binding, or result report failed'}
 except subprocess.TimeoutExpired:
  return {'name':name,'status':'fail','reason':'Browser test timed out; no acceptance inferred'}
 except Exception as error:return {'name':name,'status':'fail','reason':str(error)}

def suite_status(results):
 if any(r['status']=='fail' for r in results):return 'fail'
 if any(r['status']=='blocked' for r in results):return 'blocked'
 return 'pass' if any(r['status']=='pass' for r in results) else 'not_applicable'

def main(argv=None):
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',required=True);p.add_argument('--out',required=True);p.add_argument('--node',default=shutil.which('node'));p.add_argument('--browser',default=os.environ.get('INTERIOR_BROWSER'));p.add_argument('--playwright-module',default=os.environ.get('INTERIOR_PLAYWRIGHT_MODULE'));p.add_argument('--checks',default='core');p.add_argument('--timeout',type=int,default=180);args=p.parse_args(argv)
 checks=selected_checks(args.checks);out=Path(args.out).resolve()
 if out.exists() and any(out.iterdir()):p.error('Use a new empty evidence directory')
 out.mkdir(parents=True,exist_ok=True);case_path=Path(args.case).resolve();case=json.loads(case_path.read_text());case_hash=hashlib.sha256(case_path.read_bytes()).hexdigest();results=[]
 report={'schema':'interior-workbench-browser-suite/1','caseSha256':case_hash,'requestedChecks':checks,'checks':results,'installsPerformed':False,'externalNetworkRequired':False,'serverBinding':'127.0.0.1','scope':'Actual generated HTML pointer and scheme checks in isolated browser storage; not visual, physical-device, product/site or human acceptance'}
 missing=[label for label,value in [('Node',args.node),('browser',args.browser),('Playwright module',args.playwright_module)] if not value or not Path(value).is_file()]
 server=None;thread=None
 try:
  if missing:
   results.extend({'name':name,'status':'blocked','reason':'Existing tools missing: '+', '.join(missing)} for name in checks)
  else:
   for filename in ['before.html','after.html']:
    command=[sys.executable,str(SCRIPTS/'production/h5.py'),'build','--case',str(case_path),'--out',str(out/filename)]
    built=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
    (out/(filename+'.build.log')).write_text(built.stdout+built.stderr)
    if built.returncode:raise RuntimeError('Generated-artifact build failed; inspect '+filename+'.build.log')
   server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(out)));thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start();base_url=f'http://127.0.0.1:{server.server_address[1]}/'
   report['serverPort']=server.server_address[1]
   env={**os.environ,'INTERIOR_REAL_PLAYWRIGHT_MODULE':str(Path(args.playwright_module).resolve()),'INTERIOR_PLAYWRIGHT_MODULE':str(SCRIPTS/'browser_suite_playwright.mjs'),'INTERIOR_BROWSER':str(Path(args.browser).resolve())}
   for name in checks:
    applies,reason=prerequisite(case,REGISTRY[name][1])
    result=run_one(name,base_url,out,env,args.node,args.timeout) if applies else {'name':name,'status':'not_applicable','reason':reason}
    results.append(result);print(json.dumps(result,ensure_ascii=False),flush=True)
 except Exception as error:results.append({'name':'suite','status':'blocked','reason':str(error)})
 finally:
  if server:server.shutdown();server.server_close();thread.join(timeout=5)
  report['serverStopped']=True
  report['caseUnchanged']=case_hash==hashlib.sha256(case_path.read_bytes()).hexdigest()
  if not report['caseUnchanged']:results.append({'name':'case-preservation','status':'fail','reason':'Input case changed'})
  report['status']=suite_status(results)
  report['notApplicable']=[r['name'] for r in results if r['status']=='not_applicable']
  (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'status':report['status'],'report':str(out/'result.json'),'serverStopped':True},ensure_ascii=False))
 return 0 if report['status']=='pass' else 2

if __name__=='__main__':raise SystemExit(main())
