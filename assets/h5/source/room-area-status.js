// Room polygons remain source authority until a new partition is confirmed.
const geometry=w=>({a:w.a,b:w.b,t:w.t,demolished:!!w.demolished});
export function roomAreaStatus(original,current){
 const before=new Map(original.map(w=>[w.id,JSON.stringify(geometry(w))]));
 const after=new Map(current.map(w=>[w.id,JSON.stringify(geometry(w))]));
 const changedIds=[...new Set([...before.keys(),...after.keys()])].filter(id=>before.get(id)!==after.get(id));
 return {status:changedIds.length?'pending-repartition':'source-partitions',changedWallIds:changedIds,areaBasis:'confirmed room polygons',message:changedIds.length?'墙体已变化 · 房间分区、地面与面积待重新确认；当前数值为原分区参考。':''};
}
