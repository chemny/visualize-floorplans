import {NEUTRAL_WET_PALETTE} from './room-style-policy.js';
export const WALL_DECOR_PROFILES=Object.freeze({
 modern_minimal:{finish:'paint',pattern:'plain',art:'minimal',frame:'frame',accentOnly:true},
 wood_cream:{finish:'wood',pattern:'oak_slat',art:'botanical',frame:'wood',accentOnly:true},
 midcentury_modern:{finish:'wood',pattern:'walnut_panel',art:'retro',frame:'wood',accentOnly:true},
 modern_chinese:{finish:'wood',pattern:'chinese_frame',art:'ink',frame:'wood',accentOnly:true},
 champagne_pearl:{finish:'paint',pattern:'champagne_frame',art:'pearl',frame:'metal',accentOnly:true},
 european_luxury:{finish:'french_panel',pattern:'classic_frame',art:'landscape',frame:'metal'},
 contemporary_french:{finish:'french_panel',pattern:'french_panel',art:'floral',frame:'metal'},
 italian_luxury:{finish:'paint',pattern:'italian_panel',art:'warm_abstract',frame:'frame',accentOnly:true},
 paris_art_deco:{finish:'paint',pattern:'artdeco_frame',art:'deco',frame:'metal',accentOnly:true},
 milan_greige:{finish:'paint',pattern:'plain',art:'minimal',frame:'frame',accentOnly:true}
});
export const WALL_DECOR_PATTERNS=new Set(['plain',...Object.values(WALL_DECOR_PROFILES).map(p=>p.pattern)]);
export const wallDecorProfile=id=>WALL_DECOR_PROFILES[id]||WALL_DECOR_PROFILES.modern_minimal;
export function decorRoomRole(room={},name=''){
 const semantic=room.function||room.role||room.usage;if(semantic){const role=({bathroom:'wet',kitchen:'wet',bedroom:'dry',primary:'dry',child:'dry',guest:'dry',living:'dry',dining:'dry',study:'dry',office:'dry',balcony:'service',closet:'service',hall:'service',entrance:'service'})[semantic];if(role)return role;}
 const text=[room.function,room.role,room.usage,name||room.name,room.id].filter(Boolean).join(' ').toLowerCase();
 if(/浴|卫|厨|bath|toilet|kitchen/.test(text))return 'wet';
 if(/阳台|衣帽|玄关|过道|走廊|balcony|closet|hall|corridor|entry|entrance/.test(text))return 'service';
 if(/卧|儿童|客厅|餐厅|客餐|书房|bed|primary|master|child|guest|living|dining|study|office/.test(text))return 'dry';
 return 'unknown';
}
const inside=(p,poly)=>{let hit=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])hit=!hit;}return hit;};
// Face ownership is interval-based. A long physical wall can border several rooms.
export function wallFaceSegments(w,side,rooms){
 const dx=w.b[0]-w.a[0],dy=w.b[1]-w.a[1],len=Math.hypot(dx,dy);if(len<1)return [];
 const u=[dx/len,dy/len],sign=side==='left'?1:-1,n=[-u[1]*sign,u[0]*sign],offset=w.t/2+20;
 const origin=[w.a[0]+n[0]*offset,w.a[1]+n[1]*offset],cuts=[0,len];
 const projected=p=>[(p[0]-origin[0])*u[0]+(p[1]-origin[1])*u[1],(p[0]-origin[0])*n[0]+(p[1]-origin[1])*n[1]];
 for(const room of rooms)for(let i=0;i<room.poly.length;i++){const a=projected(room.poly[i]),b=projected(room.poly[(i+1)%room.poly.length]);
  if(Math.abs(a[1])<1e-7)cuts.push(a[0]);if(Math.abs(b[1])<1e-7)cuts.push(b[0]);
  if(a[1]*b[1]<0)cuts.push(a[0]+(b[0]-a[0])*(-a[1])/(b[1]-a[1]));
 }
 const limits=cuts.filter(t=>t>=0&&t<=len).sort((a,b)=>a-b).filter((t,i,a)=>!i||t-a[i-1]>1e-5),out=[];
 for(let i=0;i<limits.length-1;i++){const start=limits[i],end=limits[i+1];if(end-start<1e-5)continue;
  const t=(start+end)/2,p=[origin[0]+u[0]*t,origin[1]+u[1]*t],room=rooms.find(r=>inside(p,r.poly))||null,last=out.at(-1);
  if(last&&last.roomId===(room?.id||null))last.end=end;else out.push({start,end,roomId:room?.id||null});
 }return out;
}
// Dominant room is retained only for legacy whole-face UI defaults, never rendering.
export function wallFaceRoom(w,side,rooms){const lengths=new Map();for(const s of wallFaceSegments(w,side,rooms))if(s.roomId)lengths.set(s.roomId,(lengths.get(s.roomId)||0)+s.end-s.start);const id=[...lengths].sort((a,b)=>b[1]-a[1])[0]?.[0];return rooms.find(r=>r.id===id)||null;}
export function wallFinishAt(finish,along){if(!finish)return null;const a=finish.segments;if(!a?.length)return finish;return a.find(s=>along>=s.start-1e-5&&along<=s.end+1e-5)||(along<a[0].start?a[0]:a.at(-1));}
export function roomWallFinish(room,name,style,{length=0,accent=false}={}){const role=room?decorRoomRole(room,name):'unknown',profile=wallDecorProfile(style.id),decorate=role==='dry'&&length>=900&&(!profile.accentOnly||accent),kind=role==='wet'?'tile':decorate?profile.finish:'paint',decorPattern=decorate?profile.pattern:'plain',color=role==='wet'?NEUTRAL_WET_PALETTE.wall:kind==='tile'?style.palette.tile:kind==='wood'?style.palette.wood:style.palette.wall;return {kind,color,decorPattern,decorStyleId:role==='wet'?'neutral_service':style.id,finishPolicy:role==='wet'?'independent_wet':'room_style'};}
function focalFace(w,side,furniture){
 const dx=w.b[0]-w.a[0],dy=w.b[1]-w.a[1],len=Math.hypot(dx,dy),sign=side==='left'?1:-1;
 return furniture.some(f=>{let x=f.cx,y=f.cy;if(f.type==='bed'){const a=f.rot*Math.PI/180;x+=Math.sin(a)*f.d/2;y-=Math.cos(a)*f.d/2;}else if(!['wallart','tv'].includes(f.type))return false;
 const along=((x-w.a[0])*dx+(y-w.a[1])*dy)/len,normal=(-(x-w.a[0])*dy+(y-w.a[1])*dx)/len;
 return along>0&&along<len&&normal*sign>0&&Math.abs(Math.abs(normal)-w.t/2)<220;
 });
}
export function synchronizeWallDecor(s,rooms,style){
 const profile=wallDecorProfile(style.id);s.wallFinishes??={};
 for(const w of s.walls||[]){if(w.demolished)continue;for(const side of ['left','right']){
  const old=s.wallFinishes[w.id]?.[side];if(old?.decorPattern&&!WALL_DECOR_PATTERNS.has(old.decorPattern))throw Error('墙面装饰样式无效');
  if(old?.styleMode==='fixed')continue;
  const parts=wallFaceSegments(w,side,rooms),owned=parts.filter(p=>p.roomId);if(!owned.length){if(old?.autoStyle){delete s.wallFinishes[w.id][side];if(!Object.keys(s.wallFinishes[w.id]).length)delete s.wallFinishes[w.id];}continue;}
  const {segments:ignored,...base}=old||{},len=Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]),accent=focalFace(w,side,s.furniture||[]);
  const segments=parts.map(part=>{const room=rooms.find(r=>r.id===part.roomId);return {...part,...roomWallFinish(room,s.rooms?.[room?.id]?.name,style,{length:part.end-part.start,accent})};});
  const dominant=segments.filter(p=>p.roomId).sort((a,b)=>(b.end-b.start)-(a.end-a.start))[0],{start,end,roomId,...header}=dominant;
  s.wallFinishes[w.id]??={};s.wallFinishes[w.id][side]={...base,...header,styleMode:'follow',autoStyle:true,segments};
 }}
 for(const f of s.furniture||[])if(['wallart','wallpanel'].includes(f.type)){
  f.decorStyleMode??='follow';if(!['follow','fixed'].includes(f.decorStyleMode))throw Error('装饰联动设置无效');
  if(f.decorStyleMode==='follow'||!f.decorStyleId)f.decorStyleId=style.id;
  if(!WALL_DECOR_PROFILES[f.decorStyleId])throw Error('装饰风格无效');
 }
 return s;
}
