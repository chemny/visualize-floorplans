import fs from 'node:fs';import assert from 'node:assert/strict';
const {ARCHITECTURAL_PRESETS:a,presetOpening,openingPresetId}=await import('data:text/javascript;base64,'+fs.readFileSync(new URL('../assets/h5/source/architectural-presets.js',import.meta.url)).toString('base64'));
assert.equal(new Set(a.map(p=>p.id)).size,8);assert.equal(a.find(p=>p.id==="security").model,"security");
const existing={id:'original-opening',at:1300,width:850,height:2050,angle:88,hingeEnd:'end',swing:-1};
for(const p of a){const o=presetOpening(p,existing);assert.equal(o.at,1300);assert.equal(o.width,850);assert.equal(o.height,2050);assert.equal(o.id,existing.id);assert.equal(openingPresetId(o),p.id);if(p.kind!=='window'){assert.equal(o.angle,88);assert.equal(o.hingeEnd,'end')}}
const wall=presetOpening(a.find(p=>p.id==='wallslide'));assert.equal(wall.leaves,1);assert.equal(wall.slideMount,'wall');assert.equal(wall.panelFinish,'solid');
assert.equal(presetOpening(a.find(p=>p.id==='passage')).leafRemoved,true);assert.equal(presetOpening(a.find(p=>p.id==='window')).sillHeight,850);assert.throws(()=>presetOpening(null));console.log('Architectural presets: passed; browser insertion tested separately');
