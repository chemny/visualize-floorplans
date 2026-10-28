// Actual exported triangle visibility without browser, WebGL, screenshots or video.
import fs from 'node:fs';import path from 'node:path';import {pathToFileURL} from 'node:url';import crypto from 'node:crypto';
import {SCREEN_DEFAULTS,inspectScreen} from './tour_screen_quality.mjs';
import {ruleFingerprint} from './preview_gate.mjs';
import {coreInventoryCheck,coreReadability,targetIds} from './tour_core_targets.mjs';
const argv=process.argv.slice(2),arg=k=>argv[argv.indexOf('--'+k)+1],read=p=>JSON.parse(fs.readFileSync(p,'utf8')),hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const runtime=path.resolve(arg('runtime'));
const THREE=await import(pathToFileURL(path.join(runtime,'three.module.js')).href),data=read(path.join(runtime,'scene.json')),bytes=fs.readFileSync(path.join(runtime,'geometry.bin')),buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
const scene=new THREE.Scene(),mats=data.materials.map(m=>new THREE.MeshBasicMaterial({side:m.side,transparent:m.transparent,opacity:m.opacity})),hiddenTypes=new Set(data.presentationProfile?.hiddenTypes||[]),hidden=new Set(data.state.furniture.filter(f=>hiddenTypes.has(f.type)||f.planPoint||f.laundryOwner).map(f=>f.id)),meshes=[];
for(const m of data.meshes){
 if(!m.visible||hidden.has(m.objectId)||/^shower-drain/.test(m.name))continue;
 const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(new Float32Array(buffer,m.positions.offset,m.positions.count),3));
 if(m.indices)g.setIndex(new THREE.BufferAttribute(new Uint32Array(buffer,m.indices.offset,m.indices.count),1));for(const group of m.groups)g.addGroup(group.start,group.count,group.materialIndex);
 const material=m.materials.map(i=>mats[i]),obj=new THREE.Mesh(g,material.length===1?material[0]:material);obj.matrix.fromArray(m.matrix);obj.matrixAutoUpdate=false;obj.userData={objectId:m.objectId,kind:m.kind};scene.add(obj);meshes.push(obj);
}
scene.updateMatrixWorld(true);const opaque=meshes.filter(m=>!(Array.isArray(m.material)?m.material:[m.material]).every(a=>a.transparent)),camera=new THREE.PerspectiveCamera(45,16/9,.04,50),ray=new THREE.Raycaster(),samplesById=new Map();
function samples(id){
 if(samplesById.has(id))return samplesById.get(id);const result=[];
 for(const mesh of meshes.filter(m=>m.userData.objectId===id)){
  const positions=mesh.geometry.getAttribute('position'),ix=mesh.geometry.index,n=(ix?ix.count:positions.count)/3;
  for(let j=0;j<n;j+=Math.max(1,Math.floor(n/12))){const q=new THREE.Vector3();for(let k=0;k<3;k++)q.add(new THREE.Vector3().fromBufferAttribute(positions,ix?ix.getX(j*3+k):j*3+k));result.push(q.multiplyScalar(1/3).applyMatrix4(mesh.matrixWorld));}
 }
 samplesById.set(id,result);return result;
}
function shot(frame,ids){
 camera.fov=THREE.MathUtils.radToDeg(2*Math.atan(Math.tan(THREE.MathUtils.degToRad(frame.horizontalFovDegrees||76)/2)/camera.aspect));camera.position.set((frame.pointMm[0]-data.model.width/2)/1000,frame.eyeMm/1000,(frame.pointMm[1]-data.model.depth/2)/1000);camera.lookAt(camera.position.x+Math.cos(frame.yawRadians),camera.position.y+Math.tan(frame.pitchRadians),camera.position.z+Math.sin(frame.yawRadians));camera.updateProjectionMatrix();camera.projectionMatrix.elements[9]-=frame.shiftY||0;camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();camera.updateMatrixWorld(true);
 const subjects={};
 for(const id of ids){const points=samples(id),visible=[];let frustum=0;
  for(const q of points){const p=q.clone().project(camera);if(p.z< -1||p.z>1||Math.abs(p.x)>1||Math.abs(p.y)>1)continue;frustum++;const d=q.clone().sub(camera.position);ray.set(camera.position,d.clone().normalize());ray.near=.03;ray.far=d.length()+.15;const first=ray.intersectObjects(opaque,false)[0];if(first?.object.userData.objectId===id)visible.push(p);}
  const area=visible.length>1?(Math.max(...visible.map(p=>p.x))-Math.min(...visible.map(p=>p.x)))*(Math.max(...visible.map(p=>p.y))-Math.min(...visible.map(p=>p.y)))/4:0;
  const center=points.length?points.reduce((sum,q)=>sum.add(q),new THREE.Vector3()).multiplyScalar(1/points.length).project(camera):null;
  subjects[id]={totalSamples:points.length,inFrustumSamples:frustum,unoccludedSamples:visible.length,screenAreaFraction:area,screenCenterX:center?.x??null};
 }
 return subjects;
}
function audit(tour,config,out,tourPath,configPath){
if(fs.existsSync(out))throw Error('Fresh mesh evidence output required');
if(data.schemeSha256!==tour.schemeSha256)throw Error('Mesh/tour scheme mismatch');
const marks=Object.fromEntries((tour.stopFrames||tour.visits).map(v=>[v.name,v.frameIndex??v.frame])),policy={sampleHz:4,minContinuousSeconds:.25,minVisibleSamples:2,minVisibleFraction:.03,minScreenAreaFraction:.005,...config.subjectReadabilityPolicy},chapters=[];
const coreInventory=coreInventoryCheck(data,config);
for(const ch of config.chapters){if(ch.phase!=='observe')continue;
 const declared=targetIds(ch),required=coreInventory.rooms.filter(r=>r.chapters.includes(ch.name)).flatMap(r=>r.required.map(f=>f.subjectId));
 const a=marks[ch.from],z=marks[ch.to],ids=[...new Set([...declared,...required])],indices=[];for(let i=a;i<=z;i+=Math.max(1,Math.round(tour.fps/policy.sampleHz)))indices.push(i);if(indices.at(-1)!==z)indices.push(z);
 const rows=indices.map(i=>({frame:i,seconds:i/tour.fps,subjects:shot(tour.frames[i],ids)})),subjects={};
 for(const id of ids){let start=null,longest=0;for(const r of rows){const v=r.subjects[id],ok=v.unoccludedSamples>=policy.minVisibleSamples&&v.unoccludedSamples/Math.max(1,v.totalSamples)>=policy.minVisibleFraction&&v.screenAreaFraction>=policy.minScreenAreaFraction;if(!ok)start=null;else{start??=r.seconds;longest=Math.max(longest,r.seconds-start);}}subjects[id]={longestContinuousSeconds:longest,pass:longest+1e-6>=policy.minContinuousSeconds};}
 // Each shot is responsible for its declared composition; independent room
 // completeness still samples every actual core fixture across the episode.
 // Do not require both complementary shots to repeat the full room inventory.
 const composition=Object.fromEntries(declared.map(id=>[id,subjects[id]]));
 chapters.push({id:ch.name,purpose:ch.viewPurpose,startSeconds:a/tour.fps,endSeconds:z/tour.fps,subjects:composition,pass:declared.every(id=>subjects[id].pass),samples:rows});
 console.log(ch.name,chapters.at(-1).pass?'MESH_VISIBLE':'MESH_NEEDS_REVISION');
}
const coreTargets=coreReadability(data,config,chapters,policy,tour.fps);
const screenPolicy={...SCREEN_DEFAULTS,...config.visualQualityPolicy},rows=[],ids=[...new Set(chapters.flatMap(c=>Object.keys(c.subjects)))];
const screenIndices=[];for(let i=0;i<tour.frames.length;i+=Math.max(1,Math.round(tour.fps/screenPolicy.sampleHz)))screenIndices.push(i);if(screenIndices.at(-1)!==tour.frames.length-1)screenIndices.push(tour.frames.length-1);
for(const i of screenIndices){
 const frame=tour.frames[i],activeIds=[...new Set(chapters.filter(c=>i/tour.fps>=c.startSeconds-3&&i/tour.fps<=c.endSeconds+3).flatMap(c=>Object.keys(c.subjects)))],subjects=shot(frame,activeIds),counts={},focus={};let near=0,blank=0;
 for(const x of [-.8,-.4,0,.4,.8])for(const y of [-.65,0,.65]){
  ray.setFromCamera(new THREE.Vector2(x,y),camera);ray.near=.03;ray.far=50;const hit=ray.intersectObjects(opaque,false)[0];
  if(!hit){blank++;continue;}if(hit.distance<screenPolicy.nearDistanceM)near++;
  const id=hit.object.userData.objectId,kind=hit.object.userData.kind;
  if(hit.distance<screenPolicy.dominantDistanceM){const key=id||kind||'unlabelled-surface';counts[key]=(counts[key]||0)+1;}
  if(id)focus[id]=(focus[id]||0)+1/15;
 }
 const next=tour.frames[Math.min(tour.frames.length-1,i+Math.max(1,Math.round(tour.fps/4)))],dx=next.pointMm[0]-frame.pointMm[0],dy=next.pointMm[1]-frame.pointMm[1];
 const alignment=Math.abs(Math.atan2(Math.sin(Math.atan2(dy,dx)-frame.yawRadians),Math.cos(Math.atan2(dy,dx)-frame.yawRadians)));
 const extra=ids.filter(id=>!activeIds.includes(id)&&(focus[id]||0)>=.13);if(extra.length)Object.assign(subjects,shot(frame,extra));
 const targets=Object.fromEntries(Object.entries(subjects).map(([id,v])=>[id,{visibleFraction:v.screenAreaFraction,inFrameFraction:v.inFrustumSamples/Math.max(1,v.totalSamples),screenCenterX:v.screenCenterX}]));
 const elapsed=Math.max(1/tour.fps,(Math.min(tour.frames.length-1,i+Math.max(1,Math.round(tour.fps/4)))-i)/tour.fps),phase=config.chapters.find(c=>marks[c.from]<=i&&i<marks[c.to])?.phase;
 rows.push({frame:i,seconds:i/tour.fps,yawRadians:frame.yawRadians,phase,walkingForward:Math.hypot(dx,dy)/elapsed>200&&alignment<=Math.PI/2,headingDeviationDegrees:alignment*180/Math.PI,walkingAligned:Math.hypot(dx,dy)>20&&alignment<Math.PI/3,nearFraction:near/15,dominantFraction:Math.max(0,...Object.values(counts))/15,blankFraction:blank/15,focus,targets});
}
const screenQuality=inspectScreen(rows,config,chapters);
screenQuality.issues.push(...coreTargets.issues);if(coreTargets.issues.length)screenQuality.status='needs_revision';
console.log('FULL_TIMELINE_SCREEN',screenQuality.status,screenQuality.issues.length);
fs.writeFileSync(out,JSON.stringify({schema:'floor-visualization-subject-audit/1.0',rulesetVersion:'homeowner-tour-rules/2',ruleFingerprint:ruleFingerprint(),schemeSha256:tour.schemeSha256,tourSha256:hash(tourPath),configSha256:hash(configPath),geometrySha256:hash(path.join(runtime,'geometry.bin')),policy,chapters,coreTargets,screenQuality,status:chapters.every(c=>c.pass)&&screenQuality.status==='pass'?'pass':'fail',actualPlayback:'not_performed',humanAcceptance:'pending',videoGenerated:false,limitations:['Actual triangle visibility and screen rays only; no rendered image or dynamic comfort acceptance']},null,2));

}
if(argv.includes('--batch')){
 const batch=read(arg('batch'));
 if(batch.schema!=='homeowner-mesh-batch/1'||!Array.isArray(batch.jobs)||batch.jobs.length<1||batch.jobs.length>128)throw Error('Bounded mesh batch required');
 for(const job of batch.jobs)audit(read(job.tour),read(job.config),path.resolve(job.out),job.tour,job.config);
}else{
 const tourPath=arg('tour'),configPath=arg('config');
 audit(read(tourPath),read(configPath),path.resolve(arg('out')),tourPath,configPath);
}
