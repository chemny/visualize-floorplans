#!/usr/bin/env node
import {createRequire} from 'node:module';
const args=Object.fromEntries(process.argv.slice(2).reduce((rows,v,i,all)=>i%2===0?[...rows,[v.replace(/^--/,''),all[i+1]]]:rows,[]));
for(const key of ['playwright-module','browser','fixture-dir','url'])if(!args[key])throw Error('Missing --'+key);
if(!/^http:\/\/127\.0\.0\.1:\d+\/workbench$/.test(args.url))throw Error('Use independent synthetic loopback fixture only');
const {chromium}=createRequire(import.meta.url)(args['playwright-module']);
import fs from 'node:fs';
import assert from 'node:assert/strict';
const root=args['fixture-dir'];
const url=args.url;
const browser=await chromium.launch({executablePath:args.browser,headless:true});
const ctx=await browser.newContext({viewport:{width:1440,height:900}});
const a=await ctx.newPage(),b=await ctx.newPage();const errors=[];
a.on('pageerror',e=>errors.push(e.message));b.on('pageerror',e=>errors.push(e.message));
const current=()=>JSON.parse(fs.readFileSync(root+'/project/scheme-current.json','utf8'));
async function open(p){await p.goto(url);await p.waitForFunction(()=>window.homeStudio?.projectStatus);}
async function edit(p,cx){await p.evaluate(cx=>{const s=JSON.parse(homeStudio.serializeScheme());s.furniture.find(f=>f.id==='desk').cx=cx;homeStudio.importScheme(JSON.stringify(s));},cx);}
try{
 await open(a);await open(b);const v=current().revision;
 await edit(a,1450);assert.match(await a.locator('#savedState').innerText(),/未保存/);
 await a.locator('#saveScheme').click();await a.waitForFunction(()=>!homeStudio.projectStatus().busy);
 assert.equal(current().scheme.furniture.find(f=>f.id==='desk').cx,1450);
 assert.equal(current().revision,v+1);
 await a.reload();await a.waitForFunction(()=>window.homeStudio?.projectStatus);
 assert.equal(await a.evaluate(()=>JSON.parse(homeStudio.serializeScheme()).furniture.find(f=>f.id==='desk').cx),1450);
 await a.locator('#confirmProjectScheme').click();await a.waitForFunction(()=>!homeStudio.projectStatus().busy);
 assert.equal(current().confirmation?.revision,current().revision);
 await edit(a,1550);await a.locator('#saveScheme').click();await a.waitForFunction(()=>!homeStudio.projectStatus().busy);assert.equal(current().confirmation,null);
 await edit(b,1650);await b.locator('#saveScheme').click();await b.waitForFunction(()=>!homeStudio.projectStatus().busy);
 assert.match(await b.locator('#savedState').innerText(),/保存失败/);assert.equal(current().scheme.furniture.find(f=>f.id==='desk').cx,1550);
 await a.locator('#confirmProjectScheme').click();await a.waitForFunction(()=>!homeStudio.projectStatus().busy);assert.ok(current().confirmation);
 const downloadPromise=a.waitForEvent('download');await a.locator('#saveHtml').evaluate(el=>el.click());const download=await downloadPromise;await download.saveAs(root+'/portable.html');
 const portable=fs.readFileSync(root+'/portable.html','utf8');assert.ok(!portable.includes('id="projectServiceConfig"'));assert.ok(!/<button[^>]*id="confirmProjectScheme"/.test(portable));assert.ok(!portable.includes(await a.evaluate(()=>PROJECT_IO.token)));
 await a.screenshot({path:root+'/project-save-confirm.png',fullPage:true});assert.deepEqual(errors,[]);
 fs.writeFileSync(root+'/browser-result.json',JSON.stringify({passed:true,checks:['UI dirty indicator','save to disk','reload latest state','confirm exact version','edit invalidates confirmation','stale second tab conflict','portable export strips service token'],pageErrors:errors,scope:'synthetic fixture; no user browser state read'},null,2));
 console.log('PASS: seven project-service browser checks');
}finally{await browser.close();}
