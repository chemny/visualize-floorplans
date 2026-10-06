// Closed horizontal contours from triangle surfaces, including separate solids
// and nested holes. Open meshes are clipped but never given invented solid caps.
export function horizontalContours(triangles,height,eps=1e-5){
 const nodes=new Map(),edges=new Map(),key=p=>`${Math.round(p[0]/eps)},${Math.round(p[1]/eps)}`;
 for(const tri of triangles){const pts=[];for(let i=0;i<3;i++){const a=tri[i],b=tri[(i+1)%3],da=a[1]-height,db=b[1]-height;
  if(Math.abs(da)<eps)pts.push([a[0],a[2]]);
  if((da>eps&&db<-eps)||(da<-eps&&db>eps)){const t=da/(da-db);pts.push([a[0]+t*(b[0]-a[0]),a[2]+t*(b[2]-a[2])]);}}
  const unique=[...new Map(pts.map(p=>[key(p),p])).values()];if(unique.length!==2)continue;
  const [a,b]=unique.map(key);if(a===b)continue;const id=[a,b].sort().join('|');if(edges.has(id))continue;edges.set(id,[a,b]);unique.forEach(p=>{const k=key(p);if(!nodes.has(k))nodes.set(k,{p,next:[]});});nodes.get(a).next.push(b);nodes.get(b).next.push(a);
 }
 const visited=new Set(),loops=[];
 for(const [start,node]of nodes){if(visited.has(start)||node.next.length!==2)continue;let prev=null,cur=start,closed=false;const loop=[];
  for(let i=0;i<=nodes.size;i++){if(visited.has(cur)){closed=cur===start;break;}const n=nodes.get(cur);if(n.next.length!==2)break;visited.add(cur);loop.push(n.p);const next=n.next.find(x=>x!==prev);prev=cur;cur=next;}
  if(closed&&loop.length>=3)loops.push(loop);
 }
 return loops;
}
export function contourRegions(loops){
 const area=p=>Math.abs(p.reduce((s,a,i)=>{const b=p[(i+1)%p.length];return s+a[0]*b[1]-b[0]*a[1]},0)/2);
 const contains=(p,poly)=>{let inside=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])inside=!inside;}return inside;};
 const rows=loops.map(poly=>({poly,area:area(poly),parent:null,depth:0})).filter(r=>r.area>1e-10).sort((a,b)=>b.area-a.area);
 for(let i=0;i<rows.length;i++){const r=rows[i];for(let j=i-1;j>=0;j--)if(contains(r.poly[0],rows[j].poly)){r.parent=rows[j];r.depth=r.parent.depth+1;break;}}
 return rows.filter(r=>r.depth%2===0).map(r=>({outer:r.poly,holes:rows.filter(h=>h.parent===r&&h.depth%2===1).map(h=>h.poly)}));
}
