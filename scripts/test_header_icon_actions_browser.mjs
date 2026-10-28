import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
import {chooseTestTargets} from './workbench_test_targets.mjs';
const [url,out]=process.argv.slice(2);if(!/^https?:\/\//.test(url||'')||!out)throw Error('HTTP URL / report required');
const mod=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href),pw=mod.default||mod;
const b=await pw.chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true,args:['--enable-unsafe-swiftshader']});
const report={url,errors:[],executed:[],notExercised:[]};
try{
 const p=await b.newPage({viewport:{width:1440,height:1000}});p.on('pageerror',e=>report.errors.push(e.message));await p.goto(url);await p.waitForFunction(()=>window.homeStudio?.ready);
 await p.evaluate(()=>homeStudio.setView('3d'));await p.waitForFunction(()=>homeStudio.inspect().mode==='3d'&&!homeStudio.inspect().switching);
 const base=await p.evaluate(()=>JSON.stringify(homeStudio.getState()));
 const targets=chooseTestTargets(await p.evaluate(()=>homeStudio.getState()),await p.evaluate(()=>homeStudio.getRooms()));report.targets=targets;
 for(const width of [1440,390]){
  await p.setViewportSize({width,height:1000});const reference=await p.locator('#toolbarFurniture').boundingBox();assert(reference,'Sidebar toggle must remain present');
  for(const [id,name]of [['quickUndo','撤销'],['quickRedo','重做'],['saveScheme','保存']]){
   const loc=p.locator('#'+id),r=await loc.boundingBox();assert(r,'Header action must remain present');assert.equal((await loc.textContent()).trim(),'');assert.equal(await loc.getAttribute('aria-label'),name);assert.equal(await loc.locator('svg').count(),1);assert(Math.abs(r.width-reference.width)<1&&Math.abs(r.height-reference.height)<1);assert(r.x>=0&&r.x+r.width<=width);assert(await loc.getAttribute('title'));
  }
  assert.equal(await p.locator('#quickUndo').evaluate(e=>getComputedStyle(e).opacity),'1');
 }
 report.executed.push('desktop/narrow icon geometry and accessible labels');
 await p.setViewportSize({width:1440,height:1000});
 if(targets.furnitureId){
  await p.evaluate(id=>homeStudio.select({kind:'furn',id}),targets.furnitureId);await p.locator('#fab [data-context=copy]').click();report.executed.push('actual furniture copy');
 }else{
  await p.evaluate(id=>homeStudio.select({kind:'room',id}),targets.roomId);
  const choice=p.locator('#panel [data-mat]:not(.on)').first();assert(await choice.count(),'A room must expose an alternative flooring choice');await choice.click();
  report.executed.push('actual room material edit');report.notExercised.push({check:'furniture copy',reason:'No independent non-light furniture in this case'});
 }
 assert(await p.locator('#quickUndo').isEnabled());await p.locator('#quickUndo').click();assert.equal(await p.evaluate(()=>JSON.stringify(homeStudio.getState())),base);
 await p.locator('#quickRedo').click();assert.notEqual(await p.evaluate(()=>JSON.stringify(homeStudio.getState())),base);
 await p.locator('#quickUndo').click();assert.equal(await p.evaluate(()=>JSON.stringify(homeStudio.getState())),base);
 await p.locator('#saveScheme').click();await p.waitForFunction(()=>document.querySelector('#savedState').dataset.status==='saved');assert.equal(await p.evaluate(()=>JSON.stringify(homeStudio.getState())),base);
 report.executed.push('actual undo, redo, undo and save');await p.locator('.header-actions').screenshot({path:path.join(path.dirname(out),'header-icons.png')});
 assert.deepEqual(report.errors,[]);report.status='passed';report.sameButtonGeometryOnDesktopAndMobile=true;report.iconOnlyWithAccessibleNames=true;report.disabledOutlinesVisible=true;report.undoRedoSaveActualClicks=true;report.originalSchemeRestored=true;
 console.log(JSON.stringify(report));
}catch(e){report.status='failed';report.error=e.stack;throw e}
finally{fs.writeFileSync(out,JSON.stringify(report,null,2));await b.close()}
