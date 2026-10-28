// No browser/network/dependency installation: test embedded assets and loader lifecycle.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {applyEmbeddedFloorTexture,selectedFloorTexture} from '../assets/h5/source/floor-texture-runtime.js';
import {WOOD_FLOOR_TEXTURES} from '../assets/h5/source/wood-floor-textures.js';
let requests=[],invalidations=0;
const THREE={RepeatWrapping:1000,SRGBColorSpace:'srgb',TextureLoader:class{load(uri,ok,progress,fail){requests.push({uri,ok,fail});}}};
const texture=()=>({disposed:0,repeat:{set(x,y){this.x=x;this.y=y;}},dispose(){this.disposed++;}});
function setup(asset=WOOD_FLOOR_TEXTURES.wood){
 const fallback=texture(),handlers={},material={map:fallback,roughness:.5,userData:{},addEventListener(k,fn){handlers[k]=fn;}};
 applyEmbeddedFloorTexture(material,fallback,asset,{THREE,maxAnisotropy:16,invalidate(){invalidations++;}});
 return {material,fallback,retire:()=>handlers.dispose(),request:requests.at(-1)};
}
for(const kind of ['wood','walnut','marble','tile800']){
 assert.equal(selectedFloorTexture(kind),null);
 assert.equal(selectedFloorTexture(kind,{materials:{[kind]:{texture:'unknown'}}}),null);
 assert.equal(selectedFloorTexture(kind,{materials:{[kind]:{texture:'procedural'}}}),null);
}
assert.equal(selectedFloorTexture('wood',{materials:{wood:{texture:'oak-straight'}}}),WOOD_FLOOR_TEXTURES.wood);
assert.equal(selectedFloorTexture('walnut',{materials:{walnut:{texture:'walnut-straight'}}}),WOOD_FLOOR_TEXTURES.walnut);
assert.equal(selectedFloorTexture('marble',{materials:{marble:{texture:'oak-straight'}}}),null);
let bytes=0;
for(const asset of Object.values(WOOD_FLOOR_TEXTURES)){
 assert(asset.uri.startsWith('data:image/jpeg;base64,'));
 const image=Buffer.from(asset.uri.split(',')[1],'base64');assert.equal(image.readUInt16BE(0),0xffd8);bytes+=image.length;
 assert.equal(asset.layout,'parallel-straight');assert(asset.widthMetres>0&&asset.depthMetres>0);
}
assert(bytes<1_000_000,'Both compressed JPEGs should stay below 1 MB combined');
const a=setup(),loaded=texture();assert.equal(a.material.map,a.fallback);a.request.ok(loaded);
assert.equal(a.material.map,loaded);assert.equal(loaded.repeat.x,1/2.4);assert.equal(loaded.repeat.y,1/1.08);
assert.equal(loaded.colorSpace,'srgb');assert.equal(loaded.anisotropy,4);assert.equal(a.fallback.disposed,1);
assert.equal(a.material.roughness,.68);assert.equal(a.material.userData.floorTextureStatus,'ready');assert.equal(invalidations,1);
a.retire();assert.equal(loaded.disposed,1);
const b=setup();b.request.fail();assert.equal(b.material.map,b.fallback);assert.equal(b.material.roughness,.5);
assert.equal(b.material.userData.textureFallback,true);b.retire();assert.equal(b.fallback.disposed,1);
const c=setup();c.retire();const late=texture(),before=invalidations;c.request.ok(late);
assert.equal(late.disposed,1);assert.equal(invalidations,before);assert.equal(c.fallback.disposed,1);
const d=setup(WOOD_FLOOR_TEXTURES.walnut);d.retire();d.request.fail();assert.equal(d.material.userData.textureFallback,undefined);
const app=fs.readFileSync(new URL('../assets/h5/source/app.js',import.meta.url),'utf8');
assert.match(app,/selectedFloorTexture\(kind,CASE\.presentation\)/);
assert.match(app,/if \(floorMats\[key\]\) return floorMats\[key\]/);
console.log(JSON.stringify({status:'passed',embeddedJpegBytes:bytes,scope:'Explicit finish selection, default/style fallback, physical UV, sRGB, shared material cache contract, load success/failure and disposal lifecycle; not browser visual/FPS acceptance'}));
