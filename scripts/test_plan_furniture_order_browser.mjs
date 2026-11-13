// Actual exported SVG pixels and hit testing for tucked seats in any paired case.
import fs from 'node:fs';import assert from 'node:assert/strict';import {pathToFileURL} from 'node:url';
import {attachArtifactEvidence} from './browser_artifact_evidence.mjs';
const [url,out]=process.argv.slice(2),{default:pw}=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href);
const b=await pw.chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true}),report={url,errors:[],pairs:[]};
try{
 const p=await b.newPage({viewport:{width:1600,height:1100}});p.on('pageerror',e=>report.errors.push(e.message));const evidence=attachArtifactEvidence(p,{expectedUrls:[url]});
 await p.goto(url);await p.waitForFunction(()=>window.homeStudio?.ready);await p.evaluate(()=>homeStudio.setView('2d'));await p.waitForFunction(()=>homeStudio.inspect().mode==='2d'&&!homeStudio.inspect().switching);await p.waitForTimeout(900);
 const baseline=await p.evaluate(()=>homeStudio.getState());
 const pairs=await p.evaluate(()=>{
  const fs=homeStudio.getState().furniture.filter(f=>!f.assemblyOwner);
  const box=f=>{const r=f.rot*Math.PI/180,w=Math.abs(Math.cos(r))*f.w+Math.abs(Math.sin(r))*f.d,d=Math.abs(Math.sin(r))*f.w+Math.abs(Math.cos(r))*f.d;return[f.cx-w/2,f.cy-d/2,f.cx+w/2,f.cy+d/2]};
  return fs.filter(f=>['desk','dresser','table'].includes(f.type)).flatMap(table=>fs.filter(f=>['chair','officechair','barstool'].includes(f.type)).flatMap(chair=>{const a=box(table),b=box(chair),rect=[Math.max(a[0],b[0]),Math.max(a[1],b[1]),Math.min(a[2],b[2]),Math.min(a[3],b[3])];return rect[2]-rect[0]>80&&rect[3]-rect[1]>60?[{tableId:table.id,chairId:chair.id,rect}]:[]}));
 });assert(pairs.length,'No tucked seat/table pair in generated case');
 for(const pair of pairs){
  await p.evaluate(({tableId,chairId})=>{homeStudio.select(null);homeStudio.updateObject(tableId,{color:'#22ccee',colorStyleMode:'fixed'});homeStudio.updateObject(chairId,{color:'#ee22aa',colorStyleMode:'fixed'});homeStudio.setPlanDrawingMode('furniture')},pair);
  const result=await p.evaluate(async pair=>{
   const ids=[...document.querySelector('#gFurn').children].map(e=>e.dataset.fid);
   const doc=new DOMParser().parseFromString(homeStudio.exportPlanSVG(),'image/svg+xml');for(const id of ['gFurnitureLabels','gLabels','gSel'])doc.getElementById(id)?.remove();const vb=doc.documentElement.getAttribute('viewBox').split(/[ ,]+/).map(Number);
   const blob=new Blob([new XMLSerializer().serializeToString(doc)],{type:'image/svg+xml'}),src=URL.createObjectURL(blob),img=new Image();img.src=src;await img.decode();const canvas=document.createElement('canvas');canvas.width=img.naturalWidth;canvas.height=img.naturalHeight;const ctx=canvas.getContext('2d');ctx.drawImage(img,0,0);const [x0,y0,x1,y1]=pair.rect,samples=[];
   for(const u of [.4,.5,.6])for(const v of [.4,.5,.6]){const x=x0+(x1-x0)*u,y=y0+(y1-y0)*v,px=Math.floor((x-vb[0])/vb[2]*canvas.width),py=Math.floor((y-vb[1])/vb[3]*canvas.height);samples.push([...ctx.getImageData(px,py,1,1).data]);}URL.revokeObjectURL(src);
   const screen=(x,y)=>{const svg=document.querySelector('#plan'),q=svg.createSVGPoint();q.x=x;q.y=y;const p=q.matrixTransform(svg.getScreenCTM());return{x:p.x,y:p.y}};
   const chair=homeStudio.getState().furniture.find(f=>f.id===pair.chairId),a=chair.rot*Math.PI/180;
   return{order:{chair:ids.indexOf(pair.chairId),table:ids.indexOf(pair.tableId)},samples,overlapClick:screen((x0+x1)/2,(y0+y1)/2),backClick:screen(chair.cx+Math.sin(a)*chair.d*.37,chair.cy-Math.cos(a)*chair.d*.37)};
  },pair);
  assert(result.order.chair<result.order.table,'Tucked seat must paint before tabletop');
  const cyan=result.samples.filter(([r,g,b])=>r<100&&g>150&&b>150).length,magenta=result.samples.filter(([r,g,b])=>r>150&&g<100&&b>100).length;
  assert(cyan>=3,'Actual exported overlap must show tabletop pixels');assert.equal(magenta,0,'Seat must not appear on the tabletop');
  await p.mouse.click(result.overlapClick.x,result.overlapClick.y);assert.equal(await p.evaluate(()=>homeStudio.getSelection()?.id),pair.tableId);
  await p.evaluate(()=>homeStudio.select(null));await p.mouse.click(result.backClick.x,result.backClick.y);assert.equal(await p.evaluate(()=>homeStudio.getSelection()?.id),pair.chairId);
  report.pairs.push({tableId:pair.tableId,chairId:pair.chairId,order:result.order,exportedCyanPixels:cyan,exportedSeatPixels:magenta,topAndVisibleBackPickCorrect:true});
 }
 await p.evaluate(state=>{homeStudio.select(null);homeStudio.importScheme(JSON.stringify(state));},baseline);assert.deepEqual(await p.evaluate(()=>homeStudio.getState()),baseline);assert.deepEqual(report.errors,[]);
 report.artifactEvidence=await evidence.verify();report.status='passed';report.originalStateRestored=true;
}catch(e){report.status='failed';report.error=e.stack;throw e}finally{fs.writeFileSync(out,JSON.stringify(report,null,2));await b.close()}
