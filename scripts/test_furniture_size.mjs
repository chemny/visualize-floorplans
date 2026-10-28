import assert from 'node:assert/strict';
import {validateFurniturePlanSize} from '../assets/h5/source/furniture-size.js';
const base={id:'synthetic',type:'cabinet',w:500,d:400,cx:0,cy:0,rot:0};
assert.equal(validateFurniturePlanSize(base),base);
const trim={...base,type:'skirting',w:31,d:30,assemblyOwner:{kind:'room',id:'synthetic-room'}};
assert.equal(validateFurniturePlanSize(trim).w,31);
for(const value of [
 {...trim,w:0},{...trim,w:-1},{...trim,w:NaN},{...trim,d:29},
 {...trim,assemblyOwner:undefined},{...trim,assemblyOwner:{kind:'furniture'}},
 {...base,w:31},{...base,type:'endpanel',w:14},{...base,cx:Infinity}
])assert.throws(()=>validateFurniturePlanSize(value),/尺寸/);
assert.equal(validateFurniturePlanSize({...base,type:'endpanel',w:15}).w,15);
console.log(JSON.stringify({status:'pass',scope:'Owned short trim retains exact width; ordinary furniture, non-room owners, zero/negative/non-finite sizes remain rejected'}));
