import {LIGHTING_PROFILE,lightingProfile} from './lighting-profile.js';
export function createLightingRuntime({SpotLight,PointLight,Color,CASE,ROOMS,getF,inPolygon,opt,getRuntime,pixelRatio}){
let performanceSlots=[],performanceSourceSignature='',performanceLightingSignature='',performanceSources=[];
let shadowOverride=null,revision=0;
function updatePerformanceLighting(dt){
 const {lampG,scene,renderer,ceilingFill,hemi}=getRuntime();
 // Native display resolution only; motion and frame cost never reduce it.
 const nativeRatio=pixelRatio();
 if(renderer&&renderer.getPixelRatio()!==nativeRatio){renderer.setPixelRatio(nativeRatio);revision++;}
 if(CASE.render?.performanceLighting===false)return;
 const sources=lampG.children.filter(l=>l.isLight&&l.userData.fixtureId);
 const signature=sources.map(l=>l.uuid).join('|');
 if(signature!==performanceSourceSignature){
  revision++;performanceSourceSignature=signature;performanceLightingSignature='';for(const slot of performanceSlots){scene.remove(slot.light);if(slot.light.target)scene.remove(slot.light.target);slot.light.shadow?.map?.dispose();slot.light.dispose?.();}performanceSlots=[];
  performanceSources=sources.map(l=>{const f=getF(l.userData.fixtureId),room=f&&ROOMS.find(r=>inPolygon([f.cx,f.cy],r.poly));return{light:l,room:room?.id,main:f&&['ceilinground','ceilingsquare','lightpanel','pendant','linearlight'].includes(f.type)};});
  // Each main light keeps its own permanent spatial fill; secondary lights
  // contribute to the nearest main in the same room, independent of viewpoint.
  const anchors=performanceSources.filter(s=>s.main);
  for(const source of performanceSources){if(anchors.some(a=>a.room===source.room))continue;anchors.push(source);}
  for(const anchor of anchors){
   const f=getF(anchor.light.userData.fixtureId),omni=['ceilinground','ceilingsquare','lightpanel'].includes(f?.type);
   // Ceiling diffusers illuminate sideways and upwards as well as downwards.
   // Keep one light per existing group, rather than adding upper fill lights.
   const l=omni?new PointLight('#fff1db',0,10,1.4):new SpotLight('#fff1db',0,10,Math.PI*.42,.85,1.4);
   l.userData.runtimeIllumination=true;l.userData.omnidirectional=omni;l.userData.anchorFixtureId=anchor.light.userData.fixtureId;l.position.copy(anchor.light.position);
   l.position.y+=omni?(f.h??70)/1000*.39+.012:-.08;
   if(l.target){l.target.position.set(l.position.x,0,l.position.z);scene.add(l.target);}scene.add(l);
   performanceSlots.push({light:l,source:anchor.light,members:[]});
  }
  for(const source of performanceSources){const candidates=performanceSlots.filter(slot=>performanceSources.find(s=>s.light===slot.source)?.room===source.room);const slot=candidates.sort((a,b)=>a.source.position.distanceTo(source.light.position)-b.source.position.distanceTo(source.light.position))[0];if(slot)slot.members.push(source);}
 }
 // A fixed small shadow set, independent of camera location. No per-room activation.
 const configured=CASE.render?.shadowFixtureIds;
 const budget=shadowOverride===false?0:Math.max(0,Math.min(2,CASE.render?.indoorShadowBudget??(shadowOverride===true?2:0)));
 const candidates=performanceSlots.filter(s=>performanceSources.find(p=>p.light===s.source)?.main&&(!configured||configured.includes(s.source.userData.fixtureId)));
 const shadowIds=new Set(candidates.slice(0,budget).map(s=>s.source.userData.fixtureId));
 for(const slot of performanceSlots){const enabled=shadowIds.has(slot.source.userData.fixtureId);if(slot.light.castShadow!==enabled){slot.light.castShadow=enabled;revision++;}
  if(enabled){const size=CASE.render?.indoorShadowMapSize===512?512:1024;slot.light.shadow.mapSize.set(size,size);slot.light.shadow.camera.near=.05;slot.light.shadow.camera.far=slot.light.distance;slot.light.shadow.bias=-.0004;slot.light.shadow.normalBias=.018;}
 }
 for(const l of sources)l.visible=false;
 const lightingSignature=[opt.lamps,opt.night,...sources.map(l=>[l.userData.enabled,l.userData.nominalIntensity,l.color.getHex()].join(':'))].join('|');
 if(lightingSignature!==performanceLightingSignature){
  revision++;performanceLightingSignature=lightingSignature;
  for(const slot of performanceSlots){let intensity=0;const color=new Color(0,0,0);
   for(const member of slot.members){const s=member.light;if(!opt.lamps||!s.userData.enabled)continue;const weight=(s.userData.nominalIntensity||0)*(member.main?lightingProfile(opt.night).mainGain:.18);intensity+=weight;color.r+=s.color.r*weight;color.g+=s.color.g*weight;color.b+=s.color.b*weight;}
   slot.light.intensity=Math.min(intensity,LIGHTING_PROFILE.maxGroupIntensity);if(intensity>0)slot.light.color.copy(color.multiplyScalar(1/intensity));
  }
 }
 const profile=lightingProfile(opt.night);
 if(ceilingFill)ceilingFill.intensity=profile.ambient;
 hemi.intensity=profile.hemisphere;

}
return{update:updatePerformanceLighting,setShadows:enabled=>{shadowOverride=!!enabled;revision++;},status:()=>({mode:CASE.render?.performanceLighting===false?'original-fixtures':'fixed-spatial',revision,resolutionMode:'native',shadowSlots:performanceSlots.filter(s=>s.light.castShadow).map(s=>s.source.userData.fixtureId),budget:performanceSlots.length,activeSlots:performanceSlots.filter(s=>s.light.intensity>.025).length,pixelRatio:getRuntime().renderer?.getPixelRatio(),slots:performanceSlots.map(s=>({fixtureId:s.source?.userData.fixtureId,distribution:s.light.userData.omnidirectional?'omnidirectional':'downward',position:s.light.position.toArray(),intensity:s.light.intensity,members:s.members.map(m=>m.light.userData.fixtureId)})),sourceLights:performanceSources.length})};
}
