import {CASE} from './data.js';
import {roomAreaStatus} from './room-area-status.js';
import {PRESENTATION_PROFILE} from './presentation-profile.js';
// Shared browser/Node contract. Finishes and geometry have separate approval scopes.
export const PRODUCTION_SCHEMA='floor-visualization-production/1.0';
export const canonical=v=>JSON.stringify(v,(_,x)=>x&&typeof x==='object'&&!Array.isArray(x)?Object.fromEntries(Object.keys(x).sort().map(k=>[k,x[k]])):x);
export async function sha256(v){const bytes=new TextEncoder().encode(typeof v==='string'?v:canonical(v));return [...new Uint8Array(await globalThis.crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');}
export function productionScopes(state,model,rooms,preset){
 const furniture=state.furniture.map(({color,finishes,finishSpec,...f})=>f);
 const structure={footprint:model.footprint,height:model.height,rooms:rooms.map(r=>({id:r.id,poly:r.poly})),walls:state.walls};
 const layout={structure,furniture,doorStyles:state.doorStyles||{},ceilings:state.ceilings||[]};
 const style={floorConnections:model.floorConnections||[],materialPresentation:CASE.presentation?.materials||{},layout,wallFinishes:state.wallFinishes||{},style:state.style,custom:!!state.styleCustom,revision:state.styleColorRevision,finishes:preset,rooms:state.rooms,colors:state.furniture.map(f=>({id:f.id,color:f.color}))};
 return {structure,layout,style};
}
export async function scopeHashes(...args){const scopes=productionScopes(...args);return Object.fromEntries(await Promise.all(Object.entries(scopes).map(async([k,v])=>[k,await sha256(v)])));}
export async function productionStatus(state,model,rooms,preset){const hashes=await scopeHashes(state,model,rooms,preset),a=state.productionApprovals||{};return Object.fromEntries(Object.keys(hashes).map(k=>[k,{status:a[k]?.sha256===hashes[k]?'confirmed':a[k]?'stale':'unconfirmed',sha256:hashes[k],approval:a[k]||null}]));}
export async function createProductionBundle(state,model,rooms,preset){
 const clean=structuredClone(state);delete clean.costSettings;delete clean.productionApprovals;
 const status=await productionStatus(state,model,rooms,preset);
 const bundle={schema:PRODUCTION_SCHEMA,createdAt:new Date().toISOString(),units:'mm',coordinates:{plan:'X right, Y down, Z height',three:'X=(planX-width/2)/1000, Y=height/1000, Z=(planY-depth/2)/1000',blender:'X=Three.X, Y=-Three.Z, Z=Three.Y',origin:[model.width/2,model.depth/2]},caseId:state.caseId,model:{title:model.title,width:model.width,depth:model.depth,height:model.height,footprint:model.footprint,rooms:rooms.map(r=>({id:r.id,name:state.rooms[r.id].name,poly:r.poly,at:r.at}))},state:clean,finishes:structuredClone(preset),confirmations:status,limitations:['Dimensions reconstructed from supplied drawings; labelled values remain source evidence and unlabelled parameters require documented design assumptions.','Concept approvals do not certify construction or bearing-wall engineering.']};
 if(model.floorConnections?.length)bundle.model.floorConnections=structuredClone(model.floorConnections);
 // Area provenance is metadata; it does not change geometry or finish approvals.
 if(model.areaEstimate)bundle.areaMetadata=structuredClone(model.areaEstimate);
 bundle.roomGeometryStatus=roomAreaStatus(model.walls||[],state.walls||[]);
 if(bundle.roomGeometryStatus.status!=='source-partitions')bundle.limitations.push(bundle.roomGeometryStatus.message);
 bundle.presentationProfile=structuredClone(PRESENTATION_PROFILE);
 bundle.materialPresentation=structuredClone(CASE.presentation?.materials||{});
 bundle.schemeSha256=await sha256({model:bundle.model,state:bundle.state,finishes:bundle.finishes});return bundle;
}
export function serializeProductionMeshes(roots){
 const meshes=[],materials=[],materialIds=new Map(),textures=[],textureIds=new Map();
 function texture(t){if(!t?.image?.toDataURL)return null;if(!textureIds.has(t.uuid)){textureIds.set(t.uuid,textures.length);textures.push({id:textures.length,dataUrl:t.image.toDataURL('image/png'),repeat:t.repeat.toArray(),wrapS:t.wrapS,wrapT:t.wrapT,colorSpace:t.colorSpace});}return textureIds.get(t.uuid);}
 function material(m){if(!materialIds.has(m.uuid)){materialIds.set(m.uuid,materials.length);materials.push({id:materials.length,colorLinear:m.color?.toArray()||[1,1,1],emissiveLinear:m.emissive?.toArray()||[0,0,0],emissiveIntensity:m.emissiveIntensity||0,roughness:m.roughness??.8,metalness:m.metalness||0,opacity:m.opacity??1,transparent:!!m.transparent,side:m.side,role:m.userData?.finishRole||null,map:texture(m.map),bumpMap:texture(m.bumpMap),bumpScale:m.bumpScale||0});}return materialIds.get(m.uuid);}
 for(const [kind,root]of Object.entries(roots)){root.updateMatrixWorld(true);root.traverse(o=>{if(!o.isMesh)return;const geo=o.geometry,pos=geo.attributes.position;if(!pos)return;meshes.push({name:o.name||`${kind}-${meshes.length}`,kind,objectId:(()=>{for(let a=o;a;a=a.parent){if(a.userData.fid||a.userData.ceilingId||a.userData.room||a.userData.floorConnection)return a.userData.fid||a.userData.ceilingId||a.userData.room||a.userData.floorConnection;}return null;})(),positions:Array.from(pos.array),normals:geo.attributes.normal?Array.from(geo.attributes.normal.array):null,uv:geo.attributes.uv?Array.from(geo.attributes.uv.array):null,indices:geo.index?Array.from(geo.index.array):null,groups:geo.groups,matrix:o.matrixWorld.toArray(),materials:(Array.isArray(o.material)?o.material:[o.material]).map(material),openingKind:(()=>{for(let a=o;a;a=a.parent){if(a.userData.productionOpeningKind)return a.userData.productionOpeningKind;}return null;})(),visible:o.visible&&o.parent?.visible!==false});});}
 return {units:'m',coordinates:'Three.js Y-up',meshes,materials,textures};
}
