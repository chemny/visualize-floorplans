import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath,pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
process.chdir(root);
const deps=process.env.INTERIOR_TEST_NODE_MODULES;
if(!deps)throw Error('Set INTERIOR_TEST_NODE_MODULES to existing node_modules; no install performed');
const {build}=await import(pathToFileURL(path.join(deps,'esbuild/lib/main.js')).href);
const code=`
import assert from 'node:assert/strict';import fs from 'node:fs';import {skirtingRuns} from './assets/h5/source/skirting-runs.js';
const wall=(id,a,b,opens=[])=>({id,a,b,t:200,height:2750,opens});
const rooms=[{id:'R',poly:[[-1000,-1000],[4000,-1000],[4000,4000],[-1000,4000]]}];
const cases=[];
const l=[wall('a',[0,0],[2000,0]),wall('b',[2000,0],[2000,2000])];
let runs=skirtingRuns(l,rooms);
// Outside corner lies on the padded union, beyond the original wall endpoint.
assert(runs.some(r=>r.axis===0&&r.line===-100&&r.end===2100));
assert(runs.some(r=>r.axis===1&&r.line===2100&&r.start===-100));
// Both free ends have short returns (these were entirely absent before).
assert(runs.some(r=>r.axis===1&&r.line===0));assert(runs.some(r=>r.axis===0&&r.line===2000));
cases.push({name:'L corner and short returns',runs:runs.length});
const door=wall('door',[0,0],[3000,0],[{kind:'door',at:1000,width:900}]);runs=skirtingRuns([door],rooms);
assert(!runs.some(r=>r.axis===0&&r.start<1400&&r.end>1400));cases.push({name:'door remains clear',runs:runs.length});
const window=wall('window',[0,0],[3000,0],[{kind:'window',at:1000,width:900,sillHeight:850,height:1300}]);runs=skirtingRuns([window],rooms);assert(runs.some(r=>r.axis===0&&r.start<1400&&r.end>1400));cases.push({name:'continuous below raised window',runs:runs.length});
assert(skirtingRuns(l,rooms,[],{R:{skirting:false}}).length===0);
assert(skirtingRuns(l.map(w=>({...w,demolished:true})),rooms).length===0);
const cabinet={builtIn:true,fixedToWalls:true,cx:1500,cy:400,w:600,d:600,rot:0};runs=skirtingRuns([wall('a',[0,0],[3000,0])],rooms,[cabinet]);assert(!runs.some(r=>r.axis===0&&r.sign===1&&r.start<1500&&r.end>1500));
// Additional enclosed and split-room fixtures, independent of any apartment.
const square=[wall('n',[0,0],[3000,0]),wall('e',[3000,0],[3000,3000]),wall('s',[3000,3000],[0,3000]),wall('w',[0,3000],[0,0])];
const inner=[{id:'R',poly:[[100,100],[2900,100],[2900,2900],[100,2900]]}];
runs=skirtingRuns(square,inner);assert.equal(runs.length,4);for(const r of runs)assert([r.cx,r.cy,r.w,r.d,r.h].every(Number.isFinite)&&r.w>0);
const splitRooms=[{id:'left',poly:[[0,100],[1500,100],[1500,1000],[0,1000]]},{id:'right',poly:[[1500,100],[3000,100],[3000,1000],[1500,1000]]}];
const split=skirtingRuns([wall('line',[0,0],[3000,0])],splitRooms);assert(split.some(r=>r.roomId==='left'));assert(split.some(r=>r.roomId==='right'));

const insetRoom=[{id:'finish-owner',poly:[[0,130],[3000,130],[3000,1800],[0,1800]]}];
const finishBand=[{materialRoomId:'finish-owner',poly:[[0,100],[3000,100],[3000,130],[0,130]]}];
const insetWall=[wall('band-wall',[0,0],[3000,0])];
assert(!skirtingRuns(insetWall,insetRoom).some(r=>r.axis===0&&r.sign===1));
const bridged=skirtingRuns(insetWall,insetRoom,[],{},finishBand);
assert(bridged.some(r=>r.axis===0&&r.sign===1&&r.w>=3000),'finish-only band must connect skirting ownership to the room');
assert.equal(skirtingRuns(insetWall,insetRoom,[],{'finish-owner':{skirting:false}},finishBand).length,0);
cases.push({name:'explicit finish bridge belongs to adjacent room without polygon edits',runs:bridged.length});
console.log(JSON.stringify({status:'passed',scope:'CPU outline, corner returns, doors, window sill, cabinet avoidance and room switches; no browser visual test',tests:cases,caseRuns:runs.length},null,2));
`;
const result=await build({stdin:{contents:code,resolveDir:process.cwd()},bundle:true,platform:'node',format:'esm',nodePaths:[deps],write:false});fs.writeFileSync(path.join(os.tmpdir(),'interior-skirting-test-'+process.pid+'.mjs'),result.outputFiles[0].text);globalThis.document={getElementById:()=>({textContent:fs.readFileSync('assets/h5/case-template.json','utf8')})};globalThis.location={search:''};await import(pathToFileURL(path.join(os.tmpdir(),'interior-skirting-test-'+process.pid+'.mjs')).href);
