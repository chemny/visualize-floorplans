// Runtime targets only: no apartment IDs, room names or absolute placement points.
export function componentContractTargets(state){
 const furniture=state.furniture||[],walls=state.walls||[];
 return {
  shower:furniture.filter(f=>f.type==='shower'&&f.showerDoor?.type==='hinged').map(f=>({id:f.id,rot:f.rot||0})),
  vanity:furniture.filter(f=>f.type==='vanity').map(f=>({id:f.id,rot:f.rot||0})),
  bathtub:furniture.filter(f=>f.type==='bathtub').map(f=>({id:f.id,rot:f.rot||0})),
  door:walls.flatMap(w=>(w.opens||[]).flatMap((o,index)=>o.kind==='door'&&!o.leafRemoved?[{wallId:w.id,index,id:o.id}]:[])),
 };
}
export function screenResizeDelta(matrix,kind,millimetres){
 if(!['width','depth'].includes(kind)||!Number.isFinite(millimetres)||millimetres<=0)throw Error('Invalid resize request');
 const values=['a','b','c','d'].map(k=>matrix[k]);if(!values.every(Number.isFinite)||Math.abs(matrix.a*matrix.d-matrix.b*matrix.c)<1e-12)throw Error('Invalid screen transform');
 return kind==='width'?{dx:matrix.a*millimetres,dy:matrix.b*millimetres}:{dx:matrix.c*millimetres,dy:matrix.d*millimetres};
}
