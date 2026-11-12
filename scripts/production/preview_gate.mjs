import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
import {coreReadability,targetIds} from './tour_core_targets.mjs';
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
export const ruleFingerprint=()=>crypto.createHash('sha256').update(read(new URL('./tour_rules_sources.json',import.meta.url)).map(name=>name+':'+hash(new URL('./'+name,import.meta.url))+'\n').join('')).digest('hex');
const canonical=o=>JSON.stringify((function sorted(v){if(Array.isArray(v))return v.map(sorted);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,sorted(v[k])]));return v;})(o));
const sceneIdentity=s=>{const c=structuredClone(s);if(c.renderSettings)delete c.renderSettings.size;return canonical(c);};
export function requirePreview(reviewPath,tourPath,runtime){
 if(!reviewPath)throw Error('Full production/HD capture requires --preview-review; review dynamic preview first');
 const r=read(reviewPath),t=read(tourPath),scene=read(path.join(runtime,'scene.json'));const resolve=a=>path.isAbsolute(a)?a:path.resolve(path.dirname(reviewPath),a);
 if(r.schema!=='homeowner-preview-review/1'||r.status!=='passed'||!r.reviewedBy)throw Error('Passed review with actual reviewer required');
 if(r.approvalSource!=='explicit_user_confirmation'||!String(r.confirmedBy||'').trim()||!String(r.evidence||'').trim())throw Error('Dynamic preview needs explicit user confirmation; an engineering pass or reviewer name is insufficient');
 if(r.tourSha256!==hash(tourPath)||r.schemeSha256!==t.schemeSha256||r.geometrySha256!==hash(path.join(runtime,'geometry.bin'))||r.rendererSha256!==hash(path.join(runtime,'renderer.html')))throw Error('Stale tour/geometry/renderer review');
 const a=r.sceneArtifact;if(!a?.path||hash(resolve(a.path))!==a.sha256||sceneIdentity(read(resolve(a.path)))!==sceneIdentity(scene))throw Error('Preview scene changed; only resolution changes may transfer');
 for(const k of ['turnSamplesViewed','wholePreviewViewed','subjectsReadable','paceComfortable','noBlankCaptureEdges'])if(r.checks?.[k]!==true)throw Error('Preview check missing/failed: '+k);
 for(const k of ['turnSamples','wholePreview','subjectAudit','meshAudit']){
  const a=r.artifacts?.[k];if(!a?.path||!a.sha256||hash(resolve(a.path))!==a.sha256)throw Error('Missing/changed review artifact: '+k);
  if(k.endsWith('Audit')){const d=read(resolve(a.path));if(d.tourSha256!==hash(tourPath)||d.schemeSha256!==t.schemeSha256)throw Error('Stale audit: '+k);if(k==='subjectAudit'&&d.status!=='pass')throw Error('Subject audit failed');if(k==='meshAudit'&&(!d.meshAudit||d.meshAudit.hits?.length||d.errors?.length))throw Error('Mesh audit failed');}
 }
 return r;
}

// Only tests call this. h5_browser exposes no flag or environment switch for it.
let syntheticSpatialFixtures=false;
export function allowSyntheticSpatialFixturesForTests(){syntheticSpatialFixtures=true;}
const NON_SIGNERS=['synthetic','fixture','agent','codex','claude','assistant','自动','代签'];
// Same stage-one chain as tour_stage_chain.require_rehearsal_chain for direct browser capture.
function requireSpatialChain(m,tourPath,refPath){
 const planRef=m.references.spatialPlan,reviewRef=m.references.spatialReview,reportRef=m.references.spatialConformance;
 if(!planRef||!reviewRef||!reportRef)throw Error('Rehearsal has no approved spatial route; confirm the route, then regenerate the camera rehearsal');
 const review=read(refPath(reviewRef)),plan=read(refPath(planRef)),signer=String(review.confirmedBy||'').toLowerCase();
 const source=review.approvalSource,fixture=syntheticSpatialFixtures&&source==='synthetic_test_fixture';
 if(!fixture&&(source!=='explicit_user_confirmation'||NON_SIGNERS.some(word=>signer.includes(word))))throw Error('Explicit spatial route confirmation by the actual user required; agents and fixtures cannot sign');
 if(review.schema!=='homeowner-spatial-approval/1'||review.status!=='approved'||!signer.trim()||!String(review.evidence||'').trim())throw Error('Explicit spatial route confirmation required');
 for(const k of ['orderApproved','pathApproved','necessaryReturnsApproved'])if(review.checks?.[k]!==true)throw Error('Incomplete spatial approval');
 if(review.plan?.sha256!==planRef.sha256||plan.schema!=='homeowner-spatial-plan/1'||plan.status!=='pending_user_confirmation')throw Error('Spatial approval belongs to a different or unresolved plan');
 if(review.bundle?.sha256!==m.references.bundle.sha256||plan.bundle?.sha256!==m.references.bundle.sha256||plan.schemeSha256!==m.schemeSha256)throw Error('Spatial route belongs to a different bundle or scheme');
 const report=read(refPath(reportRef));
 if(report.schema!=='homeowner-spatial-conformance/1'||report.status!=='pass'||report.tourSha256!==hash(tourPath))throw Error('Camera left the approved route or conformance is stale; return to route confirmation');
}

