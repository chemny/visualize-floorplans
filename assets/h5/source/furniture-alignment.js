// Coordinates and extents are millimetres; alignment respects rotated footprints.
export function bounds(f){const a=(f.rot||0)*Math.PI/180,c=Math.abs(Math.cos(a)),s=Math.abs(Math.sin(a)),hx=(f.w*c+f.d*s)/2,hy=(f.w*s+f.d*c)/2;return {left:f.cx-hx,right:f.cx+hx,top:f.cy-hy,bottom:f.cy+hy,cx:f.cx,cy:f.cy};}
export function alignPlan(items,mode){
 const out=items.map(f=>({...f}));if(out.length<2)return out;
 const axis=mode.endsWith('X')?'x':'y',key={left:'left',right:'right',top:'top',bottom:'bottom',centerX:'cx',centerY:'cy'}[mode];
 if(key){const target=bounds(out[0])[key];for(const f of out)f[['left','right','cx'].includes(key)?'cx':'cy']+=target-bounds(f)[key];return out;}
 if(out.length<3)throw Error('等距排列至少选择三件物件');
 const lo=axis==='x'?'left':'top',hi=axis==='x'?'right':'bottom',center=axis==='x'?'cx':'cy';out.sort((a,b)=>bounds(a)[lo]-bounds(b)[lo]);
 const first=bounds(out[0]),last=bounds(out.at(-1)),total=out.reduce((n,f)=>n+bounds(f)[hi]-bounds(f)[lo],0),gap=(last[hi]-first[lo]-total)/(out.length-1);
 if(gap<0)throw Error('空间不足，无法等距排列');let edge=first[hi]+gap;
 for(let i=1;i<out.length-1;i++){const b=bounds(out[i]);out[i][center]+=edge-b[lo];edge+=b[hi]-b[lo]+gap;}return out;
}
export function snapFurniture(f,peers,tolerance){const b=bounds(f),guides=[];let dx=0,dy=0;
 for(const [axis,keys]of [['x',['left','cx','right']],['y',['top','cy','bottom']]]){let best=tolerance,hit=null;
 for(const peer of peers){const p=bounds(peer);for(const key of keys){const delta=p[key]-b[key];if(Math.abs(delta)<best){best=Math.abs(delta);hit={axis,value:p[key],from:b,to:p};if(axis==='x')dx=delta;else dy=delta;}}}if(hit)guides.push(hit);}
 return {cx:f.cx+dx,cy:f.cy+dy,guides};}
// SAT overlap depth avoids false collisions from rotated bounding boxes.
export function overlapDepth(a,b){const axes=[a,b].flatMap(f=>{const r=(f.rot||0)*Math.PI/180;return [[Math.cos(r),Math.sin(r)],[-Math.sin(r),Math.cos(r)]];});let depth=Infinity;
 for(const [x,y]of axes){const radius=f=>{const r=(f.rot||0)*Math.PI/180;return Math.abs(x*Math.cos(r)+y*Math.sin(r))*f.w/2+Math.abs(-x*Math.sin(r)+y*Math.cos(r))*f.d/2;};const d=radius(a)+radius(b)-Math.abs((a.cx-b.cx)*x+(a.cy-b.cy)*y);if(d<=0)return 0;depth=Math.min(depth,d);}return depth;}
