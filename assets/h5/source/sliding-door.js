// Millimetres, wall-start-relative coordinates. Shared by plan, mesh and clear-opening UI.
export function slidingDoorGeometry(wall,o={}){
 const dx=wall.b[0]-wall.a[0],dy=wall.b[1]-wall.a[1],length=Math.hypot(dx,dy);
 const L=o.width,n=o.leaves??2,open=o.slideOpen??0,dir=o.slideDirection??1;
 if(!length||!Number.isFinite(L)||L<n*300||![1,2,3].includes(n)||!Number.isFinite(open)||open<0||open>1||![1,-1].includes(dir))throw Error('推拉门扇数、净宽、方向或开启程度无效');
 if(n===1&&(o.slideMount!=='wall'||![1,-1].includes(o.slideSide??-1)||!Number.isFinite(o.slideOverlap??20)||(o.slideOverlap??20)<0||(o.slideOverlap??20)>100))throw Error('单扇侧滑门需要明确墙侧安装配置');
 const u=[dx/length,dy/length],normal=[-u[1],u[0]],pw=n===1?L+2*(o.slideOverlap??20):L/n+Math.min(30,L*.02),thickness=35;
 const panels=o.leafRemoved?[]:Array.from({length:n},(_,i)=>{
  const closed=-L/2+L*(i+.5)/n,target=dir*(L/2-pw/2),along=n===1?L/2+dir*pw*open:L/2+closed+(target-closed)*open,track=n===1?(o.slideSide??-1)*((wall.t||0)/2+thickness/2+12):(i-(n-1)/2)*35;
  const cx=wall.a[0]+u[0]*(o.at+along)+normal[0]*track,cy=wall.a[1]+u[1]*(o.at+along)+normal[1]*track;
  return {cx,cy,pw,thickness,along,track,v:Math.abs(u[1])>Math.abs(u[0]),w:Math.abs(u[0])*pw+Math.abs(normal[0])*thickness,d:Math.abs(u[1])*pw+Math.abs(normal[1])*thickness,interval:[Math.max(0,Math.min(L,along-pw/2)),Math.max(0,Math.min(L,along+pw/2))]};
 });
 const occupied=[];
 for(const [a,b] of panels.map(p=>p.interval).sort((a,b)=>a[0]-b[0])){if(b<=a)continue;const last=occupied.at(-1);if(last&&a<=last[1])last[1]=Math.max(b,last[1]);else occupied.push([a,b]);}
 const gaps=[];let end=0;for(const [a,b]of occupied){if(a>end)gaps.push([end,a]);end=Math.max(end,b);}if(end<L)gaps.push([end,L]);
 return {panels,occupied,gaps,netOpeningMm:Math.max(0,...gaps.map(([a,b])=>b-a)),totalClearMm:gaps.reduce((s,[a,b])=>s+b-a,0),apertureWidthMm:L};
}
export function slidingControls(w,o){
 if(o.kind!=='sliding'||o.leafRemoved)return '';
 const g=slidingDoorGeometry(w,o),horizontal=Math.abs(w.b[0]-w.a[0])>=Math.abs(w.b[1]-w.a[1]),positive=(horizontal?w.b[0]-w.a[0]:w.b[1]-w.a[1])>0,start=horizontal?(positive?'左':'右'):(positive?'上':'下'),end=horizontal?(positive?'右':'左'):(positive?'下':'上');
 return `<section data-sliding-controls><h3>推拉门</h3><div class="form"><label>扇数<select id="openingLeaves"><option value="1" ${o.leaves===1?'selected':''}>单扇侧滑</option><option value="2" ${(o.leaves??2)===2?'selected':''}>双扇</option><option value="3" ${o.leaves===3?'selected':''} ${o.width<900?'disabled':''}>三扇${o.width<900?'（洞宽不足）':''}</option></select></label><label>滑动方向<select id="openingSlideDirection"><option value="-1" ${o.slideDirection===-1?'selected':''}>向${start}侧收扇</option><option value="1" ${o.slideDirection!==-1?'selected':''}>向${end}侧收扇</option></select></label><label class="full">开启程度 <output id="openingSlidePercent">${Math.round((o.slideOpen??0)*100)}%</output><input id="openingSlideOpen" type="range" min="0" max="100" step="1" value="${Math.round((o.slideOpen??0)*100)}"></label></div><p data-sliding-net-opening>净开口 <strong>${Math.round(g.netOpeningMm)} mm</strong> · 洞宽 ${Math.round(o.width)} mm</p>${o.leaves===1?'<p class="scene-mode-note">侧墙需预留收门空间</p>':''}</section>`;
}
