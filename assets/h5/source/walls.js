import * as T from 'three';
import {DEFAULT} from './data.js';
const len=w=>Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]);
export function endpointPadding(w,all,end){const p=end?w.b:w.a,l=len(w),horizontal=Math.abs(w.b[1]-w.a[1])<.01,axis=horizontal?0:1,k=1-axis,out=(end?1:-1)*(w.b[axis]-w.a[axis])/l;let pad=0;for(const n of all){if(n===w||n.demolished)continue;const nh=Math.abs(n.b[1]-n.a[1])<.01;if(horizontal===nh)continue;const delta=n.a[axis]-p[axis];if(Math.abs(delta)>n.t/2+.1)continue;const lo=Math.min(n.a[k],n.b[k]),hi=Math.max(n.a[k],n.b[k]);if(p[k]>=lo-w.t/2-.1&&p[k]<=hi+w.t/2+.1)pad=Math.max(pad,n.t/2+delta*out);}return pad;}
export function intervals(w){let at=0,out=[];for(const o of [...w.opens].sort((a,b)=>a.at-b.at)){if(o.at>at)out.push([at,o.at]);at=Math.max(at,o.at+o.width);}if(at<len(w))out.push([at,len(w)]);return out;}
// All rectangles have the same winding. A single nonzero fill forms their union,
// so an adjacent wall cannot paint a differently colored end cap over it.
export function solidPlanPath(rects){return rects.map(r=>`M${r.x0} ${r.y0}H${r.x1}V${r.y1}H${r.x0}Z`).join('');}
// Outline only the exterior of a rectangle union, including actual opening jambs.
export function planOutline(rects){
 if(!rects.length)return '';
 const xs=[...new Set(rects.flatMap(r=>[r.x0,r.x1]))].sort((a,b)=>a-b),ys=[...new Set(rects.flatMap(r=>[r.y0,r.y1]))].sort((a,b)=>a-b),nx=xs.length-1,ny=ys.length-1,grid=new Uint8Array(nx*ny),xi=new Map(xs.map((x,i)=>[x,i])),yi=new Map(ys.map((y,i)=>[y,i]));
 for(const r of rects)for(let y=yi.get(r.y0);y<yi.get(r.y1);y++)for(let x=xi.get(r.x0);x<xi.get(r.x1);x++)grid[y*nx+x]=1;
 const filled=(x,y)=>x>=0&&x<nx&&y>=0&&y<ny&&grid[y*nx+x],edges=[];
 for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){if(!filled(x,y))continue;
  if(!filled(x,y-1))edges.push(`M${xs[x]} ${ys[y]}H${xs[x+1]}`);
  if(!filled(x,y+1))edges.push(`M${xs[x]} ${ys[y+1]}H${xs[x+1]}`);
  if(!filled(x-1,y))edges.push(`M${xs[x]} ${ys[y]}V${ys[y+1]}`);
  if(!filled(x+1,y))edges.push(`M${xs[x+1]} ${ys[y]}V${ys[y+1]}`);
 }return edges.join('');
}
export function wallRect(w,a,b,all){const l=len(w),dx=(w.b[0]-w.a[0])/l,dy=(w.b[1]-w.a[1])/l;if(a===0)a-=endpointPadding(w,all,false);if(Math.abs(b-l)<.1)b+=endpointPadding(w,all,true);const p=[w.a[0]+a*dx,w.a[1]+a*dy],q=[w.a[0]+b*dx,w.a[1]+b*dy];return {x0:Math.min(p[0],q[0])-(Math.abs(dy)*w.t/2),x1:Math.max(p[0],q[0])+(Math.abs(dy)*w.t/2),y0:Math.min(p[1],q[1])-(Math.abs(dx)*w.t/2),y1:Math.max(p[1],q[1])+(Math.abs(dx)*w.t/2),wall:w.id};}
function prism(w,a,b,z0,z1,all){return {...wallRect(w,a,b,all),z0,z1,wall:w.id,interval:[a,b]};}
export function wallPrisms(all){const out=[];for(const w of all){if(w.demolished)continue;if(Math.abs(w.a[0]-w.b[0])>.1&&Math.abs(w.a[1]-w.b[1])>.1)throw Error('墙体请使用水平或垂直方向');for(const[a,b]of intervals(w))out.push(prism(w,a,b,0,w.height,all));for(const o of w.opens){const sill=o.sillHeight??850;if(o.kind==='window'&&sill>0)out.push(prism(w,o.at,o.at+o.width,0,sill,all));const head=o.kind==='window'?sill+(o.height??1350):(o.height||2100)+50;if(w.height>head)out.push(prism(w,o.at,o.at+o.width,head,w.height,all));}}return out;}
export function unionWalls(all,mat){const prisms=wallPrisms(all),unique=k=>[...new Set(prisms.flatMap(p=>[p[k+'0'],p[k+'1']]))].sort((a,b)=>a-b),xs=unique('x'),ys=unique('y'),zs=unique('z'),nx=xs.length-1,ny=ys.length-1,nz=zs.length-1,occupied=new Uint8Array(nx*ny*nz),index=(x,y,z)=>(z*ny+y)*nx+x;
 const xi=new Map(xs.map((v,i)=>[v,i])),yi=new Map(ys.map((v,i)=>[v,i])),zi=new Map(zs.map((v,i)=>[v,i]));
 for(const p of prisms)for(let z=zi.get(p.z0);z<zi.get(p.z1);z++)for(let y=yi.get(p.y0);y<yi.get(p.y1);y++)for(let x=xi.get(p.x0);x<xi.get(p.x1);x++)occupied[index(x,y,z)]=1;
 const filled=(x,y,z)=>x>=0&&x<nx&&y>=0&&y<ny&&z>=0&&z<nz&&occupied[index(x,y,z)],positions=[],normals=[],uvs=[];
 // Faces exist only on the exterior of the union. No overlapping caps or internal wall surfaces.
 const face=(a,b,c,d,n)=>{for(const p of[a,b,c,a,c,d]){positions.push((p[0]-DEFAULT.width/2)/1000,p[2]/1000,(p[1]-DEFAULT.depth/2)/1000);normals.push(...n);uvs.push((n[0]?p[1]:p[0])/1000,(n[1]?p[1]:p[2])/1000);}};
 for(let z=0;z<nz;z++)for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){if(!filled(x,y,z))continue;const a=xs[x],b=xs[x+1],c=ys[y],d=ys[y+1],lo=zs[z],hi=zs[z+1];
 if(!filled(x,y,z-1))face([a,c,lo],[b,c,lo],[b,d,lo],[a,d,lo],[0,-1,0]);
 if(!filled(x,y,z+1))face([a,c,hi],[a,d,hi],[b,d,hi],[b,c,hi],[0,1,0]);
 if(!filled(x-1,y,z))face([a,c,lo],[a,d,lo],[a,d,hi],[a,c,hi],[-1,0,0]);
 if(!filled(x+1,y,z))face([b,c,lo],[b,c,hi],[b,d,hi],[b,d,lo],[1,0,0]);
 if(!filled(x,y-1,z))face([a,c,lo],[a,c,hi],[b,c,hi],[b,c,lo],[0,0,-1]);
 if(!filled(x,y+1,z))face([a,d,lo],[b,d,lo],[b,d,hi],[a,d,hi],[0,0,1]);}
 const g=new T.BufferGeometry();g.setAttribute('position',new T.Float32BufferAttribute(positions,3));g.setAttribute('normal',new T.Float32BufferAttribute(normals,3));g.setAttribute('uv',new T.Float32BufferAttribute(uvs,2));g.computeBoundingBox();const mesh=new T.Mesh(g,mat);mesh.castShadow=mesh.receiveShadow=true;mesh.userData.wallUnion=true;mesh.userData.prisms=prisms;mesh.userData.gridCells=occupied.length;return mesh;}
// Hinge, the direction of the closed leaf, and inward normal are explicit in plan coordinates.
export function doorPose(w,o){const l=len(w),dx=(w.b[0]-w.a[0])/l,dy=(w.b[1]-w.a[1])/l,hinge=o.hingeEnd==='end'?o.at+o.width:o.at,closed=o.hingeEnd==='end'?[-dx,-dy]:[dx,dy],inward=[-dy*o.swing,dx*o.swing],a=(o.angle??45)*Math.PI/180;return {nominalHinge:[w.a[0]+dx*hinge,w.a[1]+dy*hinge],hinge:[w.a[0]+dx*hinge+inward[0]*(w.t/2+15)+closed[0]*25,w.a[1]+dy*hinge+inward[1]*(w.t/2+15)+closed[1]*25],leafWidth:o.width-50,closed,inward,leaf:[closed[0]*Math.cos(a)+inward[0]*Math.sin(a),closed[1]*Math.cos(a)+inward[1]*Math.sin(a)],angle:a};}
