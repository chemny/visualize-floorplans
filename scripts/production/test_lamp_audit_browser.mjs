// Real runtime page: the multi-ray lamp audit must still fail a lamp that a real opaque surface hides.
// Usage: node test_lamp_audit_browser.mjs <runtime-dir> <out.json>; needs INTERIOR_PLAYWRIGHT_MODULE and INTERIOR_BROWSER.
import fs from 'node:fs';import http from 'node:http';import path from 'node:path';import assert from 'node:assert/strict';import{pathToFileURL}from'node:url';
const[dir,out]=process.argv.slice(2);
const{default:pw}=await import(pathToFileURL(process.env.INTERIOR_PLAYWRIGHT_MODULE).href);
const types={'.html':'text/html','.js':'text/javascript','.json':'application/json','.bin':'application/octet-stream'};
// Test-only copy of the page that exposes its scene; the shipped renderer.html is not changed.
const page_html=fs.readFileSync(path.join(dir,'renderer.html'),'utf8').replace('window.rendererReady=true;','window.__test={THREE,scene,meshes};window.rendererReady=true;');
const server=http.createServer((req,res)=>{const name=decodeURIComponent(req.url.split('?')[0]).replace(/^\/+/,'')||'renderer.html';
 if(name==='renderer.html'){res.setHeader('content-type','text/html');return res.end(page_html)}
 const file=path.join(dir,path.normalize(name));if(!file.startsWith(path.resolve(dir))||!fs.existsSync(file)){res.statusCode=404;return res.end()}
 res.setHeader('content-type',types[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file))});
await new Promise(r=>server.listen(0,'127.0.0.1',r));
const browser=await pw.chromium.launch({executablePath:process.env.INTERIOR_BROWSER,headless:true,args:['--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
const report={errors:[]};
try{
 const page=await browser.newPage({viewport:{width:960,height:540}});page.on('pageerror',e=>report.errors.push(e.message));
 await page.goto(`http://127.0.0.1:${server.address().port}/renderer.html`);await page.waitForFunction(()=>window.rendererReady===true,null,{timeout:60000});
 const base=await page.evaluate(()=>window.inspectLighting());
 assert(base.primaryFaces.length>0,'case has no primary lamps');
 assert.equal(base.allPrimaryFacesVisible,true,'baseline lamps must be visible');
 const target=base.primaryFaces.find(f=>f.emittingFaces.length)?.emittingFaces[0].name;assert(target,'no emitting face');
 const blocked=await page.evaluate(name=>{const{THREE,scene,meshes}=window.__test,lamp=meshes.find(m=>m.name===name),box=new THREE.Box3().setFromObject(lamp),c=box.getCenter(new THREE.Vector3());
  const plate=new THREE.Mesh(new THREE.BoxGeometry(1,.01,1),new THREE.MeshBasicMaterial({color:0x808080}));plate.position.set(c.x,box.min.y-.08,c.z);plate.updateMatrixWorld(true);plate.name='test-occluder';plate.userData={kind:'furniture',objectId:'test-occluder'};scene.add(plate);meshes.push(plate);
  const r=window.inspectLighting(),face=r.primaryFaces.flatMap(f=>f.emittingFaces).find(f=>f.name===name);return{allPrimaryFacesVisible:r.allPrimaryFacesVisible,visible:face.visible,firstName:face.firstName,probeRays:face.probeRays}},target);
 report.target=target;report.blocked=blocked;
 assert.equal(blocked.visible,false,'a lamp hidden by a real surface must not count as visible');
 assert.equal(blocked.firstName,'test-occluder');assert.equal(blocked.probeRays,9,'a blocked lamp tries every probe ray');
 assert.equal(blocked.allPrimaryFacesVisible,false);
 assert.deepEqual(report.errors,[]);report.status='passed';
}finally{fs.writeFileSync(out,JSON.stringify(report,null,2));await browser.close();server.close()}
console.log(JSON.stringify({status:report.status}));
