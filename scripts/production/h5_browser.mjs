#!/usr/bin/env node
// Local browser adapter. Dependencies/executables are supplied, never installed.
import fs from 'node:fs';
import path from 'node:path';
import http from 'node:http';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {requirePreview} from './preview_gate.mjs';
import {validateSubjectPlan,sampleIndices,summarizeChapter} from './subject_quality.mjs';
const argv=process.argv.slice(2),command=argv[0];
const flag=k=>argv.includes('--'+k),arg=k=>{const i=argv.indexOf('--'+k);return i<0?null:argv[i+1];};
if(flag('help')||!command){console.log('h5_browser.mjs export --html FILE --out EMPTY_DIR | capture/audit --runtime DIR --tour FILE/--views FILE --out DIR [--full] [--resume] [--range start:end] [--playwright-module FILE] [--browser EXECUTABLE] [--preview]');process.exit(0);}
if(!['export','capture','audit'].includes(command)||!arg('out'))throw Error('Choose export/capture/audit and an output directory');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const json=(p,v)=>{fs.writeFileSync(p+'.partial',JSON.stringify(v,null,2));fs.renameSync(p+'.partial',p);};
const out=path.resolve(arg('out')),resume=flag('resume');
if(fs.existsSync(out)&&fs.readdirSync(out).length&&!resume)throw Error('Use a new empty directory or --resume with the same source hashes');
fs.mkdirSync(out,{recursive:true});
let playwright;
const modulePath=arg('playwright-module')||process.env.FLOOR_VIS_PLAYWRIGHT;
if(modulePath)playwright=await import(pathToFileURL(path.resolve(modulePath)).href);
else {try{playwright=await import('playwright');}catch{try{playwright=await import('playwright-core');}catch{throw Error('Existing Playwright module required; pass --playwright-module. No automatic install.');}}}
const browserPath=arg('browser')||process.env.FLOOR_VIS_BROWSER;
const launch={headless:true,args:['--enable-unsafe-swiftshader']};
if(browserPath)launch.executablePath=browserPath;
const root=path.resolve(command==='export'?path.dirname(arg('html')||''):arg('runtime')||'');
const server=http.createServer((req,res)=>{
 try{
  const pathname=decodeURIComponent(new URL(req.url,'http://localhost').pathname);
  const target=path.resolve(root,'.'+pathname),relative=path.relative(root,target);
  if(relative.startsWith('..')||path.isAbsolute(relative)||!fs.existsSync(target)||!fs.statSync(target).isFile()){res.writeHead(404);res.end();return;}
  const real=fs.realpathSync(target),realRelative=path.relative(fs.realpathSync(root),real);
  if(realRelative.startsWith('..')||path.isAbsolute(realRelative)){res.writeHead(403);res.end();return;}
  res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.js':'text/javascript','.json':'application/json','.bin':'application/octet-stream','.png':'image/png'})[path.extname(target)]||'application/octet-stream');
  fs.createReadStream(target).pipe(res);
 }catch{res.writeHead(400);res.end();}
});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
let browser;
const errors=[];
try{
 browser=await playwright.chromium.launch(launch);
 // Match the viewport to the output canvas: overflow:hidden otherwise clips
 // screenshots wider/taller than the browser and fills the remainder with body background.
 const outputSize=command==='export'?[1280,720]:(JSON.parse(fs.readFileSync(path.join(root,'scene.json'),'utf8')).renderSettings?.size||[1280,720]);
 const page=await browser.newPage({viewport:{width:outputSize[0],height:outputSize[1]},deviceScaleFactor:1});
 page.on('pageerror',e=>{errors.push(e.message);console.error('PAGEERROR',e.message);});
 // Block external requests; screenshots never upload cases or request a CDN.
 await page.route('**/*',route=>{const u=route.request().url();if(u.startsWith('http://127.0.0.1:'+server.address().port+'/')||u.startsWith('data:')||u.startsWith('blob:'))return route.continue();return route.abort();});
 const source=command==='export'?arg('html'):path.join(root,'renderer.html');
 await page.goto(`http://127.0.0.1:${server.address().port}/${encodeURIComponent(path.basename(source))}`);
 if(command==='export'){
  await page.waitForFunction(()=>window.homeStudio?.ready === true,null,{timeout:60000});
  const preliminary=await page.evaluate(()=>window.homeStudio.getProductionBundle());
  if(!flag('preview')&&Object.values(preliminary.confirmations).some(c=>c.status!=='confirmed'))throw Error('Current approval scopes are unconfirmed or stale. Use --preview only for unaccepted preflight.');
  const state=await page.evaluate(()=>window.homeStudio.getState());delete state.costSettings;
  json(path.join(out,'scheme.json'),state);
  // Capture each drawing as its exported SVG and PNG rendered from those exact pixels.
  for(const mode of ['structure','furniture','hard']){
   await page.evaluate(mode=>{window.homeStudio.setPlanDrawingMode(mode);},mode);
   const svg=await page.evaluate(()=>window.homeStudio.exportPlanSVG());
   fs.writeFileSync(path.join(out,mode+'.svg'),svg);
   const picture=await browser.newPage({viewport:{width:1500,height:2000},deviceScaleFactor:1});
   try{await picture.setContent('<body style="margin:0"><img id="drawing" style="display:block" src="data:image/svg+xml;base64,'+Buffer.from(svg).toString('base64')+'">');await picture.locator('#drawing').evaluate(async img=>{await img.decode();});await picture.locator('#drawing').screenshot({path:path.join(out,mode+'.png')});}finally{await picture.close();}
  }
  await page.evaluate(async()=>{window.__floorBundleJSON=JSON.stringify(await window.homeStudio.captureActualBundle());});
  const length=await page.evaluate(()=>window.__floorBundleJSON.length);
  const temporary=path.join(out,'production-bundle.json.partial'),fd=fs.openSync(temporary,'w');
  try{for(let offset=0;offset<length;){const part=await page.evaluate(([a,b])=>{const text=window.__floorBundleJSON;let end=Math.min(b,text.length);const unit=text.charCodeAt(end-1);if(end<text.length&&unit>=0xd800&&unit<=0xdbff)end--;return {end,text:text.slice(a,end)};},[offset,offset+1024*1024]);fs.writeSync(fd,part.text,null,'utf8');offset=part.end;}}finally{fs.closeSync(fd);}
  fs.renameSync(temporary,path.join(out,'production-bundle.json'));
  json(path.join(out,'export.json'),{schemeSha256:preliminary.schemeSha256,htmlSha256:hash(source),meshCapture:'actual browser vertices/materials/textures',sourceState:'delivered defaults in a fresh browser; not the unsaved user tab',previewOnly:flag('preview'),humanAcceptance:'not granted by export',errors});
 }else{
  await page.waitForFunction(()=>window.rendererReady,null,{timeout:60000});
  const scene=read(path.join(root,'scene.json')),tourPath=arg('tour'),viewsPath=arg('views');
  if(!tourPath&&!viewsPath)throw Error('Supply explicit --tour or --views; viewpoints are not invented');
  const tour=tourPath?read(tourPath):null,viewData=viewsPath?read(viewsPath):[],views=Array.isArray(viewData)?viewData:viewData.views;
  if(!Array.isArray(views))throw Error('Views must be an array or {views:[...]}');
  if(tour&&(tour.schemeSha256!==scene.schemeSha256||!Array.isArray(tour.frames)||!tour.frames.length))throw Error('Tour hash or frame data differs from the exported scheme');
  if(command==='capture'&&flag('full')&&tour){const [w,h]=scene.renderSettings?.size||[1280,720];if(!flag('preview')||w>1280||h>720)requirePreview(arg('preview-review'),tourPath,root);}
  if(tour?.audit?.bodyRadiusMm)await page.evaluate(mm=>window.setBodyRadiusMm(mm),tour.audit.bodyRadiusMm);
  if(viewData.schemeSha256&&viewData.schemeSha256!==scene.schemeSha256)throw Error('Views hash differs from exported scheme');
  const inputs={scene:hash(path.join(root,'scene.json')),geometry:hash(path.join(root,'geometry.bin')),renderer:hash(path.join(root,'renderer.html')),tour:tourPath?hash(tourPath):null,views:viewsPath?hash(viewsPath):null,full:flag('full')};
  const fingerprint=crypto.createHash('sha256').update(JSON.stringify(inputs)).digest('hex'),journalFile=path.join(out,'journal.json');
  let journal={fingerprint,inputs,frames:{},views:{},schemeSha256:scene.schemeSha256};
  if(resume){if(!fs.existsSync(journalFile))throw Error('Resume journal missing');journal=read(journalFile);if(journal.fingerprint!==fingerprint)throw Error('Source or rendering mode changed; do not mix revisions');}
  if(command==='audit'){
   let audit=null;
   if(tour){const samples=[...tour.frames];for(let i=0;i<tour.frames.length-1;i++){const a=tour.frames[i],b=tour.frames[i+1];samples.push({...a,frame:i+.5,pointMm:a.pointMm.map((v,k)=>(v+b.pointMm[k])/2)});}audit=await page.evaluate(samples=>window.meshAudit(samples),samples);}
   const viewAudits=[];
   for(const v of views){
    const report=await page.evaluate(v=>window.renderView(v),v);
    report.cameraRequiredSubjectsMissing=!Array.isArray(v.mustShow)||v.mustShow.length===0;
    report.subjects=await page.evaluate(ids=>window.inspectSubjects(ids),v.mustShow||[]);
    viewAudits.push(report);
   }
   let subjectAudit=null;
   if(arg('subjects')){
    if(!tour)throw Error('Subject windows require a tour');
    const plan=read(arg('subjects')),tourHash=hash(tourPath);
    const actualIds=[...scene.state.furniture.map(f=>f.id),...scene.meshes.map(m=>m.objectId).filter(Boolean)];
    const policy=validateSubjectPlan(plan,tour,scene.schemeSha256,tourHash,actualIds);
    const chapters=[];
    for(const chapter of plan.chapters){
     const samples=[];
     for(const i of sampleIndices(chapter,tour,policy)){
      const f=tour.frames[i];
      const subjects=await page.evaluate(async({f,ids})=>window.inspectShot(f,ids),{f,ids:chapter.subjects});
      const composition=await page.evaluate(async f=>window.inspectComposition(f,{closeDistanceM:.8}),f);
      samples.push({frame:i,seconds:i/tour.fps,subjects,composition});
     }
     const report=summarizeChapter(chapter,samples,policy);chapters.push(report);
     const middle=sampleIndices(chapter,tour,policy)[Math.floor(samples.length/2)];
     await page.evaluate(f=>window.renderFrame(f),tour.frames[middle]);
     await page.locator('canvas').screenshot({path:path.join(out,'chapter-'+String(chapters.length).padStart(2,'0')+'.png')});
     console.log('SUBJECT',chapter.id,report.pass?'PASS':'FAIL');
    }
    subjectAudit={schema:'floor-visualization-subject-audit/1.0',schemeSha256:scene.schemeSha256,tourSha256:tourHash,planSha256:hash(arg('subjects')),fingerprint,policy,chapters,status:chapters.every(c=>c.pass)?'pass':'fail',humanAcceptance:'pending',limitations:['Discrete triangle visibility and projected bounds are proxies, not exact image segmentation or human composition acceptance']};
    json(path.join(out,'subjects.json'),subjectAudit);
   }
   const lighting=await page.evaluate(()=>window.inspectLighting()),downlights=await page.evaluate(()=>window.inspectDownlights());
   const staticSubjectsPass=viewAudits.every(v=>!v.cameraRequiredSubjectsMissing&&Object.values(v.subjects).every(s=>s.unoccludedSamples>=3&&s.screenAreaFraction>=.01));
   const subjectStatus=subjectAudit?.status||(tour?'not_checked':staticSubjectsPass?'pass':'fail');
   json(path.join(out,'audit.json'),{schemeSha256:scene.schemeSha256,tourSha256:tourPath?hash(tourPath):null,fingerprint,meshAudit:audit,viewAudits,lighting,downlights,subjectStatus,staticSubjectsPass,errors,limitations:['Ray probes are targeted checks, not a proof of full collision clearance or construction compliance','Time-window visibility does not grant internal visual review or user acceptance'],humanAcceptance:'pending'});
   if(audit?.hits.length||viewAudits.some(v=>!v.standable))throw Error('Camera clearance audit failed; inspect audit.json');
   if(!lighting.allFixturesOn||!lighting.allPrimaryFacesVisible||downlights.tests.some(t=>t.angleFromVertical===0&&!t.visible))throw Error('Fixture emission or ceiling visibility audit failed; inspect audit.json');
   if(!flag('preview')&&(subjectStatus!=='pass'||!staticSubjectsPass))throw Error('Subject quality is missing or failed; only explicit --preview can retain diagnostic preflight');
  }else{
   if(tour){
    const range=(arg('range')||'0:'+tour.frames.length).split(':').map(Number);
    if(range.length!==2||!range.every(Number.isInteger)||range[0]<0||range[1]>tour.frames.length||range[1]<=range[0])throw Error('Invalid frame range');
    const frameDir=path.join(out,'frames');fs.mkdirSync(frameDir,{recursive:true});
    const indices=flag('full')?tour.frames.map((_,i)=>i):[...new Set(tour.frames.map((_,i)=>i).filter(i=>i%tour.fps===0||i===tour.frames.length-1))];
    for(const i of indices.filter(i=>i>=range[0]&&i<range[1])){
     const target=path.join(frameDir,'frame-'+String(i).padStart(6,'0')+'.png');
     if(journal.frames[i]&&fs.existsSync(target)&&hash(target)===journal.frames[i])continue;
     await page.evaluate(f=>window.renderFrame(f),tour.frames[i]);await page.locator('canvas').screenshot({path:target});journal.frames[i]=hash(target);json(journalFile,journal);
     if(i%tour.fps===0)console.log('FRAME',i);
    }
   }
   const viewDir=path.join(out,'views');if(views.length)fs.mkdirSync(viewDir,{recursive:true});
   for(let i=0;i<views.length;i++){
    const name=String(i+1).padStart(2,'0')+'.png',target=path.join(viewDir,name);
    if(journal.views[i]&&fs.existsSync(target)&&hash(target)===journal.views[i])continue;
    const report=await page.evaluate(v=>window.renderView(v),views[i]);await page.locator('canvas').screenshot({path:target});journal.views[i]=hash(target);json(path.join(viewDir,String(i+1).padStart(2,'0')+'.json'),{...report,camera:views[i],imageSha256:hash(target)});json(journalFile,journal);
   }
   json(journalFile,journal);json(path.join(out,'capture.json'),{schemeSha256:scene.schemeSha256,fingerprint,frameCount:Object.keys(journal.frames).length,viewCount:Object.keys(journal.views).length,expectedFrames:tour?.frames.length||0,full:flag('full'),errors,humanAcceptance:'pending'});
  }
 }
 if(errors.length)throw Error(errors.join('\n'));
 console.log(JSON.stringify({command,output:out,status:'completed',humanAcceptance:'not automatic'}));
}finally{if(browser)await browser.close();await new Promise(resolve=>server.close(resolve));}
