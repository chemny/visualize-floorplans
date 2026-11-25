// Independent scene inventory; shared catalog, no camera-list-derived requirements.
import fs from 'node:fs';
export const coreSpec=JSON.parse(fs.readFileSync(new URL('../../assets/h5/tour/core-functions.json',import.meta.url),'utf8'));
export const targetIds=ch=>[...new Set([...(ch.orderedViewTargets||[]),...(ch.subjects||[])])];
const inside=(p,poly)=>{let v=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const a=poly[i],b=poly[j];if((a[1]>p[1])!==(b[1]>p[1])&&p[0]<(b[0]-a[0])*(p[1]-a[1])/(b[1]-a[1])+a[0])v=!v;}return v;};
export function inventory(bundle){
 const rooms=bundle.model?.rooms||[],out={};
 for(const f of bundle.state?.furniture||[]){const fn=coreSpec.types[f.type];if(!fn||f.assemblyOwner||f.planPoint||f.demolished)continue;
  const matches=rooms.filter(r=>inside([f.cx,f.cy],r.poly)).map(r=>r.id),room=matches.includes(f.roomId)?f.roomId:matches[0];
  if(room!==undefined)(out[room]??=[]).push({subjectId:f.id,type:f.type,function:fn});
 }
 for(const v of Object.values(out))v.sort((a,b)=>a.subjectId<b.subjectId?-1:a.subjectId>b.subjectId?1:0);return out;
}
export function firstEpisodes(config){
 const out={},closed=new Set();let previous=[];
 for(const ch of config.chapters||[]){if(ch.phase!=='observe')continue;const rooms=[...new Set([ch.roomId,...(ch.coveredRoomIds||[])].filter(r=>r!=null))];
  previous.filter(r=>!rooms.includes(r)).forEach(r=>closed.add(r));for(const room of rooms)if(!closed.has(room))(out[room]??=[]).push(ch);previous=rooms;
 }return out;
}
export function declaredIntroductions(config){
 const reason=config.tourContract?.singleEpisodeExceptionReason;
 return config.roomViewingPolicy?.singleEpisode===false&&typeof reason==='string'&&reason.trim().length>0;
}
export function introductionEpisodes(config){
 const out={},active=new Map();
 for(const ch of config.chapters||[]){if(ch.phase!=='observe')continue;
  const rooms=[...new Set([ch.roomId,...(ch.coveredRoomIds||[])].filter(r=>r!=null))];
  for(const room of active.keys())if(!rooms.includes(room))active.delete(room);
  for(const room of rooms){const token=ch.episodeId??null;
   if(!active.has(room)||active.get(room).token!==token){const episode=[];(out[room]??=[]).push(episode);active.set(room,{token,episode});}
   active.get(room).episode.push(ch);
  }
 }return out;
}
export function coreInventoryCheck(bundle,config){
 const excused=new Set((config.coreTargetPolicy?.excludedRooms||[]).filter(r=>r&&typeof r.reason==='string'&&r.reason.trim()).map(r=>r.roomId)),actual=inventory(bundle),rows=[],issues=[],separate=declaredIntroductions(config),episodes=separate?introductionEpisodes(config):Object.fromEntries(Object.entries(firstEpisodes(config)).map(([room,chs])=>[room,[chs]]));
 for(const [room,roomEpisodes] of Object.entries(episodes)){const chs=roomEpisodes.flat(),required=excused.has(room)?[]:(actual[room]||[]),declared=new Set(chs.flatMap(targetIds)),missing=required.filter(f=>!declared.has(f.subjectId)).map(f=>f.subjectId),subjectChapters={};
  for(const f of required){const episode=separate?(roomEpisodes.find(episode=>episode.some(ch=>targetIds(ch).includes(f.subjectId)))||[]):roomEpisodes[0];subjectChapters[f.subjectId]=episode.map(ch=>ch.name);}
  rows.push({roomId:room,required,chapters:chs.map(ch=>ch.name),subjectChapters,missingTargets:missing});for(const subjectId of missing)issues.push({code:'missing_core_view_target',roomId:room,subjectId});
 }return {schema:'homeowner-core-targets/1',status:issues.length?'needs_revision':'pass',rooms:rows,minimumReadableSeconds:coreSpec.minimumReadableSeconds,issues};
}
export function coreReadability(bundle,config,chapters,policy,fps){
 const report=coreInventoryCheck(bundle,config),gap=1.5/Math.max(1,policy.sampleHz)+1/fps,rows=[],issues=[...report.issues];
 for(const row of report.rooms){
  for(const f of row.required){let start=null,last=null,longest=0;
   const permitted=row.subjectChapters[f.subjectId],samples=chapters.filter(ch=>permitted.includes(ch.id)).flatMap(ch=>ch.samples||[]).sort((a,b)=>a.seconds-b.seconds);
   for(const s of samples){const v=s.subjects?.[f.subjectId]||{},ok=(v.unoccludedSamples||0)>=policy.minVisibleSamples&&(v.unoccludedSamples||0)/Math.max(1,v.totalSamples||0)>=policy.minVisibleFraction&&(v.screenAreaFraction||0)>=policy.minScreenAreaFraction;
    if(!ok){start=last=null;continue;}if(start===null||s.seconds-last>gap)start=s.seconds;last=s.seconds;longest=Math.max(longest,last-start);
   }
   const pass=longest+1e-6>=coreSpec.minimumReadableSeconds;rows.push({roomId:row.roomId,subjectId:f.subjectId,chapters:permitted,longestContinuousSeconds:longest,pass});
   if(!pass)issues.push({code:'core_facility_unreadable',roomId:row.roomId,subjectId:f.subjectId});
  }
 }return {...report,status:issues.length?'needs_revision':'pass',readability:rows,issues};
}
