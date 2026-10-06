import * as T from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';

// Detail samples use the existing object envelopes in metres. No simulated cloth
// or per-frame deformation: deterministic meshes also survive production export.
export const DETAIL_REVISION='soft-furniture-v10.2-flat';
export {material,rigid,soft,pillow,lineMesh,roundedLoop,finishGroup,projectedUV,addMesh};
const textures=new Map();
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
function tex(kind,relief=false){
 const key=kind+(relief?'-relief':'-color');if(textures.has(key))return textures.get(key);
 const canvas=document.createElement('canvas');canvas.width=canvas.height=512;
 const ctx=canvas.getContext('2d'),img=ctx.createImageData(512,512);let seed=51379;
 const rand=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
 for(let y=0;y<512;y++)for(let x=0;x<512;x++){
  const weave=(Math.sin(x*Math.PI)+Math.cos(y*Math.PI))*1.4;
  const grain=Math.sin(x*.38+Math.sin(y*.027)*.55)*2+Math.sin(x*.091)*1.2;
  const v=relief?128+(kind==='fabric'?weave*2:grain*2)+(rand()-.5)*5:246+(kind==='fabric'?weave:grain)+(rand()-.5)*3;
  const j=(y*512+x)*4;img.data[j]=img.data[j+1]=img.data[j+2]=clamp(v,0,255);img.data[j+3]=255;
 }
 ctx.putImageData(img,0,0);const tx=new T.CanvasTexture(canvas);
 tx.colorSpace=relief?T.NoColorSpace:T.SRGBColorSpace;tx.wrapS=tx.wrapT=T.RepeatWrapping;tx.userData.shared=true;tx.anisotropy=4;
 textures.set(key,tx);return tx;
}
function material(color,kind,role,spec={}){
 if(kind==='wood'&&spec.furnitureWoodFinish==='lacquer'){const m=new T.MeshPhysicalMaterial({color,roughness:spec.lacquerRoughness??.36,metalness:0,clearcoat:.18,clearcoatRoughness:.45,envMapIntensity:.3});m.userData.finishRole=role;m.userData.furnitureSurface='satin-lacquer';return m;}
 const m=new T.MeshStandardMaterial({color,roughness:kind==='fabric'?(spec.fabricRoughness??.78):kind==='wood'?(spec.woodRoughness??.62):kind==='metal'?(spec.metalRoughness??.35):.7,metalness:kind==='metal'?.72:0,envMapIntensity:kind==='metal'?.7:.2});
 if(kind==='fabric'||kind==='wood'){m.map=tex(kind);m.bumpMap=tex(kind,true);m.bumpScale=kind==='fabric'?.00035:.00055;}
 if(role==='appliance-metal'){m.bumpMap=tex('metal',true);m.bumpScale=.00012;m.userData.surface='brushed-silver';}
 m.userData.finishRole=role;return m;
}
function projectedUV(geo,period){
 const p=geo.attributes.position,n=geo.attributes.normal,uv=new Float32Array(p.count*2);
 for(let i=0;i<p.count;i++){
  const x=p.getX(i),y=p.getY(i),z=p.getZ(i),ax=Math.abs(n.getX(i)),ay=Math.abs(n.getY(i)),az=Math.abs(n.getZ(i));
  const [u,v]=ay>=ax&&ay>=az?[x,z]:ax>=az?[z,y]:[x,y];
  uv[2*i]=u/period;uv[2*i+1]=v/period;
 }geo.setAttribute('uv',new T.BufferAttribute(uv,2));return geo;
}
function addMesh(group,geometry,mat,name,pos=[0,0,0]){
 const mesh=new T.Mesh(geometry,mat);mesh.name=name;mesh.position.set(...pos);mesh.castShadow=mesh.receiveShadow=true;
 mesh.userData.detailPart=name;group.add(mesh);return mesh;
}
function rigid(group,w,h,d,pos,mat,name,r=.01){
 const geo=new RoundedBoxGeometry(w,h,d,3,Math.min(r,w/3,h/3,d/3));
 projectedUV(geo,.3);return addMesh(group,geo,mat,name,pos);
}
function soft(group,w,h,d,pos,mat,name,{radius=.035,sag=0,phase=0}={}){
 const geo=new RoundedBoxGeometry(w,h,d,5,Math.min(radius,w*.22,h*.42,d*.22)),p=geo.attributes.position;
 p.needsUpdate=true;geo.computeVertexNormals();projectedUV(geo,.24);
 return addMesh(group,geo,mat,name,pos);
}
function lineMesh(group,points,mat,name,r=.0013,closed=false){
 const curve=new T.CatmullRomCurve3(points.map(p=>new T.Vector3(...p)),closed,'centripetal');
 return addMesh(group,new T.TubeGeometry(curve,Math.max(20,points.length*3),r,5,closed),mat,name);
}
function roundedLoop(w,d,y=0,r=.025){
 const points=[],hx=w/2,hz=d/2;
 for(const [cx,cz,a]of [[hx-r,hz-r,0],[-hx+r,hz-r,Math.PI/2],[-hx+r,-hz+r,Math.PI],[hx-r,-hz+r,Math.PI*1.5]]){
  for(let i=0;i<6;i++){const t=a+i/5*Math.PI/2;points.push([cx+r*Math.cos(t),y,cz+r*Math.sin(t)]);}
 }return points;
}
// A sewn envelope rather than a rounded box. Two curved skins join at a thin
// pinched perimeter; UVs follow real dimensions, not arbitrary face stretching.
function pillow(group,w,h,d,pos,mat,seam,name,{tilt=0,yaw=0,phase=0}={}){
 const nx=30,nz=20,verts=[],uv=[],indices=[];
 for(const sign of [1,-1])for(let j=0;j<=nz;j++)for(let i=0;i<=nx;i++){
  const u=i/nx*2-1,v=j/nz*2-1;
  const bulge=Math.pow(Math.max(0,(1-u*u)*(1-v*v)),.48);
  const x=w*.5*u*(1-.045*Math.pow(Math.abs(v),6)),z=d*.5*v*(1-.06*Math.pow(Math.abs(u),6));
  const crease=0;
  verts.push(x,sign*(.004+h*.49*bulge)+crease,z);uv.push((x+w/2)/.24,(z+d/2)/.24);
 }
 const side=(nx+1)*(nz+1);
 for(let k=0;k<2;k++)for(let j=0;j<nz;j++)for(let i=0;i<nx;i++){
  const a=k*side+j*(nx+1)+i,b=a+1,c=a+nx+1,e=c+1;
  if(k===0)indices.push(a,c,b,b,c,e);else indices.push(a,b,c,b,e,c);
 }
 const border=[];
 for(let i=0;i<=nx;i++)border.push(i);
 for(let j=1;j<=nz;j++)border.push(j*(nx+1)+nx);
 for(let i=nx-1;i>=0;i--)border.push(nz*(nx+1)+i);
 for(let j=nz-1;j>0;j--)border.push(j*(nx+1));
 for(let i=0;i<border.length;i++){const a=border[i],b=border[(i+1)%border.length];indices.push(a,b,a+side,b,b+side,a+side);}
 const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(verts,3));geo.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geo.setIndex(indices);geo.computeVertexNormals();
 const wrap=new T.Group();wrap.position.set(...pos);wrap.rotation.set(tilt,yaw,0);group.add(wrap);
 addMesh(wrap,geo,mat,name);
 const outline=border.map(i=>[verts[i*3],0,verts[i*3+2]]);
 lineMesh(wrap,outline,seam,name+'-sewn-edge',.0015,true);return wrap;
}
function cloth(group,point,nx,nz,mat,name,hemMat){
 const positions=[],uv=[],indices=[];
 for(let j=0;j<=nz;j++)for(let i=0;i<=nx;i++){
  const p=point(i/nx,j/nz);positions.push(...p);uv.push(i/nx*point.width/.24,j/nz*point.depth/.24);
 }
 for(let j=0;j<nz;j++)for(let i=0;i<nx;i++){const a=j*(nx+1)+i,b=a+1,c=a+nx+1;indices.push(a,c,b,b,c,c+1);}
 const geo=new T.BufferGeometry();geo.setAttribute('position',new T.Float32BufferAttribute(positions,3));geo.setAttribute('uv',new T.Float32BufferAttribute(uv,2));geo.setIndex(indices);geo.computeVertexNormals();
 const m=mat.clone();m.side=T.DoubleSide;addMesh(group,geo,m,name);
 if(hemMat){
  const edge=[];
  for(let i=0;i<=nx;i+=2)edge.push(point(i/nx,0));
  for(let j=2;j<=nz;j+=2)edge.push(point(1,j/nz));
  for(let i=nx-2;i>=0;i-=2)edge.push(point(i/nx,1));
  for(let j=nz-2;j>0;j-=2)edge.push(point(0,j/nz));
  lineMesh(group,edge,hemMat,name+'-hem',.0016,true);
 }return geo;
}
function finishGroup(g,f){
 g.userData.furniture=f.id;g.userData.detailRevision=DETAIL_REVISION;
 const b=new T.Box3().setFromObject(g),expected=new T.Vector3(f.w/1000,f.h/1000,f.d/1000);
 // A soft silhouette must stay inside the original collision/2D envelope.
 // Normalize only if a small seam/deformation escapes it; do not stretch a
 // normal-height mattress when the user edits the bed's headboard height.
 for(const [axis,max]of [['x',expected.x],['z',expected.z]]){const span=2*Math.max(Math.abs(b.min[axis]),Math.abs(b.max[axis]));if(span>max+.0001)g.scale[axis]=max/span;}
 if(b.max.y>expected.y+.0001)g.scale.y=expected.y/b.max.y;
 return g;
}
export function refinedFurniture(f){
 const g=new T.Group(),w=f.w/1000,d=f.d/1000,h=f.h/1000,p=f.finishes||{},s=f.finishSpec||{};
 const upholstery=material(f.color,'fabric','upholstery',s),white=material(p.pillow||'#fbfaf7','fabric','textile',s),seam=material(f.color,'fabric','upholstery',s);
 const frame=material(p.bedFrame||p.wood||'#baa385','wood','bedFrame',s),head=material(p.bedHead||f.color,'fabric','bedHead',s),runner=material(p.bedRunner||f.color,'fabric','bedRunner',s);
 const base=material(f.color,'fabric','upholstery',s),feet=material(p.wood||'#8d7e6a','wood','wood',s),cushion=material(p.cushion||p.ceramic||f.color,'fabric','cushion',s);
 if(f.type==='bed'){
  const footH=Math.min(.065,h*.11),frameH=Math.min(.21,h*.26),mattH=Math.min(.215,h*.24),top=footH+frameH+mattH;
  for(const x of [-w*.39,w*.39])for(const z of [-d*.35,d*.35])rigid(g,.055,footH,.055,[x,footH/2,z],feet,'bed-foot',.006);
  rigid(g,w,frameH,d-.11,[0,footH+frameH/2,.055],frame,'bed-frame',.015);
  rigid(g,w,h,.08,[0,h/2,-d/2+.04],frame,'bed-head-structure',.012);
  const n=Math.max(3,Math.round(w/.28)),panelW=(w-.045)/n,panelH=Math.max(.14,h-top+.025);
  for(let i=0;i<n;i++){
   const x=-(w-.045)/2+(i+.5)*panelW;
   soft(g,panelW-.005,panelH,.055,[x,top-.065+panelH/2,-d/2+.091],head,'bed-head-pad-'+i,{radius:.018});
  }
  soft(g,w-.06,mattH,d-.15,[0,footH+frameH+mattH/2,.055],white,'bed-mattress',{radius:.038});
  const mattressEdge=roundedLoop(w-.065,d-.155,top-.023,.035).map(([x,y,z])=>[x,y,z+.055]);
  lineMesh(g,mattressEdge,white,'bed-mattress-piping',.0018,true);
  const z0=-d*.19,z1=d/2-.015,drop=Math.min(.15,frameH*.64);
  const drape=(u,v)=>{
   const a=u*2-1,e=Math.max(0,(Math.abs(a)-.88)/.12),x=Math.sign(a)*Math.min(Math.abs(a)*(w-.025)*.565,w/2-.012);
   const z=z0+(z1-z0)*Math.min(v/.94,1),foot=Math.max(0,(v-.94)/.06);
   const edgeDrop=Math.max(e,foot);
   const wave=0;
   const compression=0;
   return [x,top+.021+wave+compression-drop*edgeDrop,z];
  };drape.width=w;drape.depth=z1-z0;
  cloth(g,drape,72,54,white,'bed-duvet-draped',white);
  const runnerPoint=(u,v)=>{
   const globalV=.61+v*.235,q=drape(u,globalV);
   const a=u*2-1;
   q[0]+=Math.sign(a)*.004*clamp((Math.abs(a)-.72)/.16,0,1);
   q[1]+=.005;return q;
  };runnerPoint.width=w;runnerPoint.depth=(z1-z0)*.235;
  cloth(g,runnerPoint,72,18,runner,'bed-runner-draped',runner);
  const np=w>=1.3?2:1,pw=Math.min(.71,(w-.15-(np-1)*.055)/np);
  for(let i=0;i<np;i++){
   const x=np===1?0:(i===0?-1:1)*w*.235;
   pillow(g,pw,Math.min(.19,h*.19),Math.min(.42,d*.22),[x,top+.095,-d/2+.35],white,white,'bed-sleeping-pillow-'+i,{tilt:-.1,yaw:(i?1:-1)*.025,phase:i});
   pillow(g,pw*.63,Math.min(.14,h*.14),Math.min(.30,h*.29),[x,top+.145,-d/2+.56],i===0?runner:white,i===0?runner:white,'bed-accent-pillow-'+i,{tilt:Math.PI/2-.24,yaw:(i?1:-1)*.025,phase:i+.6});
  }
 }else{
  const footH=Math.min(.10,h*.13),baseH=Math.min(.20,h*.25),seatH=Math.min(.12,h*.15),seatTop=footH+baseH+seatH;
  const armW=Math.min(.13,w*.10),backD=Math.min(.14,d*.2),front=.025;
  for(const x of [-w*.39,w*.39])for(const z of [-d*.33,d*.33])rigid(g,.038,footH,.038,[x,footH/2,z],feet,'sofa-foot',.008);
  soft(g,w-.018,baseH,d-.018,[0,footH+baseH/2,0],base,'sofa-base',{radius:.035});
  soft(g,w-.025,h-footH,backD,[0,(h+footH)/2,-d/2+backD/2+.007],base,'sofa-back-frame',{radius:.042});
  const armH=Math.max(.20,h*.67-footH);
  for(const sign of [-1,1]){
   const x=sign*(w/2-armW/2-.003);
   soft(g,armW,armH,d-.03,[x,footH+armH/2,.005],base,'sofa-arm-'+sign,{radius:.042});
   const points=roundedLoop(armW-.018,d-.05,0,.015).map(([xx,yy,zz])=>[xx+x,footH+armH-.017,zz+.005]);
   lineMesh(g,points,seam,'sofa-arm-piping-'+sign,.0012,true);
  }
  const n=w>2.2?3:w>1.15?2:1,cw=(w-2*armW-.027)/n,seatD=d-backD-front-.038,seatZ=-d/2+backD+.02+seatD/2;
  for(let i=0;i<n;i++){
   const x=-(w-2*armW-.027)/2+(i+.5)*cw;
   soft(g,cw-.014,seatH,seatD,[x,seatTop-seatH/2,seatZ],upholstery,'sofa-seat-'+i,{radius:.038,sag:0,phase:i});
   const outline=roundedLoop(cw-.029,seatD-.015,seatTop-.025,.03).map(([xx,y,z])=>[xx+x,y,z+seatZ]);
   lineMesh(g,outline,seam,'sofa-seat-piping-'+i,.0013,true);
   const backH=Math.min(.39,h-seatTop-.015),cy=seatTop+backH*.49-.005;
   pillow(g,cw-.018,.17,backH,[x,cy,-d/2+backD+.068],i%2?cushion:white,i%2?cushion:white,'sofa-back-cushion-'+i,{tilt:Math.PI/2-.1,phase:i});
  }
 }
 return finishGroup(g,f);
}
