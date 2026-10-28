import test from 'node:test';
import assert from 'node:assert/strict';
import {chooseTestTargets} from './workbench_test_targets.mjs';
test('renamed rooms and arbitrary furniture IDs require no living/sofa/wardrobe',()=>{
 const s={rooms:{'zone-13':{mat:'wood'}},furniture:[{id:'custom-42',type:'desk'}]};
 assert.deepEqual(chooseTestTargets(s,[{id:'zone-13',name:'任意'}]),{roomId:'zone-13',furnitureId:'custom-42',furnitureType:'desk'});
});
test('empty or fixture-only rooms use room editing without fabricating furniture',()=>{
 for(const furniture of [[],[{id:'lamp',type:'pendant',mount:'ceiling'}],[{id:'generated',type:'wardrobe',assemblyOwner:{kind:'room'}}]]){
  const s={rooms:{only:{}},furniture},before=JSON.stringify(s);
  assert.equal(chooseTestTargets(s,[{id:'only'}]).furnitureId,null);assert.equal(JSON.stringify(s),before);
 }
});
test('ignore unmatched room labels and preserve arbitrary order',()=>{
 assert.equal(chooseTestTargets({rooms:{second:{}},furniture:[]},[{id:'missing'},{id:'second'}]).roomId,'second');
});
test('missing usable rooms fail explicitly instead of claiming skipped success',()=>{
 assert.throws(()=>chooseTestTargets({rooms:{},furniture:[]},[{id:'only'}]),/one runtime room/);
});
