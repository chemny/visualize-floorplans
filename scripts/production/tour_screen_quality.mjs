// Screen-space first-hit evidence, shared by offline preflight and regressions.
// Product thresholds are initial review choices, not a human comfort certificate.
export const SCREEN_DEFAULTS={sampleHz:4,nearDistanceM:.9,nearFraction:.6,dominantDistanceM:2,
  dominantFraction:.8,maximumObscuredSeconds:.75,maximumBlankSeconds:.5,
  minimumTargetFraction:.005,maximumTargetFraction:.8,minimumReadableSeconds:.5};
export function inspectScreen(rows,config,chapters){
 const policy={...SCREEN_DEFAULTS,...config.visualQualityPolicy},issues=[],spans=[],approachEvaluations=[],navigationEvaluations=[];
 for(const [k,v] of Object.entries(policy))if(typeof v!=='number'||!Number.isFinite(v)||v<=0)throw Error('Invalid visual quality threshold: '+k);
 const exceptions=config.ruleExceptions||[],ex=(code,ch,subject)=>exceptions.some(e=>e.code===code&&e.reason?.trim()&&(!ch||e.chapter===ch)&&(!subject||e.subjectId===subject));
 const reverseThresholds=new Set(['sampleHz','minimumTargetFraction','minimumReadableSeconds','nearDistanceM','dominantDistanceM']);
 for(const [key,value] of Object.entries(policy))if(key in SCREEN_DEFAULTS&&(reverseThresholds.has(key)?value<SCREEN_DEFAULTS[key]:value>SCREEN_DEFAULTS[key])&&!ex('visual_limit_override'))issues.push({code:'unexplained_visual_limit_override',field:key});
 function runs(predicate){const out=[];let a=null,z=null;for(const r of rows){if(predicate(r)){if(a===null||r.seconds-z>1.5/policy.sampleHz){if(a!==null)out.push([a,z]);a=r.seconds;}z=r.seconds;}else if(a!==null){out.push([a,z]);a=z=null;}}if(a!==null)out.push([a,z]);return out;}
 for(const [code,pred,cap] of [
  ['screen_near_surface_occlusion',r=>r.nearFraction>=policy.nearFraction,policy.maximumObscuredSeconds],
  ['screen_dominant_surface',r=>r.dominantFraction>=policy.dominantFraction,policy.maximumObscuredSeconds],
  ['screen_blank_segment',r=>r.blankFraction>=.9,policy.maximumBlankSeconds]]){
  for(const [a,z] of runs(pred))if(z-a+1/policy.sampleHz>cap+1e-6){spans.push({code,startSeconds:a,endSeconds:z});issues.push({code,startSeconds:a,endSeconds:z});}
 }
 // A first exposure can begin before its named observation window. Chapter
 // boundaries alone do not establish that the viewer is seeing something again.
 const readableTarget=(r,subject)=>{const x=r.targets?.[subject];return x&&x.visibleFraction>=policy.minimumTargetFraction&&x.visibleFraction<=policy.maximumTargetFraction&&x.inFrameFraction>=.35;};
 const continuousEvidence=(selected,predicate)=>{let start=null,last=null,best=0;for(const r of selected){if(predicate(r)){if(start===null||r.seconds-last>1.5/policy.sampleHz)start=r.seconds;last=r.seconds;best=Math.max(best,r.seconds-start);}else start=last=null;}return best;};
 function previouslyIntroduced(subject,seconds){
  // A completed, readable observation is evidence even when the subject remains
  // in frame. A later directed pan can then repeat that presentation.
  if(chapters.some(c=>(c.subjects||{})[subject]&&c.endSeconds<seconds&&continuousEvidence(rows.filter(r=>r.seconds>=c.startSeconds&&r.seconds<=c.endSeconds),r=>readableTarget(r,subject))>=policy.minimumReadableSeconds))return true;
  // Before the first formal observation, require a separate earlier exposure.
  // Continuous, same-direction revealing while approaching is not a repeat;
  // the approach-reversal check below still catches scanning back over it.
  return runs(r=>(r.focus?.[subject]||0)>=.13).some(([a,z])=>{
   if(z>=seconds-.35||z-a<policy.minimumReadableSeconds)return false;
   // Passing an object while looking along the route is incidental, not a
   // presentation. Only an earlier deliberate pan establishes a second episode.
   const local=rows.filter(r=>r.seconds>=a&&r.seconds<=z),directed=local.filter(r=>!r.walkingAligned);
   const sweep=directed.slice(1).reduce((sum,r,i)=>sum+Math.abs(r.yawRadians-directed[i].yawRadians),0)*180/Math.PI;
   return continuousEvidence(local,r=>!r.walkingAligned)>=policy.minimumReadableSeconds&&sweep>=8;
  });
 }
 // A single sampled flash never proves room composition. Enforce both lower and upper size.
 for(const ch of chapters){
  for(const subject of Object.keys(ch.subjects||{})){
   const selected=rows.filter(r=>r.seconds>=ch.startSeconds&&r.seconds<=ch.endSeconds),good=r=>readableTarget(r,subject);
   let start=null,last=null,best=0;for(const r of selected){if(good(r)){if(start===null||r.seconds-last>1.5/policy.sampleHz)start=r.seconds;last=r.seconds;best=Math.max(best,r.seconds-start);}else start=last=null;}
   if(best+1e-6<policy.minimumReadableSeconds&&!ex('detail_view',ch.id,subject))issues.push({code:'subject_composition_unreadable',chapter:ch.id,subjectId:subject,readableSeconds:best});
   // Walking towards a room is allowed, but showing its subject on approach and
   // reversing the camera over it again in the formal window is still a repeat.
   const before=rows.filter(r=>r.seconds>=ch.startSeconds-3&&r.seconds<ch.startSeconds&&(r.focus?.[subject]||0)>=.13);
   if(before.length>=3&&before.at(-1).seconds-before[0].seconds>=.5){
    const local=rows.filter(r=>r.seconds>=before[0].seconds&&r.seconds<=ch.endSeconds&&(r.focus?.[subject]||0)>=.13);let positive=0,negative=0;
    local.slice(1).forEach((r,i)=>{const d=(r.yawRadians-local[i].yawRadians)*180/Math.PI;positive+=Math.max(0,d);negative+=Math.max(0,-d);});
    if(Math.min(positive,negative)>8&&!ex('repeat_subject',ch.id,subject)){
     const context=rows.filter(r=>r.seconds>=before[0].seconds&&r.seconds<=ch.endSeconds),projected=context.filter(r=>readableTarget(r,subject));
     const hasCenters=projected.length>=3&&projected.every(r=>Number.isFinite(r.targets?.[subject]?.screenCenterX));
     let repeated=true,exposures=[],crossings=0;
     if(hasCenters){
      let start=null,last=null;
      for(const r of context){if(readableTarget(r,subject)){if(start===null||r.seconds-last>1.5/policy.sampleHz){if(start!==null&&last-start>=policy.minimumReadableSeconds-1e-6)exposures.push([start,last]);start=r.seconds;}last=r.seconds;}else if(start!==null){if(last-start>=policy.minimumReadableSeconds-1e-6)exposures.push([start,last]);start=last=null;}}
      if(start!==null&&last-start>=policy.minimumReadableSeconds-1e-6)exposures.push([start,last]);
      let side=0,pending=0,count=0;
      for(const r of projected){const x=r.targets[subject].screenCenterX,s=x>.1?1:x<-.1?-1:0;if(!s)continue;if(s===side){pending=0;count=0;continue;}if(s!==pending){pending=s;count=1;}else count++;if(count>=2){if(side)crossings++;side=s;pending=0;count=0;}}
      repeated=exposures.length>=2||crossings>=2;
     }
     approachEvaluations.push({chapter:ch.id,subjectId:subject,projectionAvailable:hasCenters,readableExposureSpans:exposures,centerBandCrossings:crossings,decision:repeated?'repeat_requires_revision':'single_continuous_first_reveal'});
     if(repeated)issues.push({code:'approach_view_reverses_into_observation',chapter:ch.id,subjectId:subject,startSeconds:before[0].seconds,endSeconds:ch.endSeconds});
    }
   }
   // Natural walking and a continuous first approach can show furniture. A
   // directed pan repeats it only after an earlier presentation is established.
   for(const [a,z] of runs(r=>{const v=r.focus?.[subject];return v>=.2&&!r.walkingAligned&&(r.seconds<ch.startSeconds-.35||r.seconds>ch.endSeconds+.35);} )){
    const local=rows.filter(r=>r.seconds>=a&&r.seconds<=z),sweep=local.slice(1).reduce((sum,r,i)=>sum+Math.abs(r.yawRadians-local[i].yawRadians),0)*180/Math.PI;
    if(z-a>=.5&&sweep>=8&&previouslyIntroduced(subject,a)&&!ex('repeat_subject',ch.id,subject)&&!chapters.some(c=>c.id!==ch.id&&c.endSeconds>=a&&c.startSeconds<=z&&(c.subjects||{})[subject])){
     const deviations=local.map(r=>r.headingDeviationDegrees),normalExit=local.every(r=>r.phase==='transit'&&r.walkingForward===true&&Number.isFinite(r.headingDeviationDegrees))&&deviations.at(-1)<=deviations[0]-5&&Math.max(...deviations)<=deviations[0]+5;
     navigationEvaluations.push({subjectId:subject,startSeconds:a,endSeconds:z,decision:normalExit?'forward_exit_aligning_with_path':'directed_reintroduction_requires_revision'});
     if(!normalExit)issues.push({code:'transit_reintroduces_subject',chapter:ch.id,subjectId:subject,startSeconds:a,endSeconds:z});
    }
   }
  }
 }
 return {schema:'homeowner-screen-quality/1',status:issues.length?'needs_revision':'pass',issues,spans,policy,approachEvaluations,navigationEvaluations,samples:rows,actualPlayback:'not_performed',humanAcceptance:'pending',basis:'Actual opaque first-hit screen rays and projected triangle samples on the whole timeline; neither image segmentation nor comfort acceptance.'};
}
