import * as THREE from 'three';
// Editable concept dimensions in mm; no product maxima or construction specification.
const def=(type,name,w,d,h,elevation,mount,role='ceiling',lit=false)=>({type,name,w,d,h,elevation,mount,role,lit});
export const RENOVATION_SPECS=[
 def('ceilinground','圆形吸顶灯',500,500,70,2680,'ceiling','ceiling',true),
 def('ceilingsquare','方形吸顶灯',500,500,65,2685,'ceiling','ceiling',true),
 def('lightpanel','平板灯',600,300,35,2715,'ceiling','ceiling',true),
 def('spotlight','射灯',90,90,60,2690,'ceiling','metal',true),
 def('linearlight','线性灯',1200,60,50,2700,'ceiling','metal',true),
 def('ledstrip','灯带',1200,30,20,2730,'ceiling','ceiling',true),
 def('cabinetlight','柜底灯',700,30,20,1780,'under-cabinet','metal',true),
 def('cove','灯槽',1200,120,100,2650,'ceiling','ceiling'),
 def('curtainbox','窗帘盒',1800,180,90,2660,'ceiling','ceiling'),
 def('accesshatch','检修口',450,450,20,2730,'ceiling'),
 def('airvent','送风口',700,150,35,2715,'ceiling'),
 def('returnvent','回风口',600,300,35,2715,'ceiling'),
 def('exhaustvent','排风口',200,200,35,2715,'ceiling'),
 def('curtainrail','窗帘轨道',1800,60,35,2645,'wall','metal'),
 def('curtain','帘布',450,100,2500,50,'wall','upholstery'),
 def('rollerblind','卷帘',1200,65,400,1800,'wall','upholstery'),
 def('skirting','踢脚线',1000,30,80,0,'wall','cabinet'),
 def('doortrim','门套',1000,180,2150,0,'opening','door'),
 def('windowtrim','窗套',1500,180,1430,820,'opening','frame'),
 def('threshold','门槛石',900,180,15,0,'floor','stone'),
 def('transition','地面过渡条',1000,30,15,0,'floor','metal'),
 def('switchplate','开关',86,30,86,1250,'wall','cabinet'),
 def('socketplate','插座',86,30,86,300,'wall','cabinet'),
 def('equipmentoutlet','设备插座',86,30,86,1100,'wall','cabinet'),
 def('backsplash','挡水条',1000,30,80,900,'wall','stone'),
 def('floordrain','地漏',100,100,15,0,'floor','metal'),
 def('towelrail','毛巾杆',600,80,60,1200,'wall','metal'),
 def('paperholder','纸巾架',160,100,150,650,'wall','metal'),
 def('walllamp','壁灯',180,120,260,1450,'wall','metal',true),
 def('tablelamp','台灯',240,240,400,750,'surface','metal',true),
 def('mirrorpanel','镜面',600,40,800,1100,'wall','glass'),
 def('mirrorlight','镜前灯',600,60,40,1900,'wall','metal',true),
 def('wallpanel','护墙板',1200,30,1100,0,'wall','wood')
];
export const RENOVATION_MAP=Object.fromEntries(RENOVATION_SPECS.map(s=>[s.type,s]));
export const TOP_TYPES=new Set(['pendant','downlight','tracklight',...RENOVATION_SPECS.filter(s=>s.mount==='ceiling').map(s=>s.type)]);
export const LIT_TYPES=new Set(['pendant','downlight','tracklight',...RENOVATION_SPECS.filter(s=>s.lit).map(s=>s.type)]);
export function renovationModel(f,p,night=false){
 const w=f.w/1000,d=f.d/1000,h=f.h/1000,g=new THREE.Group();
 const material=(role,color,extra={})=>{const m=new THREE.MeshStandardMaterial({color:color||p[role]||f.color,roughness:role==='metal'?.32:role==='upholstery'?.93:.65,metalness:role==='metal'?.65:0,...extra});m.userData.ownedFurnitureDetail=true;m.userData.finishRole=role;return m;};
 const shell=material(RENOVATION_MAP[f.type].role,f.color),dark=material('frame'),metal=material('metal'),glow=material('light','#ffffff',{emissive:'#ffffff',emissiveIntensity:night?1.2:1.0});
 glow.userData.visibleFixtureLens=true;
 const B=(a,b,c,x=0,y=0,z=0,m=shell)=>{const o=new THREE.Mesh(new THREE.BoxGeometry(Math.max(a,.001),Math.max(b,.001),Math.max(c,.001)),m);o.position.set(x,y+b/2,z);o.receiveShadow=true;o.castShadow=!['ledstrip','cabinetlight','floordrain'].includes(f.type);g.add(o);return o;};
 const C=(r,b,x=0,y=0,z=0,m=shell)=>{const o=new THREE.Mesh(new THREE.CylinderGeometry(r,r,b,32),m);o.position.set(x,y+b/2,z);g.add(o);return o;};
 const slats=()=>{B(w,h,d);for(let i=0;i<Math.min(24,Math.max(3,Math.floor(w/.035)));i++){const x=-w*.45+w*.9*i/(Math.min(24,Math.max(3,Math.floor(w/.035)))-1);B(.012,.002,d*.7,x,.002,0,dark);}};
 switch(f.type){
 case 'ceilinground': C(w/2,h*.22,0,h*.78);C(w/2,h*.78,0,0,0,glow);break;
 case 'ceilingsquare':case 'lightpanel': B(w,h*.22,d,0,h*.78);B(w,h*.78,d,0,0,0,glow);break;
 case 'spotlight':C(w/2,h);C(w*.34,.003,0,-.0006,0,glow);break;
 case 'linearlight':case 'ledstrip':case 'cabinetlight': B(w,h,d);B(w*.97,h*.12,d*.75,0,-.0006,0,glow);break;
 case 'cove':B(w,h,.015,0,0,-d/2+.0075);B(w,.018,d,0,h-.018);B(w,h*.35,.015,0,h*.65,d/2-.0075);break;
 case 'curtainbox': B(w,h,.018,0,0,-d/2+.009);B(w,h,.018,0,0,d/2-.009);B(w,.018,d,0,h-.018);break;
 case 'accesshatch':B(w,h,d);B(w-.024,.003,d-.024,0,0,0,material('ceiling',p.ceiling));[-.35,.35].forEach(x=>B(.03,.003,.006,w*x,0,d*.36,dark));break;
 case 'airvent':case 'returnvent':case 'exhaustvent':slats();break;
 case 'curtainrail':B(w,h,d,0,0,0,metal);B(w*.96,h*.25,d*.22,0,0,0,dark);break;
 case 'curtain': {
  const folds=Math.max(4,Math.round(w/.08)),nx=folds*12,vertices=[],uv=[],indices=[];
  for(let row=0;row<2;row++)for(let i=0;i<=nx;i++){const u=i/nx;vertices.push((u-.5)*w,row*h,Math.sin(u*folds*Math.PI*2)*d*.42);uv.push(u,row);}
  for(let i=0;i<nx;i++)indices.push(i,i+1,nx+1+i,i+1,nx+2+i,nx+1+i);
  const geo=new THREE.BufferGeometry();geo.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));geo.setAttribute('uv',new THREE.Float32BufferAttribute(uv,2));geo.setIndex(indices);geo.computeVertexNormals();
  const cloth=shell.clone();cloth.side=THREE.DoubleSide;cloth.roughness=.95;cloth.metalness=0;
  if(f.curtainLayer==='sheer'){cloth.color.set('#f5f2ec');cloth.transparent=true;cloth.opacity=.22;cloth.depthWrite=false;}
  const mesh=new THREE.Mesh(geo,cloth);mesh.name=f.curtainLayer==='sheer'?'sheer-curtain':'blackout-curtain';mesh.castShadow=f.curtainLayer!=='sheer';mesh.receiveShadow=true;g.add(mesh);break;
 }
 case 'rollerblind':B(w,.03,d,0,h-.03);B(w,h-.025,.012,0,0,d*.36);const o=C(.022,w,0,0,0,metal);o.rotation.z=Math.PI/2;o.position.set(0,h-.022,0);B(w,.012,d*.6,0,0,d*.2,metal);break;
 case 'skirting':case 'backsplash':case 'threshold':case 'transition':case 'wallpanel':B(w,h,d);break;
 case 'doortrim': {const t=Math.min(.055,w*.08);[-1,1].forEach(s=>B(t,h,d,s*(w/2-t/2)));B(w,h*.023,d,0,h-h*.023);break;}
 case 'windowtrim': {const t=.035;[-1,1].forEach(s=>B(t,h,d,s*(w/2-t/2)));B(w,t,d);B(w,t,d,0,h-t);break;}
 case 'switchplate':case 'socketplate':case 'equipmentoutlet':B(w,h,d);if(f.type==='switchplate')B(w*.72,h*.78,.003,0,h*.11,d/2+.001);else{for(const x of [-w*.18,w*.18])B(.007,h*.22,.003,x,h*.46,d/2+.001,dark);B(.007,h*.12,.003,0,h*.18,d/2+.001,dark);}break;
 case 'floordrain':B(w,h,d,0,0,0,metal);for(let i=-2;i<=2;i++)B(w*.7,.002,.005,0,h-.002,d*.13*i,dark);break;
 case 'towelrail':B(w,h*.5,.022,0,h*.25,d/2-.011,metal);[-1,1].forEach(s=>B(.024,h,d,w*.42*s,0,0,metal));break;
 case 'paperholder':B(w*.8,h*.7,d*.6,0,h*.1,d*.15,material('ceramic'));B(w,.008,d,0,h-.008,0,metal);B(w*.1,h,d*.3,-w*.45,0,-d*.35,metal);break;
 case 'walllamp':B(w,h,d*.6);B(w*.85,h*.02,d*.5,0,0,d*.25,glow);break;
 case 'tablelamp':C(w*.42,h*.07,0,0,0,metal);C(.009,h*.6,0,0,0,metal);C(w/2,h*.33,0,h*.67);C(w*.45,.004,0,h*.67-.0006,0,glow);break;
 case 'mirrorpanel':B(w,h,d,0,0,0,metal);B(w-.025,h-.025,.003,0,.0125,d/2+.002,material('glass','#d9e4e3',{metalness:.88,roughness:.07}));break;
 case 'mirrorlight':B(w,h,d,0,0,0,metal);B(w*.95,h*.8,.003,0,h*.1,d/2+.002,glow);break;
 }
 if(['ceilinground','spotlight','tablelamp'].includes(f.type))g.scale.z=d/w;
 g.userData.bodyForDimensions=true;g.userData.renovation=true;return g;
}
export function renovationSymbol(type,w,d,c){
 const s='stroke="#666158" stroke-width="1" vector-effect="non-scaling-stroke"',r=(fill=c)=>`<rect x="${-w/2}" y="${-d/2}" width="${w}" height="${d}" fill="${fill}" ${s}/>`;
 if(['ceilinground','spotlight','tablelamp'].includes(type))return `<ellipse rx="${w/2}" ry="${d/2}" fill="${c}" ${s}/><path d="M${-w*.25} 0H${w*.25}M0 ${-d*.25}V${d*.25}" ${s}/>`;
 if(['ceilingsquare','lightpanel'].includes(type))return r()+`<path d="M${-w*.3} ${-d*.3}L${w*.3} ${d*.3}M${w*.3} ${-d*.3}L${-w*.3} ${d*.3}" ${s}/>`;
 if(['airvent','returnvent','exhaustvent','floordrain'].includes(type))return r()+[-.3,-.15,0,.15,.3].map(a=>`<path d="M${-w*.4} ${d*a}H${w*.4}" ${s}/>`).join('');
 if(['doortrim','windowtrim'].includes(type))return `<rect x="${-w/2}" y="${-d/2}" width="${w}" height="${d}" fill="none" ${s}/>`;
 if(['curtain','rollerblind'].includes(type))return r()+[-.35,-.15,.05,.25,.4].map(a=>`<path d="M${w*a} ${-d*.4}v${d*.8}" ${s}/>`).join('');
 return r()+`<path d="M${-w*.4} 0H${w*.4}" ${s}/>`;
}
