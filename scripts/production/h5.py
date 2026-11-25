"""H5 entrypoint. No installations or automatic approval. Remote rendering/processing is explicit opt-in.

Build/export/prepare/capture/audit/run/package use one case and its actual meshes.
An existing case is required; templates never imply an approved floorplan.
"""
import argparse, array, hashlib, html, json, math, os, shutil, subprocess, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ASSETS = ROOT / 'assets/h5'
TOUR_EXPOSURE = 1.2  # tone-mapping exposure of the tour renderer (user decision 2026-11-17: light from the fixtures, not from raising exposure)
TOUR_FIXTURE_GAIN = 20  # exported fixture intensity 1 is ~1 candela and lights nothing; the tour runtime lights rooms with 20 (user decision 2026-11-17)
TOUR_AMBIENT = {'hemisphere': .9, 'ambient': .2}  # less flat fill, so fixtures give the light its shape
import quality
from lighting_checks import lighting_report
from floor_connection_checks import check_floor_connections

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def read_snapshot(path):
    data = Path(path).read_bytes()
    return json.loads(data), hashlib.sha256(data).hexdigest()

def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def dump(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.partial')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temp.replace(path)

def fresh(path):
    path = Path(path).resolve()
    if path.exists() and (not path.is_dir() or any(path.iterdir())):
        raise ValueError('Use a new empty output directory; existing results are preserved.')
    path.mkdir(parents=True, exist_ok=True)
    return path

def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def points(poly, name):
    if not isinstance(poly, list) or len(poly) < 3 or any(not isinstance(p, list) or len(p)!=2 or not all(map(finite,p)) for p in poly):
        raise ValueError(name + ': expected polygon of finite millimetre coordinates')
    signed=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))
    if abs(signed)<1: raise ValueError(name + ': zero area')

def validate_case(case):
    if case.get('schema') != 'floor-visualization-case/1.0': raise ValueError('Unsupported case schema')
    if not isinstance(case.get('caseId'),str) or not case['caseId'].strip(): raise ValueError('caseId is required')
    m=case['model']; s=case['initialState']
    veins=case.get('presentation',{}).get('materials',{}).get('marble',{}).get('veins',True)
    if not isinstance(veins,bool): raise ValueError('Marble veins must be boolean')
    for key in ('width','depth','height'):
        if not finite(m.get(key)) or m[key]<=0: raise ValueError('Positive model '+key+' is required')
    points(m['footprint'],'footprint'); ids=set()
    if not m['rooms']: raise ValueError('Provide reviewed rooms; the blank template is intentionally not executable')
    for r in m['rooms']:
        if not isinstance(r.get('id'),str) or r['id'] in ids: raise ValueError('Unique room IDs are required')
        ids.add(r['id']); points(r['poly'],'room '+r['id'])
        if not isinstance(r.get('at'),list) or len(r['at'])!=2 or not all(map(finite,r['at'])): raise ValueError('Explicit room label point at:[x,y] is required')
    if set(s['rooms']) != ids: raise ValueError('model.rooms and initialState.rooms must correspond')
    connection_ids=set()
    for c in m.get('floorConnections',[]):
        if not isinstance(c.get('id'),str) or c['id'] in connection_ids or c['id'] in ids: raise ValueError('Unique floor connection IDs are required')
        connection_ids.add(c['id']); points(c['poly'],'floor connection '+c['id'])
        if c.get('materialRoomId') not in ids: raise ValueError('Floor connection requires an existing material room')
    if s.get('caseId') != case['caseId']: raise ValueError('State and case IDs must match')
    wall_ids=set(); opening_ids=set()
    for w in s['walls']:
        if not isinstance(w.get('id'),str) or w['id'] in wall_ids: raise ValueError('Unique wall IDs are required')
        wall_ids.add(w['id'])
        for k in ('a','b'):
            if not isinstance(w[k],list) or len(w[k])!=2 or not all(map(finite,w[k])): raise ValueError('Invalid wall point')
        length=math.dist(w['a'],w['b'])
        if length<1 or not finite(w['t']) or not 60<=w['t']<=500 or w['height']!=m['height']: raise ValueError('Wall length, thickness or height is invalid')
        if abs(w['a'][0]-w['b'][0])>1 and abs(w['a'][1]-w['b'][1])>1: raise ValueError('Current workbench supports orthogonal walls; diagonal geometry is not supported')
        previous=0
        for i,o in enumerate(sorted(w.get('opens',[]),key=lambda o:o['at'])):
            if o['kind'] not in ('door','sliding','window') or not all(map(finite,(o['at'],o['width']))) or o['at']<previous-.1 or o['width']<=0 or o['at']+o['width']>length+.1: raise ValueError('Invalid or overlapping opening in '+w['id'])
            previous=o['at']+o['width']; opening_ids.add(o.get('id',w['id']))
    if not set(case.get('entranceOpenings',[])).issubset(wall_ids|opening_ids): raise ValueError('Unknown entrance opening ID')
    check_floor_connections(m,s['walls'])
    furniture_ids=set();known_types=set(read(ASSETS/'component-types.json')['types'])
    for f in s['furniture']:
        if f.get('type') not in known_types: raise ValueError('Unsupported furniture type: '+str(f.get('type')))
        if not isinstance(f.get('id'),str) or f['id'] in furniture_ids: raise ValueError('Unique furniture IDs are required')
        furniture_ids.add(f['id'])
        if any(not finite(f.get(k)) for k in ('cx','cy','w','d','h','rot')) or min(f['w'],f['d'],f['h'])<=0: raise ValueError('Invalid furniture dimensions: '+f['id'])
        if 'lightOn' in f and not isinstance(f['lightOn'],bool): raise ValueError('Invalid fixture enabled state: '+f['id'])
        if 'lightIntensity' in f and (not finite(f['lightIntensity']) or not 0<=f['lightIntensity']<=50): raise ValueError('Invalid fixture intensity: '+f['id'])
        if f.get('type')=='bathtub':
            from bathtub_body import ensure_body
            ensure_body(f)
        if f.get('type')=='vanity':
            from vanity_basin import ensure_layout
            ensure_layout(f)
        if f.get('showerDoor'):
            from shower_door import shower_geometry
            f['showerDoor'].setdefault('width',f['w']-40)
            shower_geometry(f)
        e=f.get('elevation',0)
        if not finite(e) or e<0 or e+f['h']>m['height']+.1: raise ValueError('Furniture exceeds model height: '+f['id'])
    for c in s.get('ceilings',[]):
        if c['roomId'] not in ids or c.get('mode') not in ('flat','perimeter') or not finite(c.get('drop')) or not 0<=c['drop']<=min(300,m['height']): raise ValueError('Invalid ceiling')
        if c.get('poly'): points(c['poly'],'ceiling')
    for key,values in case.get('dimensionChains',{}).items():
        bound=m['width' if key in ('top','bottom') else 'depth']
        start=case.get('dimensionChainStarts',{}).get(key,0)
        if not finite(start) or start<0 or not values or not all(finite(v) and v>0 for v in values) or abs(sum(values)+start-bound)>.1: raise ValueError('Dimension chain and its start offset do not sum to model '+key)
    if 'costSettings' in s: raise ValueError('Remove pricing from the case input')
    return case

