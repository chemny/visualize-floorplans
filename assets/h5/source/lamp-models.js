import * as THREE from 'three';
// Parametric decorative bodies. Light contribution is managed independently by the renderer.
export function styleLampModel(shape,width=.6,depth=width,palette={}){
 const g=new THREE.Group(),r=width/2;
 const mat=(color,roughness=.6,metalness=0)=>new THREE.MeshStandardMaterial({color,roughness,metalness});
 const white=mat('#f6f2e9'),bronze=mat(palette.metal||'#ae8c55',.35,.65),wood=mat('#b89162',.75),cloth=mat('#eee3ce',.96);
 const glow=new THREE.MeshStandardMaterial({color:'#fff7e9',emissive:'#fff7e9',emissiveIntensity:.7,roughness:.8});glow.userData.visibleFixtureLens=true;
 const add=(geo,m,x=0,y=0,z=0)=>{const mesh=new THREE.Mesh(geo,m);mesh.position.set(x,y,z);mesh.receiveShadow=true;mesh.castShadow=false;g.add(mesh);return mesh;};
 const disc=(radius,height,y,m)=>add(new THREE.CylinderGeometry(radius,radius,height,24),m,0,y,0);
 let drop;
 if(shape==='flat'){
  // Reference 1: shallow white frame and broad flat opal diffuser.
  drop=.045;disc(r*.90,.014,-.007,white);add(new THREE.CylinderGeometry(r,r,.025,64),white,0,-.024,0);
  add(new THREE.CylinderGeometry(r*.965,r*.965,.009,64),glow,0,-.040,0);
 }else if(shape==='dome'){
  // Reference 2: continuous shallow convex diffuser, flush mounted, thin gold trim.
  drop=.12;disc(r*.86,.014,-.007,white);
  disc(r*.985,.012,-.021,white);
  const rim=add(new THREE.TorusGeometry(r*.975,r*.012,8,64),bronze,0,-.030,0);rim.rotation.x=Math.PI/2;
  const shade=add(new THREE.SphereGeometry(r*.975,64,20,0,Math.PI*2,Math.PI/2,Math.PI/2),glow,0,-.033,0);
  shade.scale.y=.27;shade.name='continuous-convex-opal-diffuser';
 }else if(shape==='crystal'){
  drop=.34;disc(r*.23,.023,-.0115,bronze);disc(.009,.135,-.083,bronze);
  const crystal=new THREE.MeshPhysicalMaterial({color:'#e7f1f5',roughness:.08,metalness:.12,transparent:true,opacity:.65,depthWrite:false,clearcoat:1});
  const jewel=(x,y,z,scale=1)=>{const o=add(new THREE.OctahedronGeometry(.012,0),crystal,x,y,z);o.scale.set(.7*scale,1.7*scale,.7*scale);o.name='faceted-crystal';};
  for(let i=0;i<6;i++){
   const a=i*Math.PI*2/6,x=Math.cos(a)*r*.73,z=Math.sin(a)*r*.73;
   const pts=[new THREE.Vector3(0,-.125,0),new THREE.Vector3(x*.5,-.23,z*.5),new THREE.Vector3(x,-.20,z),new THREE.Vector3(x,-.155,z)];
   add(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts),12,.005,6,false),bronze);
   add(new THREE.CylinderGeometry(.021,.021,.005,16),bronze,x,-.155,z);
   add(new THREE.CylinderGeometry(.006,.006,.035,10),white,x,-.133,z);
   const bulb=add(new THREE.SphereGeometry(.010,10,8),glow,x,-.106,z);bulb.scale.y=1.7;
   jewel(x,-.235,z,.8);jewel(x*.7,-.268,z*.7,.8);
  }
  const rim=add(new THREE.TorusGeometry(r*.47,.005,6,32),bronze,0,-.22,0);rim.rotation.x=Math.PI/2;
  for(let i=0;i<18;i++){
   const a=i*Math.PI*2/18,rad=r*.47;jewel(Math.cos(a)*rad,-.246,Math.sin(a)*rad,.65);
  }
  disc(.028,.024,-.23,bronze);jewel(0,-.288,0,1.8);
 }else if(shape==='crystal_classic'){
  // Glass scroll arms, bead swags and teardrops; no refraction pass or new lights.
  drop=.52;
  const glass=new THREE.MeshPhysicalMaterial({color:'#f1f6fa',roughness:.12,metalness:.08,transparent:true,opacity:.64,depthWrite:false,clearcoat:1});
  const beads=[],drops=[];
  const curve=(points,radius,material)=>add(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(points),12,radius,6,false),material);
  disc(r*.18,.018,-.009,bronze);
  for(let i=0;i<3;i++){const link=add(new THREE.TorusGeometry(.011,.0025,5,12),bronze,0,-.029-i*.016,0);link.rotation.y=i%2?Math.PI/2:0;}
  const profile=[[0,-.064],[r*.07,-.065],[r*.13,-.083],[r*.07,-.10],[r*.07,-.15],[r*.20,-.19],[r*.13,-.22],[r*.07,-.25],[r*.08,-.29],[r*.32,-.315],[r*.17,-.34],[0,-.345]].map(([x,y])=>new THREE.Vector2(x,y));
  add(new THREE.LatheGeometry(profile,24),glass);disc(.006,.26,-.20,bronze);disc(r*.30,.014,-.326,bronze);
  for(let i=0;i<8;i++){
   const a=i*Math.PI/4,x=Math.cos(a)*r*.80,z=Math.sin(a)*r*.80;
   curve([new THREE.Vector3(0,-.28,0),new THREE.Vector3(x*.52,-.36,z*.52),new THREE.Vector3(x,-.29,z),new THREE.Vector3(x,-.21,z)],.009,glass);
   add(new THREE.CylinderGeometry(.024,.017,.014,12),glass,x,-.213,z);add(new THREE.CylinderGeometry(.006,.006,.040,8),bronze,x,-.185,z);
   const bulb=add(new THREE.SphereGeometry(.010,8,6),glow,x,-.152,z);bulb.scale.y=1.8;
   // The upper bead strings and inter-arm swags use repeated small crystals.
   for(let j=1;j<=7;j++){const t=j/8;beads.push([x*t,-.077-.14*t,z*t]);}
   const a2=a+Math.PI/4,x2=Math.cos(a2)*r*.80,z2=Math.sin(a2)*r*.80;
   for(let j=1;j<=5;j++){const t=j/6;beads.push([x+(x2-x)*t,-.228-Math.sin(t*Math.PI)*.036,z+(z2-z)*t]);}
   drops.push([x,-.272,z,.75],[x*.60,-.389,z*.60,1],[x*.30,-.434,z*.30,.85]);
  }
  drops.push([0,-.490,0,1.4]);
  const matrix=new THREE.Matrix4(),position=new THREE.Vector3(),quaternion=new THREE.Quaternion(),scale=new THREE.Vector3();
  const inst=(geometry,rows,isDrop)=>{const mesh=new THREE.InstancedMesh(geometry,glass,rows.length);for(let i=0;i<rows.length;i++){const[x,y,z,k=1]=rows[i];position.set(x,y,z);scale.set(k,isDrop?k*2.0:k,k);matrix.compose(position,quaternion,scale);mesh.setMatrixAt(i,matrix);}mesh.instanceMatrix.needsUpdate=true;mesh.name=isDrop?'crystal-teardrops':'crystal-bead-swags';g.add(mesh);};
  inst(new THREE.SphereGeometry(.004,8,4),beads,false);inst(new THREE.OctahedronGeometry(.011,0),drops,true);
 }else throw Error('Unknown lamp shape');
 g.scale.z=depth/width;g.updateMatrixWorld(true);const bounds=new THREE.Box3().setFromObject(g);drop=bounds.max.y-bounds.min.y;g.userData.lampBody={shape,width,depth,drop};return g;
}
