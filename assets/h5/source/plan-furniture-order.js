// Top-down symbols use surface height, not array insertion order. A chair seat
// under a tabletop is covered by it; its back outside the table stays visible.
export function planSurfaceHeight(f){
 const elevation=Number.isFinite(f.elevation)?f.elevation:0;
 const height=Number.isFinite(f.h)?Math.max(0,f.h):0;
 if(['chair','officechair','barstool'].includes(f.type)){
  const seat=f.type==='barstool'?height*.7:Math.min(460,height*.54);
  return elevation+seat+32.5;
 }
 return elevation+height;
}

export function planFurnitureOrder(furniture){
 return furniture.map((f,index)=>({f,index,height:planSurfaceHeight(f)}))
  .sort((a,b)=>a.height-b.height||a.index-b.index).map(row=>row.f);
}
