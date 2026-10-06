// Plan dimensions are mm; the walk capsule stands on the room floor.
// A hanging cabinet is clear only if its full vertical span is above the head.
export function furnitureBlocksPoint(f,x,z,{originX=0,originY=0,radius=.18,eyeHeight=1.6,heightMm=750,ignoredTypes=[]}={}){
 if(ignoredTypes.includes(f.type)||f.type==='rug')return false;
 const bottom=(f.elevation||0)/1000,top=bottom+(f.h??heightMm)/1000;
 if(top<=.05||bottom>=eyeHeight+.15)return false;
 const dx=x-(f.cx-originX)/1000,dz=z-(f.cy-originY)/1000,a=(f.rot||0)*Math.PI/180;
 const u=dx*Math.cos(a)+dz*Math.sin(a),v=-dx*Math.sin(a)+dz*Math.cos(a);
 return Math.abs(u)<f.w/2000+radius*.5&&Math.abs(v)<f.d/2000+radius*.5;
}
