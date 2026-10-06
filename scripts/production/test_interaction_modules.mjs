#!/usr/bin/env node
// Reusable no-browser regression checks; no host permission requests.
import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..'),base=path.join(root,'assets/h5/source');
const load=n=>import(pathToFileURL(path.join(base,n)).href);
const {roomAreaStatus}=await load('room-area-status.js'),{recordPointerLockFailure,pointerLockContext}=await load('pointer-lock-diagnostics.js'),{marbleHasVeins,marbleVeinSVG,paintMarbleVeins}=await load('material-presentation.js'),{persistScheme,decodeScheme,restoreScheme}=await load('scheme-storage.js'),{sceneLabelPoint}=await load('room-labels.js'),{createLightingRuntime}=await load('lighting-runtime.js');
const passed=[];function test(name,fn){fn();passed.push(name);}
const {horizontalContours,contourRegions}=await load('section-view.js');
const cubePoints=[[-1,0,-1],[1,0,-1],[1,0,1],[-1,0,1],[-1,3,-1],[1,3,-1],[1,3,1],[-1,3,1]],cubeFaces=[[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]];
const cubeTriangles=cubeFaces.map(f=>f.map(i=>cubePoints[i]));
test('section: closed solid has one level contour',()=>assert.equal(horizontalContours(cubeTriangles,1.2).length,1));
test('section: objects below plane have no cap',()=>assert.equal(horizontalContours(cubeTriangles,4).length,0));
test('section: open surfaces do not invent a solid cap',()=>assert.equal(horizontalContours(cubeTriangles.slice(0,2),1.2).length,0));
test('section: nested contours preserve openings',()=>assert.equal(contourRegions([[[0,0],[3,0],[3,3],[0,3]],[[1,1],[2,1],[2,2],[1,2]]])[0].holes.length,1));
const {furnitureBlocksPoint}=await load('walk-collision.js');
const probe={type:'wallcab',cx:1500,cy:1800,w:1000,d:400,h:700,elevation:1300,rot:0};
const walk={originX:3000,originY:2000,eyeHeight:1.6};
test('walk: low hanging cabinet intersects body',()=>assert(furnitureBlocksPoint(probe,-1.5,-.2,walk)));
test('walk: overhead cabinet leaves head clearance',()=>assert(!furnitureBlocksPoint({...probe,elevation:1800},-1.5,-.2,walk)));
test('walk: floor cabinet blocks and rug does not',()=>{assert(furnitureBlocksPoint({...probe,elevation:0},-1.5,-.2,walk));assert(!furnitureBlocksPoint({...probe,type:'rug',elevation:0},-1.5,-.2,walk));});
test('walk: rotated footprint and external clearance',()=>{assert(furnitureBlocksPoint({...probe,rot:90},-1.5,.2,walk));assert(!furnitureBlocksPoint({...probe,rot:90},-1.05,-.2,walk));});
test('walk: tall user needs overhead clearance',()=>assert(furnitureBlocksPoint({...probe,elevation:1800},-1.5,-.2,{...walk,eyeHeight:1.8})));

