import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root);
const deps=process.env.INTERIOR_TEST_NODE_MODULES;
if(!deps)throw Error('Set INTERIOR_TEST_NODE_MODULES to existing node_modules; no install performed');
const {build}=await import(pathToFileURL(path.join(deps,'esbuild/lib/main.js')).href);
const entry=`import assert from 'node:assert/strict';import * as T from 'three';import {finishMaterial} from './assets/h5/source/material-finish.js';
const rows=[];
for(const role of ['upholstery','cabinet','stone','ceramic','appliance-metal','metal']){
 const m=new T.MeshPhysicalMaterial({color:'#dfcfb7',roughness:.7});m.userData.finishRole=role;const colour=m.color.getHex();finishMaterial(m);assert.equal(m.color.getHex(),colour);assert(m.roughness>=0&&m.roughness<=1);assert(m.metalness>=0&&m.metalness<=1);
 if(['upholstery','metal','appliance-metal'].includes(role)){assert(m.roughnessMap?.userData.shared);assert.equal(m.roughnessMap.colorSpace,T.NoColorSpace);assert.equal(m.roughnessMap.image.width,128);const other=m.clone();finishMaterial(other);assert.equal(other.roughnessMap,m.roughnessMap);}
 const before=[m.roughness,m.metalness,m.clearcoat,m.envMapIntensity];finishMaterial(m);assert.deepEqual([m.roughness,m.metalness,m.clearcoat,m.envMapIntensity],before);
 rows.push({role,roughness:m.roughness,metalness:m.metalness,roughnessMap:!!m.roughnessMap});
}
const glass=new T.MeshPhysicalMaterial({transparent:true,opacity:.19,roughness:.08,depthWrite:false});finishMaterial(glass,'metal');assert.equal(glass.opacity,.19);assert.equal(glass.roughness,.08);assert.equal(glass.depthWrite,false);
const lamp=new T.MeshStandardMaterial({emissive:'#ffffff',emissiveIntensity:1.2});finishMaterial(lamp,'metal');assert.equal(lamp.emissiveIntensity,1.2);assert.equal(lamp.metalness,0);
console.log(JSON.stringify({status:'passed',scope:'material parameters, colour preservation, shared textures, idempotence, transparent/emissive exclusion; no visual/FPS test',rows},null,2));`;
const result=await build({stdin:{contents:entry,resolveDir:process.cwd()},bundle:true,platform:'node',format:'esm',write:false,nodePaths:[deps]});fs.writeFileSync(path.join(os.tmpdir(),'interior-material-test-'+process.pid+'.mjs'),result.outputFiles[0].text);await import(pathToFileURL(path.join(os.tmpdir(),'interior-material-test-'+process.pid+'.mjs')).href);
