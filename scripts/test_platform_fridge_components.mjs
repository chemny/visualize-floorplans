// Browser regression for the platform (step) component and the double-door fridge library entry.
// Usage: INTERIOR_PLAYWRIGHT_MODULE=/abs/playwright/index.js INTERIOR_BROWSER=/abs/chrome node test_platform_fridge_components.mjs HTTP_URL REPORT.json
// HTTP_URL is any generated workbench served over HTTP. The test adds its own platform and never edits a user design.
import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [url,out]=process.argv.slice(2);
if(!/^https?:\/\//.test(url||'')||!out)throw Error('Usage: node test_platform_fridge_components.mjs HTTP_URL REPORT.json');
if(!process.env.INTERIOR_PLAYWRIGHT_MODULE||!process.env.INTERIOR_BROWSER)throw Error('Use existing INTERIOR_PLAYWRIGHT_MODULE and INTERIOR_BROWSER; nothing is installed');
const imported=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href),pw=imported.default||imported;
const browser=await pw.chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true,args:['--enable-unsafe-swiftshader']});
const errors=[],report={url,checks:{}};
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.homeStudio?.ready===true,null,{timeout:60000});
 // 1. Library: both fridges in the kitchen/dining group, the platform in its own group.
 const catalog=await page.evaluate(()=>homeStudio.getCatalog());
 const group=name=>catalog.find(g=>g.cat===name)?.items||[];
 const fridges=group('餐厨').filter(i=>i[0]==='fridge').map(i=>[i[1],i[2],i[3]]);
 assert.deepEqual(fridges.map(f=>f[0]).sort(),['单开门冰箱','双开门冰箱'].sort(),'餐厨 must offer the single and the double-door fridge');
 assert.ok(fridges.find(f=>f[0]==='双开门冰箱')[1]>850,'double-door fridge must be wider than the side-by-side threshold');
 const platformItem=group('构造').find(i=>i[0]==='platform');assert.ok(platformItem,'构造 group must hold the platform component');
 report.checks.library={fridges,platform:platformItem.slice(0,4)};
 // 2. A platform can be added with its documented defaults, takes the wall colour, and keeps its place.
 const id=await page.evaluate(async()=>{const before=new Set(homeStudio.getState().furniture.map(f=>f.id));
  homeStudio.addCatalogItem('platform',0,0);const added=homeStudio.getState().furniture.find(f=>f.type==='platform'&&!before.has(f.id));return added?.id||null});
 assert.ok(id,'addCatalogItem must create a platform');
 const added=await page.evaluate(id=>{const f=homeStudio.getState().furniture.find(x=>x.id===id);return {h:f.h,e:f.elevation||0,color:f.color,wall:homeStudio.getStyle?.(homeStudio.getState().style)?.palette?.wall}},id);
 assert.equal(added.h,550,'default platform height');assert.equal(added.e,0);
 if(added.wall)assert.equal(added.color.toLowerCase(),added.wall.toLowerCase(),'platform body follows the style wall colour');
 report.checks.added=added;
 // 3. Resize and place it exactly, then check the 3D object: one body box plus one thin marble top.
 await page.evaluate(id=>{homeStudio.updateObject(id,{cx:3000,cy:3000,w:750,d:2740,h:550})},id);
 await page.evaluate(()=>homeStudio.setView('3d'));await page.waitForTimeout(2500);
 const solid=await page.evaluate(id=>{const g=homeStudio.get3D().furnG.children.find(o=>o.userData.fid===id);if(!g)return null;const meshes=[];g.traverse(o=>{if(o.isMesh){o.geometry.computeBoundingBox();const b=o.geometry.boundingBox;meshes.push({h:+(b.max.y-b.min.y).toFixed(4),w:+(b.max.x-b.min.x).toFixed(3),d:+(b.max.z-b.min.z).toFixed(3),color:'#'+o.material.color.getHexString()})}});return meshes},id);
 assert.ok(solid,'platform must have a 3D object');assert.equal(solid.length,2,'body plus top');
 const [body,top]=solid.sort((a,b)=>b.h-a.h);assert.ok(Math.abs(body.h+top.h-0.55)<0.002,'total height 550 mm');assert.ok(top.h<=0.016,'thin top slab');
 assert.equal(top.color,'#f1eee8','top slab uses the marble colour');assert.ok(Math.abs(body.w-0.75)<0.002&&Math.abs(body.d-2.74)<0.002,'footprint');
 report.checks.solid={body,top};
 // 4. The platform survives a save/import round trip (components the engine does not know are silently dropped).
 const kept=await page.evaluate(async id=>{const text=homeStudio.serializeScheme();await homeStudio.importScheme(text);const f=homeStudio.getState().furniture.find(x=>x.id===id);return f?{type:f.type,w:f.w,d:f.d,h:f.h}:null},id);
 assert.deepEqual(kept,{type:'platform',w:750,d:2740,h:550},'round trip keeps the platform');report.checks.roundTrip=kept;
 // 5. The 2D plan draws it as a solid block with a marble top.
 await page.evaluate(()=>homeStudio.setView('2d'));await page.waitForTimeout(800);
 const svg=await page.evaluate(()=>homeStudio.exportPlanSVG());assert.ok(svg.includes('fill="#f1eee8"'),'2D plan shows the marble top');assert.ok(svg.includes('台阶 550'),'2D plan labels the step height');
 // 6. The double-door fridge is a normal fridge at 910 x 700: it can be placed and validated like the single one.
 const fridge=await page.evaluate(async()=>{const before=new Set(homeStudio.getState().furniture.map(f=>f.id));
  homeStudio.addCatalogItem('fridge',0,0);const f=homeStudio.getState().furniture.find(x=>x.type==='fridge'&&!before.has(x.id));
  homeStudio.updateObject(f.id,{w:910,d:700});homeStudio.validate(homeStudio.getState());const g=homeStudio.getState().furniture.find(x=>x.id===f.id);return {type:g.type,w:g.w,d:g.d,h:g.h}});
 assert.deepEqual(fridge,{type:'fridge',w:910,d:700,h:1800});report.checks.doubleDoorFridge=fridge;
 assert.deepEqual(errors,[],'no page errors');
 report.status='pass';
}catch(e){report.status='fail';report.error=String(e.stack||e);throw e}
finally{fs.writeFileSync(out,JSON.stringify({...report,errors},null,2));await browser.close()}
