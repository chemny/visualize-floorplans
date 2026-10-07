// project-service-client/1: optional project service; portable HTML stays independent.
export function mountProjectService({config,button,status,getScheme,validate,notify,onRefresh}) {
  if(!config)return null;
  let revision=config.revision,saved=JSON.stringify(getScheme()),confirmed=config.confirmation,busy=false;
  const confirmButton=document.createElement('button');
  confirmButton.id='confirmProjectScheme';
  confirmButton.className='btn on';confirmButton.textContent='确认并继续';
  button.after(confirmButton);button.title='保存到本地项目文件';
  const when=t=>new Date(t).toLocaleTimeString([],{hour:'2-digit',minute:'2-digit',second:'2-digit'});
  let savedAt=config.savedAt,failed=false;
  function draw(){
    const dirty=JSON.stringify(getScheme())!==saved;
    status.textContent=busy?'保存中…':failed?'保存失败':dirty?'未保存':`${confirmed?'已确认':'已保存'} · ${when(savedAt)}`;
    status.dataset.status=failed?'error':dirty?'ready':'saved';
    status.title=dirty?'当前编辑尚未写入项目文件':`本地项目 · 版本 ${revision} · ${new Date(savedAt).toLocaleString()}`;
    confirmButton.disabled=busy;button.disabled=busy;
  }
  async function post(route,payload){
    const response=await fetch('/api/'+route,{method:'POST',headers:{'Content-Type':'application/json','X-Project-Token':config.token},body:JSON.stringify(payload)});
    const data=await response.json();if(!response.ok)throw Error(data.error||'项目保存失败');return data;
  }
  async function persist(confirm=false){
    if(busy)return false;busy=true;failed=false;draw();
    try{
      const snapshot=validate(structuredClone(getScheme()));
      const data=await post('save',{scheme:snapshot,expectedRevision:revision});
      revision=data.revision;saved=JSON.stringify(snapshot);savedAt=data.savedAt;confirmed=data.confirmation;
      if(confirm){
        if(JSON.stringify(getScheme())!==saved)throw Error('保存期间方案发生变化，请再次确认');
        const accepted=await post('confirm',{expectedRevision:revision,schemeHash:data.schemeHash});
        confirmed=accepted.confirmation;
        notify('已确认当前版本，可继续下一阶段');
      }else notify('已保存到项目');
      return true;
    }catch(error){failed=true;notify(error.message);return false;}
    finally{busy=false;draw();}
  }
  // Capture phase suppresses older browser-only Save click handlers.
  button.addEventListener('click',e=>{e.stopImmediatePropagation();persist();},true);
  confirmButton.onclick=()=>persist(true);
  window.addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='s'){e.preventDefault();e.stopImmediatePropagation();persist();}},true);
  window.addEventListener('beforeunload',e=>{if(JSON.stringify(getScheme())!==saved){e.preventDefault();e.returnValue='';}});
  onRefresh(draw);draw();
  return {save:()=>persist(),confirm:()=>persist(true),refresh:draw,status:()=>({revision,confirmed,busy,dirty:JSON.stringify(getScheme())!==saved})};
}
