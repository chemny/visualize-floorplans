import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root);
const deps=process.env.INTERIOR_TEST_NODE_MODULES;
if(!deps)throw Error('Set INTERIOR_TEST_NODE_MODULES to existing node_modules; no install performed');
const {build}=await import(pathToFileURL(path.join(deps,'esbuild/lib/main.js')).href);
const entry=`
import assert from 'node:assert/strict';
import fs from 'node:fs';
import * as T from 'three';
import {createHash} from 'node:crypto';
import {wholeHomeFurniture} from './assets/h5/source/furniture-detail-v11.js';
import {renovationModel} from './assets/h5/source/renovation-components-v12.js';
globalThis.document={createElement:()=>({width:512,height:512,getContext:()=>({createImageData:(w,h)=>({data:new Uint8ClampedArray(w*h*4)}),putImageData(){}})})};
const rows=[];
for(const type of ['toilet','chair','fridge'])for(const scale of [.8,1,1.2]){
 const dims=type==='toilet'?[400,700,700]:type==='chair'?[450,480,850]:[910,700,1800];
 const f={id:type,type,w:dims[0]*scale,d:dims[1]*scale,h:dims[2]*scale,color:'#eeeeea',finishes:{},finishSpec:{},accessories:false};
 const root=wholeHomeFurniture(f);root.updateMatrixWorld(true);const digest=createHash('sha256');root.traverse(o=>{if(o.isMesh){digest.update(Buffer.from(o.geometry.attributes.position.array.buffer));if(o.geometry.index)digest.update(Buffer.from(o.geometry.index.array.buffer));digest.update(JSON.stringify(o.matrixWorld.toArray()));}});
 const parts=[];let triangles=0;
 root.traverse(o=>{if(!o.isMesh)return;parts.push(o.name);const a=o.geometry.attributes.position;for(let i=0;i<a.array.length;i++)assert(Number.isFinite(a.array[i]));triangles+=(o.geometry.index?.count||a.count)/3;});
 const box=new T.Box3().setFromObject(root,true),size=box.getSize(new T.Vector3());
 assert(Math.abs(size.y-f.h/1000)<.002,'height '+type);
 assert(size.x<=f.w/1000+.004,'width '+type);assert(size.z<=f.d/1000+.004,'depth '+type);
 if(type==='toilet')for(const n of ['toilet-lid','toilet-seat','toilet-lid-hinge','toilet-base-cap'])assert(parts.includes(n),n);
 if(type==='chair'){
 const g=root.getObjectByName('chair-curved-back').geometry,edges=new Map(),ix=g.index.array;
 for(let i=0;i<ix.length;i+=3)for(const [a,b]of [[ix[i],ix[i+1]],[ix[i+1],ix[i+2]],[ix[i+2],ix[i]]]){const k=[Math.min(a,b),Math.max(a,b)].join(':');edges.set(k,(edges.get(k)||0)+1);}
 assert([...edges.values()].every(n=>n===2),'chair back must be closed');
 }
 if(type==='fridge')assert(parts.filter(n=>n===(f.w>850?'fridge-side-by-side-door':'fridge-door')).length===2);
 rows.push({type,scale,geometryHash:digest.digest('hex'),triangles,width:size.x,depth:size.z,height:size.y});
}
for(const type of ['doortrim','windowtrim','curtainbox']){
 const f={type,w:type==='curtainbox'?1800:970,d:type==='curtainbox'?200:220,h:type==='curtainbox'?150:2150,color:'#f2eee8'};
 const root=renovationModel(f,{});root.updateMatrixWorld(true);const bounds=new T.Box3().setFromObject(root).getSize(new T.Vector3());assert(Math.abs(bounds.x-f.w/1000)<.001);assert(Math.abs(bounds.y-f.h/1000)<.001);
 if(type==='curtainbox')assert(root.children.filter(o=>o.name==='curtainbox-end-cap').length===2);
 if(type==='doortrim'){
  const sides=root.children.slice(0,2);for(const m of sides){const box=new T.Box3().setFromObject(m);assert(Math.abs(Math.min(Math.abs(box.min.x),Math.abs(box.max.x))-.45)<.001,'900mm aperture must remain clear');}
 }
 rows.push({type,width:bounds.x,height:bounds.y,closure:'passed'});
}
// Narrow refrigerator and common compact toilet inputs, no case-specific IDs.
for(const f of [{id:'compact-toilet',type:'toilet',w:380,d:620,h:720},{id:'narrow-fridge',type:'fridge',w:600,d:650,h:1800}]){const root=wholeHomeFurniture({...f,color:'#eeeeea',finishes:{},finishSpec:{},accessories:false});root.updateMatrixWorld(true);const size=new T.Box3().setFromObject(root,true).getSize(new T.Vector3());assert(size.x<=f.w/1000+.004&&size.z<=f.d/1000+.004);assert(Math.abs(size.y-f.h/1000)<.002);rows.push({type:f.type,syntheticBounds:'passed'});}
console.log(JSON.stringify({status:'passed',scope:'CPU geometry only; no browser visual/FPS verification',rows},null,2));
`;
const result=await build({stdin:{contents:entry,resolveDir:process.cwd(),sourcefile:'detail-verification.js'},nodePaths:[deps],bundle:true,platform:'node',format:'esm',write:false});
fs.writeFileSync(path.join(os.tmpdir(),'interior-detail-verification-'+process.pid+'.mjs'),result.outputFiles[0].text);
await import(pathToFileURL(path.join(os.tmpdir(),'interior-detail-verification-'+process.pid+'.mjs')).href);
