export function createLightingRuntime({SpotLight,Color,CASE,ROOMS,getF,inPolygon,opt,getRuntime,pixelRatio}){
let performanceSlots=[],performanceSourceSignature='',performanceLightingSignature='',performanceSources=[];
let performanceRatio=1,performanceLastPose='',performanceStill=0,performanceFrameAverage=1/60,performanceResizeTick=0;
function updatePerformanceLighting(dt){
 if(CASE.render?.performanceLighting===false)return;
 const {lampG,scene,renderer,camera,ceilingFill,hemi,anim,fly}=getRuntime();
 const sources=lampG.children.filter(l=>l.isLight&&l.userData.fixtureId);
 const signature=sources.map(l=>l.uuid).join('|');
 if(signature!==performanceSourceSignature){
  performanceSourceSignature=signature;performanceLightingSignature='';for(const slot of performanceSlots){scene.remove(slot.light,slot.light.target);}performanceSlots=[];
  performanceSources=sources.map(l=>{const f=getF(l.userData.fixtureId),room=f&&ROOMS.find(r=>inPolygon([f.cx,f.cy],r.poly));return{light:l,room:room?.id,main:f&&['ceilinground','ceilingsquare','lightpanel','pendant','linearlight'].includes(f.type)};});
  // Each main light keeps its own permanent spatial fill; secondary lights
  // contribute to the nearest main in the same room, independent of viewpoint.
  const anchors=performanceSources.filter(s=>s.main);
  for(const source of performanceSources){if(anchors.some(a=>a.room===source.room))continue;anchors.push(source);}
  for(const anchor of anchors){const l=new SpotLight('#fff1db',0,10,Math.PI*.42,.85,1.4);l.userData.runtimeIllumination=true;l.userData.anchorFixtureId=anchor.light.userData.fixtureId;l.position.copy(anchor.light.position);l.position.y-=.08;l.target.position.set(l.position.x,0,l.position.z);scene.add(l,l.target);performanceSlots.push({light:l,source:anchor.light,members:[]});}
  for(const source of performanceSources){const candidates=performanceSlots.filter(slot=>performanceSources.find(s=>s.light===slot.source)?.room===source.room);const slot=candidates.sort((a,b)=>a.source.position.distanceTo(source.light.position)-b.source.position.distanceTo(source.light.position))[0];if(slot)slot.members.push(source);}
  renderer.setPixelRatio(Math.min(pixelRatio(),performanceRatio));
 }
 for(const l of sources)l.visible=false;
 const lightingSignature=[opt.lamps,opt.night,...sources.map(l=>[l.userData.enabled,l.userData.nominalIntensity,l.color.getHex()].join(':'))].join('|');
 if(lightingSignature!==performanceLightingSignature){
  performanceLightingSignature=lightingSignature;
  for(const slot of performanceSlots){let intensity=0;const color=new Color(0,0,0);
   for(const member of slot.members){const s=member.light;if(!opt.lamps||!s.userData.enabled)continue;const weight=(s.userData.nominalIntensity||0)*(member.main?(opt.night?2.6:1):.18);intensity+=weight;color.r+=s.color.r*weight;color.g+=s.color.g*weight;color.b+=s.color.b*weight;}
   slot.light.intensity=Math.min(intensity,12);if(intensity>0)slot.light.color.copy(color.multiplyScalar(1/intensity));
  }
 }
 if(ceilingFill)ceilingFill.intensity=opt.night?(opt.lamps?.25:.10):.28;
 if(!opt.night)hemi.intensity=.9;
 const pose=camera.position.toArray().concat(camera.quaternion.toArray()).map(n=>n.toFixed(3)).join(',');const moving=pose!==performanceLastPose||!!anim||!!fly;performanceLastPose=pose;performanceStill=moving?0:performanceStill+dt;
 performanceFrameAverage+=(dt-performanceFrameAverage)*.04;performanceResizeTick-=dt;
 if(performanceResizeTick<=0){performanceResizeTick=1;let target=Math.min(pixelRatio(),performanceStill>1?1.5:1);if(performanceFrameAverage>.025)target=Math.min(target,.85);if(performanceFrameAverage>.04)target=.75;if(Math.abs(performanceRatio-target)>.1){performanceRatio=target;renderer.setPixelRatio(target);}}
}
return{update:updatePerformanceLighting,status:()=>({mode:CASE.render?.performanceLighting===false?'original-fixtures':'fixed-spatial',budget:performanceSlots.length,activeSlots:performanceSlots.filter(s=>s.light.intensity>.025).length,pixelRatio:getRuntime().renderer?.getPixelRatio(),slots:performanceSlots.map(s=>({fixtureId:s.source?.userData.fixtureId,position:s.light.position.toArray(),intensity:s.light.intensity,members:s.members.map(m=>m.light.userData.fixtureId)})),sourceLights:performanceSources.length})};
}
