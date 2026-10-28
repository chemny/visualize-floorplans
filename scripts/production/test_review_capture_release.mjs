import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';import crypto from 'node:crypto';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import {requireReviewRelease,requireRoute,ruleFingerprint} from './preview_gate.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const copy=v=>structuredClone(v);
function fixture(){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'review-capture-release-')),runtime=path.join(root,'runtime');fs.mkdirSync(runtime);
 const tour={schemeSha256:'synthetic',fps:1,seconds:11,frames:Array.from({length:11},(_,frame)=>({frame,pointMm:[frame*10,0],yawRadians:0,pitchRadians:0,eyeMm:1600})),visits:[{name:'start',frame:0},{name:'end',frame:10}]};
 const config={tourContract:{},chapters:[{name:'room',from:'start',to:'end',phase:'observe',subjects:['cabinet']}]};
 const allowed=[{code:'screen_near_surface_occlusion',startSeconds:7,endSeconds:8}];
 const files={tour,config,bundle:{schemeSha256:'synthetic'},scene:{schemeSha256:'synthetic',renderSettings:{size:[640,360]}},geometry:Buffer.from('synthetic geometry'),renderer:'<!doctype html><canvas></canvas>',animation:'<!doctype html><p>Synthetic displayed animation</p>',
 contractReport:{schema:'homeowner-tour-contract-report/1',rulesetVersion:'homeowner-tour-rules/2',status:'numeric_pass_visual_pending',issues:[],checks:{cameraEvidence:{schema:'homeowner-camera-evidence/1'},forwardMotion:{schema:'homeowner-forward-motion/1',status:'pass',issues:[]}}},
 screenAudit:{rulesetVersion:'homeowner-tour-rules/2',status:'fail',humanAcceptance:'pending',chapters:[{startSeconds:0,endSeconds:10,pass:true,samples:[0,.5,1].map(seconds=>({seconds,subjects:{cabinet:{unoccludedSamples:3,totalSamples:4,screenAreaFraction:.1}}}))}],screenQuality:{status:'needs_revision',issues:copy(allowed)}},
 visualReview:{result:'pending',observationMode:'not_performed'},clearanceAudit:{meshAudit:{hits:[]},errors:[]}};
 const paths=Object.fromEntries(Object.keys(files).map(key=>[key,['scene','geometry','renderer'].includes(key)?path.join(runtime,{scene:'scene.json',geometry:'geometry.bin',renderer:'renderer.html'}[key]):path.join(root,key+'.json')]));
 const ref=key=>({path:paths[key],sha256:hash(paths[key])});
 const manifestPath=path.join(root,'rehearsal.json'),routePath=path.join(root,'route-review.json'),releasePath=path.join(root,'release.json');
 const manifest={schema:'homeowner-route-rehearsal/1',schemeSha256:'synthetic',timing:{overBudget:false,totalSeconds:11,maximumSeconds:12}};
 const route={schema:'homeowner-route-approval/1',status:'approved',approvalSource:'explicit_user_confirmation',confirmedBy:'SYNTHETIC USER',evidence:'Synthetic confirmation of displayed path, facing and timing; not a real case approval',checks:{animationViewed:true,pathAndFacingApproved:true,durationAndRhythmApproved:true}};
 const release={schema:'homeowner-review-capture-release/2',status:'authorized_review_capture_only',scope:'review_video_only',userInstruction:'Synthetic request to export a review video with the specifically disclosed issue.',authorizedBy:'explicit_user_confirmation',authorizationEvidence:'SYNTHETIC TEST ONLY',humanAcceptance:'pending',productionAccepted:false,allowPendingContinuousReview:true,allowedScreenIssues:copy(allowed)};
 function refresh(){
  for(const key of ['tour','config','bundle','scene','geometry','renderer','animation'])fs.writeFileSync(paths[key],['geometry','renderer','animation'].includes(key)?files[key]:JSON.stringify(files[key]));
  const common={tourSha256:hash(paths.tour),configSha256:hash(paths.config),geometrySha256:hash(paths.geometry),schemeSha256:tour.schemeSha256,ruleFingerprint:ruleFingerprint()};
  Object.assign(files.contractReport,common,{bundleSha256:hash(paths.bundle)});Object.assign(files.screenAudit,common);Object.assign(files.visualReview,common);Object.assign(files.clearanceAudit,common,{sceneSha256:hash(paths.scene),rendererSha256:hash(paths.renderer)});
  for(const key of ['contractReport','screenAudit','visualReview','clearanceAudit'])fs.writeFileSync(paths[key],JSON.stringify(files[key]));
  manifest.references=Object.fromEntries(['tour','config','bundle','scene','animation','contractReport','screenAudit','visualReview'].map(k=>[k,ref(k)]));manifest.geometrySha256=hash(paths.geometry);fs.writeFileSync(manifestPath,JSON.stringify(manifest));
  route.rehearsal={path:manifestPath,sha256:hash(manifestPath)};route.presentedAnimationSha256=hash(paths.animation);fs.writeFileSync(routePath,JSON.stringify(route));
  release.ruleFingerprint=ruleFingerprint();release.references={routeReview:{path:routePath,sha256:hash(routePath)},renderer:ref('renderer'),clearanceAudit:ref('clearanceAudit')};fs.writeFileSync(releasePath,JSON.stringify(release));
 }
 refresh();
 return {root,files,release,route,manifest,paths,routePath,releasePath,runtime,refresh,run:(options={preview:true,full:true})=>requireReviewRelease(releasePath,paths.tour,runtime,options),close:()=>fs.rmSync(root,{recursive:true,force:true})};
}
function check(fn){const f=fixture();try{fn(f);}finally{f.close();}}
test('review release permits one disclosed issue, retains failure/pending and does not relax ordinary capture',()=>check(f=>{const r=f.run();assert.equal(r.humanAcceptance,'pending');assert.equal(r.productionAccepted,false);assert.equal(f.files.screenAudit.status,'fail');assert.throws(()=>requireRoute(f.routePath,f.paths.tour,f.runtime),/Screen composition/);}));
test('issue count is case data: zero pending-playback issues and three exact issues both work',()=>check(f=>{
 f.files.screenAudit.screenQuality.issues=[];f.files.screenAudit.screenQuality.status='pass';f.files.screenAudit.status='pass';f.release.allowedScreenIssues=[];f.refresh();f.run();
 const issues=[1,3,7].map(startSeconds=>({code:'screen_dominant_surface',startSeconds,endSeconds:startSeconds+.5}));
 f.release.allowedScreenIssues=copy(issues);f.files.screenAudit.screenQuality.issues=issues;f.files.screenAudit.screenQuality.status='needs_revision';f.files.screenAudit.status='fail';f.refresh();f.run();
}));
test('missing confirmation or mismatched displayed animation blocks release',()=>check(f=>{f.release.authorizationEvidence='';f.refresh();assert.throws(()=>f.run(),/confirmation/);f.release.authorizationEvidence='synthetic';f.route.checks.animationViewed=false;f.refresh();assert.throws(()=>f.run(),/approval missing/);}));
test('no review release for production, HD or ranges',()=>check(f=>{for(const options of [{preview:false,full:true},{preview:true,full:false},{preview:true,full:true,range:'0:2'}])assert.throws(()=>f.run(options),/preview --full/);f.files.scene.renderSettings.size=[1920,1080];f.refresh();assert.throws(()=>f.run(),/production\/HD/);}));
test('new issue and blanket/nonvisual allowances cannot be silently included',()=>check(f=>{f.files.screenAudit.screenQuality.issues.push({code:'screen_blank_segment',startSeconds:4,endSeconds:5});f.refresh();assert.throws(()=>f.run(),/exact authorized/);f.release.allowedScreenIssues=[{code:'collision',startSeconds:4,endSeconds:5}];f.refresh();assert.throws(()=>f.run(),/time-bounded visual/);}));
test('numeric, unreadable subjects, missing actual target samples and collision failures remain blocking',()=>check(f=>{
 f.files.contractReport.issues=[{code:'collision'}];f.refresh();assert.throws(()=>f.run(),/contract/);f.files.contractReport.issues=[];
 f.files.screenAudit.chapters[0].pass=false;f.refresh();assert.throws(()=>f.run(),/unreadable/);f.files.screenAudit.chapters[0].pass=true;
 const samples=f.files.screenAudit.chapters[0].samples;f.files.screenAudit.chapters[0].samples=[];f.refresh();assert.throws(()=>f.run(),/target audit/);f.files.screenAudit.chapters[0].samples=samples;
 f.files.clearanceAudit.meshAudit.hits=[{id:'wall'}];f.refresh();assert.throws(()=>f.run(),/collisions/);
}));
test('a failed continuous review cannot masquerade as a pending review',()=>check(f=>{f.files.visualReview.result='fail';f.refresh();assert.throws(()=>f.run(),/playback review/);f.files.visualReview.result='pending';f.release.allowPendingContinuousReview=false;f.refresh();assert.throws(()=>f.run(),/playback review/);}));
test('capture reconstructs actual room fixtures and rejects an omitted toilet independently of a forged passing audit',()=>check(f=>{
 f.files.bundle.model={rooms:[{id:'different-zone',poly:[[0,0],[1000,0],[1000,1000],[0,1000]]}]};
 f.files.bundle.state={furniture:[{id:'actual-wc',type:'toilet',cx:500,cy:500,roomId:'different-zone'}]};
 f.files.config.chapters[0].roomId='different-zone';f.refresh();assert.throws(()=>f.run(),/core facility/);
}));
test('capture rejects a missing or failed final forward-walking check even with empty aggregate issues',()=>check(f=>{
 const original=copy(f.files.contractReport.checks.forwardMotion);
 delete f.files.contractReport.checks.forwardMotion;f.refresh();assert.throws(()=>f.run(),/contract/);
 f.files.contractReport.checks.forwardMotion={...original,status:'needs_revision',issues:[{code:'sustained_backward_walking'}]};f.refresh();assert.throws(()=>f.run(),/contract/);
}));
test('stale sources, renderer, clearance and altered approval all block',()=>check(f=>{
 for(const key of ['tour','animation','renderer','clearanceAudit']){const before=fs.readFileSync(f.paths[key]);fs.appendFileSync(f.paths[key],' ');assert.throws(()=>f.run());fs.writeFileSync(f.paths[key],before);}
 const before=fs.readFileSync(f.routePath);fs.appendFileSync(f.routePath,' ');assert.throws(()=>f.run(),/Changed.*routeReview/);fs.writeFileSync(f.routePath,before);
}));
test('over budget, false acceptance and falsified screen pass stay blocking',()=>check(f=>{f.manifest.timing.overBudget=true;f.refresh();assert.throws(()=>f.run(),/Over-budget/);f.manifest.timing.overBudget=false;f.release.productionAccepted=true;f.refresh();assert.throws(()=>f.run(),/acceptance/);f.release.productionAccepted=false;f.files.screenAudit.status='pass';f.refresh();assert.throws(()=>f.run(),/actual status/);}));
test('both Python and browser entries use the same validator before loading a browser or creating output',()=>check(f=>{
 const args=['check-review-release','--runtime',f.runtime,'--tour',f.paths.tour,'--review-release',f.releasePath,'--preview','--full'];
 const js=()=>spawnSync(process.execPath,[path.join(here,'h5_browser.mjs'),...args],{encoding:'utf8'});
 const source="import sys;from types import SimpleNamespace;sys.path.insert(0,sys.argv[1]);import h5;h5.require_capture_review(SimpleNamespace(command='capture',runtime=sys.argv[2],tour=sys.argv[3],review_release=sys.argv[4],node=sys.argv[5],preview=True,full=True))";
 const py=()=>spawnSync(process.env.FLOOR_VIS_PYTHON||'python3',['-c',source,here,f.runtime,f.paths.tour,f.releasePath,process.execPath],{encoding:'utf8'});
 for(const run of [js,py]){const r=run();assert.equal(r.status,0,r.stderr);}
 f.route.checks.animationViewed=false;f.refresh();for(const run of [js,py])assert.notEqual(run().status,0);
 const out=path.join(f.root,'no-output');const r=spawnSync(process.execPath,[path.join(here,'h5_browser.mjs'),'capture',...args.slice(1),'--out',out],{encoding:'utf8'});assert.notEqual(r.status,0);assert.equal(fs.existsSync(out),false);
}));
