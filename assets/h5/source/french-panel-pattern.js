// Accepted French finish compatibility; surface only.
export function paintFrenchPanels(g,size){
 g.fillStyle='#ffffff';g.fillRect(0,0,size,size);
 const line=(x,y,w,h)=>{g.strokeStyle='#d4cbbb';g.lineWidth=2.6;g.strokeRect(x,y,w,h);g.strokeStyle='#ffffff';g.lineWidth=1.4;g.strokeRect(x+3,y+3,w-6,h-6);};
 // One full-height paint/moulding repeat; represented as surface relief.
 line(46,64,420,275);line(46,379,420,91);
 g.fillStyle='#dfd8cc';g.fillRect(0,356,size,3);g.fillStyle='#fff';g.fillRect(0,359,size,3);
 for(const y of [14,21,489,496]){g.fillStyle='#e1dacd';g.fillRect(0,y,size,2);}
}