// Route approval precedes every video capture, including small diagnostic ranges.
export function requireRoute(reviewPath,tourPath,runtime){
 return requireRouteEvidence(reviewPath,tourPath,runtime);
}
function requireRouteEvidence(reviewPath,tourPath,runtime,release=null){
 if(!reviewPath)throw Error('Video capture requires --route-review: show and confirm the timed route animation first (including --preview/--range)');
 const r=read(reviewPath),resolve=p=>path.isAbsolute(p)?p:path.resolve(path.dirname(reviewPath),p);
 if(r.schema!=='homeowner-route-approval/1'||r.status!=='approved'||r.approvalSource!=='explicit_user_confirmation'||!String(r.confirmedBy||'').trim()||!String(r.evidence||'').trim())throw Error('Explicit user approval of displayed rehearsal required; text itinerary/internal review is insufficient');
 for(const k of ['animationViewed','pathAndFacingApproved','durationAndRhythmApproved'])if(r.checks?.[k]!==true)throw Error('Route animation/facing/timing approval missing');
 const a=r.rehearsal;if(!a?.path||hash(resolve(a.path))!==a.sha256)throw Error('Rehearsal manifest missing/changed');
 const mp=resolve(a.path),m=read(mp),refPath=a=>path.isAbsolute(a.path)?a.path:path.resolve(path.dirname(mp),a.path);
 if(m.schema!=='homeowner-route-rehearsal/1')throw Error('Invalid rehearsal');
 for(const a of Object.values(m.references))if(hash(refPath(a))!==a.sha256)throw Error('Rehearsal source or displayed animation changed');
 if(m.references.tour.sha256!==hash(tourPath)||m.schemeSha256!==read(tourPath).schemeSha256||m.schemeSha256!==read(path.join(runtime,'scene.json')).schemeSha256)throw Error('Route or scheme changed; show a new animation');
 if(r.presentedAnimationSha256!==m.references.animation.sha256)throw Error('Approval does not identify displayed animation');
 if(m.geometrySha256!==hash(path.join(runtime,'geometry.bin'))||sceneIdentity(read(refPath(m.references.scene)))!==sceneIdentity(read(path.join(runtime,'scene.json'))))throw Error('Runtime geometry/scene changed');
 if(m.timing.overBudget||m.timing.totalSeconds>m.timing.maximumSeconds+1e-6)throw Error('Over-budget route: replan and reconfirm timing');
 const cfg=read(refPath(m.references.config));
 if(!cfg.tourContract)throw Error('Missing tour contract; migrate legacy config and regenerate rehearsal before capture');
 requireSpatialChain(m,tourPath,refPath);
 if(cfg.tourContract){
  const ref=m.references.contractReport;
  if(!ref)throw Error('Tour contract report missing; regenerate rehearsal');
  const report=read(refPath(ref));
  if(report.schema!=='homeowner-tour-contract-report/1'||report.rulesetVersion!=='homeowner-tour-rules/2'||report.ruleFingerprint!==ruleFingerprint()||report.status!=='numeric_pass_visual_pending'||report.issues?.length||report.checks?.cameraEvidence?.schema!=='homeowner-camera-evidence/1'||report.checks?.forwardMotion?.schema!=='homeowner-forward-motion/1'||report.checks.forwardMotion.status!=='pass'||!Array.isArray(report.checks.forwardMotion.issues)||report.checks.forwardMotion.issues.length)throw Error('Tour contract requires revision before capture');
  if(release)for(const [key,value] of Object.entries({tourSha256:hash(tourPath),configSha256:hash(refPath(m.references.config)),bundleSha256:hash(refPath(m.references.bundle)),schemeSha256:m.schemeSha256}))if(report[key]!==value)throw Error('Stale numeric report input: '+key);
 }
 for(const key of ['screenAudit','visualReview']){
  const ref=m.references[key];if(!ref)throw Error('Missing '+key+'; regenerate rehearsal and review');
  const value=read(refPath(ref));if(value.tourSha256!==hash(tourPath)||value.configSha256!==hash(refPath(m.references.config))||value.geometrySha256!==m.geometrySha256||value.ruleFingerprint!==ruleFingerprint())throw Error('Stale '+key);
  if(key==='screenAudit'){
   const core=coreReadability(read(refPath(m.references.bundle)),cfg,value.chapters||[],{sampleHz:4,minVisibleSamples:2,minVisibleFraction:.03,minScreenAreaFraction:.005,...value.policy},read(tourPath).fps);
   if(core.issues.length)throw Error('Actual core facility audit incomplete: '+JSON.stringify(core.issues));
   if(value.rulesetVersion!=='homeowner-tour-rules/2')throw Error('Screen audit rules changed');
   if(release){
    const issues=value.screenQuality?.issues,allowed=release.allowedScreenIssues;
    if(!Array.isArray(issues)||canonical(issues.map(canonical).sort())!==canonical(allowed.map(canonical).sort()))throw Error('Screen issues differ from the exact authorized review list');
    if(value.status!==(issues.length?'fail':'pass')||value.screenQuality.status!==(issues.length?'needs_revision':'pass'))throw Error('Screen audit must retain its actual status');
    if(!Array.isArray(value.chapters)||!value.chapters.length||value.chapters.some(c=>c.pass!==true))throw Error('Review release cannot waive unreadable observation subjects');
    requireActualTargets(cfg,read(tourPath),value);
   }else if(value.status!=='pass'||value.screenQuality?.status!=='pass')throw Error('Screen composition/occlusion requires revision');
  }else {
   const passed=value.result==='pass'&&value.observationMode==='continuous_playback'&&value.reviewedBy?.trim()&&value.evidence?.trim()&&['transitionsNatural','noRepeatedIntroduction','noSustainedObstruction','noUncomfortableTurns'].every(k=>value.checks?.[k]===true);
   if(!passed&&!(release?.allowPendingContinuousReview===true&&value.result==='pending'))throw Error('Actual continuous playback review is pending or failed');
  }
 }
 for(const key of ['roomBudgets','observationPoints','choreography'])if(m.timing[key]?.issues?.length)throw Error('Route '+key+' requires revision before capture');
 if(m.timing.coverage?.status==='needs_revision')throw Error('Room coverage below case minimum');

 return r;
}

