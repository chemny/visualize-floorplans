// mm plan geometry; explicitly configured mechanism, never inferred from a pull.
export function showerDoorGeometry(f,open=f.showerDoor?.open??0){
 const s=f.showerDoor;if(!s||s.type!=='hinged')throw Error('需明确淋浴门机制');
 if(!['left','right'].includes(s.hinge)||![s.angle,open].every(Number.isFinite)||s.angle<5||s.angle>100||open<0||open>1||Math.min(f.w,f.d)<500)throw Error('淋浴门参数无效');
 const sign=s.hinge==='left'?1:-1,hinge=[-sign*(f.w/2-20),f.d/2],length=s.width??f.w-40,a=s.angle*open*Math.PI/180;
 if(!Number.isFinite(length)||length<300||length>f.w-40+.01)throw Error('淋浴房宽度不能小于门宽加40 mm');
 const fixedEnd=[sign*(f.w/2-20),f.d/2],closedTip=[hinge[0]+sign*length,hinge[1]],fixedPanels=f.w-40-length>.01?[[closedTip,fixedEnd]]:[];
 const tip=[hinge[0]+sign*length*Math.cos(a),hinge[1]+length*Math.sin(a)],rot=(f.rot||0)*Math.PI/180;
 const world=p=>[f.cx+p[0]*Math.cos(rot)-p[1]*Math.sin(rot),f.cy+p[0]*Math.sin(rot)+p[1]*Math.cos(rot)];
 const handle=[hinge[0]+sign*(length-65)*Math.cos(a),hinge[1]+(length-65)*Math.sin(a)];
 const normal=[-Math.sin(a),sign*Math.cos(a)];
 return {hinge,tip,length,sign,rotationY:-sign*a,worldHinge:world(hinge),worldTip:world(tip),handle:world([handle[0]+normal[0]*32,handle[1]+normal[1]*32]),netOpeningMm:Math.max(0,length*(1-Math.cos(a))-20),thicknessMm:10,fixedPanels,worldFixedPanels:fixedPanels.map(pair=>pair.map(world))};
}

export function showerEnclosureSegments(f,open){const a=(f.rot||0)*Math.PI/180,world=p=>[f.cx+p[0]*Math.cos(a)-p[1]*Math.sin(a),f.cy+p[0]*Math.sin(a)+p[1]*Math.cos(a)],w=f.w/2-5,d=f.d/2-5,g=showerDoorGeometry(f,open);return [[world([-w,-d]),world([w,-d]),5],[world([-w,-d]),world([-w,d]),5],[world([w,-d]),world([w,d]),5],...g.worldFixedPanels.map(([a,b])=>[a,b,5]),[g.worldHinge,g.worldTip,5],[g.handle,g.handle,9]];}
