"""Cross-platform local release checks; no installs, network calls or approvals."""
import argparse,json,os,shutil,subprocess,sys
from pathlib import Path

def javascript_module_tests(root):
    # Browser entry modules are separately invoked through the artifact suite.
    browser_entries={'test_sliding_editor.mjs','test_night_lighting.mjs',
                     'test_platform_fridge_components.mjs','test_security_door.mjs','test_variant_switch.mjs'}
    return [p for directory in ('scripts','scripts/production')
            for p in sorted((Path(root)/directory).glob('test_*.mjs'))
            if not p.name.endswith('_browser.mjs') and p.name not in browser_entries]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,help='New empty evidence directory')
    parser.add_argument('--test-node-modules',help='Existing node_modules containing three/esbuild for CPU geometry checks; never installs')
    parser.add_argument('--blender',help='Explicit existing Blender for the three isolated API checks')
    parser.add_argument('--with-media-browser',action='store_true',help='Real synthetic narration and four-stage browser integration')
    parser.add_argument('--node',help='Existing Node executable; required for subject checks')
    parser.add_argument('--with-browser',action='store_true',help='Run actual generated-artifact browser acceptance; no installs')
    parser.add_argument('--browser-case',help='Case JSON for isolated browser acceptance')
    parser.add_argument('--browser',help='Existing Chrome/Chromium executable')
    parser.add_argument('--playwright-module',help='Existing Playwright entry module')
    parser.add_argument('--browser-checks',default='core',help='core/full or comma-separated browser checks')
    parser.add_argument('--with-cross-layout',action='store_true',help='Run independent synthetic-layout browser matrix; no client case edits')
    parser.add_argument('--cross-layout-checks',default='core,components,floors')
    args=parser.parse_args();root=Path(__file__).resolve().parent.parent;out=Path(args.out).resolve()
    if out.exists() and (not out.is_dir() or any(out.iterdir())):raise SystemExit('Use a new empty evidence directory')
    out.mkdir(parents=True,exist_ok=True);node=args.node or shutil.which('node')
    env={**os.environ,'PYTHONUTF8':'1'};commands=[('doctor',[sys.executable,str(root/'scripts/production/h5.py'),'doctor']),('engine-provenance',[sys.executable,str(root/'scripts/production/engine_provenance.py'),'check']),('python-regression',[sys.executable,'-m','unittest','discover','-s',str(root/'scripts'),'-p','test_*.py'])]
    commands.append(('production-python-regression',[sys.executable,'-m','unittest','discover','-s',str(root/'scripts/production'),'-p','test_*.py']))
    if args.test_node_modules:env['INTERIOR_TEST_NODE_MODULES']=str(Path(args.test_node_modules).resolve())
    commands.append(('component-capability-index',[sys.executable,str(root/'scripts/check_component_capabilities.py')]))
    if node:
        commands.append(('javascript-module-regression',[node,'--test',*[str(p) for p in javascript_module_tests(root)]]))
    if args.with_browser:
        if not args.browser_case:parser.error('--with-browser requires --browser-case')
        browser_command=[sys.executable,str(root/'scripts/workbench_browser_suite.py'),'--case',args.browser_case,'--out',str(out/'browser'),'--checks',args.browser_checks]
        for option,value in [('--node',node),('--browser',args.browser),('--playwright-module',args.playwright_module)]:
            if value:browser_command.extend([option,value])
        commands.append(('generated-browser-acceptance',browser_command))
    if args.with_cross_layout:
        matrix_command=[sys.executable,str(root/'scripts/workbench_cross_layout.py'),'--out',str(out/'cross-layout'),'--checks',args.cross_layout_checks]
        for option,value in [('--node',node),('--browser',args.browser),('--playwright-module',args.playwright_module)]:
            if value:matrix_command.extend([option,value])
        commands.append(('cross-layout-browser-acceptance',matrix_command))
    if args.blender:
        for file in ('test_blender_source_import.py','test_blender_room_presentation.py','test_blender_render_quality.py'):
            commands.append(('blender-'+file.removeprefix('test_').removesuffix('.py'),[args.blender,'--background','--factory-startup','--python-exit-code','1','--python',str(root/'scripts'/file)]))
    if args.with_media_browser:
        if not all((node,args.browser,args.playwright_module,shutil.which('ffmpeg'),shutil.which('ffprobe'))):parser.error('--with-media-browser requires existing Node, browser, Playwright, FFmpeg/ffprobe')
        commands.append(('media-browser',[sys.executable,str(root/'scripts/production/test_production_browser.py'),str(out/'media-browser'),node,args.browser,args.playwright_module,shutil.which('ffmpeg'),shutil.which('ffprobe')]))
    results=[]
    for name,command in commands:
        run=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,encoding='utf-8',errors='replace')
        (out/(name+'.txt')).write_text(run.stdout+run.stderr,encoding='utf-8');results.append({'name':name,'exitCode':run.returncode,'evidence':name+'.txt'})
    if not node:results.append({'name':'subject-regression','exitCode':None,'reason':'Existing Node executable missing; no automatic install'})
    report={'testNodeModules':env.get('INTERIOR_TEST_NODE_MODULES'),'javascriptModuleTests':[str(p.relative_to(root)) for p in javascript_module_tests(root)] if node else [],'platform':sys.platform,'python':sys.version.split()[0],'node':node,'checks':results,'status':'pass' if all(r['exitCode']==0 for r in results) else 'fail','scope':'Installed source/module regression; generated-artifact browser interactions only when explicitly requested; not visual/device/video or human acceptance','installsPerformed':False,'externalNetworkCalls':False,'blenderApiRequested':bool(args.blender),'mediaBrowserRequested':args.with_media_browser,'loopbackHttp':args.with_browser or args.with_cross_layout or args.with_media_browser,'browserAcceptance':{'requested':args.with_browser,'report':'browser/result.json' if args.with_browser else None,'status':'see browser/result.json' if args.with_browser else 'not_requested'},'crossLayoutAcceptance':{'requested':args.with_cross_layout,'report':'cross-layout/result.json' if args.with_cross_layout else None,'status':'see cross-layout/result.json' if args.with_cross_layout else 'not_requested'}}
    (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=True));return 0 if report['status']=='pass' else 1
if __name__=='__main__':raise SystemExit(main())
