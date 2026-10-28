import fs from 'node:fs';import assert from 'node:assert/strict';
const source=fs.readFileSync(new URL('../assets/h5/source/app.js',import.meta.url),'utf8');
const text=source.slice(source.indexOf('function validateWalls('),source.indexOf('function initialWallSegments('));
const wall={id:'synthetic',a:[0,0],b:[4000,0],t:120,height:2800,bearing:false,opens:[{id:'opening',kind:'door',at:1400,width:900,swing:1,hingeEnd:'start',angle:90}]};
const DEFAULT={height:2800,walls:[wall]},validateRemovedIntervals=()=>{},initialWallSegments=()=>[];
const validate=eval('('+text+')');
for(const angle of [5,90,135,150,180]){const w=structuredClone(wall);w.opens[0].angle=angle;assert.equal(validate([w])[0].opens[0].angle,angle)}
for(const angle of [0,4,181,-90,NaN,Infinity,'150']){const w=structuredClone(wall);w.opens[0].angle=angle;assert.throws(()=>validate([w]),/门轴或开启方向无效/)}
console.log('Approved-angle compatibility and invalid-angle rejection passed');
