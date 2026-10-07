// Only explicitly declared predecessor revisions of this project may be inspected.
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const copy=v=>v===undefined?undefined:structuredClone(v);
const FIELDS=['id','type','name','cx','cy','w','d','h','rot','elevation','color','fitToCeiling','roomId','mount','basins','mirror','upperCabinet','accessories','assemblyOptions','finishOptions','lightOn','lightIntensity','lightTemperature','tabletopDecor'];
function project(s){const out={};for(const k of ['style','styleCustom','rooms','walls','ceilings','wallFinishes','doorStyles','doors','measures'])if(s[k]!==undefined)out[k]=copy(s[k]);out.furniture=(s.furniture||[]).filter(f=>!f.assemblyOwner).map(f=>Object.fromEntries(FIELDS.filter(k=>f[k]!==undefined).map(k=>[k,copy(f[k])])));return out;}
export function planRevisionMigration(baseline,saved,current){
 const conflicts=[],applied=[];
 function merge(old,user,next,path){
  if(same(old,user))return copy(next);
  if(same(user,next))return copy(next);
  if(same(old,next)){applied.push(path);return copy(user);}
  if(Array.isArray(old)&&Array.isArray(user)&&Array.isArray(next)&&[old,user,next].every(a=>a.every(v=>v&&typeof v.id==='string'))){
   for(const a of [old,user,next])if(new Set(a.map(v=>v.id)).size!==a.length)throw Error('重复对象编号，不能迁移');
   const O=new Map(old.map(v=>[v.id,v])),U=new Map(user.map(v=>[v.id,v])),N=new Map(next.map(v=>[v.id,v]));
   return [...new Set([...N.keys(),...U.keys(),...O.keys()])].map(id=>merge(O.get(id),U.get(id),N.get(id),path+'/'+id)).filter(v=>v!==undefined);
  }
  if(old&&user&&next&&![old,user,next].some(Array.isArray)&&[old,user,next].every(v=>typeof v==='object')){
   const result={};for(const k of new Set([...Object.keys(old),...Object.keys(user),...Object.keys(next)])){const v=merge(old[k],user[k],next[k],path+'/'+k);if(v!==undefined)result[k]=v;}return result;
  }
  conflicts.push({path,previousDefault:copy(old),userEdit:copy(user),newDefault:copy(next)});return copy(next);
 }
 const merged=merge(project(baseline),project(saved),project(current),'scheme'),state=copy(current);
 for(const [key,val]of Object.entries(merged)){
  if(key==='furniture'){const existing=new Map(current.furniture.filter(f=>!f.assemblyOwner).map(f=>[f.id,f]));state.furniture=val.map(f=>({...copy(existing.get(f.id)||{}),...f}));}
  else state[key]=val;
 }
 state.caseId=current.caseId;state.productionApprovals={};
 return {state,applied,conflicts};
}
export function findPreviousScheme(storage,revisions,currentCaseId){
 const found=[],errors=[];
 for(const revision of revisions||[]){if(revision.caseId===currentCaseId)continue;const key='floor-visualization:'+revision.caseId;
  try{const raw=storage.getItem(key);if(!raw)continue;const state=JSON.parse(raw);if(state.caseId!==revision.caseId||!Array.isArray(state.furniture))throw Error('旧版数据编号或家具无效');found.push({key,raw,state,baseline:revision.baseline,savedAt:storage.getItem(key+':saved-at')||'',revision:revision.caseId});}
  catch(e){errors.push({key,message:e.message});}
 }
 found.sort((a,b)=>b.savedAt.localeCompare(a.savedAt));return {candidate:found[0]||null,errors};
}
