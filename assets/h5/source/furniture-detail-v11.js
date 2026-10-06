import {tabletopDecor} from './tabletop-decor.js';
import * as T from 'three';
import {refinedFurniture,material,rigid,soft,pillow,lineMesh,roundedLoop,finishGroup,projectedUV,addMesh} from './soft-furniture-v10.js';
export const FULL_REVISION='whole-home-detail-v11.1';
export const FULL_TYPES=['bed','sofa','sofabed','armchair','chair','wardrobe','bookshelf','nightstand','desk','dresser','table','tvstand','coffee','rug','counter','vanity','ksink','stove','fridge','toilet','shower','plant','wallcab','fridgecab','endpanel','hood','pendant','downlight','tv'];
const limit=(v,a,b)=>Math.max(a,Math.min(b,v));
function cylinder(g,r,h,pos,m,name,rTop=r){return addMesh(g,new T.CylinderGeometry(rTop,r,h,32,1),m,name,pos);}
function rod(g,a,b,r,m,name,rTop=r){const A=new T.Vector3(...a),B=new T.Vector3(...b),o=addMesh(g,new T.CylinderGeometry(rTop,r,A.distanceTo(B),12),m,name);o.position.copy(A).add(B).multiplyScalar(.5);o.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),B.sub(A).normalize());return o;}
function ring(g,r,t,pos,m,name,sx=1,sz=1){const o=addMesh(g,new T.TorusGeometry(r,t,8,48),m,name,pos);o.rotation.x=-Math.PI/2;o.scale.set(sx,sz,1);return o;}
function veneer(f){const p=f.finishes||{},s=f.finishSpec||{};return {wood:material(p.wood||f.color,'wood','wood',s),body:material(f.color,'plain','cabinet',s),fabric:material(f.color,'fabric','upholstery',s),metal:material(p.metal||'#a89479','metal','metal',s),dark:material('#343937','plain','detail-shadow',s),stone:material(p.stone||'#eee9df','plain','stone',s),ceramic:new T.MeshPhysicalMaterial({color:p.ceramic||'#f5f2eb',roughness:.24,clearcoat:.55,clearcoatRoughness:.3}),glass:new T.MeshPhysicalMaterial({color:p.glass||'#c8d5cd',roughness:.12,transparent:true,opacity:.15,depthWrite:false})};}
function markOwned(g){g.traverse(o=>{if(!o.isMesh)return;for(const m of Array.isArray(o.material)?o.material:[o.material])if(m&&!m.userData.borrowedDetail)m.userData.ownedFurnitureDetail=true;});}
function body(g,f){
 g.userData.bodyForDimensions=true;finishGroup(g,f);
 // Oblique tapered legs must be checked against vertices rather than a rotated
 // local AABB, whose corner expansion can falsely add several millimetres.
 const b=new T.Box3().setFromObject(g,true),height=b.max.y-b.min.y,target=f.h/1000;
 if(height>1e-5){const ratio=target/height;g.scale.y*=ratio;g.position.y=-b.min.y*ratio;}
 return g;
}
// A profile edits furniture bodies independently of supported tabletop items.
// Existing lamps/screens are carried over; body height is never inferred from them.
function carryAccessories(root,base,f){
 if(!base||!['desk','nightstand'].includes(f.type))return;
 const anchor=f.type==='nightstand'?.5*base.scale.y:.745*base.scale.y;
 base.position.set(0,0,0);base.rotation.set(0,0,0);base.updateMatrixWorld(true);
 const props=new T.Group();props.name='existing-tabletop-items';props.userData.accessories=true;
 const keep=base.children.filter(o=>{const b=new T.Box3().setFromObject(o);return b.min.y>=anchor-.007&&b.max.y>anchor+.008;});
 for(const o of keep){const a=o.clone();a.position.y*=base.scale.y;a.scale.y*=base.scale.y;a.position.y+=f.h/1000-anchor;a.traverse(c=>{if(c.isMesh){c.geometry=c.geometry.clone();c.material=Array.isArray(c.material)?c.material.map(m=>m.clone()):c.material.clone();for(const m of Array.isArray(c.material)?c.material:[c.material])m.userData.ownedFurnitureDetail=true;}});props.add(a);}
 if(props.children.length)root.add(props);
}
function cupboard(g,f,m){
 const w=f.w/1000,d=f.d/1000,h=f.h/1000,t=Math.min(.018,w*.035,d*.05),floating=['wallcab','fridgecab'].includes(f.type),bottom=floating?0:Math.min(.075,h*.12),front=d/2-.01;
 if(!floating)rigid(g,w-.025,bottom,d-.065,[0,bottom/2,-.025],m.dark,'cabinet-recessed-plinth',.002);
 for(const x of [-w/2+t/2,w/2-t/2])rigid(g,t,h-bottom,d-.012,[x,(h+bottom)/2,-.006],m.body,'cabinet-side',.0018);
 for(const y of [bottom+t/2,h-t/2])rigid(g,w-2*t,t,d-.012,[0,y,-.006],m.body,'cabinet-horizontal',.0018);
 rigid(g,w-2*t,h-bottom-2*t,t,[0,(h+bottom)/2,-d/2+t/2],m.body,'cabinet-back',.0015);
 const n=Math.max(1,Math.round(w/.53)),pw=(w-2*t)/n;
 if(f.type==='bookshelf'){
  const levels=Math.max(3,Math.round((h-bottom)/.38));
  for(let i=1;i<n;i++)rigid(g,t,h-bottom-2*t,d-.02,[-w/2+t+i*pw,(h+bottom)/2,-.004],m.wood,'bookcase-stile',.0015);
  for(let k=1;k<levels;k++){const y=bottom+k*(h-bottom)/levels;rigid(g,w-2*t,t,d-.022,[0,y,-.005],m.wood,'bookcase-shelf',.002);
   for(let j=0;j<n;j++)for(let b=0;b<4;b++){const bw=Math.min(.048,pw*.085),bh=.17+(b%3)*.025,bd=Math.min(.19,d*.63),x=-w/2+t+j*pw+.07+b*(bw+.009),color=[f.finishes?.pillow,f.finishes?.bedRunner,f.finishes?.cushion,f.finishes?.wood][b]||f.color;
    const book=material(color,'plain','book');rigid(g,bw,bh,bd,[x,y+t/2+bh/2,d*.04],book,'book-volume',.001);
    rigid(g,bw*.92,.004,.001,[x,y+t/2+bh*.72,d*.04+bd/2+.001],m.stone,'book-spine-line',.0003);
   }
  }
 }else{
  for(let i=0;i<n;i++){const x=-w/2+t+(i+.5)*pw,rows=f.type==='nightstand'?2:1,dh=(h-bottom-t)/rows;
   for(let k=0;k<rows;k++){const y=bottom+(k+.5)*dh;rigid(g,pw-.004,dh-.004,.019,[x,y,front],(f.finishSpec?.id==='champagne_pearl'&&f.type==='wardrobe'&&i===n-1?m.champagne:m.body),'cabinet-door',.0018);
    if(f.type==='wardrobe')rod(g,[x+pw*.3,Math.min(1.04,h*.52)-.105,d/2-.004],[x+pw*.3,Math.min(1.04,h*.52)+.105,d/2-.004],.0025,m.metal,'wardrobe-pull');
    else rigid(g,pw*.5,.007,.004,[x,y+dh*.26,d/2-.003],m.metal,'cabinet-pull',.001);
   }
  }
 }
}
function curvedChair(g,f,m){
 const w=f.w/1000,d=f.d/1000,h=f.h/1000,seatY=Math.min(.46,h*.54),sz=.01;
 for(const sx of [-1,1])for(const ss of [-1,1])rod(g,[sx*(w/2-.025),0,ss*(d/2-.03)],[sx*(w/2-.065),seatY-.04,ss*(d/2-.075)],.010,m.wood,'chair-tapered-leg',.016);
 rigid(g,w-.065,.03,d-.07,[0,seatY-.048,sz],m.wood,'chair-seat-frame',.012);
 soft(g,w-.025,.072,d-.035,[0,seatY-.021,sz],m.fabric,'chair-seat-cushion',{radius:.031,sag:0});
 const bw=w-.045,bh=Math.max(.13,h-seatY-.062),positions=[],uv=[],idx=[],nx=24,ny=12;
 for(let j=0;j<=ny;j++)for(let i=0;i<=nx;i++){const u=i/nx*2-1,v=j/ny,x=bw/2*u,y=seatY+.055+v*bh,z=-d/2+.037+.06*u*u-.018*v;positions.push(x,y,z);uv.push((x+bw/2)/.24,v*bh/.24);}
 for(let j=0;j<ny;j++)for(let i=0;i<nx;i++){const a=j*(nx+1)+i;idx.push(a,a+1,a+nx+1,a+1,a+nx+2,a+nx+1);}
 const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(positions,3));geo.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geo.setIndex(idx);geo.computeVertexNormals();
 const fm=m.fabric.clone();fm.side=T.DoubleSide;addMesh(g,geo,fm,'chair-curved-back');
 const edge=[];for(let i=0;i<=nx;i++)edge.push(positions.slice((ny*(nx+1)+i)*3,(ny*(nx+1)+i)*3+3));lineMesh(g,edge,m.wood,'chair-back-top',.007);
 for(const sx of [-1,1])rod(g,[sx*(bw/2-.005),seatY-.025,-d/2+.063],[sx*(bw/2-.005),h-.007,-d/2+.083],.006,m.wood,'chair-back-support');
}
function table(g,f,m){const w=f.w/1000,d=f.d/1000,h=f.h/1000,t=['desk','dresser'].includes(f.type)?.027:.032;
 const fitted=['desk','dresser'].includes(f.type)&&f.builtIn,bodyMat=fitted?material(f.color,'wood','cabinet',{...f.finishSpec,furnitureWoodFinish:'lacquer'}):m.body;
 if(fitted)addMesh(g,new T.BoxGeometry(w,t,d),bodyMat,'wall-fitted-lacquer-top',[0,h-t/2,0]);
 else rigid(g,w,t,d,[0,h-t/2,0],f.type==='dresser'?m.body:f.type==='desk'?m.wood:m.stone,'beveled-table-top',.010);
 const legTop=h-t,rx=w/2-.065,rz=d/2-.065;
 if(f.type==='dresser'||f.supportConstruction==='side-panels'){const panel=.025;for(const sx of [-1,1]){
  const pos=[sx*(w/2-panel/2),legTop/2,0];
  if(fitted)addMesh(g,new T.BoxGeometry(panel,legTop,d),bodyMat,'dresser-full-side-panel',pos);
  else rigid(g,panel,legTop,d-.006,pos,m.body,'dresser-full-side-panel',.002);
 }}
 else for(const sx of [-1,1])for(const ss of [-1,1])rod(g,[sx*(rx+.013),0,ss*(rz+.012)],[sx*rx,legTop,ss*rz],.012,f.type==='desk'?m.dark:m.wood,'table-tapered-leg',.020);
 for(const z of [-rz,rz])rigid(g,w-.15,.052,.018,[0,h-t-.038,z],f.type==='dresser'?m.body:m.wood,'table-apron',.003);
 if(['desk','dresser'].includes(f.type)){const dw=Math.min(.46,w*.34),x=w/2-dw/2-.05;rigid(g,dw,.09,d-.12,[x,h-t-.065,0],m.wood,'desk-drawer',.004);rigid(g,dw*.40,.006,.009,[x,h-t-.059,d/2-.055],m.metal,'desk-pull',.001);}
}
function coffee(g,f,m){const w=f.w/1000,d=f.d/1000,h=f.h/1000,t=.027,r=w/2-.001,top=cylinder(g,r,t,[0,h-t/2,0],m.stone,'coffee-table-top');top.scale.z=d/w;
 ring(g,r-.004,.003,[0,h-.004,0],m.metal,'coffee-table-edge',1,d/w);
 for(let i=0;i<3;i++){const a=i*Math.PI*2/3;rod(g,[Math.cos(a)*w*.28,0,Math.sin(a)*d*.28],[Math.cos(a)*w*.24,h-t,Math.sin(a)*d*.24],.008,m.wood,'coffee-table-leg',.015);}
}
function fridge(g,f,m){const w=f.w/1000,d=f.d/1000,h=f.h/1000,pl=.045;rigid(g,w,h-pl,d-.038,[0,(h+pl)/2,-.019],m.body,'fridge-shell',.009);rigid(g,w-.035,pl,d-.055,[0,pl/2,-.022],m.dark,'fridge-plinth',.002);
 const split=h*.29;for(const [y,hh]of [[(pl+split)/2,split-pl-.006],[(split+h)/2,h-split-.006]]){rigid(g,w-.006,hh,.018,[0,y,d/2-.019],m.body,'fridge-door',.006);rod(g,[w*.35,y-.095,d/2-.006],[w*.35,y+.095,d/2-.006],.003,m.metal,'fridge-grip');}
 for(let i=0;i<10;i++)rigid(g,w*.65,.002,.002,[0,.010+i*.0028,d/2-.019],m.body,'fridge-vent',.0005);
 rigid(g,w*.26,.018,.001,[0,h*.75,d/2-.008],m.dark,'fridge-control-strip',.001);
}
function toilet(g,f,m){const w=f.w/1000,d=f.d/1000,h=f.h/1000,seat=Math.min(.44,h*.62),r=w*.45,cy=seat-.025,z=d*.13;
 const profile=[[.64,0],[.67,.025],[.68,.12],[.83,.20],[.96,cy-.065],[1,cy-.02],[.95,cy],[.78,cy-.01],[.65,cy-.09],[.40,.14],[.10,.12],[0,.12]].map(([rr,y])=>new T.Vector2(rr*r,y));
 const geo=new T.LatheGeometry(profile,48),inside=m.ceramic.clone();inside.color.multiplyScalar(.87);geo.clearGroups();for(let a=0;a<48;a++){const offset=a*(profile.length-1)*6;geo.addGroup(offset,6*6,0);geo.addGroup(offset+6*6,(profile.length-1-6)*6,1);}
 const mesh=addMesh(g,geo,[m.ceramic,inside],'toilet-curved-bowl',[0,0,z]);mesh.scale.z=d*.34/r;
 rigid(g,w*.58,.20,d*.37,[0,.10,-d*.19],m.ceramic,'toilet-rear-pedestal',.035);
 ring(g,r*.88,.011,[0,cy+.014,z],m.ceramic,'toilet-seat-rim',1,d*.34/r);
 rigid(g,w*.86,h-seat*.65,d*.23,[0,(h+seat*.65)/2,-d*.35],m.ceramic,'toilet-tank',.034);
 cylinder(g,.020,.002,[0,h-.001,-d*.35],m.metal,'toilet-flush-button');
 cylinder(g,.022,.004,[0,.126,z],m.dark,'toilet-bowl-drain');
}
function enrich(base,f,m){
 const w=f.w/1000,d=f.d/1000,h=f.h/1000;
 // Preserve holes, faucets, door glazing and stable component identity. New
 // parts are placed inside the existing envelope, never over the basin opening.
 if(['counter','vanity','ksink','shower','tv','hood','pendant','downlight','endpanel','plant','rug'].includes(f.type)){
  base.position.set(0,0,0);base.rotation.set(0,0,0);
  if(['counter','vanity'].includes(f.type)){
   const n=Math.max(1,Math.round(w/.55));for(let i=1;i<n;i++)rigid(base,.0015,h-.12,.002,[-w/2+i*w/n,(h+.07)/2,d/2-.005],m.dark,'cabinet-reveal-line',.0004);
  }else if(f.type==='ksink'){
   ring(base,.021,.001,[0,-.155,0],m.metal,'sink-drain-lip');for(let i=-2;i<=2;i++)rigid(base,.030,.001,.001,[0,-.153,i*.005],m.dark,'sink-drain-slot',.0002);
  }else if(f.type==='shower'){
   rigid(base,.15,.002,.075,[w*.28,.029,-d*.30],m.metal,'shower-drain',.003);for(let i=0;i<7;i++)rigid(base,.003,.001,.055,[w*.28-.057+i*.019,.031,-d*.30],m.dark,'shower-drain-slot',.0005);
   rod(base,[w*.29,h*.40,-d*.31],[w*.29,h*.68,-d*.31],.007,m.metal,'shower-rail');
  }else if(f.type==='hood'){
   for(let i=0;i<14;i++)rigid(base,w*.70,.001,.002,[0,.025,-d*.23+i*d*.035],m.dark,'hood-filter-slot',.0003);
   for(const x of [-w*.32,w*.32])cylinder(base,.018,.002,[x,.006,d*.28],m.ceramic,'hood-light');
  }else if(f.type==='tv'){
   rigid(base,w*.045,.002,.001,[0,.012,d/2-.002],m.metal,'tv-lower-mark',.0005);
  }else if(f.type==='downlight'){
   cylinder(base,w*.42,h*.42,[0,h*.24,0],m.dark,'downlight-recess',w*.33);ring(base,w*.43,.002,[0,.003,0],m.metal,'downlight-rim',1,d/w);
  }else if(f.type==='pendant'){
   ring(base,.005,.001,[0,h-.021,0],m.metal,'pendant-canopy-detail');
  }else if(f.type==='rug'){
   const points=roundedLoop(w-.035,d-.035,h-.001,.025);lineMesh(base,points,material(f.color,'fabric','rug-binding',f.finishSpec),'rug-bound-edge',.0012,true);
  }else if(f.type==='endpanel'){
   rigid(base,.002,h-.02,d-.008,[w/2-.002,h/2,0],m.body,'endpanel-edge-band',.0005);
  }else if(f.type==='plant'){
   ring(base,w*.245,.005,[0,h*.29,0],m.ceramic,'plant-pot-rim',1,d/w);
  }
  return base;
 }
 return null;
}
function hob(g,f,m){const w=f.w/1000,d=f.d/1000,h=f.h/1000;
 rigid(g,w,.008,d,[0,.004,0],m.dark,'hob-glass-base',.009);
 for(const x of [-w*.25,w*.25]){const r=Math.min(w*.145,d*.23),o=cylinder(g,r,.008,[x,.012,-d*.04],m.dark,'hob-burner');o.userData.burner=true;
  ring(g,r*.80,.002,[x,.016,-d*.04],m.metal,'hob-burner-ring');for(let j=0;j<4;j++){const a=j*Math.PI/2;rod(g,[x+Math.cos(a)*r*.20,.018,-d*.04+Math.sin(a)*r*.20],[x+Math.cos(a)*r*1.1,.018,-d*.04+Math.sin(a)*r*1.1],.0018,m.dark,'hob-grate');}
 }
 for(const x of [-w*.12,w*.12])cylinder(g,.015,Math.min(.011,h-.008),[x,.008+Math.min(.011,h-.008)/2,d*.32],m.metal,'hob-control');
}
export function wholeHomeFurniture(f,base){
 if(!FULL_TYPES.includes(f.type))return null;
 const root=new T.Group(),m=veneer(f);let g=new T.Group();
 m.body.roughness=f.finishSpec?.lacquerRoughness??.46;
 m.champagne=material(f.finishes?.champagne||f.color,'plain','cabinet',f.finishSpec);
 if(f.type==='fridge'){m.body=material(f.color,'metal','appliance-metal',f.finishSpec);m.body.roughness=.42;m.body.metalness=.78;m.body.userData.finishRole='appliance-metal';}
 m.stone.roughness=f.finishSpec?.stoneRoughness??.40;
 m.ceramic.userData.finishRole='ceramic';m.glass.userData.finishRole='glass';
 if(['bed','sofa','sofabed','armchair'].includes(f.type)){g=refinedFurniture(f);g.userData.bodyForDimensions=true;}
 else if(f.type==='chair')curvedChair(g,f,m);
 else if(['wardrobe','bookshelf','nightstand','wallcab','fridgecab'].includes(f.type))cupboard(g,f,m);
 else if(['table','desk','dresser'].includes(f.type))table(g,f,m);
 else if(f.type==='coffee')coffee(g,f,m);
 else if(f.type==='tvstand')cupboard(g,f,m);
 else if(f.type==='fridge')fridge(g,f,m);
 else if(f.type==='toilet')toilet(g,f,m);
 else if(f.type==='stove')hob(g,f,m);
 else {g=enrich(base,f,m);if(!g)return null;}
 if(!['counter','vanity','ksink','plant'].includes(f.type))body(g,f);
 else g.userData.bodyForDimensions=false; // Above/below-datum plumbing and tabletop objects retain their original bounds.
 g.name='furniture-body-v11';root.add(g);markOwned(g);carryAccessories(root,base,f);
 if(f.type==='dresser'){const a=new T.Group();a.name='dressing-table-accessories';a.userData.accessories=true;const w=f.w/1000,d=f.d/1000,y=f.h/1000,z=-d/2+.065;const mirror=new T.Mesh(new T.CircleGeometry(.28,64),new T.MeshPhysicalMaterial({color:'#dce1dd',metalness:.94,roughness:.08,side:T.DoubleSide}));mirror.position.set(0,y+.36,z);mirror.scale.y=1.10;a.add(mirror);const rim=addMesh(a,new T.TorusGeometry(.286,.007,10,64),m.metal,'dressing-mirror-frame',[0,y+.36,z]);rim.scale.y=1.10;rod(a,[0,y,z],[0,y+.085,z],.008,m.metal,'mirror-stand');rigid(a,.18,.012,.10,[0,y+.006,z+.01],m.metal,'mirror-base',.004);rigid(a,.22,.012,.13,[-w*.31,y+.006,0],m.stone,'cosmetic-tray',.012);for(let i=0;i<3;i++)cylinder(a,.018,.065+i*.012,[-w*.31+(i-1)*.045,y+.015,0],m.ceramic,'cosmetic-bottle');markOwned(a);root.add(a);}

 const decor=tabletopDecor(f,m);if(decor){markOwned(decor);root.add(decor);}
 root.userData.detailAssembly=FULL_REVISION;root.userData.furniture=f.id;return root;
}
