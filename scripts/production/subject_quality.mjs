#!/usr/bin/env node
// Geometry-derived time-window probes. These are not a human composition review.
export function validateSubjectPlan(plan,tour,schemeHash,tourHash,objectIds){
 const require=(v,m)=>{if(!v)throw Error(m);};
 require(plan.schema==='floor-visualization-subject-plan/1.0','Unsupported subject plan');
 require(plan.schemeSha256===schemeHash&&plan.tourSha256===tourHash,'Subject plan source/camera revision changed');
 require(Array.isArray(plan.chapters)&&plan.chapters.length>0,'Explicit homeowner chapters required');
 const ids=new Set(),available=new Set(objectIds),policy={sampleHz:2,minContinuousSeconds:2,minVisibleSamples:3,minVisibleFraction:.03,minScreenAreaFraction:.01,maxCloseArchitectureRatio:.6,maxBadCompositionFraction:.25,...plan.policy};
 for(const k of ['sampleHz','minContinuousSeconds','minVisibleSamples','minVisibleFraction','minScreenAreaFraction','maxCloseArchitectureRatio','maxBadCompositionFraction'])require(Number.isFinite(policy[k]),'Finite subject policy required');
 require(policy.sampleHz>=1&&policy.sampleHz<=tour.fps&&policy.minContinuousSeconds>0&&policy.minVisibleSamples>=1,'Invalid time/sample policy');
 for(const k of ['minVisibleFraction','minScreenAreaFraction','maxCloseArchitectureRatio','maxBadCompositionFraction'])require(policy[k]>=0&&policy[k]<=1,'Fraction policy must be 0..1');
 for(const c of plan.chapters){
  require(typeof c.id==='string'&&c.id.trim()&&!ids.has(c.id),'Unique chapter IDs required');ids.add(c.id);
  require(typeof c.purpose==='string'&&c.purpose.trim(),'Chapter functional purpose missing');
  require(Number.isFinite(c.startSeconds)&&Number.isFinite(c.endSeconds)&&c.startSeconds>=0&&c.endSeconds>c.startSeconds&&c.endSeconds<=tour.seconds,'Chapter window outside route');
  require(c.endSeconds-c.startSeconds>=policy.minContinuousSeconds,'Observation window is shorter than readability policy');
  require(Array.isArray(c.subjects)&&c.subjects.length>0&&new Set(c.subjects).size===c.subjects.length&&c.subjects.every(id=>available.has(id)),'Chapter subject is missing from actual scheme');
 }
 return policy;
}

export function sampleIndices(chapter,tour,policy){
 const start=Math.ceil(chapter.startSeconds*tour.fps),end=Math.min(tour.frames.length-1,Math.floor(chapter.endSeconds*tour.fps));
 const step=Math.max(1,Math.floor(tour.fps/policy.sampleHz)),indices=[];
 for(let i=start;i<=end;i+=step)indices.push(i);
 if(indices.at(-1)!==end)indices.push(end);
 return indices;
}

export function summarizeChapter(chapter,samples,policy){
 const subjects={};
 for(const id of chapter.subjects){
  let start=null,last=null,longest=0,qualifying=0;
  for(const s of samples){
   const m=s.subjects[id]||{};
   const ok=m.unoccludedSamples>=policy.minVisibleSamples&&m.unoccludedSamples/Math.max(1,m.totalSamples)>=policy.minVisibleFraction&&m.screenAreaFraction>=policy.minScreenAreaFraction;
   if(ok){if(start===null)start=s.seconds;last=s.seconds;longest=Math.max(longest,last-start);qualifying++;}else{start=last=null;}
  }
  subjects[id]={longestContinuousSeconds:longest,qualifyingSamples:qualifying,pass:longest+1e-6>=policy.minContinuousSeconds};
 }
 const bad=samples.filter(s=>s.composition.closeArchitectureRatio>policy.maxCloseArchitectureRatio).length;
 const badFraction=bad/Math.max(1,samples.length);
 return {id:chapter.id,purpose:chapter.purpose,startSeconds:chapter.startSeconds,endSeconds:chapter.endSeconds,
  subjects,badCompositionFraction:badFraction,pass:Object.values(subjects).every(s=>s.pass)&&badFraction<=policy.maxBadCompositionFraction,samples};
}
