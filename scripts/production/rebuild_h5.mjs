#!/usr/bin/env node
// Maintenance only. Users build HTML from the already bundled engine with h5.py.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath,pathToFileURL} from 'node:url';
const args=process.argv.slice(2),arg=k=>args[args.indexOf(k)+1];
if(args.includes('--help')){console.log('node rebuild_h5.mjs --esbuild-module /path/to/esbuild/lib/main.js --node-modules /path/to/node_modules');process.exit(0);}
if(!args.includes('--esbuild-module')||!args.includes('--node-modules'))throw Error('Pass existing esbuild module and node_modules. This command never installs dependencies.');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const hash=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
function sourceInputs(){
 const files=[];
 function visit(dir){for(const entry of fs.readdirSync(dir,{withFileTypes:true})){if(entry.name.startsWith('.')||entry.name==='node_modules')continue;const p=path.join(dir,entry.name);if(entry.isDirectory())visit(p);else if(entry.isFile()&&/\.(js|mjs|css|json)$/.test(entry.name))files.push(p);}}
 visit(path.join(root,'assets/h5/source'));files.push(path.join(root,'assets/h5/version.json'));
 return files.map(p=>({path:path.relative(root,p).split(path.sep).join('/'),sha256:hash(fs.readFileSync(p))})).sort((a,b)=>a.path<b.path?-1:a.path>b.path?1:0);
}
const inputs=sourceInputs();
const {build}=await import(pathToFileURL(path.resolve(arg('--esbuild-module'))).href);
const result=await build({entryPoints:[path.join(root,'assets/h5/source/app.js')],nodePaths:[path.resolve(arg('--node-modules'))],bundle:true,minify:true,format:'iife',write:false,target:'es2020',legalComments:'inline'});
if(JSON.stringify(sourceInputs())!==JSON.stringify(inputs))throw Error('Source changed during compilation; rerun the build. No new provenance written.');
const out=path.join(root,'assets/h5/engine.js');
fs.writeFileSync(out,result.outputFiles[0].text);

// Build-time registry mirrors literal catalog specs without requiring Node at HTML build.
const source=fs.readFileSync(path.join(root,'assets/h5/source/app.js'),'utf8'),dimensions=fs.readFileSync(path.join(root,'assets/h5/source/dimensions-v9.js'),'utf8'),renovation=fs.readFileSync(path.join(root,'assets/h5/source/renovation-components-v12.js'),'utf8');
const types=new Set([...source.matchAll(/\[\s*'([a-z][a-z0-9]+)'\s*,\s*'[^']+'\s*,\s*\d/g),...dimensions.matchAll(/\[\s*'([a-z][a-z0-9]+)'\s*,\s*'[^']+'\s*,\s*\d/g),...renovation.matchAll(/def\('([^']+)'/g)].map(m=>m[1]));
for(const alias of ['sink','basin','hob'])types.add(alias);
fs.writeFileSync(path.join(root,'assets/h5/component-types.json'),JSON.stringify({source:'literal catalog specs, regenerated with engine',types:[...types].sort()},null,2)+'\n');
if(JSON.stringify(sourceInputs())!==JSON.stringify(inputs))throw Error('Source changed during registry build; rerun the build. No new provenance written.');
const provenance={schema:'h5-engine-provenance/1',sourceSha256:hash(inputs.map(row=>row.path+'\0'+row.sha256+'\n').join('')),inputs,engineSha256:hash(fs.readFileSync(out)),registrySha256:hash(fs.readFileSync(path.join(root,'assets/h5/component-types.json'))),compiler:{name:'esbuild',version:(await import(pathToFileURL(path.resolve(arg('--esbuild-module'))).href)).version,options:{bundle:true,minify:true,format:'iife',target:'es2020',legalComments:'inline'}},scope:'Installed source and bundled engine/registry correspondence; not UI, visual or layout acceptance'};
const manifest=path.join(root,'assets/h5/engine.provenance.json');
fs.writeFileSync(manifest+'.partial',JSON.stringify(provenance,null,2)+'\n');fs.renameSync(manifest+'.partial',manifest);
console.log(JSON.stringify({engine:out,bytes:fs.statSync(out).size,provenance:manifest,sourceSha256:provenance.sourceSha256}));
