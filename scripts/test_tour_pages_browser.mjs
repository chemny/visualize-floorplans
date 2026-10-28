/** Real generated-page regression through an existing CUA Tab adapter.
 * No browser installation, hidden state mutation or user acceptance.
 * Caller opens a fresh generated artifact and supplies its actual node/frame data.
 */
import assert from 'node:assert/strict';
export async function checkRoutePage(tab,{nodeLabel,expectedTime}){
 const before=await tab.playwright.evaluate(()=>({videos:document.querySelectorAll('video').length,frames:document.querySelectorAll('iframe').length,nodes:[...document.querySelectorAll('.chapter')].map(e=>e.textContent)}));
 assert.equal(before.videos,0);assert.equal(before.frames,0);assert.ok(before.nodes[0].includes('开始'));assert.ok(before.nodes.at(-1).includes('结束'));
 await tab.playwright.getByRole('button',{name:nodeLabel,exact:true}).click();await tab.getAXState({emit:false});
 const seek=await tab.playwright.evaluate(()=>Number(document.querySelector('#seek').value));assert.ok(Math.abs(seek-expectedTime)<.001);
 await tab.playwright.getByRole('button',{name:'播放',exact:true}).click();await tab.getAXState({emit:false});await tab.playwright.getByRole('button',{name:'暂停',exact:true}).click();await tab.getAXState({emit:false});
 return{routeOnly:true,startAndEnd:true,nodeSeek:seek,playPause:true};
}
export async function checkMediaPage(tab,{chapterLabel,expectedFrame,expectedPoint,narrated=false}){
 await tab.playwright.getByRole('tab',{name:'房间列表',exact:true}).click();await tab.getAXState({emit:false});
 await tab.playwright.getByRole('button',{name:chapterLabel,exact:true}).click();await tab.getAXState({emit:false});
 const state=await tab.playwright.evaluate(()=>({time:document.querySelector('video').currentTime,frame:Number(document.querySelector('.sync-map').dataset.frame),point:document.querySelector('.sync-map').dataset.point,videoCount:document.querySelectorAll('video').length}));
 assert.equal(state.videoCount,1);assert.equal(state.frame,expectedFrame);assert.equal(state.point,expectedPoint.join(','));
 await tab.playwright.getByRole('tab',{name:'房间列表',exact:true}).click();await tab.getAXState({emit:false});assert.equal(await tab.playwright.getByRole('tab',{name:'房间列表',exact:true}).getAttribute('aria-selected'),'true');
 await tab.playwright.getByRole('tab',{name:'路线图',exact:true}).click();await tab.getAXState({emit:false});assert.equal(await tab.playwright.getByRole('tab',{name:'路线图',exact:true}).getAttribute('aria-selected'),'true');
 if(narrated){await tab.playwright.getByLabel('字幕',{exact:true}).uncheck();await tab.getAXState({emit:false});assert.equal(await tab.playwright.evaluate(()=>document.querySelector('#subtitle').textContent),'');await tab.playwright.getByLabel('字幕',{exact:true}).check();await tab.getAXState({emit:false});await tab.playwright.getByText('查看讲解文稿',{exact:true}).click();await tab.getAXState({emit:false});assert.equal(await tab.playwright.evaluate(()=>document.querySelector('details.script').open),true)}
 return{...state,mapListSwitch:true,narrationControls:narrated?'checked':'not_applicable'};
}

/** Structural UI check shared by all three review stages. */
export async function checkPresentationShell(tab){
 const state=await tab.playwright.evaluate(()=>({navs:document.querySelectorAll('nav.steps').length,items:[...document.querySelectorAll('nav.steps>a')].map(a=>({label:a.textContent,top:a.getBoundingClientRect().top})),frames:document.querySelectorAll('iframe').length,videos:document.querySelectorAll('video').length}));
 assert.equal(state.navs,1);assert.equal(state.items.length,3);assert.equal(state.frames,0);assert.ok(state.videos<=1);assert.ok(state.items.every(x=>Math.abs(x.top-state.items[0].top)<2));return state;
}
export async function checkAuxiliaryPreview(tab){
 const state=await tab.playwright.evaluate(()=>({navs:document.querySelectorAll('nav.steps').length,targets:[...document.querySelectorAll('iframe')].map(e=>e.getAttribute('src'))}));
 assert.equal(state.navs,0);assert.equal(JSON.stringify(state.targets),JSON.stringify(['route-embed.html','runtime/renderer.html']));
 const map=tab.playwright.frameLocator('#plan');assert.equal(await map.locator('nav,button,video,iframe').count(),0);assert.equal(await map.locator('body').getAttribute('data-tour-surface'),'route-map');
 await tab.playwright.getByRole('button',{name:'播放',exact:true}).click();await tab.getAXState({emit:false});await tab.playwright.getByRole('button',{name:'暂停',exact:true}).click();await tab.getAXState({emit:false});
 return {...state,pureMap:true,playPause:true};
}