// Final production cannot substitute an unrelated passing subject-plan for the route targets.
export function requireTargetAudit(routeReviewPath,previewReviewPath,tourPath){
 const rr=read(routeReviewPath),rp=p=>path.isAbsolute(p)?p:path.resolve(path.dirname(routeReviewPath),p);
 const mp=rp(rr.rehearsal.path),m=read(mp),cp=m.references.config.path,cfg=read(path.isAbsolute(cp)?cp:path.resolve(path.dirname(mp),cp));
 const review=read(previewReviewPath),ap=review.artifacts.subjectAudit.path,audit=read(path.isAbsolute(ap)?ap:path.resolve(path.dirname(previewReviewPath),ap)),tour=read(tourPath);
 return requireActualTargets(cfg,tour,audit);
}
function requireActualTargets(cfg,tour,audit){
 const marks=Object.fromEntries((tour.stopFrames||tour.visits).map(x=>[x.name,x.frameIndex??x.frame])),p=audit.policy||{},minimum=Math.max(.25,p.minContinuousSeconds||0),gap=1.5/Math.max(1,p.sampleHz||2)+1/tour.fps;
 for(const ch of cfg.chapters){
  if(ch.phase!=='observe')continue;
  const ordered=ch.orderedViewTargets||[],ids=targetIds(ch),a=marks[ch.from]/tour.fps,z=marks[ch.to]/tour.fps;let cursor=a;
  for(const id of ids){
   if(!ordered.includes(id))cursor=a;let found=null;
   for(const row of audit.chapters||[]){
    if(row.startSeconds<a-1/tour.fps||row.endSeconds>z+1/tour.fps)continue;
    let start=null,last=null;
    for(const s of row.samples||[]){
     const t=s.seconds,v=s.subjects?.[id]||{},ok=t>=cursor&&t<=z&&(v.unoccludedSamples||0)>=(p.minVisibleSamples??3)&&(v.unoccludedSamples||0)/Math.max(1,v.totalSamples||0)>=(p.minVisibleFraction??.03)&&(v.screenAreaFraction||0)>=(p.minScreenAreaFraction??.01);
     if(!ok){start=last=null;continue;}
     if(start===null||t-last>gap)start=t;last=t;
     if(last-start+1e-6>=minimum){found=last;break;}
    }
    if(found!==null)break;
   }
   if(found===null)throw Error('Actual target audit missing/occluded/out of order: '+id+' / '+ch.name);
   if(ordered.includes(id))cursor=found;
  }
 }
 return true;
}

