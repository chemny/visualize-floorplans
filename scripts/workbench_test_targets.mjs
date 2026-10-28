// Case-independent selectors for isolated browser regressions, not layout rules.
const LIGHTS=new Set(['ceilinground','ceilingsquare','pendant','downlight','tracklight','lightpanel','spotlight','linearlight','ledstrip','walllamp']);
export function chooseTestTargets(state,rooms){
 const room=(rooms||[]).find(r=>r&&typeof r.id==='string'&&state.rooms?.[r.id]);
 if(!room)throw Error('Regression requires one runtime room with saved room state');
 const furniture=(state.furniture||[]).find(f=>f&&typeof f.id==='string'&&!f.assemblyOwner&&!LIGHTS.has(f.type)&&f.mount!=='ceiling')||null;
 return {roomId:room.id,furnitureId:furniture?.id||null,furnitureType:furniture?.type||null};
}
