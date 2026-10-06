// Pure diagnostics; requesting native permission remains in the user's click.
export function pointerLockContext(element,doc,nav,win){return{apiAvailable:typeof element.requestPointerLock==='function',focused:doc.hasFocus(),visibility:doc.visibilityState,userActivation:nav.userActivation?.isActive??null,topLevel:win.top===win};}
export function recordPointerLockFailure(previous,error){
 const detailed=!!error?.name;
 const diagnostic=detailed||!previous?.error?{...previous,error:{name:error?.name||'PointerLockError',message:error?.message||'浏览器报告锁定失败，未提供具体错误。'},failedAt:new Date().toISOString()}:previous;
 const name=diagnostic.error.name;return{diagnostic,reason:name,unavailable:!['WrongDocumentError','InvalidStateError'].includes(name)};
}
