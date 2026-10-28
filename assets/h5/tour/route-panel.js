// One route panel, two synchronized views. Switching never seeks or pauses media.
export function initRoutePanel(root=document,onChange=()=>{}){
 const tabs=[root.getElementById('routeMapTab'),root.getElementById('roomListTab')],panels=[root.getElementById('routeMapPanel'),root.getElementById('roomListPanel')];
 function select(index,focus=false){tabs.forEach((tab,i)=>{tab.setAttribute('aria-selected',String(i===index));tab.tabIndex=i===index?0:-1;panels[i].hidden=i!==index});if(focus)tabs[index].focus();onChange(index===0?'map':'list')}
 tabs.forEach((tab,i)=>{tab.addEventListener('click',()=>select(i));tab.addEventListener('keydown',event=>{const next=event.key==='Home'?0:event.key==='End'?1:['ArrowLeft','ArrowRight'].includes(event.key)?1-i:null;if(next!==null){event.preventDefault();select(next,true)}})});select(0);return{select};
}
