import {showerEnclosureSegments} from './shower-door.js';
// Plan dimensions are mm; the walk capsule stands on the room floor.
// A hanging cabinet is clear only if its full vertical span is above the head.
export function furnitureBlocksPoint(f,x,z,{originX=0,originY=0,radius=.18,eyeHeight=1.6,heightMm=750,ignoredTypes=[]}={}){
 if(ignoredTypes.includes(f.type)||f.type==='rug')return false;
 const bottom=(f.elevation||0)/1000,top=bottom+(f.h??heightMm)/1000;
 if(top<=.05||bottom>=eyeHeight+.15)return false;
 if(f.type==='shower'&&f.showerDoor){const q=[x*1000+originX,z*1000+originY];return showerEnclosureSegments(f).some(([a,b,pad])=>{const v=[b[0]-a[0],b[1]-a[1]],den=v[0]**2+v[1]**2,t=den?Math.max(0,Math.min(1,((q[0]-a[0])*v[0]+(q[1]-a[1])*v[1])/den)):0;return Math.hypot(q[0]-a[0]-v[0]*t,q[1]-a[1]-v[1]*t)<radius*1000+pad;});}
 const dx=x-(f.cx-originX)/1000,dz=z-(f.cy-originY)/1000,a=(f.rot||0)*Math.PI/180;
 const u=dx*Math.cos(a)+dz*Math.sin(a),v=-dx*Math.sin(a)+dz*Math.cos(a);
 return Math.abs(u)<f.w/2000+radius*.5&&Math.abs(v)<f.d/2000+radius*.5;
}
