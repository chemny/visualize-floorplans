import test from'node:test';import assert from'node:assert/strict';
import{componentContractTargets,screenResizeDelta}from'./component_contract_targets.mjs';
test('targets use component mechanisms instead of apartment IDs',()=>{
 const s={furniture:[{id:'任意-盆',type:'vanity',rot:90},{id:'tub-X',type:'bathtub',rot:-90},{id:'leaf-Z',type:'shower',rot:180,showerDoor:{type:'hinged'}},{id:'shape-only',type:'shower'}],walls:[{id:'partition-R',opens:[{id:'入口-X',kind:'door'},{kind:'window'},{kind:'door',leafRemoved:true}]}]};
 const r=componentContractTargets(s);assert.equal(r.vanity[0].id,'任意-盆');assert.equal(r.shower.length,1);assert.deepEqual(r.door,[{wallId:'partition-R',index:0,id:'入口-X'}]);assert.deepEqual(r.bathtub,[{id:'tub-X',rot:-90}]);
});
test('missing fixtures are explicit empty scopes',()=>{assert.deepEqual(componentContractTargets({}),{shower:[],vanity:[],bathtub:[],door:[]});});
test('width and depth drags follow local axes at every quarter turn',()=>{
 for(const degrees of[0,90,-90,180]){const a=degrees*Math.PI/180,c=Math.cos(a)*.1,s=Math.sin(a)*.1,m={a:c,b:s,c:-s,d:c};const w=screenResizeDelta(m,'width',200),d=screenResizeDelta(m,'depth',200);assert(Math.abs(Math.hypot(w.dx,w.dy)-20)<1e-8);assert(Math.abs(w.dx*d.dx+w.dy*d.dy)<1e-8);assert(Math.abs(w.dx-c*200)<1e-8);assert(Math.abs(d.dy-c*200)<1e-8)}
});
test('invalid transforms cannot turn a missing drag into a passing test',()=>{for(const args of[[{},'width',200],[{a:0,b:0,c:0,d:0},'width',200],[{a:1,b:0,c:0,d:1},'wrong',200],[{a:1,b:0,c:0,d:1},'width',0]])assert.throws(()=>screenResizeDelta(...args));});
