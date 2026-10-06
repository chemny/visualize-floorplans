import * as T from 'three';
// Accessories are a separate assembly, never part of body-height normalization.
export function tabletopDecor(f,m){
 if(f.accessories===false||!['table','coffee','counter'].includes(f.type))return null;
 if(f.type==='counter'&&!f.tabletopDecor)return null;
 const w=f.w/1000,d=f.d/1000;if(w<.4||d<.35)return null;
 const g=new T.Group();g.name='tabletop-decoration';g.userData.accessories=true;g.userData.tabletopDecor=true;g.position.y=f.h/1000;
 const scale=Math.min(1,w/(f.type==='table'?1.2:.6),d/(f.type==='table'?.65:.55));
 const mesh=(geo,mat,name,x,y,z)=>{const o=new T.Mesh(geo,mat);o.position.set(x,y,z);o.name=name;o.userData.detailPart=name;o.castShadow=o.receiveShadow=true;g.add(o);return o;};
 const box=(x,y,z,a,b,c,mat,name)=>mesh(new T.BoxGeometry(a,b,c),mat,name,x,y+b/2,z);
 const cylinder=(x,y,z,r,h,mat,name,rt=r)=>mesh(new T.CylinderGeometry(rt,r,h,24),mat,name,x,y+h/2,z);
 const cup=(x,y,z)=>{const r=.028*scale,h=.056*scale;cylinder(x,y,z,r,h,m.ceramic,'porcelain-cup');mesh(new T.CircleGeometry(r*.83,24),m.dark,'tea-surface',x,y+h+.0001,z).rotation.x=-Math.PI/2;const handle=mesh(new T.TorusGeometry(r*.6,.003*scale,6,16),m.ceramic,'cup-handle',x+r,y+h*.55,z);};
 const vase=(x,z)=>{const profile=[[.025,0],[.045,.035],[.04,.11],[.019,.16],[.020,.19]].map(([r,y])=>new T.Vector2(r*scale,y*scale));mesh(new T.LatheGeometry(profile,24),m.ceramic,'pearl-vase',x,0,z);
  const greenery=new T.MeshStandardMaterial({color:'#81907b',roughness:.9});for(let i=0;i<3;i++){const dx=(i-1)*.027*scale,top=(.32+i*.018)*scale;cylinder(x+dx,.15*scale,z,.002*scale,top-.15*scale,greenery,'vase-stem');for(let j=0;j<2;j++){const leaf=mesh(new T.SphereGeometry(.017*scale,10,6),greenery,'vase-leaf',x+dx+(j?-.015:.015)*scale,(.24+j*.045)*scale,z);leaf.scale.set(1.5,.22,.75);leaf.rotation.z=j?.5:-.5;}}};
 if(f.type==='table'){
  vase(0,0);for(const x of [-w*.29,w*.29])for(const z of [-d*.24,d*.24]){cylinder(x,0,z,.09*scale,.007*scale,m.ceramic,'dining-plate');cylinder(x,.007*scale,z,.065*scale,.003*scale,m.stone,'plate-center');box(x+.11*scale,0,z,.045*scale,.003*scale,.12*scale,m.fabric,'linen-napkin');cup(x-.115*scale,.001,z-.015*scale);}
 }else if(f.type==='coffee'){
  box(-w*.18,0,0,.20*scale,.018*scale,.14*scale,m.wood,'coffee-book');box(-w*.18,.018*scale,.01*scale,.18*scale,.014*scale,.13*scale,m.ceramic,'coffee-book-top');
  if(w>=.6){box(w*.18,0,0,.22*scale,.01*scale,.19*scale,m.metal,'champagne-tray');cup(w*.18,.01*scale,0);cylinder(w*.18+.067*scale,.01*scale,.035*scale,.022*scale,.045*scale,m.ceramic,'small-candle');}else cup(w*.18,.001,0);
 }else{
  const x=Math.max(-w/2+.12,Math.min(w/2-.34,(f.tabletopDecor.xMm||0)/1000)),z=-d*.24;
  box(x,0,z,.18*scale,.012*scale,.13*scale,m.wood,'kitchen-cutting-board');
  for(let i=0;i<2;i++){const px=x+(.15+i*.09)*scale,h=(.085+i*.025)*scale;cylinder(px,0,z,.028*scale,h,m.ceramic,'kitchen-storage-jar');cylinder(px,h,z,.030*scale,.009*scale,m.wood,'storage-jar-lid');}
 }
 return g;
}
