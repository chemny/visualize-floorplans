// Preserve the last valid snapshot, never replace it with invalid import data.
export function persistScheme(storage,key,state,validate){
 validate(state);const raw=JSON.stringify(state),previous=storage.getItem(key);let backupWarning=null;
 if(previous){let valid=false;try{validate(JSON.parse(previous));valid=true;}catch{}if(valid&&previous!==raw){try{storage.setItem(key+'-backup',previous);}catch(error){backupWarning=error.message;}}}
 storage.setItem(key,raw);if(storage.getItem(key)!==raw)throw Error('写入后读取不一致');return{saved:true,backupWarning};
}
export function decodeScheme(raw,validate){return validate(JSON.parse(raw));}

// Caller supplies a document-scoped cache; a corrupt cache is reported, never silently ignored.
export function restoreScheme(raw,seed,validate){return raw?decodeScheme(raw,validate):seed?validate(seed):null;}

// Escape embedded JSON so user names cannot terminate the export script element.
export function exportSchemeSeed(state,validate){return JSON.stringify(validate(state)).replace(/</g,'\\u003c');}
