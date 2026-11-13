// Style is a bounded furniture body, independent of placement, colour and operation.
import * as T from 'three';
import {rigid,soft,pillow,addMesh} from './soft-furniture-v10.js';
export const FURNITURE_STYLE_TYPES=new Set(['sofa','sofabed','armchair','chair','barstool','tvstand','nightstand','wardrobe','table','desk','dresser','bed']);
export const FURNITURE_STYLES=Object.freeze({
 modern_minimal:{family:'linear',round:.012,legs:'metal',leg:.07,arm:.11,back:.92,panel:false},
 wood_cream:{family:'soft',round:.055,legs:'wood',leg:.09,arm:.14,back:.95,panel:false},
 midcentury_modern:{family:'timber',round:.025,legs:'splay',leg:.16,arm:.075,back:.88,panel:false},
 modern_chinese:{family:'lattice',round:.009,legs:'straight',leg:.14,arm:.07,back:1,panel:true},
 champagne_pearl:{family:'tailored',round:.035,legs:'metal',leg:.10,arm:.10,back:.96,panel:true},
 european_luxury:{family:'classic',round:.04,legs:'curve',leg:.14,arm:.15,back:1,panel:true},
 contemporary_french:{family:'french',round:.03,legs:'curve',leg:.13,arm:.12,back:1,panel:true},
 italian_luxury:{family:'low',round:.04,legs:'metal',leg:.055,arm:.17,back:.85,panel:false},
 paris_art_deco:{family:'deco',round:.022,legs:'metal',leg:.11,arm:.12,back:1,panel:true},
 milan_greige:{family:'linear',round:.018,legs:'metal',leg:.08,arm:.105,back:.94,panel:false}
});
export function furnitureStyleId(f){return f.furnitureStyleMode==='fixed'?f.furnitureStyleId:f.finishSpec?.id;}
export function furnitureStyleEligible(f){return FURNITURE_STYLE_TYPES.has(f?.type)&&!!FURNITURE_STYLES[furnitureStyleId(f)];}
export function ensureFurnitureStyle(f,id){
 if(!FURNITURE_STYLE_TYPES.has(f.type))return;
 if(f.furnitureStyleMode!==undefined&&!['follow','fixed'].includes(f.furnitureStyleMode))throw Error('家具款式联动无效');
 f.furnitureStyleMode??='follow';
 if(f.furnitureStyleMode==='fixed'&&!FURNITURE_STYLES[f.furnitureStyleId])throw Error('固定家具款式无效');
 if(f.furnitureStyleMode==='follow')f.furnitureStyleId=id;
 if(!FURNITURE_STYLES[f.furnitureStyleId])throw Error('家具风格无效');
 f.furnitureStyleRevision=1;
}
function tube(g,points,r,m,name){const c=new T.CatmullRomCurve3(points.map(p=>new T.Vector3(...p)));return addMesh(g,new T.TubeGeometry(c,16,r,6,false),m,name);}
function rod(g,a,b,r,m,name){const A=new T.Vector3(...a),B=new T.Vector3(...b),o=addMesh(g,new T.CylinderGeometry(r*.75,r,A.distanceTo(B),8),m,name);o.position.copy(A).add(B).multiplyScalar(.5);o.quaternion.setFromUnitVectors(new T.Vector3(0,1,0),B.sub(A).normalize());return o;}
function legs(g,w,d,h,p,m,prefix){for(const x of [-1,1])for(const z of [-1,1]){
 const xx=x*(w/2-.045),zz=z*(d/2-.045),material=p.legs==='metal'?m.metal:m.wood;
 if(p.legs==='curve')tube(g,[[xx,h,zz],[xx+x*.012,h*.7,zz+z*.01],[xx-x*.024,h*.25,zz-z*.012],[xx,0,zz]],.016,material,prefix+'-curved-leg');
 else rod(g,[xx,0,zz],[xx*(p.legs==='splay'?.86:1),h,zz*(p.legs==='splay'?.86:1)],p.legs==='metal'?.010:.019,material,prefix+'-'+p.legs+'-leg');
}}
function crest(g,w,h,bottom,z,p,m,name){const classic=['french','classic'].includes(p.family),shape=new T.Shape(),x=w/2;
 shape.moveTo(-x,bottom);shape.lineTo(x,bottom);shape.lineTo(x,h*.87);
 if(classic){shape.bezierCurveTo(x,h*.99,x*.65,h*.92,x*.4,h*.94);shape.quadraticCurveTo(0,h*1.06,-x*.4,h*.94);shape.bezierCurveTo(-x*.65,h*.92,-x,h*.99,-x,h*.87);}
 else if(p.family==='deco'){shape.lineTo(x*.70,h*.91);shape.lineTo(x*.70,h);shape.lineTo(-x*.70,h);shape.lineTo(-x*.70,h*.91);shape.lineTo(-x,h*.87);}
 else{shape.lineTo(x,h);shape.lineTo(-x,h);}
 shape.closePath();const geo=new T.ExtrudeGeometry(shape,{depth:.028,bevelEnabled:true,bevelThickness:.004,bevelSize:.004,bevelSegments:2,curveSegments:10});return addMesh(g,geo,m,name,[0,0,z]);}
