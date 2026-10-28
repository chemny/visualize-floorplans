// Tolerate microsecond-truncated media timestamps at exact frame boundaries.
// Shared final-frame timebase and wall-clipped planar map. No apartment constants.
export function frameAt(seconds,fps,length){return Math.max(0,Math.min(length-1,Math.floor((Number.isFinite(seconds)?seconds:0)*fps+1e-4)))}
export function path(points){return points.length?'M'+points.map(p=>p.join(',')).join(' L'):''}
export function stamp(t){return Math.floor(t/60)+':'+String(Math.floor(t%60)).padStart(2,'0')}
export function ray(p,angle,walls){const dx=Math.cos(angle),dy=Math.sin(angle);let best=7000;for(const[s,e,r]of walls){const lo=[Math.min(s[0],e[0])-r,Math.min(s[1],e[1])-r],hi=[Math.max(s[0],e[0])+r,Math.max(s[1],e[1])+r];let near=0,far=best;for(let j=0;j<2;j++){const v=j?dy:dx;if(Math.abs(v)<1e-8){if(p[j]<lo[j]||p[j]>hi[j]){far=-1;break}}else{const a=(lo[j]-p[j])/v,b=(hi[j]-p[j])/v;near=Math.max(near,Math.min(a,b));far=Math.min(far,Math.max(a,b))}}if(far>=near&&near>1)best=Math.min(best,near)}return[p[0]+dx*best,p[1]+dy*best]}
export function sample(data,seconds){const index=frameAt(seconds,data.fps,data.frames.length),f=data.frames[index],points=[f.p];for(let j=0;j<=36;j++)points.push(ray(f.p,f.yaw+(j/36-.5)*f.fov*Math.PI/180,data.walls));return{index,point:f.p,yaw:f.yaw,done:framePath(data.frames.slice(0,index+1)),cone:path(points)+' Z',axis:path([f.p,ray(f.p,f.yaw,data.walls)])}}

// Seek inside the requested frame, not infinitesimally before its encoded PTS.
export function seekTime(seconds,fps,length){return (frameAt(seconds,fps,length)+.5)/fps}

export function framePath(frames){return frames.map((f,i)=>(!i||f.cutBefore?'M':'L')+f.p.join(',')).join(' ')}
