// Browser regression: night room lights stay inside their room and scale with room size.
// Usage: INTERIOR_PLAYWRIGHT_MODULE=/abs/playwright/index.js INTERIOR_BROWSER=/abs/chrome node test_night_lighting.mjs HTTP_URL REPORT.json
// HTTP_URL is any generated workbench with ceiling fixtures; the test only reads the lights.
import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [url,out]=process.argv.slice(2);
if(!/^https?:\/\//.test(url||'')||!out)throw Error('Usage: node test_night_lighting.mjs HTTP_URL REPORT.json');
if(!process.env.INTERIOR_PLAYWRIGHT_MODULE||!process.env.INTERIOR_BROWSER)throw Error('Use existing INTERIOR_PLAYWRIGHT_MODULE and INTERIOR_BROWSER; nothing is installed');
const imported=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href),pw=imported.default||imported;
const browser=await pw.chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true,args:['--enable-unsafe-swiftshader']});
const errors=[],report={url,checks:{}};
try{
 const page=await browser.newPage({viewport:{width:1280,height:900}});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.homeStudio?.ready===true,null,{timeout:60000});
 await page.evaluate(()=>homeStudio.setView('3d'));await page.waitForTimeout(2500);
 await page.evaluate(()=>document.querySelector('[data-light-mode="night"]').click());await page.waitForTimeout(2500);
 const rows=await page.evaluate(()=>{const g=homeStudio.get3D(),m=homeStudio.getModel(),W=m.width,D=m.depth;
  const inside=(x,y,poly)=>{let on=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const[a,b]=poly[i],[c,d]=poly[j];if(((b>y)!==(d>y))&&x<(c-a)*(y-b)/(d-b)+a)on=!on}return on};
  const area=poly=>Math.abs(poly.reduce((n,a,i)=>{const b=poly[(i+1)%poly.length];return n+a[0]*b[1]-b[0]*a[1]},0))/2e6;
  const out=[];g.scene.traverse(o=>{if(!(o.isLight&&o.type==='PointLight'&&o.visible))return;const x=o.position.x*1000+W/2,y=o.position.z*1000+D/2,r=m.rooms.find(r=>inside(x,y,r.poly));if(!r)return;
   const reach=Math.max(...r.poly.map(q=>Math.hypot(q[0]-x,q[1]-y)))/1000;out.push({room:r.id,area:area(r.poly),reach:Math.hypot(reach,o.position.y),distance:o.distance,intensity:o.intensity})});return out});
 assert.ok(rows.length>=3,'room lights found');
 for(const r of rows)assert.ok(r.distance<=r.reach*1.1+0.05,`${r.room}: range ${r.distance.toFixed(2)} stays within its room (farthest corner ${r.reach.toFixed(2)} m)`);
 const sorted=[...rows].sort((a,b)=>a.area-b.area),small=sorted[0],large=sorted[sorted.length-1];
 assert.ok(large.intensity>small.intensity,`strength follows room size: ${small.room} ${small.intensity.toFixed(2)} < ${large.room} ${large.intensity.toFixed(2)}`);
 assert.ok(rows.every(r=>r.intensity<=9.5+1e-6),'group strength cap');
 report.checks.lights=rows.map(r=>({room:r.room,area:+r.area.toFixed(1),distance:+r.distance.toFixed(2),intensity:+r.intensity.toFixed(2)}));
 assert.deepEqual(errors,[],'no page errors');report.status='pass';
}catch(e){report.status='fail';report.error=String(e.stack||e);throw e}
finally{fs.writeFileSync(out,JSON.stringify({...report,errors},null,2));await browser.close()}
