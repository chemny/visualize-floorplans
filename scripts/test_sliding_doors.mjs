import fs from 'node:fs';import path from 'node:path';import assert from 'node:assert/strict';import {fileURLToPath} from 'node:url';import {spawnSync} from 'node:child_process';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const {slidingDoorGeometry,slidingControls}=await import('data:text/javascript;base64,'+fs.readFileSync(path.join(root,'assets/h5/source/sliding-door.js')).toString('base64'));
const fixtures=[];
for(const [a,b]of [[[0,0],[3000,0]],[[3000,0],[0,0]],[[0,0],[0,3000]],[[0,3000],[0,0]]])for(const leaves of [2,3])for(const slideDirection of [-1,1])for(const slideOpen of [0,.25,.5,.75,1]){
 const wall={a,b},o={at:300,width:1800,kind:'sliding',leaves,slideDirection,slideOpen};const g=slidingDoorGeometry(wall,o);
 assert.equal(g.panels.length,leaves);assert(g.netOpeningMm>=0&&g.netOpeningMm<1800);
 if(slideOpen===0)assert.equal(g.netOpeningMm,0);
 if(slideOpen===1)assert.equal(g.netOpeningMm,1800-(1800/leaves+30));
 assert.equal(g.totalClearMm,g.gaps.reduce((n,[a,b])=>n+b-a,0));
 fixtures.push({wall,o,g});
}
const probe=spawnSync('python3',['-c',`import json,sys\nsys.path.insert(0,sys.argv[1])\nfrom door_checks import sliding_geometry\nprint(json.dumps([sliding_geometry(x['wall'],x['o']) for x in json.load(sys.stdin)]))`,path.join(root,'scripts/production')],{input:JSON.stringify(fixtures),encoding:'utf8'});assert.equal(probe.status,0,probe.stderr);
const py=JSON.parse(probe.stdout);function near(a,b){if(typeof a==='number')assert(Math.abs(a-b)<1e-8);else if(a&&typeof a==='object'){assert.deepEqual(Object.keys(a),Object.keys(b));for(const k of Object.keys(a))near(a[k],b[k]);}else assert.equal(a,b);}
fixtures.forEach((f,i)=>near(f.g,py[i]));
const w={a:[0,0],b:[3000,0]},o={kind:'sliding',at:100,width:1200};
assert.equal(slidingDoorGeometry(w,{...o,leafRemoved:true}).netOpeningMm,1200);
for(const bad of [{leaves:4},{leaves:3,width:789},{slideDirection:0},{slideOpen:NaN},{slideOpen:-.1},{slideOpen:1.1}])assert.throws(()=>slidingDoorGeometry(w,{...o,...bad}));
assert.match(slidingControls(w,{...o,width:789}),/value="3"[^>]*disabled/);
assert.equal(slidingControls(w,{...o,leafRemoved:true}),'');
console.log(JSON.stringify({status:'pass',crossLanguageFixtures:fixtures.length,rejectedInvalidParameters:6,scope:'JS geometry, Python parity and control markup; browser integration separately'}));