// Hash-bound authorization for an UNACCEPTED review video only. A retained
// failing screen audit never becomes a passing audit or production acceptance.
export function requireReviewRelease(releasePath,tourPath,runtime,options={}){
 if(!releasePath)throw Error('Review capture requires --review-release');
 if(options.preview!==true||options.full!==true||options.range)throw Error('Review release is only valid for --preview --full capture without --range');
 const r=read(releasePath),base=path.dirname(path.resolve(releasePath));
 if(r.schema!=='homeowner-review-capture-release/2'||r.status!=='authorized_review_capture_only'||r.scope!=='review_video_only'||!String(r.userInstruction||'').trim()||r.authorizedBy!=='explicit_user_confirmation'||!String(r.authorizationEvidence||'').trim())throw Error('Explicit, scoped user instruction and confirmation for review capture required');
 if(r.humanAcceptance!=='pending'||r.productionAccepted!==false)throw Error('Review release cannot grant production/human acceptance');
 if(r.ruleFingerprint!==ruleFingerprint())throw Error('Stale review release engine fingerprint');
 const refs={};
 for(const key of ['routeReview','renderer','clearanceAudit']){
  const ref=r.references?.[key];
  if(!ref||typeof ref.path!=='string'||!/^[0-9a-f]{64}$/.test(ref.sha256||''))throw Error('Missing hash-bound review release reference: '+key);
  const file=path.isAbsolute(ref.path)?ref.path:path.resolve(base,ref.path);
  if(hash(file)!==ref.sha256)throw Error('Changed review release reference: '+key);
  refs[key]=file;
 }
 if(hash(path.join(runtime,'renderer.html'))!==r.references.renderer.sha256)throw Error('Review release renderer changed');
 const scene=read(path.join(runtime,'scene.json')),size=scene.renderSettings?.size;
 if(!Array.isArray(size)||size.length!==2||!size.every(Number.isInteger)||size.some(v=>v<=0)||size[0]>1280||size[1]>720)throw Error('Review release refuses production/HD output; maximum 1280x720');
 const allowed=r.allowedScreenIssues;
 const codes=new Set(['screen_near_surface_occlusion','screen_dominant_surface','screen_blank_segment','transit_reintroduces_subject','approach_view_reverses_into_observation']);
 if(!Array.isArray(allowed)||new Set(allowed.map(canonical)).size!==allowed.length)throw Error('Exact, unique screen issue list required');
 const tour=read(tourPath);
 for(const issue of allowed)if(!codes.has(issue.code)||!Number.isFinite(issue.startSeconds)||!Number.isFinite(issue.endSeconds)||issue.startSeconds<0||issue.startSeconds>issue.endSeconds||issue.endSeconds>tour.seconds)throw Error('Only exact, time-bounded visual issues may be authorized for review');
 const clearance=read(refs.clearanceAudit);
 for(const [key,value] of Object.entries({tourSha256:hash(tourPath),geometrySha256:hash(path.join(runtime,'geometry.bin')),sceneSha256:hash(path.join(runtime,'scene.json')),rendererSha256:hash(path.join(runtime,'renderer.html')),schemeSha256:tour.schemeSha256}))if(clearance[key]!==value)throw Error('Stale clearance audit: '+key);
 if(!Array.isArray(clearance.meshAudit?.hits)||clearance.meshAudit.hits.length||!Array.isArray(clearance.errors)||clearance.errors.length)throw Error('Review release cannot waive actual mesh collisions or capture errors');
 requireRouteEvidence(refs.routeReview,tourPath,runtime,r);
 return {...r,sourceReleasePath:path.resolve(releasePath),sourceReleaseSha256:hash(releasePath)};
}
