"""Local H5 entrypoint. No installations, external services or automatic approval.

Build/export/prepare/capture/audit/run/package use one case and its actual meshes.
An existing case is required; templates never imply an approved floorplan.
"""
import argparse, array, hashlib, html, json, math, os, shutil, subprocess, sys, zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
ASSETS = ROOT / 'assets/h5'
import quality
from lighting_checks import lighting_report

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

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
    furniture_ids=set();known_types=set(read(ASSETS/'component-types.json')['types'])
    for f in s['furniture']:
        if f.get('type') not in known_types: raise ValueError('Unsupported furniture type: '+str(f.get('type')))
        if not isinstance(f.get('id'),str) or f['id'] in furniture_ids: raise ValueError('Unique furniture IDs are required')
        furniture_ids.add(f['id'])
        if any(not finite(f.get(k)) for k in ('cx','cy','w','d','h','rot')) or min(f['w'],f['d'],f['h'])<=0: raise ValueError('Invalid furniture dimensions: '+f['id'])
        if 'lightOn' in f and not isinstance(f['lightOn'],bool): raise ValueError('Invalid fixture enabled state: '+f['id'])
        if 'lightIntensity' in f and (not finite(f['lightIntensity']) or not 0<=f['lightIntensity']<=50): raise ValueError('Invalid fixture intensity: '+f['id'])
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
    case=validate_case(read(case_path)); out=Path(out_path).resolve()
    if out.exists(): raise ValueError('Output HTML already exists; use a new revision filename')
    template=(ASSETS/'template.html').read_text(encoding='utf-8')
    version=read(ASSETS/'version.json')['version']
    payload=json.dumps(case,ensure_ascii=False,allow_nan=False).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    engine=(ASSETS/'engine.js').read_text(encoding='utf-8').replace('</script','<\\/script')
    # Embedded PNG references are optional. No machine paths are copied into output HTML.
    import base64
    for token,key in [('__PLAN_REFERENCE__','plan'),('__FURNITURE_REFERENCE__','furniture')]:
        ref=case.get('references',{}).get(key)
        data=base64.b64encode((Path(case_path).resolve().parent/ref).read_bytes()).decode() if ref else ''
        template=template.replace(token,data)
    for token,value in [('__WORKBENCH_VERSION__',version),('__CASE_JSON__',payload),('__WALL_HEIGHT_M__',str(case['model']['height']/1000)),('__REFERENCE_NOTE__',html.escape(case.get('referenceNote','参考图用于校核；未标尺寸为设计初值。'))),('__BUNDLE__',engine)]:
        template=template.replace(token,value)
    if '__CASE_JSON__' in template or '__BUNDLE__' in template: raise ValueError('Unresolved template marker')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(template,encoding='utf-8')
    dump(out.with_suffix('.build.json'),{'caseId':case['caseId'],'caseSha256':sha(case_path),'engineSha256':sha(ASSETS/'engine.js'),'htmlSha256':sha(out),'status':'built','humanAcceptance':'not inferred from build','sourceSchemeSha256':case.get('sourceSchemeSha256'),'validation':'input contract only; no visual or cross-floorplan regression','workbenchVersion':version,'templateSha256':sha(ASSETS/'template.html'),'lightingCheck':lighting_report(case)})
    return out

def validate_bundle(bundle,preview=False):
    if bundle.get('schema')!='floor-visualization-production/1.0': raise ValueError('Unsupported production bundle schema')
    if not isinstance(bundle.get('schemeSha256'),str) or len(bundle['schemeSha256'])!=64: raise ValueError('Missing scheme hash')
    if 'costSettings' in bundle['state']: raise ValueError('Pricing is excluded from production')
    cs=bundle.get('confirmations',{})
    if not preview and (set(cs)!=set(('structure','layout','style')) or any(v.get('status')!='confirmed' for v in cs.values())): raise ValueError('Current structure/layout/style confirmation is required; --preview permits explicitly unaccepted preflight only')
    if not bundle.get('scene',{}).get('meshes'): raise ValueError('Export actual meshes before rendering')
    if bundle.get('dimensionAudit',{}).get('errors'): raise ValueError('Exported model dimension audit failed')

def prepare(bundle_path,out_path,preview=False,size=(1280,720)):
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
    meta.update(meshes=meshes,schemeSha256=b['schemeSha256'],model=b['model'],state=b['state'],finishes=b['finishes'],presentationProfile=b.get('presentationProfile',{'hiddenTypes':[]}),renderSettings={'size':list(size),'exposure':1,'shiftY':0,'bodyRadiusMm':160},previewOnly=preview)
    dump(out/'scene.json',meta)
    for filename in ('renderer.html','three.module.js','three.core.js','THREE-LICENSE.txt'):
        shutil.copy2(ASSETS/'runtime'/filename,out/filename)
    dump(out/'prepare.json',{'bundleSha256':sha(bundle_path),'schemeSha256':b['schemeSha256'],'meshCount':len(meshes),'geometryBytes':offset,'runtimeHashes':{f.name:sha(f) for f in out.iterdir() if f.is_file()},'humanAcceptance':'pending','previewOnly':preview})
    return out

def node_call(command,args):
    node=getattr(args,'node',None) or os.environ.get('FLOOR_VIS_NODE') or shutil.which('node')
    if not node: raise ValueError('Existing Node.js required; pass --node')
    cmd=[node,str(HERE/'h5_browser.mjs'),command]
    for key in ('html','runtime','out','tour','views','subjects','playwright_module','browser'):
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

def handoff(directory, manifest_path=None, title='Floor Visualization', accepted=None):
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

