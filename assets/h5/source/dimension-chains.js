// Presentation dimensions retain exact anchors; only displayed millimetres are rounded.
export function wallDimensionSegments(w){
 const len=Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]);if(w.demolished||len<1)return [];
 const cuts=[0,len];for(const o of w.opens||[]){if(o.at>=0&&o.at+o.width<=len+.01)cuts.push(o.at,o.at+o.width);}
 const pts=[...new Set(cuts)].sort((a,b)=>a-b);return pts.slice(0,-1).map((a,i)=>({start:a,end:pts[i+1],length:pts[i+1]-a,label:Math.round(pts[i+1]-a)})).filter(v=>v.length>1);
}
