// Shared continuous preview sampler. Source frames and capture timing stay intact.
export function samplePose(tour,seconds){
 const at=Math.max(0,Math.min(tour.frames.length-1,seconds*tour.fps)),i=Math.floor(at),a=tour.frames[i],b=tour.frames[Math.min(i+1,tour.frames.length-1)],u=b.cutBefore?0:at-i;
 const mix=(x,y)=>x+(y-x)*u,dy=Math.atan2(Math.sin(b.yawRadians-a.yawRadians),Math.cos(b.yawRadians-a.yawRadians));
 const f={...a,pointMm:a.pointMm.map((v,k)=>mix(v,b.pointMm[k])),yawRadians:a.yawRadians+dy*u,pitchRadians:mix(a.pitchRadians,b.pitchRadians)};
 for(const key of ['eyeMm','horizontalFovDegrees','shiftY'])if(Number.isFinite(a[key])&&Number.isFinite(b[key]))f[key]=mix(a[key],b[key]);
 if('fadeToBlack'in a||'fadeToBlack'in b)f.fadeToBlack=mix(a.fadeToBlack??0,b.fadeToBlack??0);
 return f;
}
const percentile=(v,p)=>v.length?[...v].sort((a,b)=>a-b)[Math.min(v.length-1,Math.floor((v.length-1)*p))]:0;
export class TimelinePlayer{
 constructor({getRenderer,onTime=()=>{},onStats=()=>{},onState=()=>{},mode='smooth',raf=cb=>requestAnimationFrame(cb),now=()=>performance.now()}){
  Object.assign(this,{getRenderer,onTime,onStats,onState,mode,raf,now});this.playing=false;this.at=0;this.busy=false;this.last=null;this.epoch=0;this.tour=null;this.range=null;this.resetStats();this.raf(t=>this.tick(t));
 }
 resetStats(){this.stats={draws:0,skippedBusy:0,intervals:[],cpu:[],startedAt:null,lastDraw:null};}
 statsReport(){const s=this.stats,span=s.lastDraw!==null&&s.startedAt!==null?(s.lastDraw-s.startedAt)/1000:0;return{mode:this.mode,draws:s.draws,updatesPerSecond:span>0?(s.draws-1)/span:0,p95FrameMs:percentile(s.intervals,.95),longFramesOver100ms:s.intervals.filter(v=>v>100).length,p95SubmitMs:percentile(s.cpu,.95),skippedBusy:s.skippedBusy,seconds:span};}
 setTour(tour,range=null){this.epoch++;this.tour=tour;this.range=range||[0,(tour.frames.length-1)/tour.fps];this.at=this.range[0];this.playing=false;this.last=null;this.resetStats();this.draw(true);this.onState(false);}
 setMode(mode){this.epoch++;this.mode=mode;this.resetStats();this.draw(true);}
 seek(at){this.epoch++;this.at=Math.max(this.range[0],Math.min(this.range[1],at));this.playing=false;this.last=null;this.draw(true);this.onState(false);}
 play(){if(!this.tour||!this.getRenderer()?.rendererReady)return;if(this.at>=this.range[1])this.at=this.range[0];this.last=null;this.resetStats();this.playing=true;this.onState(true);}
 pause(){this.playing=false;this.last=null;this.onState(false);this.onStats(this.statsReport());}
 draw(force=false){
  if(!this.tour)return;const view=this.getRenderer();if(!view?.rendererReady)return;
  if(this.busy){this.stats.skippedBusy++;return;}
  const token=this.epoch,submitted=this.now(),record=this.playing||force;
  const frame=this.mode==='legacy'?this.tour.frames[Math.min(this.tour.frames.length-1,Math.round(this.at*this.tour.fps))]:samplePose(this.tour,this.at);
  const completed=()=>{this.busy=false;if(token!==this.epoch){this.draw(true);return;}if(record){const s=this.stats,time=this.now();if(s.startedAt===null)s.startedAt=time;if(s.lastDraw!==null)s.intervals.push(time-s.lastDraw);s.lastDraw=time;s.draws++;s.cpu.push(time-submitted);if(s.draws%15===0)this.onStats(this.statsReport());}};
  if(this.mode==='legacy'){this.busy=true;Promise.resolve(view.renderFrame(frame)).then(completed).catch(e=>{this.busy=false;this.pause();this.onState(false,e.message);});}
  else {if(typeof view.renderInteractiveFrame!=='function')throw Error('Updated interactive renderer required');view.renderInteractiveFrame(frame);completed();}
  this.onTime(this.at);
 }
 tick(time){
  if(this.playing&&this.tour){if(this.last!==null)this.at=Math.min(this.range[1],this.at+Math.max(0,time-this.last)/1000);this.last=time;this.draw();if(this.at>=this.range[1])this.pause();}
  this.raf(t=>this.tick(t));
 }
}
export async function initPreview(){
 const $=id=>document.getElementById(id),view=$('view'),plan=$('plan');
 const player=new TimelinePlayer({getRenderer:()=>view.contentWindow,onTime:at=>{$('seek').value=at;$('clock').textContent=at.toFixed(1)+' / '+player.tour.seconds.toFixed(1)+' 秒';plan.contentWindow.rehearsalPlayback?.setTime(at);},onState:playing=>{$('play').textContent=playing?'暂停':'播放';}});
 const tour=await fetch('replay.json',{cache:'no-store'}).then(r=>r.json());$('seek').max=(tour.frames.length-1)/tour.fps;player.setTour(tour);
 $('play').onclick=()=>player.playing?player.pause():player.play();$('reset').onclick=()=>{player.seek(0);player.play();};$('seek').oninput=()=>player.seek(Number($('seek').value));
 window.addEventListener('message',e=>{if(e.source===plan.contentWindow&&e.origin===location.origin&&e.data?.kind==='homeowner-seek'&&Number.isFinite(e.data.seconds))player.seek(e.data.seconds);});
 document.addEventListener('visibilitychange',()=>{if(document.hidden)player.pause();});
 const ready=setInterval(()=>{if(view.contentWindow.rendererReady&&plan.contentWindow.rehearsalPlayback){clearInterval(ready);$('play').disabled=false;$('reset').disabled=false;player.draw(true);}},100);
 plan.onload=()=>player.draw(true);
}
