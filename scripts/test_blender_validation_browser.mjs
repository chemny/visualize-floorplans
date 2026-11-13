/** Run against actual generated sample pages with an existing Playwright page. */
import assert from 'node:assert/strict';
export async function checkBlenderValidationPage(page,{url,durations}){
 await page.goto(url);await page.waitForFunction(()=>[...document.querySelectorAll('video')].every(v=>v.readyState>=1));assert.equal(await page.locator('video').count(),durations.length);
 assert(await page.evaluate(()=>[...document.querySelectorAll('video')].every(v=>{const r=v.getBoundingClientRect();return Math.abs(r.width/r.height-16/9)<.01})));
 const playback=[];
 for(let i=0;i<durations.length;i++){
  const result=await page.evaluate(async i=>{const v=document.querySelectorAll('video')[i];v.loop=false;v.muted=true;await v.play();await new Promise(resolve=>{if(v.ended)resolve();else v.addEventListener('ended',resolve,{once:true})});const q=v.getVideoPlaybackQuality();return{ended:v.ended,seconds:v.duration,dropped:q.droppedVideoFrames}},i);
  assert(result.ended);assert(Math.abs(result.seconds-durations[i])<.01);playback.push(result);
 }
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));return{playback,aspect16by9:true,mobileNoOverflow:true};
}
