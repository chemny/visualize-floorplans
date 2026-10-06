export function sceneLabelPoint(r,furnitureState,inPolygon){
 const xs=r.poly.map(p=>p[0]),ys=r.poly.map(p=>p[1]),span=Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys));
 const step=Math.max(200,span/16),candidates=[r.at],furniture=furnitureState.filter(f=>(f.elevation||0)<1300&&!['rug','downlight','socketplate','transition'].includes(f.type));
 for(let y=Math.min(...ys)+180;y<Math.max(...ys)-120;y+=step)for(let x=Math.min(...xs)+180;x<Math.max(...xs)-120;x+=step)candidates.push([x,y]);
 function score(p){if(!inPolygon(p,r.poly))return Infinity;let value=Math.hypot(p[0]-r.at[0],p[1]-r.at[1])/span;for(const [dx,dy]of [[180,0],[-180,0],[0,180],[0,-180]])if(!inPolygon([p[0]+dx,p[1]+dy],r.poly))value+=3;
  for(const f of furniture){const a=f.rot*Math.PI/180,dx=p[0]-f.cx,dy=p[1]-f.cy,u=dx*Math.cos(a)+dy*Math.sin(a),v=-dx*Math.sin(a)+dy*Math.cos(a);if(Math.abs(u)<f.w/2+120&&Math.abs(v)<f.d/2+120)value+=5;}
  return value;
 }
 return candidates.map(point=>({point,score:score(point)})).sort((a,b)=>a.score-b.score)[0].point;
}
