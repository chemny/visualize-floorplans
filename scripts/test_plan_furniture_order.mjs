import assert from 'node:assert/strict';
import {planFurnitureOrder,planSurfaceHeight} from '../assets/h5/source/plan-furniture-order.js';
const seat={id:'seat',type:'chair',h:850,elevation:0,rot:180},table={id:'desk',type:'desk',h:750,elevation:0},rug={id:'rug',type:'rug',h:15};
for(const input of [[table,seat,rug],[rug,seat,table]]){
 const before=JSON.stringify(input),sorted=planFurnitureOrder(input);
 assert.deepEqual(sorted.map(f=>f.id),['rug','seat','desk']);assert.equal(JSON.stringify(input),before);assert.equal(sorted[1],seat);
}
assert(planSurfaceHeight(seat)<planSurfaceHeight(table));
assert.deepEqual(planFurnitureOrder([seat,{...table,id:'a'}, {...table,id:'b'}]).map(f=>f.id),['seat','a','b']);
assert.equal(planFurnitureOrder([table,{...seat,elevation:1000}])[1].id,'seat');
assert.equal(planFurnitureOrder([seat,{...table,type:'dresser'}])[1].id,'desk');
assert.equal(planFurnitureOrder([]).length,0);
console.log(JSON.stringify({status:'pass',scope:'Stable, non-mutating surface order; physical nesting checked independently'}));