function panels(g,w,h,y,z,p,m,prefix){
 const n=Math.max(1,Math.round(w/.6)),pw=(w-.04)/n;
 for(let i=0;i<n;i++){const x=-w/2+.02+(i+.5)*pw;rigid(g,pw-.008,h,.018,[x,y,z],m.body,prefix+'-door',.002);
 if(p.panel){for(const sign of [-1,1]){rigid(g,pw-.07,.012,.010,[x,y+sign*(h/2-.03),z+.012],p.family==='deco'?m.metal:m.wood,prefix+'-panel-rail',.002);rigid(g,.012,h-.06,.010,[x+sign*(pw/2-.035),y,z+.012],p.family==='deco'?m.metal:m.wood,prefix+'-panel-stile',.002);}}
 if(p.family==='lattice')for(let k=-1;k<=1;k++)rigid(g,.012,h*.72,.010,[x+k*pw*.18,y,z+.015],m.wood,prefix+'-lattice',.001);
 if(p.family==='timber')for(let k=-2;k<=2;k++)rigid(g,.009,h*.84,.009,[x+k*pw*.13,y,z+.014],m.wood,prefix+'-flute',.001);
 if(p.panel||p.family==='timber')addMesh(g,new T.SphereGeometry(.009,8,6),m.metal,prefix+'-pull',[x+pw*.3,y,z+.026]);
 }
}
export function styleFurnitureBody(f,m){
 if(f.finishSpec?.id==='neutral_service'||!furnitureStyleEligible(f))return null;
 const id=furnitureStyleId(f),p=FURNITURE_STYLES[id],g=new T.Group(),w=f.w/1000,d=f.d/1000,h=f.h/1000,classic=['french','classic'].includes(p.family),frame=p.family==='classic'?m.metal:m.wood;
 g.userData.furnitureStyleId=id;g.userData.styleFamily=p.family;
 if(['sofa','sofabed','armchair'].includes(f.type)){
  const lh=Math.min(.14,h*p.leg),baseH=h*.18,seat=h*.44,armW=Math.min(w*.14,p.arm),backZ=-d/2+.055;
  legs(g,w-.035,d-.04,lh,p,m,'sofa');soft(g,w-.015,baseH,d-.03,[0,lh+baseH/2,0],m.fabric,'styled-sofa-base',{radius:p.round});
  if(classic||p.family==='deco'){crest(g,w-.035,h-.008,seat-.03,backZ,p,frame,'sofa-shaped-wood-back');crest(g,w-.11,h-.045,seat,backZ+.033,p,m.fabric,'sofa-shaped-upholstery');}
  else soft(g,w-.03,h*p.back-lh,.10,[0,(h*p.back+lh)/2,backZ+.035],m.fabric,'sofa-'+p.family+'-back',{radius:p.round});
  const count=w>2.2?3:w>1.1?2:1,cw=(w-2*armW-.025)/count;
  for(let i=0;i<count;i++){const x=-(w-2*armW-.025)/2+(i+.5)*cw;soft(g,cw-.012,h*.13,d-.17,[x,seat-.045,.025],m.fabric,'styled-sofa-seat',{radius:p.round});
   if(!classic)soft(g,cw-.02,h*.33,.13,[x,seat+h*.17,backZ+.10],i%2?m.fabric:m.fabric,'styled-sofa-back-cushion',{radius:p.round});}
  for(const sign of [-1,1]){const x=sign*(w/2-armW/2-.008),armTop=h*(p.family==='low'?.60:.73);
   soft(g,armW,armTop-lh,d-.04,[x,(armTop+lh)/2,0],m.fabric,'sofa-'+p.family+'-arm',{radius:Math.min(p.round,armW*.3)});
   if(classic){const roll=addMesh(g,new T.CylinderGeometry(armW*.46,armW*.46,d-.065,16),m.fabric,'sofa-rolled-arm',[x,armTop-.01,0]);roll.rotation.x=Math.PI/2;
    tube(g,[[x,lh+.02,d/2-.02],[x-sign*.018,armTop*.52,d/2-.02],[x+sign*.018,armTop-.015,d/2-.02]],.012,frame,'sofa-front-wood-scroll');}
   if(p.family==='lattice'||p.family==='timber')rigid(g,armW,.026,d-.06,[x,armTop+.012,0],m.wood,'sofa-exposed-wood-arm',.004);
  }
  if(classic){const accent=m.fabric.clone();accent.color.set(f.finishes?.pillow||'#b8baa5');for(const sign of[-1,1])pillow(g,Math.min(.40,w*.16),.105,Math.min(.38,h*.40),[sign*(w/2-armW-.23),seat+.15,backZ+.18],accent,accent,'sofa-accent-pillow',{tilt:Math.PI/2-.23,yaw:sign*.12});}
  if(classic)tube(g,[[-w/2+.04,lh+.035,d/2-.01],[-w*.25,lh+.02,d/2-.01],[0,lh+.045,d/2-.01],[w*.25,lh+.02,d/2-.01],[w/2-.04,lh+.035,d/2-.01]],.014,frame,'sofa-curved-front-apron');
 }else if(['chair','barstool'].includes(f.type)){
  const sy=f.type==='barstool'?h*.7:Math.min(.46,h*.54),bh=h-sy-.045,cy=sy+.035+bh/2;
  legs(g,w-.025,d-.025,sy-.04,p,m,'chair');rigid(g,w-.04,.035,d-.035,[0,sy-.035,.01],m.wood,'chair-seat-frame',.012);soft(g,w-.025,.065,d-.025,[0,sy,.005],m.fabric,'chair-seat',{radius:p.round});
  if(classic){const ry=bh/2-.008,rx=Math.min((w-.05)/2,ry*(p.family==='classic'?1.00:.88)),z=-d/2+.043;
   const rim=addMesh(g,new T.TorusGeometry(1,.055,6,36),frame,'chair-oval-wood-frame',[0,cy,z]);rim.scale.set(rx,ry,.16);
   const fill=addMesh(g,new T.SphereGeometry(1,20,12),m.fabric,'chair-oval-upholstery',[0,cy,z+.012]);fill.scale.set(rx*.93,ry*.93,.025);
   for(const sign of [-1,1])rod(g,[sign*rx*.7,sy-.025,z],[sign*rx*.7,cy-ry*.64,z],.012,frame,'chair-back-post');
  }else if(p.family==='lattice'){
   for(const x of [-1,1])rigid(g,.022,bh+.05,.025,[x*(w/2-.035),cy-.015,-d/2+.04],m.wood,'chair-wood-upright',.003);
   rigid(g,w-.035,.045,.05,[0,h-.025,-d/2+.035],m.wood,'chair-wood-toprail',.006);rigid(g,w*.17,bh*.84,.025,[0,cy,-d/2+.04],m.wood,'chair-splat',.004);
  }else{
   const rw=p.family==='timber'?w*.88:p.family==='low'?w*.93:w-.04,hh=p.family==='timber'?bh*.38:bh*.96,y=p.family==='timber'?h-bh*.25:cy;
   soft(g,rw,hh,.065,[0,y,-d/2+.04],p.family==='timber'?m.wood:m.fabric,'chair-'+p.family+'-back',{radius:p.round});
   for(const sign of [-1,1])rod(g,[sign*w*.33,sy,-d/2+.045],[sign*w*.33,y,-d/2+.045],.009,p.legs==='metal'?m.metal:m.wood,'chair-back-post');
  }
 }else if(['tvstand','nightstand','wardrobe'].includes(f.type)){
  const tall=f.type==='wardrobe',lh=tall?.045:Math.min(h*.22,.10),top=.025,bodyH=h-lh-top;
  if(tall||p.family==='linear'||p.family==='low')rigid(g,w-.05,lh,d-.06,[0,lh/2,0],m.dark,'cabinet-recessed-base',.001);else legs(g,w-.02,d-.02,lh,p,m,'cabinet');
  rigid(g,w-.01,bodyH,d-.035,[0,lh+bodyH/2,-.012],m.body,'styled-cabinet-body',.004);rigid(g,w,top,d,[0,h-top/2,0],m.body,'styled-cabinet-top',p.round*.2);
  panels(g,w-.02,bodyH-.018,lh+bodyH/2,d/2-.023,p,{...m,wood:classic?m.body:m.wood},'cabinet');
 }else if(['table','desk','dresser'].includes(f.type)){
  const t=.03;rigid(g,w,t,d,[0,h-t/2,0],f.type==='table'?m.stone:m.wood,'styled-table-top',p.round*.45);
  if(p.family==='low'&&f.type==='table'){for(const sign of [-1,1])rigid(g,.07,h-t,d*.62,[sign*w*.27,(h-t)/2,0],m.body,'table-pedestal',.025);}
  else legs(g,w-.035,d-.035,h-t,p,m,'table');
  for(const sign of [-1,1])rigid(g,w-.11,.05,.02,[0,h-t-.03,sign*(d/2-.045)],classic?m.body:m.wood,'table-apron',.004);
 }else if(f.type==='bed'){
  const lh=Math.min(.07,h*.08),base=.18,matt=.18,top=lh+base+matt;
  legs(g,w-.035,d-.035,lh,p,m,'bed');rigid(g,w-.02,base,d-.03,[0,lh+base/2,0],m.wood,'styled-bed-frame',.015);
  soft(g,w-.055,matt,d-.12,[0,lh+base+matt/2,.02],m.fabric,'bed-mattress',{radius:.045});
  if(classic||p.family==='deco'){crest(g,w-.018,h-.008,lh,-d/2+.012,p,frame,'bed-shaped-headboard');crest(g,w-.09,h-.045,lh+.05,-d/2+.045,p,m.fabric,'bed-shaped-head-padding');}
  else soft(g,w-.02,h-lh,.08,[0,(h+lh)/2,-d/2+.04],p.family==='timber'||p.family==='lattice'?m.wood:m.fabric,'bed-'+p.family+'-headboard',{radius:p.round});
  soft(g,w-.065,.075,d*.72,[0,top+.024,d*.105],m.fabric,'bed-duvet',{radius:.035});
  const runner=m.fabric.clone();runner.color.set(f.finishes?.bedRunner||'#b7b49e');soft(g,w-.06,.025,d*.22,[0,top+.07,d*.24],runner,'bed-runner',{radius:.008});
  const count=w>1.2?2:1;for(let i=0;i<count;i++)soft(g,w/count*.78,.09,.36,[(i-(count-1)/2)*w/count,top+.045,-d/2+.34],m.fabric,'bed-pillow',{radius:.035});
 }
 g.name='style-body-'+id;return g;
}
