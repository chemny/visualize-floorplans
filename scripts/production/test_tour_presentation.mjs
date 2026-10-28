import test from 'node:test';import assert from 'node:assert/strict';import fs from 'node:fs';
const url=new URL('../../assets/h5/tour/tour-map.js',import.meta.url);
const {frameAt,path,ray,sample,seekTime,framePath}=await import('data:text/javascript;base64,'+fs.readFileSync(url).toString('base64'));
test('seeks use capture frame rather than nearest future frame',()=>{assert.equal(frameAt(39.292,24,1437),943);assert.equal(frameAt(39.291666,24,1437),943);assert.equal(frameAt(39.29160,24,1437),942);assert.equal(frameAt(0,24,1437),0);assert.equal(frameAt(59.875,24,1437),1436);assert.equal(frameAt(-10,24,1437),0);assert.equal(frameAt(1.49,2,8),2)});
test('backward seeking removes future traveled route',()=>{let data={fps:2,frames:Array.from({length:8},(_,i)=>({p:[i*100,400],yaw:0,fov:70})),walls:[]};assert.equal(sample(data,2).index,4);assert.equal(sample(data,0).done,'M0,400');assert.ok(!sample(data,0).done.includes('400,400'));assert.equal(sample(data,3.5).point[0],700)});
test('facing and path derive from independent axes, with walls clipping field',()=>{assert.deepEqual(ray([0,0],0,[[[100,-200],[100,200],5]]),[95,0]);let data={fps:3,frames:[{p:[50,400],yaw:Math.PI/2,fov:60}],walls:[]};let s=sample(data,0);assert.equal(s.yaw,Math.PI/2);assert.ok(s.axis.includes('7400'));assert.equal(s.index,0);assert.equal(path([]),'')});

test('chapter seeking lands inside the requested encoded frame',()=>{assert.equal(frameAt(seekTime(943/24,24,1437),24,1437),943);assert.ok(seekTime(943/24,24,1437)>943/24);assert.ok(seekTime(59.875,24,1437)<59.875)});

test('editorial cuts never draw fictitious travel across rooms',()=>{assert.equal(framePath([{p:[0,0]},{p:[100,0]},{p:[900,800],cutBefore:true},{p:[950,800]}]),'M0,0 L100,0 M900,800 L950,800')});
