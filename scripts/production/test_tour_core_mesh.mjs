// Actual triangle projection/raycast regressions; no browser or real apartment IDs.
import fs from 'node:fs';import os from 'node:os';import path from 'node:path';
import {fileURLToPath} from 'node:url';import {spawnSync} from 'node:child_process';
import {test} from 'node:test';import assert from 'node:assert/strict';
import * as T from '../../assets/h5/runtime/three.module.js';
const here=path.dirname(fileURLToPath(import.meta.url));
function check(mode){
 const root=fs.mkdtempSync(path.join(os.tmpdir(),'core-mesh-'));
 try{
  for(const f of ['three.module.js','three.core.js'])fs.copyFileSync(path.resolve(here,'../../assets/h5/runtime',f),path.join(root,f));
  const objects=[['one','vanity',3000,2000],['two','shower',3000,2500],['three','toilet',3000,3000]];
  const meshes=[],buffers=[];let offset=0;
  function box(id,x,y,w=.35,d=.35,h=1){const g=new T.BoxGeometry(w,h,d).toNonIndexed(),v=g.getAttribute('position').array,bytes=Buffer.from(v.buffer,v.byteOffset,v.byteLength),mat=new T.Matrix4().makeTranslation((x-2500)/1000,h/2,(y-2500)/1000);
   meshes.push({objectId:id,name:id,kind:'furniture',visible:true,positions:{offset,count:v.length},materials:[0],groups:[],matrix:mat.toArray()});buffers.push(bytes);offset+=bytes.length;
  }
  objects.forEach(([id,kind,x,y])=>box(id,x,y));if(mode==='occluded')box('opaque-blocker',2000,2780,.4,.5,2.4);
  const bundle={schemeSha256:'SYNTHETIC',model:{width:5000,depth:5000,rooms:[{id:'renamed-zone',poly:[[0,0],[5000,0],[5000,5000],[0,5000]]}]},state:{furniture:objects.map(([id,type,cx,cy])=>({id,type,cx,cy,roomId:'renamed-zone'}))},materials:[{side:2,transparent:false,opacity:1}],meshes};
  const frames=Array.from({length:mode==='split'?17:9},(_,frame)=>({frame,pointMm:[600,2500],yawRadians:mode==='behind'?Math.PI:0,pitchRadians:-.2,eyeMm:1600,horizontalFovDegrees:76,shiftY:0}));
  const tour={schemeSha256:'SYNTHETIC',frames,fps:8,seconds:9/8,visits:[{name:'a',frame:0},{name:'b',frame:8}]};
  if(mode==='split'){tour.seconds=17/8;tour.visits=[{name:'a',frame:0},{name:'mid',frame:8},{name:'b',frame:16}];}
  const config={chapters:[{name:'room-view',phase:'observe',roomId:'renamed-zone',from:'a',to:'b',subjects:mode==='omitted'?['one','two']:['one','two','three']}]};
  if(mode==='split')config.chapters=[{name:'first',phase:'observe',roomId:'renamed-zone',from:'a',to:'mid',subjects:['one','two']},{name:'second',phase:'observe',roomId:'renamed-zone',from:'mid',to:'b',subjects:['three']}];
  for(const [f,v] of [['scene.json',bundle],['tour.json',tour],['config.json',config]])fs.writeFileSync(path.join(root,f),JSON.stringify(v));fs.writeFileSync(path.join(root,'geometry.bin'),Buffer.concat(buffers));
  const run=spawnSync(process.execPath,[path.join(here,'tour_mesh_preflight.mjs'),'--runtime',root,'--tour',path.join(root,'tour.json'),'--config',path.join(root,'config.json'),'--out',path.join(root,'audit.json')],{encoding:'utf8'});
  assert.equal(run.status,0,run.stderr);const report=JSON.parse(fs.readFileSync(path.join(root,'audit.json')));return mode==='split'?report:report.coreTargets;
 }finally{fs.rmSync(root,{recursive:true,force:true});}
}
test('one continuous shot reads all three core fixtures',()=>assert.equal(check('visible').status,'pass'));
test('an omitted toilet fails even when actual mesh is visible',()=>assert.ok(check('omitted').issues.some(i=>i.code==='missing_core_view_target'&&i.subjectId==='three')));
test('a toilet behind the camera cannot pass',()=>assert.ok(check('behind').issues.some(i=>i.code==='core_facility_unreadable'&&i.subjectId==='three')));
test('an opaque blocker prevents actual readability',()=>assert.ok(check('occluded').issues.some(i=>i.code==='core_facility_unreadable'&&i.subjectId==='three')));

test('complementary shots keep composition targets separate while core completeness uses all actual samples',()=>{const r=check('split');assert.deepEqual(Object.keys(r.chapters[0].subjects),['one','two']);assert.deepEqual(Object.keys(r.chapters[1].subjects),['three']);assert.ok(r.chapters.every(c=>c.samples.every(s=>Object.keys(s.subjects).length===3)));assert.equal(r.coreTargets.status,'pass');assert.ok(!r.screenQuality.issues.some(i=>i.code==='subject_composition_unreadable'));});
