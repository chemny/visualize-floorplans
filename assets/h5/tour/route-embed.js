import{sample,framePath}from './tour-map.js';
const data=await fetch('route-data.json',{cache:'no-store'}).then(r=>r.json()),svg=document.querySelector('.sync-map');
for(const p of svg.querySelectorAll('[data-line="full"]'))p.setAttribute('d',framePath(data.frames));
let at=0;function setTime(seconds){at=Math.max(0,Math.min((data.frames.length-1)/data.fps,seconds));const s=sample(data,at);for(const key of ['done','cone','axis'])svg.querySelector('[data-line="'+key+'"]').setAttribute('d',s[key]);svg.querySelector('[data-mark="camera"]').setAttribute('transform',`translate(${s.point}) rotate(${s.yaw*180/Math.PI})`);svg.querySelector('[data-mark="start"]').setAttribute('cx',data.frames[0].p[0]);svg.querySelector('[data-mark="start"]').setAttribute('cy',data.frames[0].p[1]);svg.dataset.frame=s.index;svg.dataset.point=s.point.join(',');}
window.rehearsalPlayback={setTime,getTime:()=>at};setTime(0);