def parser():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='command',required=True)
    sub.add_parser('doctor',help='Read-only dependency availability; never installs or runs a regression suite')
    p=sub.add_parser('build',help='Case JSON -> offline single-file workbench');p.add_argument('--case',required=True);p.add_argument('--out',required=True)
    p=sub.add_parser('prepare',help='Actual mesh bundle -> H5 renderer runtime');p.add_argument('--bundle',required=True);p.add_argument('--out',required=True);p.add_argument('--preview',action='store_true');p.add_argument('--width',type=int,default=1280);p.add_argument('--height',type=int,default=720)
    p=sub.add_parser('quality',help='Verify source/image/tour review records without granting approval');p.add_argument('--bundle',required=True);p.add_argument('--review',required=True);p.add_argument('--stage',action='append',choices=quality.STAGES);p.add_argument('--out',required=True);p.add_argument('--accepted',action='store_true')
    p=sub.add_parser('review-template',help='Case-local review skeleton with pending provenance/acceptance');p.add_argument('--bundle',required=True);p.add_argument('--out',required=True)
    for command in ('export','capture','audit','run'):
        p=sub.add_parser(command);p.add_argument('--out',required=True)
        p.add_argument('--node');p.add_argument('--playwright-module');p.add_argument('--browser');p.add_argument('--preview',action='store_true')
        if command=='export':p.add_argument('--html',required=True)
        elif command in ('capture','audit'):
            p.add_argument('--runtime',required=True);p.add_argument('--tour');p.add_argument('--views');p.add_argument('--subjects');p.add_argument('--full',action='store_true');p.add_argument('--resume',action='store_true');p.add_argument('--range',help='Frame range start:end, end exclusive')
        else:
            p.add_argument('--bundle',required=True);p.add_argument('--config');p.add_argument('--tour');p.add_argument('--views');p.add_argument('--subjects');p.add_argument('--quality-review');p.add_argument('--animation',action='store_true');p.add_argument('--ffmpeg');p.add_argument('--ffprobe')
    p=sub.add_parser('package',help='Relocatable folder -> SHA-256 manifest + ZIP');p.add_argument('--directory',required=True);p.add_argument('--archive',required=True)
    p=sub.add_parser('handoff',help='Local assets -> relocatable preview index');p.add_argument('--directory',required=True);p.add_argument('--manifest');p.add_argument('--title',default='Floor Visualization')
    for command in ('package','handoff'):
        p=sub.choices[command];p.add_argument('--accepted',action='store_true');p.add_argument('--quality-review');p.add_argument('--bundle')
    return ap

def main():
    args=parser().parse_args()
    if args.command=='doctor':
        runtime={'python':sys.version.split()[0],'node':os.environ.get('FLOOR_VIS_NODE') or shutil.which('node'),'browserOverride':os.environ.get('FLOOR_VIS_BROWSER'),'playwrightModuleOverride':os.environ.get('FLOOR_VIS_PLAYWRIGHT'),'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe'),'blenderOptional':shutil.which('blender'),'bundledEngine':(ASSETS/'engine.js').exists(),'bundledRenderer':(ASSETS/'runtime/renderer.html').exists(),'installsPerformed':False,'regressionExecuted':False}
        print(json.dumps(runtime,ensure_ascii=False,indent=2));return
    elif args.command=='build': result=build(args.case,args.out)
    elif args.command=='review-template':
        out=fresh(args.out);dump(out/'quality-review.json',quality.template(read(args.bundle)));result=out
    elif args.command=='quality':
        out=fresh(args.out);report=quality.evaluate(args.review,read(args.bundle),args.stage)
        dump(out/'quality.json',report)
        print(json.dumps(report,ensure_ascii=False,indent=2))
        if report['status']=='failed' or (args.accepted and not report['readyForAcceptedDelivery']):raise ValueError('Quality gate blocked; inspect '+str(out/'quality.json'))
        result=out
    elif args.command=='prepare':
        if args.width<320 or args.height<180 or args.width%2 or args.height%2:raise ValueError('Use even output dimensions >= 320 x 180')
        result=prepare(args.bundle,args.out,args.preview,(args.width,args.height))
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
            cfg=read(args.config);tour=read(out/'tour.json')
            for f in tour['frames']:f.update(horizontalFovDegrees=cfg.get('horizontalFovDegrees',76),shiftY=cfg.get('shiftY',0))
            dump(out/'tour.json',tour)
        elif args.animation:raise ValueError('Animation requires --tour or --config')
        args.runtime=str(out/'runtime');args.tour=str(out/'tour.json') if (out/'tour.json').exists() else None
        if not args.tour and not args.views:raise ValueError('Provide a tour or explicit views; cameras are not invented')
        if args.views:shutil.copy2(args.views,out/'views.json');args.views=str(out/'views.json')
        args.out=str(out/'audit');node_call('audit',args)
        args.out=str(out/'capture');args.full=args.animation;node_call('capture',args)
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
        audit=read(out/'audit/audit.json')
        dump(out/'run.json',{'schemeSha256':b['schemeSha256'],'engine':'h5','previewOnly':args.preview,'humanAcceptance':'pending for new artifacts','video':video.name if video else None,'subjectStatus':audit['subjectStatus'],'visualReview':'pending','acceptedDelivery':False,'Seedance':'not executed'})
        handoff(out)
        result=out
    else:node_call(args.command,args);result=args.out
    message={'command':args.command,'output':str(result)}
    if args.command=='build':
        evidence=read(Path(result).with_suffix('.build.json'));message.update(workbenchVersion=evidence['workbenchVersion'],lightingWarnings=evidence['lightingCheck']['warnings'],buildMetadata=str(Path(result).with_suffix('.build.json')))
    print(json.dumps(message,ensure_ascii=False))

if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as e:raise SystemExit(str(e))
