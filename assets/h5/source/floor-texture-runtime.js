import {WOOD_FLOOR_TEXTURES} from './wood-floor-textures.js';
// Explicit case finish overrides; no image may silently replace a style palette.
export function selectedFloorTexture(kind,presentation){
 const requested=presentation?.materials?.[kind]?.texture;
 const key=kind==='wood'&&requested==='oak-straight'?'wood':kind==='walnut'&&requested==='walnut-straight'?'walnut':null;
 return key?WOOD_FLOOR_TEXTURES[key]:null;
}
// Keep the existing procedural map visible until the embedded image is decoded.
export function applyEmbeddedFloorTexture(material,fallback,asset,{THREE,maxAnisotropy=1,invalidate=()=>{},tint=null,roughness=null}){
 let retired=false,loaded=null;
 material.userData.floorLayout=asset.layout;
 material.userData.floorTextureStatus='loading';
 material.addEventListener('dispose',()=>{
  retired=true;
  if(loaded){loaded.dispose();loaded=null;}
  else fallback.dispose();
 });
 new THREE.TextureLoader().load(asset.uri,texture=>{
  if(retired){texture.dispose();return;}
  texture.wrapS=texture.wrapT=THREE.RepeatWrapping;
  texture.repeat.set(1/asset.widthMetres,1/asset.depthMetres);
  texture.colorSpace=THREE.SRGBColorSpace;
  texture.anisotropy=Math.min(4,Math.max(1,maxAnisotropy));
  loaded=texture;material.map=texture;material.roughness=roughness??asset.roughness;
  // Reuse the albedo grain while matching the chosen palette; sample once at 32px.
  if(tint){const cv=document.createElement('canvas');cv.width=cv.height=32;const ctx=cv.getContext('2d',{willReadFrequently:true});ctx.drawImage(texture.image,0,0,32,32);const pixels=ctx.getImageData(0,0,32,32).data,avg=[0,0,0];for(let i=0;i<pixels.length;i+=4)for(let k=0;k<3;k++)avg[k]+=pixels[i+k]/255/1024;const src=new THREE.Color().setRGB(...avg,THREE.SRGBColorSpace),target=new THREE.Color(tint);material.color.setRGB(target.r/Math.max(.02,src.r),target.g/Math.max(.02,src.g),target.b/Math.max(.02,src.b));material.userData.styleTint=tint;}

  material.userData.floorTextureStatus='ready';material.needsUpdate=true;
  fallback.dispose();invalidate();
 },undefined,()=>{
  if(retired)return;
  material.userData.floorTextureStatus='fallback';material.userData.textureFallback=true;
  invalidate();
 });
 return material;
}
