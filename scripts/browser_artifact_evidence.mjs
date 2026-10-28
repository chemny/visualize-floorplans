// Bind evidence to the document response actually loaded by Playwright. Never refetch HTML.
import crypto from 'node:crypto';
import fs from 'node:fs';
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const clean=url=>{const u=new URL(url);u.hash='';u.search='';return u.href};
export function verifyDocumentBytes(bytes,manifest,url){
 if(manifest.status!=='built')throw Error('Artifact build manifest is not built: '+url);
 const htmlSha256=hash(bytes);if(htmlSha256!==manifest.htmlSha256)throw Error('Loaded HTML differs from build manifest: '+url);
 for(const key of ['engineSha256','templateSha256','caseSha256'])if(!/^[0-9a-f]{64}$/.test(manifest[key]||''))throw Error('Missing artifact fingerprint '+key);
 const source=bytes.toString('utf8'),scripts=[...source.matchAll(/<script>([\s\S]*?)<\/script>/g)];
 if(!scripts.length)throw Error('Bundled engine script missing');
 const hasEngine=scripts.some(match=>hash(Buffer.from(match[1].replace(/<\\\/script/g,'</script')))===manifest.engineSha256);
 if(!hasEngine)throw Error('Embedded engine differs from build manifest: '+url);
 return {url,htmlSha256,engineSha256:manifest.engineSha256,templateSha256:manifest.templateSha256,caseSha256:manifest.caseSha256,sourceSha256:manifest.engineProvenance?.sourceSha256||null,provenanceManifestSha256:manifest.engineProvenance?.manifestSha256||null,registrySha256:manifest.engineProvenance?.registrySha256||null,identityBasis:'HTML and embedded engine computed from loaded response; template/case/source linked through matching build manifest',workbenchVersion:manifest.workbenchVersion,caseId:manifest.caseId};
}
export function attachArtifactEvidence(page,{expectedUrls=[]}={}){
 const wanted=new Set(expectedUrls.map(clean)),jobs=[],records=[],errors=[];
 page.on('response',response=>{let navigation=false;try{navigation=response.request().isNavigationRequest()&&response.frame()===page.mainFrame()}catch{}if(!navigation||!/^https?:/.test(response.url()))return;if(wanted.size&&!wanted.has(clean(response.url())))return;
 jobs.push((async()=>{if(response.status()!==200)throw Error('Document status '+response.status());const bytes=await response.body();const metadataUrl=new URL(response.url());metadataUrl.search='';metadataUrl.hash='';metadataUrl.pathname=metadataUrl.pathname.replace(/\.html$/,'.build.json');const meta=await page.request.get(metadataUrl.href);if(!meta.ok())throw Error('Build manifest unavailable: '+metadataUrl.href);const receipt=verifyDocumentBytes(bytes,await meta.json(),response.url());records.push(receipt)})().catch(error=>errors.push(String(error.message))));});
 return {async verify(){await Promise.all(jobs);if(errors.length)throw Error(errors.join('; '));if(!records.length)throw Error('No loaded document response captured');for(const url of wanted)if(!records.some(r=>clean(r.url)===url))throw Error('Expected document not loaded: '+url);return {status:'passed',capture:'actual Playwright navigation response body',artifacts:records}},records,errors,get jobCount(){return jobs.length}};
}
export function writeEvidence(path,value){fs.writeFileSync(path,JSON.stringify(value,null,2)+'\n')}
