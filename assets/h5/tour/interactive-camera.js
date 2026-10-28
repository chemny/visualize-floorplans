// Interactivity uses one draw. Deterministic capture retains its settle/double draw.
export function createPoseRenderer({renderer,camera,scene,settings,model}){
 let viewport='',projection='';
 function applyFade(f){
  const fade=f.fadeToBlack??0;if(!Number.isFinite(fade)||fade<0||fade>1)throw Error('Frame fade must be between zero and one');
  if(renderer.domElement?.style)renderer.domElement.style.filter=fade?`brightness(${1-fade})`:'';
 }
 function apply(f){
  applyFade(f);
  const size=settings.size,key=size.join('x');
  if(key!==viewport||(renderer.domElement&&(renderer.domElement.width!==size[0]||renderer.domElement.height!==size[1]))){renderer.setSize(...size);camera.aspect=size[0]/size[1];viewport=key;projection='';}
  const hfov=f.horizontalFovDegrees??70,shift=f.shiftY??settings.shiftY??0,pkey=[key,hfov,shift].join(':');
  const expectedFov=2*Math.atan(Math.tan(hfov*Math.PI/360)/(size[0]/size[1]))*180/Math.PI;
  if(pkey!==projection||Math.abs(camera.fov-expectedFov)>1e-9||camera.aspect!==size[0]/size[1]||Math.abs(camera.projectionMatrix.elements[9]+shift)>1e-9){camera.aspect=size[0]/size[1];camera.fov=expectedFov;camera.updateProjectionMatrix();camera.projectionMatrix.elements[9]-=shift;camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();projection=pkey;}
  camera.position.set((f.pointMm[0]-model.width/2)/1000,f.eyeMm/1000,(f.pointMm[1]-model.depth/2)/1000);camera.up.set(0,1,0);
  camera.lookAt(camera.position.x+Math.cos(f.yawRadians),camera.position.y+Math.tan(f.pitchRadians),camera.position.z+Math.sin(f.yawRadians));camera.updateMatrixWorld(true);
 }
 return {applyFade,draw(f){apply(f);renderer.render(scene,camera);},async capture(f){apply(f);renderer.render(scene,camera);await new Promise(r=>requestAnimationFrame(r));renderer.render(scene,camera);}};
}
