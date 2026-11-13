// Real generated page: scale from the video container, including mobile/fullscreen.
import fs from 'node:fs';import assert from 'node:assert/strict';import{pathToFileURL}from'node:url';
const[url,out]=process.argv.slice(2);
const{default:pw}=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href);
const browser=await pw.chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true});
const page=await browser.newPage({viewport:{width:1440,height:1000}}),report={errors:[],samples:[]};
try{
 page.on('pageerror',e=>report.errors.push(e.message));await page.goto(url);
 await page.waitForFunction(()=>document.querySelector('video')?.readyState>=2);
 await page.evaluate(()=>new Promise(r=>{const v=document.querySelector('video');v.addEventListener('seeked',r,{once:true});v.currentTime=12}));
 await page.waitForTimeout(250);await page.locator('video').evaluate(v=>v.controls=false);
 async function sample(mode){
  const row=await page.locator('.subtitle').evaluate(el=>{const s=getComputedStyle(el),span=getComputedStyle(el.querySelector('span')),player=el.closest('.player').getBoundingClientRect();return{width:player.width,font:parseFloat(s.fontSize),stroke:parseFloat(s.webkitTextStrokeWidth),strokeColor:s.webkitTextStrokeColor,weight:s.fontWeight,shadow:span.textShadow,background:span.backgroundColor,paintOrder:s.paintOrder,text:el.textContent}});
  assert(Math.abs(row.font-38*row.width/1280)<.02);assert(Math.abs(row.stroke-3.3*row.width/1280)<.02);
  assert.equal(row.strokeColor,'rgb(0, 0, 0)');assert.equal(row.weight,'400');assert.equal(row.shadow,'none');assert.equal(row.background,'rgba(0, 0, 0, 0)');assert(row.text);assert.equal(row.paintOrder,'stroke');
  report.samples.push({mode,...row});await page.screenshot({path:out.replace(/\.json$/,`-${mode}.png`),fullPage:true});
 }
 await sample('desktop');
 await page.locator('.player').evaluate(el=>el.requestFullscreen());await page.waitForTimeout(250);assert(await page.evaluate(()=>!!document.fullscreenElement));await sample('fullscreen');await page.evaluate(()=>document.exitFullscreen());
 await page.setViewportSize({width:390,height:844});await sample('mobile');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.locator('#subsOn').uncheck();assert.equal(await page.locator('#subtitle').innerText(),'');await page.locator('#subsOn').check();assert(await page.locator('#subtitle').innerText());
 assert.deepEqual(report.errors,[]);report.status='passed';
}finally{fs.writeFileSync(out,JSON.stringify(report,null,2));await browser.close()}
console.log(JSON.stringify({status:report.status,modes:report.samples.map(s=>s.mode)}));