const wall={id:'w',a:[0,0],b:[1000,0],t:120,demolished:false};
test('area: unchanged and opening-only edits retain source status',()=>{assert.equal(roomAreaStatus([wall],[wall]).status,'source-partitions');assert.equal(roomAreaStatus([wall],[{...wall,opens:[{kind:'door'}]}]).status,'source-partitions');});
for(const [key,value]of [['a',[100,0]],['b',[2000,0]],['t',200],['demolished',true]])test('area: '+key+' marks pending and undo clears it',()=>{assert.equal(roomAreaStatus([wall],[{...wall,[key]:value}]).status,'pending-repartition');assert.equal(roomAreaStatus([wall],[wall]).changedWallIds.length,0);});
test('area: added/deleted walls mark pending',()=>{assert.equal(roomAreaStatus([wall],[]).status,'pending-repartition');assert.equal(roomAreaStatus([],[wall]).status,'pending-repartition');});
for(const order of ['generic-first','detailed-first'])test('lock: '+order+' preserves native message',()=>{let d={context:{focused:true}};if(order==='generic-first')d=recordPointerLockFailure(d).diagnostic;d=recordPointerLockFailure(d,{name:'NotAllowedError',message:'Permission denied'}).diagnostic;d=recordPointerLockFailure(d).diagnostic;assert.equal(d.error.message,'Permission denied');assert(recordPointerLockFailure(d).unavailable);});
for(const name of ['WrongDocumentError','InvalidStateError'])test('lock: '+name+' permits retry',()=>assert(!recordPointerLockFailure(null,{name}).unavailable));
test('lock: context detects API absence and activation',()=>{const win={};win.top=win;assert.deepEqual(pointerLockContext({}, {hasFocus:()=>false,visibilityState:'hidden'},{userActivation:{isActive:false}},win),{apiAvailable:false,focused:false,visibility:'hidden',userActivation:false,topLevel:true});});
test('marble: case choice shared by SVG and canvas',()=>{const plain={materials:{marble:{veins:false}}};assert(!marbleHasVeins(plain));assert.equal(marbleVeinSVG(plain,'#aaa'),'');let strokes=0;const g={beginPath(){},moveTo(){},bezierCurveTo(){},stroke(){strokes++}};paintMarbleVeins(g,512,512,()=>.5,plain);assert.equal(strokes,0);paintMarbleVeins(g,512,512,()=>.5,{});assert.equal(strokes,6);assert(marbleVeinSVG({},'#aaa').includes('C250'));});
const validate=s=>{if(!s||s.caseId!=='synthetic'||!Array.isArray(s.furniture))throw Error('Invalid case');return s;};
function storage(){const data=new Map;return{getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,v),data};}
const state={caseId:'synthetic',rooms:{r:{mat:'marble',name:'房间'}},furniture:[{id:'a',rot:32,w:700}],doors:{d:false},walls:[wall],ceilings:[],lighting:{on:true}};
test('storage: export/save/reopen roundtrip preserves scheme',()=>{const s=storage();persistScheme(s,'case',state,validate);assert.deepEqual(decodeScheme(s.getItem('case'),validate),state);const next=structuredClone(state);next.furniture[0].rot=65;persistScheme(s,'case',next,validate);assert.deepEqual(JSON.parse(s.getItem('case-backup')),state);});
test('storage: invalid data cannot overwrite prior scheme',()=>{const s=storage();persistScheme(s,'case',state,validate);assert.throws(()=>persistScheme(s,'case',{caseId:'other'},validate));assert.deepEqual(JSON.parse(s.getItem('case')),state);});
test('storage: backup quota failure still attempts current save',()=>{const s=storage();persistScheme(s,'case',state,validate);const write=s.setItem;s.setItem=(k,v)=>{if(k.endsWith('-backup'))throw Error('quota');write(k,v)};const next={...state,doors:{d:true}};assert(persistScheme(s,'case',next,validate).backupWarning);assert.deepEqual(JSON.parse(s.getItem('case')),next);});
test('storage: exported seed yields to its own latest cache',()=>{assert.deepEqual(restoreScheme(JSON.stringify({...state,doors:{d:true}}),state,validate),{...state,doors:{d:true}});});
test('storage: new document uses seed without borrowing old data',()=>assert.deepEqual(restoreScheme(null,state,validate),state));
test('storage: malformed own cache requests recovery',()=>assert.throws(()=>restoreScheme('{bad',state,validate)));
const inside=([x,y],poly)=>x>Math.min(...poly.map(p=>p[0]))&&x<Math.max(...poly.map(p=>p[0]))&&y>Math.min(...poly.map(p=>p[1]))&&y<Math.max(...poly.map(p=>p[1]));
test('labels: anchor stays inside and avoids occupied center',()=>{const r={poly:[[0,0],[4000,0],[4000,3000],[0,3000]],at:[2000,1500]};const p=sceneLabelPoint(r,[{cx:2000,cy:1500,w:1000,d:1000,rot:0}],inside);assert(inside(p,r.poly));assert(Math.abs(p[0]-2000)>620||Math.abs(p[1]-1500)>620);});
// Minimal deterministic renderer doubles test rig behavior, never actual GPU performance.
class Vec{constructor(x=0,y=0,z=0){Object.assign(this,{x,y,z})}copy(v){Object.assign(this,v);return this}set(x,y,z){Object.assign(this,{x,y,z});return this}distanceTo(v){return Math.hypot(this.x-v.x,this.y-v.y,this.z-v.z)}toArray(){return[this.x,this.y,this.z]}}
class Color{constructor(r=1,g=1,b=1){Object.assign(this,{r,g,b})}getHex(){return 123}copy(c){Object.assign(this,c);return this}multiplyScalar(k){this.r*=k;this.g*=k;this.b*=k;return this}}
class Light{constructor(){this.userData={};this.position=new Vec();this.target={position:new Vec()};this.color=new Color();this.intensity=0;this.castShadow=false;this.shadow={mapSize:{set(){}},camera:{}}}}
const fixtures=[{id:'main',type:'ceilinground',cx:1000,cy:1000},{id:'side',type:'sconce',cx:1500,cy:1500}];
const sources=fixtures.map((f,i)=>({isLight:true,uuid:f.id,userData:{fixtureId:f.id,enabled:true,nominalIntensity:3},position:new Vec(i,2.6,i),color:new Color(),visible:true}));
const opts={night:false,lamps:true},runtime={lampG:{children:sources},scene:{add(){},remove(){}},renderer:{setPixelRatio(v){this.ratio=v},getPixelRatio(){return this.ratio}},camera:{position:new Vec(),quaternion:{toArray:()=>[0,0,0,1]}},ceilingFill:{},hemi:{},anim:false,fly:false};
const rig=createLightingRuntime({SpotLight:Light,PointLight:Light,Color,CASE:{render:{indoorShadowBudget:2}},ROOMS:[{id:'r',poly:[[0,0],[4000,0],[4000,3000],[0,3000]]}],getF:id=>fixtures.find(f=>f.id===id),inPolygon:inside,opt:opts,getRuntime:()=>runtime,pixelRatio:()=>2});
test('lighting: every fixture contributes once, lights stay fixed when moving',()=>{rig.update(1/60);const a=rig.status();assert.deepEqual(a.slots[0].members,['main','side']);runtime.camera.position.x=5;rig.update(1/60);assert.deepEqual(rig.status().slots,a.slots);assert(sources.every(s=>!s.visible));});
test('lighting: night/restored day stable, rebuild fixture set',()=>{const before=rig.status().slots[0].intensity;opts.night=true;rig.update(1/60);assert(rig.status().slots[0].intensity>before);opts.night=false;rig.update(1/60);assert.equal(rig.status().slots[0].intensity,before);sources.pop();rig.update(1/60);assert.deepEqual(rig.status().slots[0].members,['main']);});
test('lighting: ceiling diffuser supplies omni light without adding groups',()=>{rig.update(1/60);assert.equal(rig.status().budget,1);assert.equal(rig.status().slots[0].distribution,'omnidirectional');});
test('resolution: slow frames, movement and idle all retain native pixels',()=>{rig.update(1/60);assert.equal(runtime.renderer.ratio,2);for(let i=0;i<180;i++){runtime.camera.position.x+=.2;rig.update(.05);}assert.equal(runtime.renderer.ratio,2);for(let i=0;i<180;i++)rig.update(.1);assert.equal(runtime.renderer.ratio,2);assert.equal(rig.status().resolutionMode,'native');});
let displayRatio=3;const nativeRig=createLightingRuntime({SpotLight:Light,PointLight:Light,Color,CASE:{render:{performanceLighting:false}},ROOMS:[],getF:()=>null,inPolygon:inside,opt:opts,getRuntime:()=>runtime,pixelRatio:()=>displayRatio});
test('resolution: displays above DPR2 and display changes follow native ratio',()=>{nativeRig.update(.05);assert.equal(runtime.renderer.ratio,3);displayRatio=1.25;nativeRig.update(.05);assert.equal(runtime.renderer.ratio,1.25);rig.update(1/60);});
test('lighting: fixed budget shadows can be disabled for visual comparison',()=>{assert.deepEqual(rig.status().shadowSlots,['main']);rig.setShadows(false);rig.update(1/60);assert.deepEqual(rig.status().shadowSlots,[]);rig.setShadows(true);rig.update(1/60);assert.deepEqual(rig.status().shadowSlots,['main']);});
test('UI contract: no entry modal, no global fixture switch, joystick and shortcuts remain',()=>{const html=fs.readFileSync(path.join(root,'assets/h5/template.html'),'utf8'),app=fs.readFileSync(path.join(base,'app.js'),'utf8');assert(!html.includes('fixtureLightsToggle'));assert(html.includes('id="joy"'));assert(html.includes('WASD'));assert(!/walk.*showModal/.test(app));assert(app.includes("$('#walkLock').hidden=COARSE||walkLockUnavailable"));assert(html.includes('data-workbench-version="__WORKBENCH_VERSION__"'));});
// Hash/approval binding uses the actual production contract with synthetic data.
globalThis.document={getElementById:()=>({textContent:JSON.stringify({presentation:{materials:{marble:{veins:false}}},model:{width:1000,depth:1000,height:2800,rooms:[]},initialState:{walls:[],furniture:[],rooms:{}},caseId:'synthetic'})})};
const {productionScopes,createProductionBundle}=await load('production-contract.js');
const model={width:1000,depth:1000,height:2800,footprint:[[0,0],[1000,0],[1000,1000],[0,1000]],walls:[wall]};
test('production: material presentation bound to style scope',()=>assert.equal(productionScopes(state,model,[],{}).style.materialPresentation.marble.veins,false));
const bundle=await createProductionBundle(state,model,[],{});test('production: area status and material configuration survive export',()=>{assert.equal(bundle.roomGeometryStatus.status,'source-partitions');assert.equal(bundle.materialPresentation.marble.veins,false)});
console.log(JSON.stringify({pass:true,count:passed.length,checks:passed},null,2));
