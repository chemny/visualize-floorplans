// Run only against an isolated synthetic workbench; never edit a user's current project.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
const [workbench,out]=process.argv.slice(2);if(!workbench||!out)throw Error('Usage: node test_sliding_editor.mjs synthetic-workbench.html output-directory');
if(!process.env.INTERIOR_PLAYWRIGHT_MODULE||!process.env.INTERIOR_BROWSER)throw Error('Set INTERIOR_PLAYWRIGHT_MODULE and INTERIOR_BROWSER to existing runtime paths; no install performed');
const {chromium}=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href);
const b=await chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true});fs.mkdirSync(out,{recursive:true});
try{
 const p=await b.newPage({viewport:{width:1440,height:1050}}),errors=[];p.on('pageerror',e=>errors.push(e.message));await p.goto(pathToFileURL(path.resolve(workbench)).href);await p.waitForFunction(()=>window.homeStudio?.getSlidingDoorChecks);
 assert.equal(await p.evaluate(()=>homeStudio.getState().caseId),'synthetic-sliding-editor','Must use synthetic test case');
 const baseline=await p.evaluate(()=>homeStudio.getState()),rows=[];
 async function select(wallId,id){await p.evaluate(({wallId,id})=>homeStudio.select({kind:'opening',wallId,openingId:id,index:0}),{wallId,id});await p.locator('#openingLeaves').waitFor();}
 async function setValue(selector,value){await p.locator(selector).evaluate((e,v)=>{e.value=String(v);e.dispatchEvent(new Event('change',{bubbles:true}));},value);}
 async function check(id,n,dir,op){
  const r=await p.evaluate(id=>{const g=homeStudio.getSlidingDoorChecks().find(x=>x.openingId===id);const rects=[...document.querySelectorAll('[data-sliding-panel="'+id+'"]')].map(e=>Object.fromEntries(['x','y','width','height'].map(k=>[k,Number(e.getAttribute(k))])));return {g,rects,text:document.querySelector('[data-sliding-net-opening]')?.textContent};},id);
  assert.equal(r.g.panels.length,n);assert.equal(r.rects.length,n);assert(r.text.includes(String(Math.round(r.g.netOpeningMm))));r.g.panels.forEach((a,i)=>{const z=r.rects[i];assert(Math.abs(z.x-(a.cx-a.w/2))<1e-7);assert(Math.abs(z.y-(a.cy-a.d/2))<1e-7);assert.equal(z.width,a.w);assert.equal(z.height,a.d);});
  rows.push({id,n,dir,op,netOpeningMm:r.g.netOpeningMm,planMatches:true});return r.g;
 }
 for(const [wallId,id]of [['W0','D0'],['W1','D1']]){
  await select(wallId,id);
  for(const n of [2,3])for(const dir of [-1,1])for(const op of [0,50,100]){await setValue('#openingLeaves',n);await setValue('#openingSlideDirection',dir);await setValue('#openingSlideOpen',op);await check(id,n,dir,op);}
 }
 let after=await p.evaluate(()=>homeStudio.getState());assert.deepEqual(after.walls[1],baseline.walls[1],'Protected aperture must remain unchanged');assert.equal(after.doorStyles.D1.leaves,3);assert.equal(after.doorStyles.D1.slideOpen,1);
 await select('W2','D2');await p.waitForFunction(()=>document.querySelector('#openingLeaves option[value="3"]')?.disabled);await setValue('#openingLeaves',3);assert.equal((await p.evaluate(()=>homeStudio.getSlidingDoorChecks().find(x=>x.openingId==='D2'))).panels.length,2,'invalid edit rolled back');
 await select('W0','D0');await setValue('#openingSlideOpen',50);const half=await check('D0',3,1,50);await p.evaluate(()=>homeStudio.undo());await select('W0','D0');assert.equal(await p.locator('#openingSlideOpen').inputValue(),'100');await p.evaluate(()=>homeStudio.redo());await select('W0','D0');assert.equal(await p.locator('#openingSlideOpen').inputValue(),'50');
 await p.screenshot({path:path.join(out,'editor-2d.png')});
 await p.evaluate(()=>homeStudio.setView('3d'));await p.waitForFunction(()=>homeStudio.inspect().mode==='3d'&&!homeStudio.inspect().switching);
 await select('W0','D0');await setValue('#openingSlideDirection',-1);await setValue('#openingSlideOpen',100);
 const mesh=await p.evaluate(()=>{const d=homeStudio.get3D();d.archUp.updateMatrixWorld(true);const result=[];d.archUp.traverse(g=>{if(!g.userData.slidingLeaf)return;let bounds=null;g.traverse(m=>{if(!m.isMesh)return;m.geometry.computeBoundingBox();const box=m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld);if(bounds)bounds.union(box);else bounds=box;});result.push({opening:g.userData.opening,position:[g.position.x,g.position.z],size:bounds?[bounds.max.x-bounds.min.x,bounds.max.z-bounds.min.z]:null});});return {leaves:result,checks:homeStudio.getSlidingDoorChecks()};});
 const origins=[];for(const g of mesh.checks){const leaves=mesh.leaves.filter(x=>x.opening.openingId===g.openingId);assert.equal(leaves.length,g.panels.length,'actual mesh count');g.panels.forEach((panel,i)=>{const leaf=leaves[i];origins.push([panel.cx-leaf.position[0]*1000,panel.cy-leaf.position[1]*1000]);assert(Math.abs(leaf.size[0]*1000-panel.w)<.002);assert(Math.abs(leaf.size[1]*1000-panel.d)<.002);});}for(const o of origins)assert(Math.hypot(o[0]-origins[0][0],o[1]-origins[0][1])<.002,'actual mesh centres match plan with common world origin');
 assert.equal(await p.locator('#openingSlideDirection').inputValue(),'-1');await p.screenshot({path:path.join(out,'editor-3d.png')});
 await p.evaluate(()=>homeStudio.saveScheme());const saved=await p.evaluate(()=>homeStudio.getState());await p.reload();await p.waitForFunction(()=>window.homeStudio?.getSlidingDoorChecks);assert.deepEqual(await p.evaluate(()=>homeStudio.getState().doorStyles),saved.doorStyles);assert.deepEqual(await p.evaluate(()=>homeStudio.getState().walls),saved.walls);
 assert.deepEqual(saved.furniture,baseline.furniture);for(const [i,w]of saved.walls.entries()){assert.deepEqual(w.a,baseline.walls[i].a);assert.deepEqual(w.b,baseline.walls[i].b);assert.equal(w.opens[0]?.width,baseline.walls[i].opens[0]?.width);}
 assert.deepEqual(errors,[]);fs.writeFileSync(path.join(out,'browser-check.json'),JSON.stringify({status:'pass',rows,actualMeshes:mesh,protectedApertureUnchanged:true,undoRedo:true,reloadPersistence:true,errors},null,2));console.log(JSON.stringify({status:'pass',uiStates:rows.length,actualMeshLeaves:mesh.leaves.length,undoRedo:true,reload:true}));
}finally{await b.close();}
