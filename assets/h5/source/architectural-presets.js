// Architectural components attach to real wall openings; never standalone furniture.
export const ARCHITECTURAL_PRESETS=[
 {id:'hinged',label:'单扇平开门',kind:'door',model:'single',width:900,panelFinish:'solid'},
 {id:'wallslide',label:'单扇侧滑门',kind:'sliding',model:'sliding',width:800,leaves:1,slideMount:'wall',slideSide:-1,slideOverlap:20,panelFinish:'solid'},
 {id:'sliding',label:'双扇推拉门',kind:'sliding',model:'sliding',width:1600,leaves:2,panelFinish:'clear'},
 {id:'window',label:'普通窗洞',kind:'window',width:1200,height:1350,sillHeight:850},
 {id:'passage',label:'开放口',kind:'door',model:'single',width:900,leafRemoved:true},
 {id:'double',label:'对开门',kind:'door',model:'double',width:1400,leafRatio:.5,panelFinish:'solid',optional:true},
 {id:'hidden',label:'隐藏门',kind:'door',model:'hidden',width:900,panelFinish:'solid',optional:true},
 {id:'security',label:'防盗门',kind:'door',model:'security',width:1000,panelFinish:'solid'}
];
export const PANEL_FINISHES=[['solid','实心'],['clear','透明'],['frosted','磨砂']];
export function presetOpening(preset,existing={}){
 if(!preset)throw Error('未知门窗预设');
 const result={...existing,kind:preset.kind,label:preset.label,width:existing.width??preset.width,height:existing.height??preset.height??2100};
 if(preset.kind==='window'){result.sillHeight=existing.sillHeight??preset.sillHeight;return result;}
 Object.assign(result,{doorModel:preset.model,hingeEnd:existing.hingeEnd||'start',swing:existing.swing||1,angle:existing.angle??90,leafRemoved:!!preset.leafRemoved});
 if(preset.panelFinish)result.panelFinish=preset.panelFinish;
 if(preset.kind==='sliding')Object.assign(result,{leaves:preset.leaves,slideDirection:existing.slideDirection??1,slideOpen:existing.slideOpen??0,...(preset.leaves===1?{slideMount:'wall',slideSide:existing.slideSide??-1,slideOverlap:existing.slideOverlap??20}:{})});
 if(preset.model==='double')result.leafRatio=existing.leafRatio??.5;
 return result;
}
export function openingPresetId(o){return o.kind==='window'?'window':o.leafRemoved?'passage':o.kind==='sliding'?(o.leaves===1?'wallslide':'sliding'):o.doorModel==='double'?'double':o.doorModel==='hidden'?'hidden':o.doorModel==='security'?'security':'hinged';}
