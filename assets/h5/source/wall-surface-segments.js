// Split existing vertical surface triangles only; no structural wall/opening changes.
const lerp=(a,b,t)=>a.map((v,i)=>v+(b[i]-v)*t);
function clip(poly,value,cut,lower){const out=[];for(let i=0;i<poly.length;i++){
 const a=poly[i],b=poly[(i+1)%poly.length],da=value(a)-cut,db=value(b)-cut,ia=lower?da<=1e-7:da>=-1e-7,ib=lower?db<=1e-7:db>=-1e-7;
 if(ia)out.push(a);if(ia!==ib)out.push(lerp(a,b,da/(da-db)));
 }return out.filter((v,i,a)=>!i||Math.hypot(...v.map((x,k)=>x-a[i-1][k]))>1e-6);
}
export function wallTrianglePieces(triangle,wall,segments){
 if(!segments?.length)return [triangle];const dx=wall.b[0]-wall.a[0],dy=wall.b[1]-wall.a[1],len=Math.hypot(dx,dy),value=p=>((p[0]-wall.a[0])*dx+(p[2]-wall.a[1])*dy)/len;
 const cuts=[...new Set(segments.flatMap(s=>[s.start,s.end]))].sort((a,b)=>a-b);let polys=[triangle];
 for(const cut of cuts){const next=[];for(const poly of polys){const values=poly.map(value);if(Math.min(...values)<cut-1e-6&&Math.max(...values)>cut+1e-6){next.push(clip(poly,value,cut,true),clip(poly,value,cut,false));}else next.push(poly);}polys=next;}
 return polys.flatMap(poly=>{const out=[];for(let i=1;i<poly.length-1;i++){const a=poly[0],b=poly[i],c=poly[i+1],u=b.map((v,k)=>v-a[k]),v=c.map((x,k)=>x-a[k]),cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];if(Math.hypot(...cross)>1e-5)out.push([a,b,c]);}return out;});
}
