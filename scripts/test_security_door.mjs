// Browser regression for the security (anti-theft) door: red-brown leaf and frame, inward/outward opening buttons.
// Usage: INTERIOR_PLAYWRIGHT_MODULE=/abs/playwright/index.js INTERIOR_BROWSER=/abs/chrome node test_security_door.mjs HTTP_URL REPORT.json
// HTTP_URL is any generated workbench with at least one door in an exterior wall; the test changes only its own page state.
import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [url,out]=process.argv.slice(2);
if(!/^https?:\/\//.test(url||'')||!out)throw Error('Usage: node test_security_door.mjs HTTP_URL REPORT.json');
if(!process.env.INTERIOR_PLAYWRIGHT_MODULE||!process.env.INTERIOR_BROWSER)throw Error('Use existing INTERIOR_PLAYWRIGHT_MODULE and INTERIOR_BROWSER; nothing is installed');
const imported=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href),pw=imported.default||imported;
const browser=await pw.chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true,args:['--enable-unsafe-swiftshader']});
const errors=[],report={url,checks:{}};
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.homeStudio?.ready===true,null,{timeout:60000});
 // The preset is offered in the architectural catalog.
 const catalog=await page.evaluate(()=>homeStudio.getArchitecturalCatalog());
 assert.ok(catalog.some(p=>p.id==='security'&&p.label==='防盗门'&&p.model==='security'));
 // Pick the entrance door when the case declares one, otherwise the first swing door.
 const target=await page.evaluate(()=>{const s=homeStudio.getState(),walls=homeStudio.getWalls();for(const w of walls)for(const o of w.opens)if(o.kind==='door'&&!o.leafRemoved&&o.id)return {wallId:w.id,openingId:o.id}});
 assert.ok(target,'needs a door');
 await page.evaluate(t=>homeStudio.select({kind:'opening',wallId:t.wallId,openingId:t.openingId}),target);
 await page.waitForSelector('#doorTypeMenu');
 await page.click('#doorTypeMenu summary');await page.click('[data-door-preset="security"]');await page.waitForTimeout(500);
 const effective=()=>page.evaluate(t=>{const s=homeStudio.getState(),w=s.walls.find(x=>x.id===t.wallId),raw=w.opens.find(o=>o.id===t.openingId),style=(s.doorStyles||{})[t.openingId]||(s.doorStyles||{})[t.wallId]||{};return {...raw,...style}},target);
 assert.equal((await effective()).doorModel,'security','door became a security door');
 // Inward/outward buttons exist, exactly one is pressed, and pressing the other flips the swing.
 await page.waitForSelector('#doorDirectionMenu');await page.click('#doorDirectionMenu summary');
 const pressed=()=>page.evaluate(()=>({in:document.querySelector('[data-security-open="in"]').getAttribute('aria-pressed'),out:document.querySelector('[data-security-open="out"]').getAttribute('aria-pressed')}));
 const first=await pressed();assert.notEqual(first.in,first.out,'exactly one direction is active');
 const swing0=(await effective()).swing||1;
 const other=first.in==='true'?'out':'in';await page.click(`[data-security-open="${other}"]`);await page.waitForTimeout(500);
 await page.click('#doorDirectionMenu summary').catch(()=>{});
 const swing1=(await effective()).swing||1;assert.equal(swing1,-swing0,'switching direction flips the swing');
 // 'in' means the leaf swings to the inside of the footprint: check it against the geometry itself.
 const inwardNow=await page.evaluate(t=>{const s=homeStudio.getState(),w=s.walls.find(x=>x.id===t.wallId),raw=w.opens.find(o=>o.id===t.openingId),style=(s.doorStyles||{})[t.openingId]||{},o={...raw,...style},L=Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]),ux=(w.b[0]-w.a[0])/L,uy=(w.b[1]-w.a[1])/L,sw=o.swing||1,inward=[-uy*sw,ux*sw],c=[w.a[0]+ux*(o.at+o.width/2),w.a[1]+uy*(o.at+o.width/2)],p=[c[0]+inward[0]*(w.t/2+500),c[1]+inward[1]*(w.t/2+500)],poly=homeStudio.getModel().footprint;let on=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const[a,b]=poly[i],[cc,d]=poly[j];if(((b>p[1])!==(d>p[1]))&&p[0]<(cc-a)*(p[1]-b)/(d-b)+a)on=!on}return on},target);
 const after=await pressed();assert.equal(after[inwardNow?'in':'out'],'true','pressed button agrees with the geometry');
 report.checks.direction={before:first,after,swing0,swing1,inwardNow};
 // 3D: leaf and raised panels are red-brown, the casing follows.
 await page.evaluate(()=>homeStudio.setView('3d'));await page.waitForTimeout(2500);
 const colours=await page.evaluate(()=>{const c={};homeStudio.get3D().scene.traverse(o=>{if(o.isMesh&&o.material&&o.material.color){const h=o.material.color.getHexString();c[h]=(c[h]||0)+1}});return c});
 assert.ok(colours['5f2220']>=1,'red-brown leaf');assert.ok(colours['74302a']>=2,'raised panels');
 const trim=await page.evaluate(()=>homeStudio.getState().furniture.filter(f=>f.type==='doortrim').map(f=>f.color.toLowerCase()));
 assert.ok(trim.includes('#4a1a17'),'door casing uses the security frame colour');
 report.checks.colours={leaf:colours['5f2220'],panel:colours['74302a'],trim:trim.filter(c=>c==='#4a1a17').length};
 assert.deepEqual(errors,[],'no page errors');report.status='pass';
}catch(e){report.status='fail';report.error=String(e.stack||e);throw e}
finally{fs.writeFileSync(out,JSON.stringify({...report,errors},null,2));await browser.close()}
