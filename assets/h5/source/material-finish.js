import {DataTexture,RGBAFormat,RepeatWrapping,LinearFilter,LinearMipmapLinearFilter,NoColorSpace} from 'three';
const textures=new Map();
// Shared roughness variation, independent of colour. No external assets or passes.
function variation(kind){
 if(textures.has(kind))return textures.get(kind);
 const n=128,data=new Uint8Array(n*n*4);let seed=1763;
 for(let y=0;y<n;y++)for(let x=0;x<n;x++){
  seed=(Math.imul(seed,1664525)+1013904223)>>>0;
  const pattern=kind==='fabric'?(Math.cos(x*Math.PI/2)+Math.cos(y*Math.PI/2))*3:Math.cos(y*Math.PI/2)*5;
  const value=Math.round(244+pattern+(seed/4294967296-.5)*3),i=(y*n+x)*4;
  data[i]=data[i+1]=data[i+2]=value;data[i+3]=255;
 }
 const texture=new DataTexture(data,n,n,RGBAFormat);texture.colorSpace=NoColorSpace;texture.wrapS=texture.wrapT=RepeatWrapping;texture.magFilter=LinearFilter;texture.minFilter=LinearMipmapLinearFilter;texture.generateMipmaps=true;texture.userData.shared=true;texture.needsUpdate=true;textures.set(kind,texture);return texture;
}
const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,Number.isFinite(v)?v:lo));
export function finishMaterial(m,kind='plain'){
 if(!m?.isMeshStandardMaterial||m.transparent||m.emissive?.getHex())return m;
 const role=m.userData.finishRole||'';
 const fabric=kind==='fabric'||kind==='rug'||['upholstery','textile','bedHead','bedRunner','cushion','rug-binding'].includes(role);
 if(fabric){
  m.metalness=0;m.roughness=clamp(m.roughness,.84,.94);m.envMapIntensity=.16;m.roughnessMap=variation('fabric');
  if(m.bumpMap)m.bumpScale=kind==='rug'?.0012:.00065;
 }else if(role==='appliance-metal'||kind==='metal'||role==='metal'){
  m.metalness=role==='appliance-metal'?.82:.76;m.roughness=role==='appliance-metal'?.34:clamp(m.roughness,.27,.38);m.roughnessMap=variation('metal');m.envMapIntensity=role==='appliance-metal'?.55:.60;
 }else if(role==='cabinet'||kind==='lacquer'||m.userData.furnitureSurface==='satin-lacquer'){
  m.metalness=0;m.roughness=clamp(m.roughness,.32,.42);m.envMapIntensity=.30;
  if(m.isMeshPhysicalMaterial){m.clearcoat=.16;m.clearcoatRoughness=.38;}
 }else if(role==='stone'||kind==='stone'){
  m.metalness=0;m.roughness=clamp(m.roughness,.26,.36);m.envMapIntensity=.30;
  if(m.isMeshPhysicalMaterial){m.clearcoat=.10;m.clearcoatRoughness=.32;}
 }else if(role==='ceramic'){
  m.metalness=0;m.roughness=.23;m.envMapIntensity=.30;
  if(m.isMeshPhysicalMaterial){m.clearcoat=.22;m.clearcoatRoughness=.25;}
 }
 m.userData.materialFinishRevision='restrained-surfaces/1';return m;
}
