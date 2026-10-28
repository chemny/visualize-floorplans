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
export function wallFaceRoom(w,side,rooms){
 const dx=w.b[0]-w.a[0],dy=w.b[1]-w.a[1],len=Math.hypot(dx,dy);if(len<1)return null;
 const sign=side==='left'?1:-1,offset=w.t/2+20;const counts=new Map();
 for(const t of [.18,.34,.5,.66,.82]){const p=[w.a[0]+dx*t-dy/len*offset*sign,w.a[1]+dy*t+dx/len*offset*sign];for(const room of rooms)if(inside(p,room.poly)){counts.set(room,(counts.get(room)||0)+1);break;}}
 return [...counts].sort((a,b)=>b[1]-a[1])[0]?.[0]||null;
}
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
  const room=wallFaceRoom(w,side,rooms);if(!room){if(old?.autoStyle){delete s.wallFinishes[w.id][side];if(!Object.keys(s.wallFinishes[w.id]).length)delete s.wallFinishes[w.id];}continue;}
  const role=decorRoomRole(room,s.rooms?.[room.id]?.name);const len=Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]);
  const accent=focalFace(w,side,s.furniture||[]),decorate=role==='dry'&&len>=900&&(!profile.accentOnly||accent);
  const kind=role==='wet'?'tile':decorate?profile.finish:'paint',pattern=decorate?profile.pattern:'plain';
  const color=kind==='tile'?style.palette.tile:kind==='wood'?style.palette.wood:style.palette.wall;
  s.wallFinishes[w.id]??={};s.wallFinishes[w.id][side]={...old,kind,color,styleMode:'follow',decorPattern:pattern,decorStyleId:style.id,autoStyle:true};
 }}
 for(const f of s.furniture||[])if(['wallart','wallpanel'].includes(f.type)){
  f.decorStyleMode??='follow';if(!['follow','fixed'].includes(f.decorStyleMode))throw Error('装饰联动设置无效');
  if(f.decorStyleMode==='follow'||!f.decorStyleId)f.decorStyleId=style.id;
  if(!WALL_DECOR_PROFILES[f.decorStyleId])throw Error('装饰风格无效');
 }
 return s;
}
