// Existing browser/Playwright only. Exact downloadable video playback plus optional generated-page controls.
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {pathToFileURL} from 'node:url';import assert from 'node:assert/strict';
const args={};for(let i=2;i<process.argv.length;i+=2)args[process.argv[i].replace(/^--/,'')]=process.argv[i+1];
for(const k of ['url','video','out','browser','playwright-module'])if(!args[k])throw Error('Missing --'+k);
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');const bound=f=>({path:path.resolve(f),sha256:sha(fs.readFileSync(f))});
const pw=(await import(pathToFileURL(args['playwright-module']).href)).default;
const report={schema:'homeowner-playback-check/1',video:bound(args.video),rate:1,ended:false,errors:[],pageControls:[],approvalGranted:false};
const browser=await pw.chromium.launch({executablePath:args.browser,headless:true,args:['--autoplay-policy=no-user-gesture-required']});
try{
 const p=await browser.newPage({viewport:{width:1440,height:1000}});p.on('pageerror',e=>report.errors.push(e.message));
 async function verifyUrl(url,file){const r=await p.request.get(url);assert(r.ok());const body=await r.body();assert(body.length<512*1024**2);assert.equal(sha(body),bound(file).sha256)}
 await verifyUrl(args.url,args.video);
 await p.setContent('<video controls playsinline preload="auto" style="width:1280px;max-width:100%;aspect-ratio:16/9"></video>');
 await p.locator('video').evaluate((v,url)=>{v.src=url;v.muted=true;v.loop=false},args.url);
 await p.waitForFunction(()=>document.querySelector('video').readyState===4);
 const playback=await p.locator('video').evaluate(async v=>{
  const stalls=[];v.addEventListener('waiting',()=>stalls.push(v.currentTime));const start=performance.now();const before=v.getVideoPlaybackQuality().droppedVideoFrames;
  const end=new Promise(r=>v.addEventListener('ended',r,{once:true}));await v.play();await end;const q=v.getVideoPlaybackQuality();
  return{ended:v.ended,seconds:v.duration,width:v.videoWidth,height:v.videoHeight,decodedFrames:q.totalVideoFrames,droppedFrames:q.droppedVideoFrames-before,stalls,elapsedSeconds:(performance.now()-start)/1000};
 });Object.assign(report,playback);assert(report.ended);
 if(args['page-url']){
  await p.addInitScript(()=>{const A=window.Audio;window.__tracks=[];window.Audio=function(...a){const v=new A(...a);window.__tracks.push(v);return v}});
  await p.goto(args['page-url']);await p.waitForFunction(()=>document.querySelector('video')?.readyState>=2);
  await verifyUrl(await p.locator('video').evaluate(v=>v.currentSrc),args['page-video']||args.video);
  assert.equal(await p.locator('nav.steps>*').count(),4);report.pageControls.push('four-stage-navigation');
  if(await p.locator('#roomListTab').count()){
   await p.locator('#roomListTab').click();assert(await p.locator('#roomListPanel').isVisible());await p.locator('#routeMapTab').click();report.pageControls.push('map-list');
  }
  if(args['composition-job']){
   const job=JSON.parse(fs.readFileSync(args['composition-job'],'utf8'));const settings=JSON.parse(await p.locator('#tour-page-data').textContent());assert.equal(settings.musicGain,job.musicGain??1);
   for(const kind of ['voice','music'])if(job[kind]){assert.equal(bound(job[kind].path).sha256,job[kind].sha256);await verifyUrl(new URL(settings.audio[kind],args['page-url']).href,job[kind].path)}
   await p.waitForFunction(()=>window.__tracks?.length>0&&window.__tracks.every(a=>a.readyState>=3));
   const cue=settings.subtitleCues[0];const time=cue?(cue.start+cue.end)/2:0;
   await p.locator('video').evaluate((v,t)=>v.currentTime=t,time);await p.waitForFunction(()=>!document.querySelector('video').seeking);
   if(cue){await p.waitForTimeout(300);report.subtitleDebug=await p.evaluate(()=>({text:document.querySelector('#subtitle').textContent,time:document.querySelector('video').currentTime,on:document.querySelector('#subsOn').checked,settings:JSON.parse(document.querySelector('#tour-page-data').textContent).subtitleCues}));assert.equal(report.subtitleDebug.text,cue.text);await p.locator('#subsOn').uncheck();assert.equal(await p.locator('#subtitle').textContent(),'');await p.locator('#subsOn').check();report.pageControls.push('subtitle-switch')}
   await p.locator('video').evaluate(v=>v.play());await p.waitForTimeout(180);
   report.pageAudio=await p.evaluate(()=>({time:document.querySelector('video').currentTime,tracks:window.__tracks.map(a=>({time:a.currentTime,volume:a.volume,paused:a.paused}))}));
   for(const t of report.pageAudio.tracks)assert(Math.abs(t.time-report.pageAudio.time)<.4);
   for(const kind of ['voice','music'])if(job[kind]){await p.locator('#'+kind+'On').uncheck();await p.waitForFunction(kind=>window.__tracks.find(a=>a.src.includes(kind)).paused,kind);await p.locator('#'+kind+'On').check()}
   await p.locator('video').evaluate(v=>v.muted=true);await p.waitForFunction(()=>window.__tracks.every(a=>a.volume===0));await p.locator('video').evaluate(v=>v.pause());report.pageControls.push('voice-music-switches','master-mute','bound-audio-sources');
  }
  await p.setViewportSize({width:390,height:844});assert(await p.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));report.pageControls.push('mobile-no-overflow');
 }
 assert.deepEqual(report.errors,[]);report.status='passed';report.visualReviewRequired=true;
}finally{fs.writeFileSync(args.out,JSON.stringify(report,null,2));await browser.close()}
console.log(JSON.stringify({status:report.status,ended:report.ended,seconds:report.seconds,droppedFrames:report.droppedFrames,pageControls:report.pageControls}));
