// Browser regression: same-type variant switching, TV sizes, and flush doorway floors.
// Usage: INTERIOR_PLAYWRIGHT_MODULE=/abs/playwright/index.js INTERIOR_BROWSER=/abs/chrome node test_variant_switch.mjs HTTP_URL REPORT.json
// HTTP_URL is any generated workbench with walls; the test adds its own furniture and never edits a user design.
import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [url,out]=process.argv.slice(2);
if(!/^https?:\/\//.test(url||'')||!out)throw Error('Usage: node test_variant_switch.mjs HTTP_URL REPORT.json');
if(!process.env.INTERIOR_PLAYWRIGHT_MODULE||!process.env.INTERIOR_BROWSER)throw Error('Use existing INTERIOR_PLAYWRIGHT_MODULE and INTERIOR_BROWSER; nothing is installed');
const imported=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href),pw=imported.default||imported;
const browser=await pw.chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true,args:['--enable-unsafe-swiftshader']});
const errors=[],report={url,checks:{}};
try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});page.on('pageerror',e=>errors.push(e.message));
 await page.goto(url);await page.waitForFunction(()=>window.homeStudio?.ready===true,null,{timeout:60000});
 const state=()=>page.evaluate(()=>homeStudio.getState());
 const add=async(type,patch)=>page.evaluate(async([type,patch])=>{const before=new Set(homeStudio.getState().furniture.map(f=>f.id));homeStudio.addCatalogItem(type,0,0);
  const f=homeStudio.getState().furniture.find(x=>x.type===type&&!before.has(x.id));homeStudio.updateObject(f.id,patch);homeStudio.select({kind:'furn',id:f.id});return f.id},[type,patch]);
 const pick=async label=>{const value=await page.evaluate(l=>[...document.querySelectorAll('#fVariant option')].find(o=>o.textContent.split(' · ')[0]===l)?.value,label);assert.ok(value,'option '+label);await page.selectOption('#fVariant',value);await page.waitForTimeout(250)};
 const find=async id=>(await state()).furniture.find(f=>f.id===id);
 // 1. Library: single/double-door fridge names and the four TV sizes.
 const catalog=await page.evaluate(()=>homeStudio.getCatalog());const items=catalog.flatMap(g=>g.items);
 assert.ok(items.some(i=>i[1]==='单开门冰箱')&&items.some(i=>i[1]==='双开门冰箱'));
 assert.deepEqual(items.filter(i=>i[0]==='tv').map(i=>i[2]).sort((a,b)=>a-b),[1230,1450,1680,1900],'55/65/75/85 inch TVs');
 const P=await page.evaluate(()=>{const area=p=>Math.abs(p.reduce((n,a,i)=>{const b=p[(i+1)%p.length];return n+a[0]*b[1]-b[0]*a[1]},0))/2;const r=homeStudio.getModel().rooms.filter(r=>r.poly.length===4).sort((a,b)=>area(b.poly)-area(a.poly))[0];const xs=r.poly.map(p=>p[0]),ys=r.poly.map(p=>p[1]);return [(Math.min(...xs)+Math.max(...xs))/2,(Math.min(...ys)+Math.max(...ys))/2]});
 // 1b. Short labels, ascending order, merged chairs.
 const labelsOf=async(type,patch)=>{await add(type,patch);await page.waitForSelector('#fVariant');return page.evaluate(()=>[...document.querySelectorAll('#fVariant option')].map(o=>o.textContent))};
 assert.deepEqual(await labelsOf('bed',{cx:P[0],cy:P[1],rot:0}),['单人 · 1200×2000','1.5 米 · 1500×2000','1.8 米 · 1800×2000','2.2 米 · 2200×2000','自定义…']);
 assert.deepEqual(await labelsOf('fridge',{cx:P[0],cy:P[1],rot:0}),['单开门 · 700×700','双开门 · 910×700']);
 assert.deepEqual((await labelsOf('tv',{cx:P[0],cy:P[1],rot:0})).slice(0,4),['55 寸 · 1230×35','65 寸 · 1450×35','75 寸 · 1680×35','85 寸 · 1900×35']);
 await add('chair',{cx:P[0],cy:P[1],rot:0});await page.waitForTimeout(400);
 assert.equal(await page.evaluate(()=>!!document.querySelector('#fVariant')),false,'椅子 and 餐椅 merge into one spec, so there is nothing to switch');
 assert.deepEqual(await labelsOf('nightstand',{cx:P[0],cy:P[1],rot:0}),['标准 · 450×400','自定义…']);
 // 2. Panel offers same-type variants, and a back-anchored item keeps its back edge when the depth changes.
 const wid=await add('wardrobe',{cx:P[0],cy:P[1],rot:0,fitToCeiling:false});
 await page.waitForSelector('#fVariant');
 const before=await find(wid);const back=f=>f.cy-f.d/2;
 await pick('1.2 米');const small=await find(wid);
 assert.deepEqual([small.w,small.d],[1200,550]);assert.ok(Math.abs(back(small)-back(before))<0.01,'back edge stays fixed');
 assert.ok(small.name.includes('小衣柜'),'catalog name follows the variant');
 await pick('2 米');const large=await find(wid);assert.deepEqual([large.w,large.d],[2000,600]);assert.ok(Math.abs(back(large)-back(before))<0.01);
 // A rotated item keeps its back edge too (rot 180: the back faces +y).
 await page.evaluate(([id,P0,P1])=>homeStudio.updateObject(id,{rot:180,cx:P0,cy:P1}),[wid,P[0],P[1]]);await page.evaluate(id=>homeStudio.select({kind:'furn',id}),wid);await page.waitForSelector('#fVariant');
 const flipped=await find(wid);await pick('1.2 米');const flippedSmall=await find(wid);
 assert.ok(Math.abs((flippedSmall.cy+flippedSmall.d/2)-(flipped.cy+flipped.d/2))<0.01,'back edge fixed when rotated');
 report.checks.backAnchor={before:[before.w,before.d],small:[small.w,small.d]};
 // 3. Fridge: single to double door keeps the centre line and the back edge.
 const fid=await add('fridge',{cx:P[0],cy:P[1],rot:180});await page.waitForSelector('#fVariant');const fb=await find(fid);
 await pick('双开门');const fd=await find(fid);assert.deepEqual([fd.w,fd.d],[910,700]);assert.ok(Math.abs((fd.cy+fd.d/2)-(fb.cy+fb.d/2))<0.01);assert.equal(fd.cx,fb.cx);
 // 4. Centre-anchored item (dining table) keeps its centre; TV height follows the screen width.
 const tid=await add('table',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#fVariant');await pick('六人');const t=await find(tid);assert.deepEqual([t.cx,t.cy,t.w,t.d],[P[0],P[1],1800,900]);
 const tvid=await add('tv',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#fVariant');await pick('85 寸');const tv=await find(tvid);assert.equal(tv.w,1900);assert.equal(tv.h,Math.round(1900*.5625+25));
 // 5. Walls: one side blocked -> the item grows toward the free side; no room on either side -> refused.
 const addWalls=(x1,x2,y0,y1,tag)=>page.evaluate(async([x1,x2,y0,y1,tag])=>{const o=JSON.parse(homeStudio.serializeScheme());
  for(const [id,x] of [['t-wall-'+tag+'-a',x1],['t-wall-'+tag+'-b',x2]])o.walls.push({id,a:[x,y0],b:[x,y1],t:100,height:2700,bearing:false,demolished:false,opens:[]});
  await homeStudio.importScheme(JSON.stringify(o))},[x1,x2,y0,y1,tag]);
 const X0=P[0]-5000,YA=P[1]-1500,YB=P[1]+1500; // a free stretch far to the left of the room centre
 const gap=1900,left=X0,right=X0+gap+100; // inner faces: left+50 .. right-50  => clear width = gap
 await addWalls(left,right,YA,YB,'wide');
 const faceL=left+50,faceR=right-50;
 const bid=await add('bed',{cx:faceL+10+750,cy:P[1],rot:0});await page.waitForSelector('#fVariant');
 await pick('1.5 米');await page.evaluate(([id,x,y])=>homeStudio.updateObject(id,{cx:x,cy:y}),[bid,faceL+10+750,P[1]]);await page.evaluate(id=>homeStudio.select({kind:'furn',id}),bid);await page.waitForSelector('#fVariant');
 assert.equal((await find(bid)).w,1500);
 await pick('1.8 米');const grown=await find(bid);
 assert.equal(grown.w,1800,'blocked on the left, so it grows toward the free right side');
 assert.ok(grown.cx-grown.w/2>=faceL-1&&grown.cx+grown.w/2<=faceR+1,'bed sits between the two walls');
 assert.ok(grown.cx>faceL+10+750,'the centre moved to the free side');
 report.checks.extendToFreeSide={cx:grown.cx,w:grown.w};
 // Now squeeze the same bed into a clear width of 1700: 1.8 m cannot fit on either side.
 const X1=X0-3000,narrowL=X1,narrowR=X1+1700+100,nfL=narrowL+50;
 await addWalls(narrowL,narrowR,YA,YB,'narrow');
 await page.evaluate(([id,x,y])=>homeStudio.updateObject(id,{w:1500,cx:x,cy:y}),[bid,nfL+10+750,P[1]]);await page.evaluate(id=>homeStudio.select({kind:'furn',id}),bid);await page.waitForSelector('#fVariant');
 await pick('1.8 米');const refused=await find(bid);
 assert.equal(refused.w,1500,'no room on either side: refused');report.checks.refusal='refused';
 // 6a. Sizes asked for: sofa bed 1.2/1.5/1.8 m and the 2.2 m bed.
 assert.deepEqual(items.filter(i=>i[0]==='sofabed').map(i=>i[2]).sort((a,b)=>a-b),[1200,1500,1800]);
 assert.ok(items.some(i=>i[0]==='bed'&&i[2]===2200),'2.2 m bed in the library');
 const sbid=await add('sofabed',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#fVariant');await pick('1.8 米');const sb=await find(sbid);assert.deepEqual([sb.w,sb.d],[1800,820]);
 const b22=await add('bed',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#fVariant');await pick('2.2 米');assert.equal((await find(b22)).w,2200);
 // 6b. A custom entry exists for flexible furniture only; fixed appliances just switch between library specs.
 const opts=()=>page.evaluate(()=>({panel:[...document.querySelectorAll('#fVariant option')].map(o=>o.textContent),fab:[...document.querySelectorAll('#fab #fabVariant option')].map(o=>o.textContent)}));
 await add('fridge',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#fVariant');const fo=await opts();
 assert.ok(fo.panel.length>=2&&!fo.panel.some(t=>t.includes('自定义…'))&&!fo.fab.some(t=>t.includes('自定义…')),'fridge: variants but no custom entry');
 await add('ksink',{cx:P[0],cy:P[1],rot:0});await page.waitForTimeout(400);
 assert.equal(await page.evaluate(()=>!!document.querySelector('#fVariant')||!!document.querySelector('#fab #fabVariant')),false,'sink: no spec menu at all');
 const tb=await add('table',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#fVariant');const to=await opts();
 assert.ok(to.panel.some(t=>t.includes('自定义…'))&&to.fab.some(t=>t.includes('自定义…')),'table offers a custom entry');
 await page.selectOption('#fab #fabVariant',{label:to.fab.find(t=>t.includes('自定义…'))});await page.waitForSelector('#furnitureSizeForm');
 await page.fill('#sizeLength','2000');await page.fill('#sizeDepth','1000');await page.evaluate(()=>document.querySelector('#furnitureSizeForm').requestSubmit());await page.waitForTimeout(500);
 const ct=await find(tb);assert.deepEqual([ct.w,ct.d],[2000,1000],'custom size applies');
 // 6c. Heights of fixed-height furniture are not asked for; adjustable ones still are.
 await page.evaluate(id=>homeStudio.select({kind:'furn',id}),tb);await page.waitForSelector('#editFurnitureSize');await page.click('#editFurnitureSize');await page.waitForSelector('#furnitureSizeForm');
 assert.equal(await page.evaluate(()=>!!document.querySelector('#sizeHeight')),false,'table: no height field');
 const hidd=await add('wardrobe',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#editFurnitureSize');await page.click('#editFurnitureSize');await page.waitForSelector('#furnitureSizeForm');
 assert.equal(await page.evaluate(()=>!!document.querySelector('#sizeHeight')),true,'wardrobe keeps its height field');
 const plat=await add('platform',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#editFurnitureSize');await page.click('#editFurnitureSize');await page.waitForSelector('#furnitureSizeForm');
 assert.equal(await page.evaluate(()=>!!document.querySelector('#sizeHeight')),true,'platform keeps its height field');
 // 6d. Coffee tables: only two shapes (round, square), each with three presets; switching between them changes the shape.
 assert.deepEqual(items.filter(i=>i[0]==='coffee').map(i=>i[2]).sort((a,b)=>a-b),[600,800,1000]);
 assert.deepEqual(items.filter(i=>i[0]==='coffeetable').map(i=>i[2]+'x'+i[3]).sort(),['1200x600','1400x700','800x800']);
 const cid=await add('coffee',{cx:P[0],cy:P[1],rot:0});await page.waitForSelector('#fVariant');
 const shapeMenu=await page.evaluate(()=>({groups:[...document.querySelectorAll('#fVariant optgroup')].map(g=>g.label),options:[...document.querySelectorAll('#fVariant option')].map(o=>o.textContent)}));
 assert.deepEqual(shapeMenu.groups,['圆形','方形']);
 assert.deepEqual(shapeMenu.options.slice(-7),['Ø600','Ø800','Ø1000','800×800','1200×600','1400×700','自定义…']);
 const c0=await find(cid);await pick('1200×600');const c1=await find(cid);
 assert.deepEqual([c1.type,c1.w,c1.d,c1.cx,c1.cy],['coffeetable',1200,600,c0.cx,c0.cy],'round to rectangular keeps the centre');
 assert.equal(c1.originalType,undefined);
 await page.evaluate(()=>homeStudio.setView('3d'));await page.waitForTimeout(2000);
 const span=await page.evaluate(id=>{const g=homeStudio.get3D().furnG.children.find(o=>o.userData.fid===id);let x0=1e9,x1=-1e9,z0=1e9,z1=-1e9;g.traverse(o=>{if(o.isMesh&&o.geometry){o.geometry.computeBoundingBox();const b=o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld);x0=Math.min(x0,b.min.x);x1=Math.max(x1,b.max.x);z0=Math.min(z0,b.min.z);z1=Math.max(z1,b.max.z)}});return [x1-x0,z1-z0]},cid);
 assert.ok(Math.abs(span[0]-1.2)<0.06&&Math.abs(span[1]-0.6)<0.06,'3D table follows the new shape: '+span);
 await page.evaluate(()=>homeStudio.setView('2d'));await page.evaluate(id=>homeStudio.select({kind:'furn',id}),cid);await page.waitForSelector('#fVariant');
 await pick('Ø800');const c2=await find(cid);assert.deepEqual([c2.type,c2.w,c2.d],['coffee',800,800],'back to round');
 report.checks.coffeeShapes=[c1.type,c2.type];
 // 6. Doorway floors are flush: no raised thresholds by default and no floor mesh above the floor level.
 const thresholds=(await state()).furniture.filter(f=>f.type==='threshold').length;assert.equal(thresholds,0,'no threshold stones unless switched on');
 await page.evaluate(()=>homeStudio.setView('3d'));await page.waitForTimeout(2500);
 const tops=await page.evaluate(()=>{const g=homeStudio.get3D(),t=[];g.archFloor.traverse(o=>{if(o.isMesh&&o.geometry){o.geometry.computeBoundingBox();t.push(+o.geometry.boundingBox.clone().applyMatrix4(o.matrixWorld).max.y.toFixed(4))}});return t});
 assert.ok(tops.length>0&&Math.max(...tops)<=0.0025,'all floor surfaces at floor level: '+Math.max(...tops));report.checks.floorTops=[...new Set(tops)];
 assert.deepEqual(errors,[],'no page errors');report.status='pass';
}catch(e){report.status='fail';report.error=String(e.stack||e);throw e}
finally{fs.writeFileSync(out,JSON.stringify({...report,errors},null,2));await browser.close()}
