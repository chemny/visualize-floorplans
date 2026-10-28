import {wallPrisms} from './walls.js';
const inside=([x,y],poly)=>{let hit=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const[a,b]=poly[i],[c,d]=poly[j];if((b>y)!==(d>y)&&x<(c-a)*(y-b)/(d-b)+a)hit=!hit;}return hit;};
// Union boundaries include the short returns at outside corners and door jambs.
// Unlike independent wall centre lines, no hidden internal face gets trim.
export function skirtingRuns(walls,rooms,furniture=[],roomState={},floorConnections=[]){
 const rects=wallPrisms(walls).filter(r=>r.z0<.01&&r.z1>=80);
 if(!rects.length)return [];
 const xs=[...new Set(rects.flatMap(r=>[r.x0,r.x1]))].sort((a,b)=>a-b),ys=[...new Set(rects.flatMap(r=>[r.y0,r.y1]))].sort((a,b)=>a-b),nx=xs.length-1,ny=ys.length-1,grid=new Uint8Array(nx*ny),xi=new Map(xs.map((v,i)=>[v,i])),yi=new Map(ys.map((v,i)=>[v,i]));
 for(const r of rects)for(let y=yi.get(r.y0);y<yi.get(r.y1);y++)for(let x=xi.get(r.x0);x<xi.get(r.x1);x++)grid[y*nx+x]=1;
 const filled=(x,y)=>x>=0&&y>=0&&x<nx&&y<ny&&grid[y*nx+x],groups=new Map();
 const edge=(axis,line,a,b,sign)=>{const k=[axis,line,sign].join(':');if(!groups.has(k))groups.set(k,{axis,line,sign,spans:[]});groups.get(k).spans.push([a,b]);};
 for(let y=0;y<ny;y++)for(let x=0;x<nx;x++){if(!filled(x,y))continue;
 if(!filled(x,y-1))edge(0,ys[y],xs[x],xs[x+1],-1);
 if(!filled(x,y+1))edge(0,ys[y+1],xs[x],xs[x+1],1);
 if(!filled(x-1,y))edge(1,xs[x],ys[y],ys[y+1],-1);
 if(!filled(x+1,y))edge(1,xs[x+1],ys[y],ys[y+1],1);
 }
 const finishRegions=floorConnections.filter(f=>rooms.some(r=>r.id===f.materialRoomId)).map(f=>({id:f.materialRoomId,poly:f.poly}));
 const result=[],thickness=30;
 for(const {axis,line,sign,spans}of groups.values()){
 spans.sort((a,b)=>a[0]-b[0]);const merged=[];for(const s of spans){const tail=merged.at(-1);if(tail&&s[0]<=tail[1]+.01)tail[1]=Math.max(tail[1],s[1]);else merged.push([...s]);}
 const point=(t,offset)=>axis===0?[t,line+sign*offset]:[line+sign*offset,t];
 for(const [start,end]of merged){
 // Split at room boundaries: a long wall can border multiple rooms.
 const cuts=[start,end];for(const r of [...rooms,...finishRegions])for(let i=0;i<r.poly.length;i++){
 const a=r.poly[i],b=r.poly[(i+1)%r.poly.length],normal=1-axis,probe=line+sign*15;
 if(Math.abs(b[normal]-a[normal])<1e-8)continue;
 const u=(probe-a[normal])/(b[normal]-a[normal]);if(u<0||u>1)continue;
 const t=a[axis]+u*(b[axis]-a[axis]);if(t>start+.01&&t<end-.01)cuts.push(t);
 }
 cuts.sort((a,b)=>a-b);
 for(let i=0;i<cuts.length-1;i++){
 const a=cuts[i],b=cuts[i+1];if(b-a<.5)continue;
 const room=rooms.find(r=>inside(point((a+b)/2,15),r.poly))||finishRegions.find(r=>inside(point((a+b)/2,15),r.poly));if(!room||roomState[room.id]?.skirting===false)continue;
 let visible=[[a,b]];
 for(const f of furniture){if(!(f.builtIn&&f.fixedToWalls))continue;
 const rad=(f.rot||0)*Math.PI/180,c=Math.cos(rad),s=Math.sin(rad),q=point(0,15),dx=q[0]-f.cx,dy=q[1]-f.cy;
 const origin=[dx*c+dy*s,-dx*s+dy*c],direction=axis===0?[c,-s]:[s,c],half=[f.w/2+15,f.d/2+15];let lo=-Infinity,hi=Infinity;
 for(let k=0;k<2;k++){if(Math.abs(direction[k])<1e-9){if(Math.abs(origin[k])>half[k]){lo=1;hi=0;break;}}else{const t0=(-half[k]-origin[k])/direction[k],t1=(half[k]-origin[k])/direction[k];lo=Math.max(lo,Math.min(t0,t1));hi=Math.min(hi,Math.max(t0,t1));}}
 if(hi>lo)visible=visible.flatMap(([x,y])=>hi<=x||lo>=y?[[x,y]]:[[x,Math.min(y,lo)],[Math.max(x,hi),y]].filter(([u,v])=>v-u>.5));
 }
 for(const [x,y]of visible){
 // Half-thickness extension overlaps the perpendicular return at a real corner.
 // Room divisions and cabinet cut-outs do not receive this extension.
 const left=Math.abs(x-start)<.01?15:0,right=Math.abs(y-end)<.01?15:0;
 const center=point((x-left+y+right)/2,15),back=point((x+y)/2,-.1),wall=rects.find(r=>back[0]>=r.x0-.01&&back[0]<=r.x1+.01&&back[1]>=r.y0-.01&&back[1]<=r.y1+.01);
 result.push({cx:center[0],cy:center[1],w:y-x+left+right,d:thickness,h:80,rot:axis===0?0:90,roomId:room.id,wallId:wall?.wall,key:[axis,line,sign,x,y].join(':'),axis,line,sign,start:x,end:y});
 }
 }
 }
 }
 return result;
}
