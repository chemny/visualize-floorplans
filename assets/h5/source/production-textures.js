// Lossless production transport for Canvas, decoded Image and ImageBitmap textures.
export function serializeTextureImage(t){
 if(!t)return null;
 const im=t.image,w=im?.naturalWidth||im?.videoWidth||im?.width,h=im?.naturalHeight||im?.videoHeight||im?.height;
 if(!im||!w||!h||im.complete===false)throw Error('Production texture is not decoded: '+(t.name||t.uuid));
 let dataUrl;
 try{if(typeof im.toDataURL==='function')dataUrl=im.toDataURL('image/png');else{const canvas=document.createElement('canvas');canvas.width=w;canvas.height=h;canvas.getContext('2d').drawImage(im,0,0);dataUrl=canvas.toDataURL('image/png');}}
 catch(e){throw Error('Production texture cannot be exported: '+e.message);}
 return {dataUrl,repeat:t.repeat.toArray(),offset:t.offset.toArray(),center:t.center.toArray(),rotation:t.rotation,flipY:t.flipY,wrapS:t.wrapS,wrapT:t.wrapT,colorSpace:t.colorSpace};
}
export async function waitForProductionTextures(roots,{timeoutMs=10000}={}){
 const start=performance.now();
 for(;;){const materials=new Set();for(const root of Object.values(roots))root.traverse(o=>{for(const m of (Array.isArray(o.material)?o.material:[o.material]))if(m)materials.add(m);});
 if([...materials].some(m=>m.userData?.floorTextureStatus==='fallback'))throw Error('Required floor image failed to load; retry export after fixing the asset');
 if(![...materials].some(m=>m.userData?.floorTextureStatus==='loading'))return;
 if(performance.now()-start>timeoutMs)throw Error('Timed out waiting for production floor textures');
 await new Promise(r=>setTimeout(r,25));}
}
