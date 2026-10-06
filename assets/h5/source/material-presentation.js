// Per-case presentation, independent from the shared palette and geometry.
export function marbleHasVeins(presentation){return presentation?.materials?.marble?.veins!==false;}
export function marbleVeinSVG(presentation,stroke){return marbleHasVeins(presentation)?`<path d="M-50 300C250 260 380 520 700 470S1100 640 1260 600M200 1200C300 950 520 980 640 820" stroke="${stroke}" stroke-width="12" fill="none"/>`:'';}
export function paintMarbleVeins(g,W,H,R,presentation){if(!marbleHasVeins(presentation))return;g.strokeStyle='rgba(160,150,135,.35)';for(let k=0;k<6;k++){g.lineWidth=1+R()*3;g.beginPath();g.moveTo(R()*W,0);g.bezierCurveTo(R()*W,R()*H,R()*W,R()*H,R()*W,H);g.stroke();}}
