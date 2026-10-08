import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const hash=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8'));
const canonical=o=>JSON.stringify((function sorted(v){if(Array.isArray(v))return v.map(sorted);if(v&&typeof v==='object')return Object.fromEntries(Object.keys(v).sort().map(k=>[k,sorted(v[k])]));return v;})(o));
const sceneIdentity=s=>{const c=structuredClone(s);if(c.renderSettings)delete c.renderSettings.size;return canonical(c);};
export function requirePreview(reviewPath,tourPath,runtime){
 if(!reviewPath)throw Error('Full production/HD capture requires --preview-review; review dynamic preview first');
 const r=read(reviewPath),t=read(tourPath),scene=read(path.join(runtime,'scene.json'));const resolve=a=>path.isAbsolute(a)?a:path.resolve(path.dirname(reviewPath),a);
 if(r.schema!=='homeowner-preview-review/1'||r.status!=='passed'||!r.reviewedBy)throw Error('Passed review with actual reviewer required');
 if(r.tourSha256!==hash(tourPath)||r.schemeSha256!==t.schemeSha256||r.geometrySha256!==hash(path.join(runtime,'geometry.bin'))||r.rendererSha256!==hash(path.join(runtime,'renderer.html')))throw Error('Stale tour/geometry/renderer review');
 const a=r.sceneArtifact;if(!a?.path||hash(resolve(a.path))!==a.sha256||sceneIdentity(read(resolve(a.path)))!==sceneIdentity(scene))throw Error('Preview scene changed; only resolution changes may transfer');
 for(const k of ['turnSamplesViewed','wholePreviewViewed','subjectsReadable','paceComfortable','noBlankCaptureEdges'])if(r.checks?.[k]!==true)throw Error('Preview check missing/failed: '+k);
 for(const k of ['turnSamples','wholePreview','subjectAudit','meshAudit']){
  const a=r.artifacts?.[k];if(!a?.path||!a.sha256||hash(resolve(a.path))!==a.sha256)throw Error('Missing/changed review artifact: '+k);
  if(k.endsWith('Audit')){const d=read(resolve(a.path));if(d.tourSha256!==hash(tourPath)||d.schemeSha256!==t.schemeSha256)throw Error('Stale audit: '+k);if(k==='subjectAudit'&&d.status!=='pass')throw Error('Subject audit failed');if(k==='meshAudit'&&(!d.meshAudit||d.meshAudit.hits?.length||d.errors?.length))throw Error('Mesh audit failed');}
 }
 return r;
}
