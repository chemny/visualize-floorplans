import * as T from 'three';import {showerDoorGeometry} from './shower-door.js';
export function operableShower(f,p){
 const geo=showerDoorGeometry(f),g=new T.Group(),w=f.w/1000,d=f.d/1000,h=f.h/1000;
 const metal=new T.MeshStandardMaterial({color:p.metal||'#a89479',roughness:.35,metalness:.65}),glass=new T.MeshPhysicalMaterial({color:p.glass||'#c8d5cd',transparent:true,opacity:.16,roughness:.12,depthWrite:false}),tray=new T.MeshStandardMaterial({color:'#eeeae2',roughness:.35});
 function box(parent,name,x,y,z,px,py,pz,m){const o=new T.Mesh(new T.BoxGeometry(x,y,z),m);o.name=name;o.position.set(px,py,pz);parent.add(o);return o;}
 box(g,'shower-tray',w,.03,d,0,.015,0,tray);
 box(g,'shower-back-glass',w-.01,h-.04,.01,0,h/2,-d/2+.005,glass);
 for(const x of [-w/2+.005,w/2-.005]){box(g,'shower-side-glass',.01,h-.04,d-.01,x,h/2,0,glass);box(g,'shower-front-post',.014,h,.02,x,h/2,d/2,metal);}
 box(g,'shower-head-rail',w,.015,.02,0,h-.0075,d/2,metal);
 box(g,'shower-rail',.022,h*.7,.022,w*.3,h*.6,-d*.36,metal);box(g,'shower-head',.18,.018,.15,w*.3,h*.94,-d*.23,metal);
 box(g,'shower-drain',.15,.002,.075,w*.28,.031,-d*.3,metal);
 for(const [a,b]of geo.fixedPanels){box(g,'shower-front-fixed-glass',Math.abs(b[0]-a[0])/1000,h-.04,.01,(a[0]+b[0])/2000,h/2,d/2,glass);box(g,'shower-door-jamb',.014,h,.02,a[0]/1000,h/2,d/2,metal);}
 const pivot=new T.Group();pivot.name='shower-door-pivot';pivot.position.set(geo.hinge[0]/1000,0,geo.hinge[1]/1000);pivot.rotation.y=geo.rotationY;pivot.userData.showerDoor=f.id;g.add(pivot);
 box(pivot,'shower-operable-leaf',geo.length/1000,h-.05,.01,geo.sign*geo.length/2000,h/2,0,glass);
 box(pivot,'shower-door-pull',.014,.22,.018,geo.sign*(geo.length-65)/1000,1,geo.sign*.032,metal);
 g.userData.showerDoorMechanism='hinged';return g;
}
export function showerPlan(f){const g=showerDoorGeometry(f),w=f.w,d=f.d;return `<g data-shower-door="${f.id}" data-open="${f.showerDoor.open}"><rect x="${-w/2}" y="${-d/2}" width="${w}" height="${d}" fill="${f.color}" fill-opacity=".3"/><path d="M${-w/2} ${d/2}V${-d/2}H${w/2}V${d/2}" fill="none" stroke="#837868" stroke-width="2" vector-effect="non-scaling-stroke"/>${g.fixedPanels.map(([a,b])=>`<path data-shower-fixed="${f.id}" d="M${a}L${b}" fill="none" stroke="#837868" stroke-width="2" vector-effect="non-scaling-stroke"/>`).join('')}<path data-shower-leaf="${f.id}" d="M${g.hinge}L${g.tip}" fill="none" stroke="#a47e50" stroke-width="3" vector-effect="non-scaling-stroke"/></g>`;}
