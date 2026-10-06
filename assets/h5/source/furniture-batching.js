// Combine only plain opaque static leaves inside ONE furniture ID. Picking,
// dimensions and export keep the same owner and exact transformed surfaces.
import {Mesh,Matrix4} from 'three';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
export function batchFurniture(root){
 root.updateMatrixWorld(true);const buckets=new Map();
 root.traverse(mesh=>{
  if(!mesh.isMesh||mesh.isSkinnedMesh||mesh.isInstancedMesh||Array.isArray(mesh.material)||mesh.material.transparent||mesh.children.length||Object.keys(mesh.userData).some(k=>k!=='detailPart'))return;
  let owner=root;for(let p=mesh.parent;p&&p!==root;p=p.parent){if(p.userData.bodyForDimensions!==undefined)owner=p;if(Object.keys(p.userData).some(k=>!['bodyForDimensions','detailRevision','fullRevision','furniture'].includes(k)))return;}
  const key=[owner.uuid,mesh.material.uuid,mesh.castShadow,mesh.receiveShadow,mesh.visible,mesh.renderOrder].join(':');
  if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push({mesh,owner});
 });
 let removed=0,batches=0;
 for(const entries of buckets.values()){
  const meshes=entries.map(e=>e.mesh),owner=entries[0].owner,inverse=new Matrix4().copy(owner.matrixWorld).invert();
  if(meshes.length<2)continue;
  const copies=meshes.map(mesh=>{const g=mesh.geometry.index?mesh.geometry.toNonIndexed():mesh.geometry.clone();g.clearGroups();g.applyMatrix4(new Matrix4().multiplyMatrices(inverse,mesh.matrixWorld));return g;});
  // A failed merge leaves the source meshes untouched.
  let geometry;try{geometry=mergeGeometries(copies,false);}finally{copies.forEach(g=>g.dispose());}
  if(!geometry)continue;geometry.computeBoundingBox();geometry.computeBoundingSphere();
  const first=meshes[0],batch=new Mesh(geometry,first.material);batch.castShadow=first.castShadow;batch.receiveShadow=first.receiveShadow;batch.visible=first.visible;batch.renderOrder=first.renderOrder;batch.name='static-furniture-batch';
  batch.userData.staticBatch=true;batch.userData.sourceMeshCount=meshes.length;batch.userData.sourceParts=meshes.map(m=>m.name);owner.add(batch);
  const disposed=new Set();for(const mesh of meshes){mesh.removeFromParent();if(!disposed.has(mesh.geometry)){disposed.add(mesh.geometry);mesh.geometry.dispose();}}
  removed+=meshes.length-1;batches++;
 }
 return{savedDrawCalls:removed,batches};
}
