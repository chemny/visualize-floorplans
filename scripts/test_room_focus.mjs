// Installed-source regression: final camera wrapper and actual label handlers.
// No browser, downloads, dependencies, case files, visual or performance claims.
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const src=fs.readFileSync(path.join(root,'assets/h5/source/app.js'),'utf8');
const css=fs.readFileSync(path.join(root,'assets/h5/template.html'),'utf8');
function element(){return {style:{},hidden:false,dataset:{},listeners:{},attrs:{},classList:{add(){}},setAttribute(k,v){this.attrs[k]=v;},addEventListener(k,fn){this.listeners[k]=fn;},append(child){this.child=child;},querySelector(){return this.child;}};}
class Vector3{constructor(x,y,z){Object.assign(this,{x,y,z});}}
let reduced=false,pose={whole:1},last=null,flyCount=0,keys=0;
const rooms=[{id:'a',at:[800,800],poly:[[0,0],[3000,0],[3000,4000],[0,4000]]},{id:'b',at:[6500,500],poly:[[5000,0],[9000,0],[9000,3000],[5000,3000]]}];
const c=vm.createContext({active:true,anim:null,opt:{mode:'orbit'},ROOMS:rooms,sceneRevision:0,
 THREE:{Vector3},wx:v=>v/1000,wz:v=>v/1000,M:v=>v/1000,SW:()=>1200,SH:()=>800,FOV:50,
 pose:(t,p)=>({t,p}),curPose:()=>pose,isoWhole:()=>({default:true}),flyToRoom(){},
 fly:{},flyTo(p,d){last={p,d};flyCount++;},setPose:p=>last={p,d:0},closeMenus(){},closeDrawers(){},
 window:{matchMedia:()=>({matches:reduced})},document:{createElement:element},
 buildLabels(){c.labelG.children=rooms.map(()=>({element:element(),userData:{},position:{set(){}}}));},
 labelG:{children:[]},chooseSceneLabelPoint:r=>r.at,state:{rooms:{a:{name:'主卧'},b:{name:'次卧'}},furniture:[]},
 inPolygon(){},esc:x=>x,nm:x=>x,area:()=>12,opt:{mode:'orbit',cut:2},
});
const labelStart=src.indexOf('let focusedRoomId=null,roomFocusReturnPose=null;');assert(labelStart>0);
vm.runInContext(src.slice(labelStart,src.indexOf('function declutterSceneLabels(){',labelStart)),c);
vm.runInContext(src.slice(src.indexOf('function enterRoom(id){'),src.indexOf('function findWalkLanding(r){')),c);
// Include the last runtime assignment: first declaration alone missed overrides.
const finalStart=src.lastIndexOf('const experienceRoomFly=flyToRoom;');assert(finalStart>0);
vm.runInContext(src.slice(finalStart,src.indexOf("$('#walkSensitivity')",finalStart)),c);
const get=k=>vm.runInContext(k,c);
c.buildLabels();
const a=c.labelG.children[0].element,b=c.labelG.children[1].element;
assert(a.child.hidden&&b.child.hidden);assert.equal(a.tabIndex,0);
const event={key:'Enter',stopPropagation(){keys++;},preventDefault(){keys++;}};
a.listeners.click(event);assert.equal(c.opt.mode,'orbit');assert.equal(get('focusedRoomId'),'a');
assert.equal(a.child.hidden,false);assert.equal(b.child.hidden,true);assert.equal(last.d,650);
assert.equal(last.p.t.x,1.5);assert.equal(last.p.t.z,2); // Geometry centre, not label anchor.
pose={roomA:true};b.listeners.keydown(event);assert.equal(get('focusedRoomId'),'b');
assert(a.child.hidden&&!b.child.hidden);assert.equal(get('roomFocusReturnPose').whole,1);
// Rebuild labels during focus must retain the exit control on the selected room.
c.buildLabels();assert.equal(c.labelG.children[1].element.child.hidden,false);
const before=flyCount;c.labelG.children[1].element.child.listeners.click(event);
assert.equal(flyCount,before+1);assert.equal(last.p.whole,1);assert.equal(get('focusedRoomId'),null);
c.exitRoomFocus();assert.equal(flyCount,before+1);assert(c.labelG.children.every(l=>l.element.child.hidden));
reduced=true;pose={whole:2};c.enterRoom('b');assert.equal(last.d,0);assert.equal(c.fly,null);
c.exitRoomFocus();assert.equal(last.p.whole,2);assert.equal(get('roomFocusReturnPose'),null);
last=null;c.enterRoom('unknown');assert.equal(last,null);
c.opt.mode='walk';c.enterRoom('a');assert.equal(last,null);
c.opt.mode='orbit';c.anim={};c.enterRoom('a');assert.equal(last,null);c.anim=null;
assert.match(css,/\.rlabel\.room-focus-label\{pointer-events:auto!important;cursor:pointer!important/);
assert.match(css,/\.rlabel\.room-focus-label \*\{pointer-events:none!important/);
assert.match(css,/\.rlabel\.room-focus-label \.room-focus-exit\{pointer-events:auto!important/);
assert.match(css,/room-focus-exit\[hidden\]\{display:none!important/);
assert.match(src,/if\(!hit\?\.room\)return/);assert(keys>0);
console.log(JSON.stringify({status:'passed',scope:'Installed source: final camera wrapper, actual label handlers, keyboard, A/B/exit, rebuild, reduced motion, mode guards, CSS contracts; browser appearance/performance not tested'}));