def build(case_path,out_path):
    from room_light_placement import apply_room_light_defaults
    from floor_boundaries import normalize_floor_boundaries
    raw,input_sha=read_snapshot(case_path);out=Path(out_path).resolve()
    if out.exists(): raise ValueError('Output HTML already exists; use a new revision filename')
    try: normalized,floor_boundary=normalize_floor_boundaries(raw)
    except ValueError as error:
        dump(out.with_suffix('.floors.json'),getattr(error,'report',{'status':'failed','error':str(error)}))
        raise
    dump(out.with_suffix('.floors.json'),floor_boundary)
    case=validate_case(apply_room_light_defaults(normalized))
    from door_checks import audit_source_doors
    from door_operation_review import review_doors
    door_operation = review_doors(case)
    dump(out.with_suffix('.doors.json'),door_operation)
    if case.get('doorLayoutPolicy',{}).get('required') and (door_operation['status']!='pass' or door_operation['pathStatus']!='checked'):
        raise ValueError('Door operation review failed; inspect '+str(out.with_suffix('.doors.json')))
    from desk_placement import review_desks
    desk_review=review_desks(case)
    dump(out.with_suffix('.desks.json'),desk_review)
    if case.get('deskPlacementPolicy',{}).get('required') and desk_review['status']!='pass':
        raise ValueError('Desk entry approach review failed; inspect '+str(out.with_suffix('.desks.json')))
    from facility_use_review import review_facilities
    facility_use = review_facilities(case)
    dump(out.with_suffix('.facilities.json'),facility_use)
    if case.get('facilityUsePolicy',{}).get('required') and facility_use['status']!='pass':
        raise ValueError('Facility use review failed; inspect '+str(out.with_suffix('.facilities.json')))
    door_review = audit_source_doors(case['initialState'], case['doorSourceReview'], Path(case_path).resolve().parent) if 'doorSourceReview' in case else {'status':'not_provided','scope':'Legacy input; source door leaf counts not verified'}
    layout_review = {'status':'not_provided','scope':'Legacy build; layout reasonableness/group/intent not verified'}
    if 'layoutReview' in case:
        sys.path.insert(0,str(HERE.parent))
        from layout_review import artifact, review
        review_path=artifact(case['layoutReview'],Path(case_path).resolve().parent)
        layout_review=review(case,read(review_path),review_path.parent)
    from engine_provenance import require_current_engine
    engine_provenance = require_current_engine(ROOT)
    template_bytes=(ASSETS/'template.html').read_bytes()
    template=template_bytes.decode('utf-8')
    version=read(ASSETS/'version.json')['version']
    payload=json.dumps(case,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    engine_bytes=(ASSETS/'engine.js').read_bytes()
    if hashlib.sha256(engine_bytes).hexdigest()!=engine_provenance['engineSha256']:
        raise ValueError('H5 engine changed during generation; rebuild and retry')
    engine=engine_bytes.decode('utf-8').replace('</script','<\\/script')
    # Embedded PNG references are optional. No machine paths are copied into output HTML.
    import base64
    for token,key in [('__PLAN_REFERENCE__','plan'),('__FURNITURE_REFERENCE__','furniture')]:
        ref=case.get('references',{}).get(key)
        data=base64.b64encode((Path(case_path).resolve().parent/ref).read_bytes()).decode() if ref else ''
        template=template.replace(token,data)
    for token,value in [('__WORKBENCH_VERSION__',version),('__CASE_JSON__',payload),('__WALL_HEIGHT_M__',str(case['model']['height']/1000)),('__REFERENCE_NOTE__',html.escape(case.get('referenceNote','参考图用于校核；未标尺寸为设计初值。'))),('__BUNDLE__',engine)]:
        template=template.replace(token,value)
    if '__CASE_JSON__' in template or '__BUNDLE__' in template: raise ValueError('Unresolved template marker')
    if require_current_engine(ROOT)!=engine_provenance or sha(case_path)!=input_sha:
        raise ValueError('H5 engine or case input changed during generation; retry from a stable snapshot')
    out.parent.mkdir(parents=True,exist_ok=True)
    # Preserve embedded engine bytes on hosts whose text writer translates LF.
    out.write_bytes(template.encode('utf-8'))
    dump(out.with_suffix('.build.json'),{'caseId':case['caseId'],'caseSha256':input_sha,'engineSha256':hashlib.sha256(engine_bytes).hexdigest(),'htmlSha256':sha(out),'engineProvenance':engine_provenance,'status':'built','humanAcceptance':'not inferred from build','sourceSchemeSha256':case.get('sourceSchemeSha256'),'validation':'input contract only; no visual or cross-floorplan regression','workbenchVersion':version,'templateSha256':hashlib.sha256(template_bytes).hexdigest(),'lightingCheck':lighting_report(case),'floorBoundaryCheck':floor_boundary,'doorSourceCheck':door_review,'doorOperationCheck':door_operation,'facilityUseCheck':facility_use,'layoutReviewCheck':layout_review})
    return out

def validate_bundle(bundle,preview=False):
    if bundle.get('schema')!='floor-visualization-production/1.0': raise ValueError('Unsupported production bundle schema')
    if not isinstance(bundle.get('schemeSha256'),str) or len(bundle['schemeSha256'])!=64: raise ValueError('Missing scheme hash')
    if 'costSettings' in bundle['state']: raise ValueError('Pricing is excluded from production')
    cs=bundle.get('confirmations',{})
    if not preview and (set(cs)!=set(('structure','layout','style')) or any(v.get('status')!='confirmed' for v in cs.values())): raise ValueError('Current structure/layout/style confirmation is required; --preview permits explicitly unaccepted preflight only')
    if not bundle.get('scene',{}).get('meshes'): raise ValueError('Export actual meshes before rendering')
    if bundle.get('dimensionAudit',{}).get('errors'): raise ValueError('Exported model dimension audit failed')

def prepare(bundle_path,out_path,preview=False,size=(1280,720),exposure=TOUR_EXPOSURE,fixture_gain=TOUR_FIXTURE_GAIN):
    if isinstance(exposure,bool) or not isinstance(exposure,(int,float)) or not .5<=exposure<=3:raise ValueError('exposure must be between 0.5 and 3')
    b=read(bundle_path);validate_bundle(b,preview); out=fresh(out_path)
    scene=b['scene']; meta={k:v for k,v in scene.items() if k!='meshes'};meshes=[];offset=0
    with (out/'geometry.bin').open('wb') as stream:
        for m in scene['meshes']:
            n={k:v for k,v in m.items() if k not in ('positions','normals','uv','indices')}
            for key in ('positions','normals','uv','indices'):
                values=m.get(key)
                if values is None:n[key]=None;continue
                data=array.array('I' if key=='indices' else 'f',values)
                if data.itemsize!=4: raise ValueError('Runtime requires 32-bit array items')
                if sys.byteorder!='little': data.byteswap()
                raw=data.tobytes();stream.write(raw);n[key]={'offset':offset,'count':len(values)};offset+=len(raw)
            meshes.append(n)
    if isinstance(fixture_gain,bool) or not isinstance(fixture_gain,(int,float)) or not 1<=fixture_gain<=50:raise ValueError('fixture gain must be between 1 and 50')
    meta['illumination']=[{**l,'intensity':min(50.,l['intensity']*fixture_gain)} for l in meta.get('illumination',[])]
    meta.update(meshes=meshes,schemeSha256=b['schemeSha256'],model=b['model'],state=b['state'],finishes=b['finishes'],presentationProfile=b.get('presentationProfile',{'hiddenTypes':[]}),renderSettings={'size':list(size),'exposure':exposure,'shiftY':0,'bodyRadiusMm':160,'lighting':dict(TOUR_AMBIENT)},previewOnly=preview)
    dump(out/'scene.json',meta)
    for filename in ('renderer.html','three.module.js','three.core.js','THREE-LICENSE.txt'):
        shutil.copy2(ASSETS/'runtime'/filename,out/filename)
    dump(out/'prepare.json',{'bundleSha256':sha(bundle_path),'schemeSha256':b['schemeSha256'],'meshCount':len(meshes),'geometryBytes':offset,'runtimeHashes':{f.name:sha(f) for f in out.iterdir() if f.is_file()},'humanAcceptance':'pending','previewOnly':preview})
    return out

def node_call(command,args):
    node=getattr(args,'node',None) or os.environ.get('FLOOR_VIS_NODE') or shutil.which('node')
    if not node: raise ValueError('Existing Node.js required; pass --node')
    cmd=[node,str(HERE/'h5_browser.mjs'),command]
    for key in ('html','runtime','out','tour','views','subjects','playwright_module','browser','preview_review','route_review','review_release'):
        value=getattr(args,key,None)
        if value:cmd+=['--'+key.replace('_','-'),str(Path(value).resolve())]
    if getattr(args,'preview',False):cmd+=['--preview']
    if getattr(args,'full',False):cmd+=['--full']
    if getattr(args,'resume',False):cmd+=['--resume']
    if getattr(args,'range',None):cmd+=['--range',args.range]
    subprocess.run(cmd,check=True)

def package(directory,archive,review_result=None):
    directory=Path(directory).resolve();archive=Path(archive).resolve()
    if archive.exists() or archive.is_relative_to(directory): raise ValueError('Archive must be new and outside the package folder')
    files=[p for p in directory.rglob('*') if p.is_file() and not any(v in p.parts for v in ('.git','node_modules','__pycache__')) and not p.name.endswith(('.partial','.pyc')) and p.name!='.DS_Store']
    if any(p.is_symlink() for p in directory.rglob('*')):raise ValueError('Symlinks are not packaged; provide copied local files')
    manifest={'schema':'floor-visualization-package/1.0','files':[{'path':p.relative_to(directory).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files if p.name!='package-manifest.json'],'acceptance':'file manifest only; not human or visual acceptance'}
    if review_result:manifest.update(qualityReview=review_result,acceptance='Only the hash-bound reviewed output scopes are accepted; supporting files are not separately approved')
    dump(directory/'package-manifest.json',manifest)
    archive.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files:
            if p.name!='package-manifest.json':z.write(p,p.relative_to(directory).as_posix())
        z.write(directory/'package-manifest.json','package-manifest.json')
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise ValueError('Archive integrity failure')
    dump(archive.with_suffix('.zip.json'),{'archiveSha256':sha(archive),'files':len(manifest['files']),'bytes':archive.stat().st_size})
    return archive

def handoff(directory, manifest_path=None, title='Interior Design', accepted=None):
    """Make a relocatable preview index without promoting artifacts to accepted."""
    from urllib.parse import quote
    directory=Path(directory).resolve();target=directory/'index.html'
    if target.exists():raise ValueError('A handoff index already exists; preserve it or use a new folder')
    if manifest_path:
        manifest=read(manifest_path);items=manifest['items']
    else:
        items=[]
        for p in sorted(directory.rglob('*')):
            if not p.is_file() or p.suffix.lower() not in ('.html','.svg','.png','.mp4','.json','.md'):continue
            rel=p.relative_to(directory).as_posix()
            if 'runtime/' in rel or 'frames/' in rel or p.name=='production-bundle.json':continue
            items.append({'path':rel,'title':p.stem,'accepted':False})
        manifest={'schema':'floor-visualization-handoff/1.0','title':title,'items':items,'humanAcceptance':'pending'}
    manifest['humanAcceptance']='accepted for the hash-bound reviewed outputs' if accepted else 'pending'
    cards=[]
    for item in items:
        p=(directory/item['path']).resolve()
        if not p.is_relative_to(directory) or not p.is_file():raise ValueError('Missing or nonlocal handoff artifact: '+item['path'])
        is_accepted=bool(accepted and accepted.get(p)==sha(p))
        if accepted and not is_accepted:raise ValueError('Unreviewed artifact in accepted handoff: '+item['path'])
        item['accepted']=is_accepted
        href=quote(p.relative_to(directory).as_posix());label=html.escape(item.get('title',p.stem));status='已确认' if is_accepted else '待查看'
        media=f'<img src="{href}" alt="{label}" loading="lazy">' if p.suffix.lower() in ('.png','.svg','.jpg','.jpeg') else f'<video src="{href}" controls preload="metadata"></video>' if p.suffix.lower()=='.mp4' else ''
        cards.append(f'<article><a href="{href}">{label}</a><small>{status}</small>{media}</article>')
    title=html.escape(manifest.get('title',title))
    target.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>body{margin:0;background:#f5f3ee;color:#37332d;font:15px/1.6 system-ui,sans-serif}header,main{max-width:1200px;margin:auto;padding:24px}h1{font-size:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}article{background:white;border:1px solid #e4dfd6;border-radius:10px;padding:16px}a{color:#806040}small{display:block;color:#777}img,video{display:block;width:100%;max-height:450px;object-fit:contain;margin-top:12px}</style><header><h1>'+title+'</h1><p>新生成的内容须查看后确认。文件完整性检查不代表视觉验收。</p></header><main>'+''.join(cards)+'</main></html>',encoding='utf-8')
    dump(directory/'handoff.json',manifest)
    return target

def require_capture_review(args):
    if getattr(args,'review_release',None):
        if getattr(args,'command','capture')!='capture' or not getattr(args,'tour',None):
            raise ValueError('--review-release is only valid for a tour review capture')
        # The Python and direct browser entries share the same validator.
        node_call('check-review-release',args)
        return
    if not getattr(args,'tour',None):return
    from route_rehearsal import require_route
    route=require_route(getattr(args,'route_review',None),args.tour,args.runtime)
    if not getattr(args,'full',False):return
    scene=read(Path(args.runtime)/'scene.json');w,h=scene.get('renderSettings',{}).get('size',[1280,720])
    if not getattr(args,'preview',False) or w>1280 or h>720:
        from tour_workflow import require_preview
        reviewed=require_preview(getattr(args,'preview_review',None),args.tour,args.runtime)
        review_path=Path(args.preview_review);manifest=read(route['rehearsal']['path'])
        config=read(manifest['references']['config']['path'])
        audit_path=Path(reviewed['artifacts']['subjectAudit']['path'])
        if not audit_path.is_absolute():audit_path=review_path.parent/audit_path
        from tour_camera_evidence import require_actual_targets
        require_actual_targets(config,read(args.tour),read(audit_path),read(manifest['references']['bundle']['path']))

def parser():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    p=sub.add_parser('case-upgrade-check',help='Review legacy migration and case-bound demo media; no automatic edits or approval');p.add_argument('--case',required=True);p.add_argument('--source',required=True);p.add_argument('--build');p.add_argument('--media-manifest');p.add_argument('--scheme-sha256');p.add_argument('--out',required=True)
    p=sub.add_parser('remote-production',help='Frozen SSH/Windows task; no installs or service changes');p.add_argument('--action',required=True,choices=('prepare','start','status','resume','collect'));p.add_argument('--job');p.add_argument('--out',required=True)
    p=sub.add_parser('video-upscale',help='Explicit short enlargement comparison, no diffusion or full film');p.add_argument('--job',required=True);p.add_argument('--out',required=True);p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True);p.add_argument('--comfy')
    p=sub.add_parser('video-upscale-pages',help='Shared auxiliary enlargement comparison page');p.add_argument('--result',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('video-quality',help='Global/local temporal diagnostics, not acceptance');p.add_argument('--job',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('delivery-check',help='Read-only final picture/audio/playback/version checks');p.add_argument('--job',required=True);p.add_argument('--out',required=True);p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True)
    p=sub.add_parser('doctor',help='Read-only dependency availability; never installs or runs a regression suite');p.add_argument('--for',dest='feature',choices=['basic','video','blender','remote','quality','delivery'],default='basic');p.add_argument('--blender');p.add_argument('--ffmpeg');p.add_argument('--ffprobe');p.add_argument('--node');p.add_argument('--browser');p.add_argument('--playwright-module')
    p=sub.add_parser('blender-review-film',help='Explicitly authorized complete silent review film from validated exact route');p.add_argument('--job',required=True);p.add_argument('--out',required=True);p.add_argument('--blender',required=True);p.add_argument('--ffmpeg',required=True)
    p=sub.add_parser('blender-draft',help='Bounded exact-route dynamic sample, never full animation');p.add_argument('--job',required=True);p.add_argument('--out',required=True);p.add_argument('--blender',required=True);p.add_argument('--ffmpeg',required=True)
    p=sub.add_parser('render-prepare',help='Prepare shared standard/Blender branch from an approved exact route; no video');p.add_argument('--job',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('tour-pages',help='Generate four-stage tour pages from a bound rehearsal; never captures video');p.add_argument('--rehearsal',required=True);p.add_argument('--job',help='Optional bound preview/decorated video/narration JSON');p.add_argument('--out',required=True);p.add_argument('--ffprobe',help='Existing ffprobe for supplied video verification')
    p=sub.add_parser('decoration-plan',help='Prepare exact-frame image tasks; does not call image or remote services');p.add_argument('--job',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('decoration-check',help='Check source, frame bindings and image review evidence');p.add_argument('--plan',required=True)
    p=sub.add_parser('decoration-render',help='Explicit remote ComfyUI opt-in; no installation or narration');p.add_argument('--plan',required=True);p.add_argument('--remote',required=True);p.add_argument('--client-module',required=True);p.add_argument('--ffmpeg',required=True);p.add_argument('--segment',action='append')
    p=sub.add_parser('decoration-assemble',help='Assemble checked segment timelines into a silent pending-review video');p.add_argument('--plan',required=True);p.add_argument('--out',required=True);p.add_argument('--ffmpeg',required=True);p.add_argument('--ffprobe',required=True)
    for name in ('narration-prepare','narration-compose'):
        p=sub.add_parser(name,help='Requires explicit approval of exact source video before narration work');p.add_argument('--job',required=True);p.add_argument('--out',required=True);p.add_argument('--ffmpeg')
    p=sub.add_parser('plan-route',help='Stage 1: rooms, openings, ordered path and returns; no cameras, frames or approval');p.add_argument('--job',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('record-approval',help="Write the camera rehearsal, exact-video or narrated-film (--pending = composition-report.json) approval from the user's verbatim words; refuses agent names, empty evidence and unfinished rehearsals");p.add_argument('--kind',required=True,choices=('camera','video','narrated'));p.add_argument('--pending',required=True);p.add_argument('--confirmed-by',required=True);p.add_argument('--evidence',required=True);p.add_argument('--out',required=True);p.add_argument('--review-only',action='store_true',help='camera only: confirm a rehearsal that fails just the screen audit, for a low-resolution review video; never production')
    p=sub.add_parser('tour-draft',help='Seconds-long camera draft with diagnostics; never for confirmation');p.add_argument('--bundle',required=True);p.add_argument('--brief',required=True);p.add_argument('--out',required=True);p.add_argument('--runtime');p.add_argument('--node')
    p=sub.add_parser('validate-corpus',help='Run route, brief and camera draft for every case in a manifest and compare with recorded baselines');p.add_argument('--manifest',required=True);p.add_argument('--out',required=True);p.add_argument('--only',action='append')
    p=sub.add_parser('optimize-stations',help='Choose observation stations by exported-mesh audit inside the approved route tolerance; verifies and undoes moves that add turn failures');p.add_argument('--brief',required=True);p.add_argument('--plan',required=True);p.add_argument('--runtime',required=True);p.add_argument('--out',required=True);p.add_argument('--node');p.add_argument('--no-verify',action='store_true')
    p=sub.add_parser('brief-from-route',help='Camera brief from an approved spatial route, with an assumptions list; no cameras, no approval');p.add_argument('--plan',required=True);p.add_argument('--out',required=True);p.add_argument('--maximum-seconds',type=float);p.add_argument('--coverage-minimum-percent',type=float);p.add_argument('--coverage-off',action='store_true');p.add_argument('--camera-options',choices=('tuned','basic'),default='tuned');p.add_argument('--eye-mm',type=float,default=1300);p.add_argument('--eye-reason');p.add_argument('--fov',type=float,default=76);p.add_argument('--overrides')
    p=sub.add_parser('record-route-approval',help="Write the route approval from the user's verbatim words; refuses agent names and empty evidence");p.add_argument('--pending',required=True);p.add_argument('--confirmed-by',required=True);p.add_argument('--evidence',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('tour-stage-status',help='Read-only four-stage status from actual bound files; never grants approval');p.add_argument('--job',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('plan-tour',help='Stage 2 from an approved route: joint camera candidates, bounded repairs and rehearsal; never video');p.add_argument('--job',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('design-tour',help='Lower-level camera design from an approved route; no video');p.add_argument('--bundle',required=True);p.add_argument('--brief',required=True);p.add_argument('--out',required=True);p.add_argument('--spatial-plan');p.add_argument('--spatial-review')
    p=sub.add_parser('build',help='Case JSON -> offline single-file workbench');p.add_argument('--case',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('prepare',help='Actual mesh bundle -> H5 renderer runtime');p.add_argument('--bundle',required=True);p.add_argument('--out',required=True);p.add_argument('--preview',action='store_true');p.add_argument('--width',type=int,default=1280);p.add_argument('--height',type=int,default=720);p.add_argument('--exposure',type=float,default=TOUR_EXPOSURE);p.add_argument('--fixture-gain',type=float,default=TOUR_FIXTURE_GAIN)
    p=sub.add_parser('quality',help='Verify source/image/tour review records without granting approval');p.add_argument('--bundle',required=True);p.add_argument('--review',required=True);p.add_argument('--stage',action='append',choices=quality.STAGES);p.add_argument('--out',required=True);p.add_argument('--accepted',action='store_true')
    p=sub.add_parser('review-template',help='Case-local review skeleton with pending provenance/acceptance');p.add_argument('--bundle',required=True);p.add_argument('--out',required=True)
    for command in ('export','capture','audit','run'):
        p=sub.add_parser(command);p.add_argument('--out',required=True)
        p.add_argument('--route-review',help='User approval bound to displayed timed route animation; required for every tour capture, including low-resolution previews and ranges');p.add_argument('--node');p.add_argument('--playwright-module');p.add_argument('--browser');p.add_argument('--preview',action='store_true');p.add_argument('--preview-review',help='Hash-bound dynamic preview review required before full production/HD capture')
        if command=='capture':p.add_argument('--review-release',help='Explicit hash-bound authorization for an unaccepted low-resolution review video; cannot authorize production')
        if command=='export':p.add_argument('--html',required=True)
        elif command in ('capture','audit'):
            p.add_argument('--runtime',required=True);p.add_argument('--tour');p.add_argument('--views');p.add_argument('--subjects');p.add_argument('--full',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--range',help='Frame range start:end, end exclusive')
        else:
            p.add_argument('--bundle',required=True);p.add_argument('--config');p.add_argument('--tour');p.add_argument('--views');p.add_argument('--subjects');p.add_argument('--quality-review');p.add_argument('--animation',action='store_true');p.add_argument('--ffmpeg');p.add_argument('--ffprobe')
    p=sub.add_parser('package',help='Relocatable folder -> SHA-256 manifest + ZIP');p.add_argument('--directory',required=True);p.add_argument('--archive',required=True)
    p=sub.add_parser('handoff',help='Local assets -> relocatable preview index');p.add_argument('--directory',required=True);p.add_argument('--manifest');p.add_argument('--title',default='Interior Design')
    for command in ('package','handoff'):
        p=sub.choices[command];p.add_argument('--accepted',action='store_true');p.add_argument('--quality-review');p.add_argument('--bundle')
    return ap

def main():
    args=parser().parse_args()
    if args.command=='doctor':
        runtime={'python':sys.version.split()[0],'node':os.environ.get('FLOOR_VIS_NODE') or shutil.which('node'),'browserOverride':os.environ.get('FLOOR_VIS_BROWSER'),'playwrightModuleOverride':os.environ.get('FLOOR_VIS_PLAYWRIGHT'),'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),'blenderOptional':shutil.which('blender'),'bundledEngine':(ASSETS/'engine.js').exists(),'bundledRenderer':(ASSETS/'runtime/renderer.html').exists(),'installsPerformed':False,'regressionExecuted':False}
        from runtime_requirements import inspect as inspect_runtime
        runtime['selectedFeature']=inspect_runtime(args.feature,vars(args))
        print(json.dumps(runtime,ensure_ascii=False,indent=2))
        if runtime['selectedFeature']['status']!='pass':raise SystemExit(1)
        return
    elif args.command=='case-upgrade-check':
        from case_upgrade import inspect
        target=Path(args.out)
        if target.exists():raise ValueError('Use a new review report path')
        result=inspect(args.case,args.source,args.build,args.media_manifest,args.scheme_sha256);dump(target,result);print(json.dumps(result,ensure_ascii=False,indent=2))
        if result['status']=='blocked':raise SystemExit(2)
        return
    elif args.command=='build': result=build(args.case,args.out)
    elif args.command=='remote-production':
        import remote_production as remote
        if args.action=='prepare':
            if not args.job:raise ValueError('--job required for prepare')
            result=remote.prepare(read(args.job),Path(args.job).resolve().parent,args.out)
        elif args.action in ('start','resume'):result=remote.start(args.out,resume=args.action=='resume')
        else:result=getattr(remote,args.action)(args.out)
        print(json.dumps(result,ensure_ascii=False,indent=2));return
    elif args.command=='video-upscale':
        from video_upscale import execute
        result=execute(read(args.job),Path(args.job).resolve().parent,args.out,args.ffmpeg,args.ffprobe,args.comfy)
    elif args.command=='video-upscale-pages':
        from video_upscale import page
        result=page(read(args.result),Path(args.result).resolve().parent,args.out)
    elif args.command=='video-quality':
        from tour_media_quality import inspect
        result=inspect(read(args.job),Path(args.job).resolve().parent,args.out)
    elif args.command=='delivery-check':
        from tour_delivery import inspect
        result=inspect(read(args.job),Path(args.job).resolve().parent,args.out,args.ffmpeg,args.ffprobe)
    elif args.command=='review-template':
        out=fresh(args.out);dump(out/'quality-review.json',quality.template(read(args.bundle)));result=out
    elif args.command=='quality':
        out=fresh(args.out);report=quality.evaluate(args.review,read(args.bundle),args.stage)
        dump(out/'quality.json',report)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if report['status']=='failed' or (args.accepted and not report['readyForAcceptedDelivery']):raise ValueError('Quality gate blocked; inspect '+str(out/'quality.json'))
        result=out
    elif args.command=='blender-review-film':
        from blender_review_film import run as run_film
        result=run_film(read(args.job),Path(args.job).resolve().parent,args.out,args.blender,args.ffmpeg)
    elif args.command=='blender-draft':
        from blender_draft import run as run_draft
        result=run_draft(read(args.job),Path(args.job).resolve().parent,args.out,args.blender,args.ffmpeg)
    elif args.command=='render-prepare':
        from tour_render import prepare as prepare_render
        result=prepare_render(read(args.job),Path(args.job).resolve().parent,args.out)
    elif args.command=='tour-pages':
        from tour_pages import build as build_pages
        job=read(args.job) if args.job else {}
        build_pages(args.rehearsal,args.out,job,Path(args.job).resolve().parent if args.job else None,args.ffprobe)
        result=args.out
    elif args.command.startswith('decoration-'):
        import tour_decorated as decorated
        if args.command=='decoration-plan':result=decorated.prepare(decorated.read(args.job),args.out)
        elif args.command=='decoration-check':
            plan=decorated.read(args.plan);decorated.validate_plan(plan)
            for segment in plan['segments']:
                if segment['id'] in plan.get('frozenSegments',{}):decorated.assembly_receipt(plan,segment,Path(args.plan).parent)
                else:decorated.ready(plan,segment)
            result={'status':'ready','segments':len(plan['segments']),'approvalGranted':False}
        elif args.command=='decoration-render':
            decorated.remote_render(args.plan,args.remote,args.client_module,args.ffmpeg,args.segment)
            result={'status':'segments_generated_pending_review','plan':args.plan,'approvalGranted':False}
        else:result=decorated.assemble(args.plan,args.out,args.ffmpeg,args.ffprobe)
    elif args.command in ('narration-prepare','narration-compose'):
        from tour_stage_gate import prepare as prepare_narration, compose as compose_narration
        job=read(args.job);base=Path(args.job).resolve().parent
        if args.command=='narration-prepare':prepare_narration(job,base,args.out)
        else:compose_narration(job,base,args.out,args.ffmpeg)
        result=args.out
    elif args.command=='plan-route':
        from tour_spatial_plan import run as run_route
        plan=run_route(read(args.job),Path(args.job).resolve().parent,args.out)
        print(json.dumps({'status':plan['status'],'distanceM':round(plan['distanceM'],3),'issues':plan['issues'],'output':str(args.out),'approvalGranted':False},ensure_ascii=False,indent=2))
        return
    elif args.command=='record-approval':
        import record_approval
        record=(record_approval.record_camera(args.pending,args.out,args.confirmed_by,args.evidence,review_only=args.review_only) if args.kind=='camera' else {'video':record_approval.record_video,'narrated':record_approval.record_narrated}[args.kind](args.pending,args.out,args.confirmed_by,args.evidence))
        print(json.dumps({'status':record['status'],'kind':args.kind,'output':str(args.out),'note':'Any change to the bound files invalidates it'},ensure_ascii=False));return
    elif args.command=='tour-draft':
        from tour_draft import draft as make_draft
        summary,_,_=make_draft(args.bundle,args.brief,args.out,args.runtime,args.node);print(json.dumps(summary,ensure_ascii=False,indent=2));return
    elif args.command=='validate-corpus':
        from validate_case import run_corpus
        if Path(args.out).exists():raise ValueError('Use a new output directory')
        rows=run_corpus(args.manifest,args.out,set(args.only) if args.only else None)
        for r in rows:print(r['id'],r['status'],r.get('failure') or '',[x['code'] for x in r.get('problems',[])])
        if any(r['status']=='regressed' for r in rows):raise SystemExit(1)
        return
    elif args.command=='optimize-stations':
        from optimize_stations import optimize as optimize_stations
        _,report=optimize_stations(args.brief,args.plan,args.runtime,args.out,args.node,verify=not args.no_verify)
        print(json.dumps({'moved':[r['name'] for r in report if r['moved']],'kept':[r['name'] for r in report if not r['moved']],'output':str(args.out)},ensure_ascii=False));return
    elif args.command=='brief-from-route':
        from brief_from_route import build as build_brief
        target=Path(args.out)
        if target.exists():raise ValueError('Use a new output directory')
        brief,notes=build_brief(args.plan,{'maximumSeconds':args.maximum_seconds,'coverageMinimumPercent':args.coverage_minimum_percent,'coverageOff':args.coverage_off,'cameraOptions':args.camera_options,'eyeMm':args.eye_mm,'eyeReason':args.eye_reason,'fovDegrees':args.fov,'overrides':read(args.overrides) if args.overrides else None})
        dump(target/'brief.json',brief);dump(target/'brief-assumptions.json',notes)
        print(json.dumps({'stations':len(brief['rooms']),'passThrough':[x['station'] for x in notes['passThrough']]+notes['routePassThrough'],'output':str(target)},ensure_ascii=False));return
    elif args.command=='record-route-approval':
        from record_approval import record_route
        record_route(args.pending,args.out,args.confirmed_by,args.evidence)
        print(json.dumps({'status':'approved','output':str(args.out),'note':'Bound to the plan, bundle and page hashes; any change invalidates it'},ensure_ascii=False));return
    elif args.command=='tour-stage-status':
        from tour_stage_chain import evaluate
        target=Path(args.out)
        if target.exists():raise ValueError('Use a new stage state path')
        state=evaluate(read(args.job),Path(args.job).resolve().parent);dump(target,state);print(json.dumps(state['stages'],ensure_ascii=False,indent=2))
        return
    elif args.command=='plan-tour':
        from tour_pipeline import run
        result=run(read(args.job),args.out)
        print(json.dumps(result,ensure_ascii=False,indent=2))
        if result.get('engineeringStatus')!='pass':raise ValueError('Engineering stage requires action; inspect closeout-report.json and contract-report.json. No capture performed.')
        return
    elif args.command=='design-tour':
        from tour_stage_chain import require_camera_entry
        require_camera_entry({'bundle':args.bundle,'spatialPlan':args.spatial_plan,'spatialReview':args.spatial_review})
        from design_homeowner_tour import design
        out=fresh(args.out);tour,config,report=design(read(args.bundle),read(args.brief))
        for name,value in [('tour.json',tour),('camera-config.json',config),('design-report.json',report)]:dump(out/name,value)
        if report['status']!='pending_user_review':raise ValueError('Tour design needs revision; see design-report.json; no capture performed')
        result=out
    elif args.command=='prepare':
        if args.width<320 or args.height<180 or args.width%2 or args.height%2:raise ValueError('Use even output dimensions >= 320 x 180')
        result=prepare(args.bundle,args.out,args.preview,(args.width,args.height),args.exposure,args.fixture_gain)
    elif args.command in ('package','handoff'):
        report=None;accepted=None
        if args.accepted:
            if not args.quality_review or not args.bundle:raise ValueError('Accepted delivery needs --quality-review and --bundle')
            b=read(args.bundle);validate_bundle(b)
            requested=read(args.quality_review).get('requiredStages',[])
            if 'source' not in requested:raise ValueError('Accepted delivery must include source calibration review')
            report=quality.require_ready(args.quality_review,b)
            accepted=quality.accepted_outputs(args.quality_review,requested)
            if not all(p.is_relative_to(Path(args.directory).resolve()) for p in accepted):raise ValueError('Accepted outputs must be copied into delivery and reviewed by their current paths')
        result=package(args.directory,args.archive,report) if args.command=='package' else handoff(args.directory,args.manifest,args.title,accepted)
    elif args.command=='run':
        out=fresh(args.out);b=read(args.bundle);validate_bundle(b,args.preview)
        if not args.preview:
            if not args.quality_review:raise ValueError('Production needs a current source calibration review; --preview remains unaccepted')
            quality.require_ready(args.quality_review,b,['source'])
            if args.animation and not args.subjects:raise ValueError('Production animation needs explicit subject time windows')
        shutil.copy2(args.bundle,out/'production-bundle.json');prepare(args.bundle,out/'runtime',args.preview)
        if args.tour:shutil.copy2(args.tour,out/'tour.json')
        elif args.config:
            shutil.copy2(args.config,out/'tour-config.json')
            subprocess.run([sys.executable,str(HERE/'plan_route.py'),'--bundle',str(out/'production-bundle.json'),'--config',str(out/'tour-config.json'),'--output',str(out/'tour.json')]+(['--preview'] if args.preview else []),check=True)
            cfg=read(args.config)
            if not cfg.get('cameraKeys'):raise ValueError('Camera keys required for shared homeowner method; route alone cannot produce a reviewed tour')
            from camera_gaze import generate, PROFILE
            from tour_workflow import retime, intent_check
            profile=read(PROFILE);tour=generate(read(out/'tour.json'),cfg,profile)
            tour=retime(tour,cfg,{**profile['reviewLimits'],**cfg.get('motionReviewLimits',{})})
            tour['chapterReview']=intent_check(tour,cfg)
            dump(out/'tour.json',tour)
            if cfg is not None:
                from tour_contract import inspect as inspect_contract
                contract_report=inspect_contract(b,tour,cfg);dump(out/'tour-contract-report.json',contract_report)
                if contract_report['issues']:raise ValueError('Tour contract failed before rendering; inspect tour-contract-report.json')
            if tour['cameraMethod']['thresholdFailures'] or tour['chapterReview']['failures']:raise ValueError('Motion/chapter review failed; inspect generated tour.json before rendering')
        elif args.animation:raise ValueError('Animation requires --tour or --config')
        args.runtime=str(out/'runtime');args.tour=str(out/'tour.json') if (out/'tour.json').exists() else None
        if not args.tour and not args.views:raise ValueError('Provide a tour or explicit views; cameras are not invented')
        if args.views:shutil.copy2(args.views,out/'views.json');args.views=str(out/'views.json')
        args.out=str(out/'audit');node_call('audit',args)
        args.out=str(out/'capture');args.full=args.animation;require_capture_review(args);node_call('capture',args)
        video=None
        if args.animation:
            ffmpeg=args.ffmpeg or shutil.which('ffmpeg');ffprobe=args.ffprobe or shutil.which('ffprobe')
            if not ffmpeg or not ffprobe:raise ValueError('Existing FFmpeg and ffprobe required; completed frames are retained')
            tour=read(out/'tour.json');video=out/'continuous-preflight.mp4'
            subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-framerate',str(tour['fps']),'-i',str(out/'capture/frames/frame-%06d.png'),'-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(video)],check=True)
            probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames,duration','-of','json',str(video)]))
            stream=probe['streams'][0]
            if int(stream['nb_read_frames'])!=len(tour['frames']) or abs(float(stream['duration'])-tour['seconds'])>.1:raise ValueError('Encoded duration/frame count mismatch')
            dump(out/'video-probe.json',probe)
            from tour_pages import for_encoded_video
            for_encoded_video(video,out/'tour.json',args.route_review,out/'tour-pages',ffprobe)
        audit=read(out/'audit/audit.json')
        dump(out/'run.json',{'schemeSha256':b['schemeSha256'],'engine':'h5','previewOnly':args.preview,'humanAcceptance':'pending for new artifacts','video':video.name if video else None,'subjectStatus':audit['subjectStatus'],'visualReview':'pending','acceptedDelivery':False,'Seedance':'not executed'})
        handoff(out)
        result=out
    else:
        if args.command=='capture':require_capture_review(args)
        node_call(args.command,args);result=args.out
    message={'command':args.command,'output':str(result)}
    if args.command=='build':
        evidence=read(Path(result).with_suffix('.build.json'));message.update(workbenchVersion=evidence['workbenchVersion'],lightingWarnings=evidence['lightingCheck']['warnings'],buildMetadata=str(Path(result).with_suffix('.build.json')))
    print(json.dumps(message,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as e:raise SystemExit(str(e))
