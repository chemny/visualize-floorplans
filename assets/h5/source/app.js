import {LIGHTING_PROFILE,lightingProfile} from './lighting-profile.js';
import {horizontalContours,contourRegions} from './section-view.js';
import {furnitureBlocksPoint} from './walk-collision.js';
import {batchFurniture} from './furniture-batching.js';
import {WORKBENCH_VERSION} from './version.js';
import {createLightingRuntime} from './lighting-runtime.js';
import {sceneLabelPoint as chooseSceneLabelPoint} from './room-labels.js';
import {roomAreaStatus} from './room-area-status.js';
import {marbleVeinSVG,paintMarbleVeins} from './material-presentation.js';
import {persistScheme,decodeScheme,restoreScheme} from './scheme-storage.js';
import {pointerLockContext,recordPointerLockFailure} from './pointer-lock-diagnostics.js';
import {PRESENTATION_PROFILE} from './presentation-profile.js';
import {RENOVATION_SPECS,RENOVATION_MAP,TOP_TYPES,LIT_TYPES,renovationModel,renovationSymbol} from './renovation-components-v12.js';
import {wholeHomeFurniture,FULL_REVISION,FULL_TYPES} from './furniture-detail-v11.js';
import {refinedFurniture,DETAIL_REVISION} from './soft-furniture-v10.js';
import {DIMENSIONS,NEW_COMPONENTS,WALL_FINISHES,validateDimensions} from './dimensions-v9.js';
import {material as surfaceMaterial} from './enhancements.js';

import {canonical,productionScopes,productionStatus,createProductionBundle,serializeProductionMeshes} from './production-contract.js';import {CASE,DEFAULT,CHAINS,CHAIN_STARTS,FOOTPRINT} from './data.js';
import {intervals,wallRect,doorPose,wallPrisms,unionWalls,solidPlanPath,planOutline} from './walls.js';
import {furniture as detailedFurniture} from './enhancements.js';
import {STYLE_PRESETS,getStyle,styleFurnitureColor,styleFloorFinish,styleRoomMaterial} from './styles-v8.js';

/* ======================= 多语言（中文 / English，默认中文） ======================= */
const LANG_KEY = 'floor-visualization-language';
let LANG = (() => { try { return localStorage.getItem(LANG_KEY) === 'en' ? 'en' : 'zh'; } catch(e) { return 'zh'; } })();
const tr = (zh, en) => LANG === 'en' ? en : zh;
// 内置的房间 / 材料 / 家具名称存的是中文；英文界面下显示译名，用户自己改过的名称原样显示
const NAMES_EN = {
  '主卧室':'Master Bedroom', '主卫浴':'Master Bath', '小孩房':"Kids' Room", '客卫浴':'Guest Bath', '洗衣阳台':'Laundry Balcony',
  '子女房':"Children's Room", '厨房':'Kitchen', '餐厅':'Dining', '过道':'Hallway', '客厅':'Living Room', '休闲阳台':'Leisure Balcony',
  '主卧飘窗':'Master Bay Window', '子女房飘窗':"Children's Bay Window",
  '橡木地板':'Oak Flooring', '胡桃木地板':'Walnut Flooring', '800 地砖':'800 Tile', '600 地砖':'600 Tile', '大理石':'Marble',
  '300 防滑砖':'300 Anti-slip Tile', '水磨石':'Terrazzo', '满铺地毯':'Wall-to-wall Carpet',
  '卧室':'Bedroom', '餐厨':'Dining & Kitchen', '卫浴':'Bathroom', '家电':'Appliances', '书房 · 休闲':'Study & Leisure',
  '双人床 1.8m':'Double Bed 1.8m', '双人床 1.5m':'Double Bed 1.5m', '双人床':'Double Bed', '单人床':'Single Bed', '婴儿床':'Crib',
  '床头柜':'Nightstand', '衣柜':'Wardrobe', '小衣柜':'Small Wardrobe', '梳妆台':'Dresser', '书桌':'Desk', '椅子':'Chair',
  '书架':'Bookshelf', '飘窗垫':'Bay Cushion', '三人沙发':'3-Seat Sofa', '双人沙发':'Loveseat', '转角沙发':'Corner Sofa',
  '单人沙发':'Armchair', '懒人沙发':'Beanbag', '茶几':'Coffee Table', '边几':'Side Table', '电视柜':'TV Stand', '地毯':'Rug',
  '鞋柜':'Shoe Cabinet', '玄关柜':'Entry Cabinet', '落地灯':'Floor Lamp', '绿植':'Plant', '大绿植':'Large Plant',
  '餐桌':'Dining Table', '六人餐桌':'6-Seat Dining Table', '圆桌':'Round Table', '餐椅':'Dining Chair', '岛台':'Kitchen Island',
  '吧椅':'Bar Stool', '橱柜台面':'Kitchen Counter', '燃气灶':'Gas Stove', '水槽':'Sink', '冰箱':'Fridge', '餐边柜':'Sideboard',
  '马桶':'Toilet', '浴室柜':'Vanity', '双盆浴室柜':'Double Vanity', '淋浴房':'Shower', '淋浴区':'Shower Area', '浴缸':'Bathtub',
  '洗衣机':'Washer', '洗衣池':'Laundry Sink', '电热水器':'Water Heater', '储物柜':'Storage Cabinet', '65 寸电视':'65" TV',
  '55 寸电视':'55" TV', '对开门冰箱':'French-door Fridge', '柜机空调':'Floor AC', '挂机空调':'Wall AC', '洗碗机':'Dishwasher',
  '蒸烤箱高柜':'Oven Tower', '烘干机':'Dryer', '空气净化器':'Air Purifier', '长书桌':'Long Desk', '办公椅':'Office Chair',
  '大书架':'Large Bookshelf', '立式钢琴':'Upright Piano', '跑步机':'Treadmill', '阅读椅':'Reading Chair', '茶桌':'Tea Table', '休闲椅':'Lounge Chair',
};
const nm = s => LANG === 'en' ? (NAMES_EN[s] ?? s) : s;
// 静态文案：元素上写 data-en / data-en-title，中文原文首次切换时存进 dataset
function applyStaticLang(){
  document.documentElement.lang = tr('zh-CN', 'en');
  document.title = 'Floor Visualization';
  document.querySelectorAll('[data-en]').forEach(el => { el.dataset.zh ??= el.textContent; el.textContent = tr(el.dataset.zh, el.dataset.en); });
  document.querySelectorAll('[data-en-title]').forEach(el => { el.dataset.zhTitle ??= el.title; el.title = tr(el.dataset.zhTitle, el.dataset.enTitle); });
  document.getElementById('langBtn').textContent = tr('EN', '中文');
}

// 单位 mm；墙体与洞口从本项目确认数据生成，b=原图黑填保护墙，n=可编辑隔墙。
// Authoritative case geometry: confirmed plan, not the reference project's demo apartment.
const CASE_ID=CASE.caseId;
const isEntrance=(w,o)=>o.entry===true||(CASE.entranceOpenings||[]).includes(o.id||w.id);
const matMap={oak:'wood',walnut:'walnut',stone:'marble',tile:'tile600',antislip:'antislip',terrazzo:'terrazzo',carpet:'carpet'};
const typeMap={coffee:'coffee',sofabed:'sofabed',sink:'ksink',basin:'vanity',hob:'stove'};
const WALLS=[],WINS=[],DOORS=[],SLIDES=[];
for(const w of DEFAULT.walls){
  const rect=(a,b)=>{const r=wallRect(w,a,b,DEFAULT.walls);return[r.x0,r.y0,r.x1,r.y1,w.bearing?'b':'n',w.id];};
  for(const[a,b]of intervals(w))WALLS.push(rect(a,b));
  for(const o of w.opens){const raw=wallRect(w,o.at,o.at+o.width,[]),r=[raw.x0,raw.y0,raw.x1,raw.y1,w.bearing?'b':'n',w.id];
    if(o.kind==='window'){r.sillHeight=o.sillHeight??850;r.windowHeight=o.height??1350;WINS.push(r);}
    if(o.kind==='sliding')SLIDES.push({rect:r,v:Math.abs(w.b[1]-w.a[1])>1,wall:w.id});
    if(o.kind==='door'){const p=doorPose(w,{...o,angle:o.angle??90});DOORS.push({name:o.label||'房门',rect:r,h:p.hinge,c:p.closed,o:p.leaf,len:p.leafWidth,wall:w.id,id:w.id,entry:isEntrance(w,o)});}
  }
}
const FLOOR_CONNECTIONS=DEFAULT.floorConnections||[];
const connectionMat=c=>state.rooms[c.materialRoomId].mat;
function floorTotals(){const rooms=ROOMS.reduce((n,r)=>n+area(r.poly),0),connections=FLOOR_CONNECTIONS.reduce((n,c)=>n+area(c.poly),0);return{rooms,connections,total:rooms+connections};}
const ROOMS=DEFAULT.rooms.map(r=>({id:r.id,name:r.name,poly:r.poly,mat:CASE.initialState.rooms[r.id]?.mat||matMap[r.material]||'marble',at:r.at}));
const nominalHeights={crib:900,dresser:750,cornersofa:850,beanbag:600,sidetable:550,shoecab:1100,floorlamp:1650,island:900,barstool:800,bathtub:600,washer:850,waterheater:700,aircon:1800,acwall:300,dishwasher:850,ovencol:2200,dryer:850,purifier:650,officechair:1150,piano:1200,treadmill:1300,baycushion:880,bed:1080,sofa:850,sofabed:850,coffee:420,lsofa:850,armchair:850,chair:860,desk:750,table:750,roundtable:750,coffeetable:430,wardrobe:2750,bookshelf:2750,cabinet:850,nightstand:450,tvstand:450,tv:840,fridge:1800,ksink:230,counter:900,stove:20,vanity:850,toilet:750,rug:15,plant:1000,shower:2000};
function caseFurniture(f){return {...f,type:typeMap[f.type]||f.type,originalType:f.type,cx:f.cx??f.x,cy:f.cy??f.y,elevation:f.elevation||0};}
const wallRemoved=id=>!!state.walls.find(w=>w.id===id)?.demolished;
function liveWalls(){return state.walls;}
const MATS = {
  wood:    {name:'橡木地板', sw:'#d8b88a'},
  walnut:  {name:'胡桃木地板', sw:'#9b7250'},
  tile800: {name:'800 地砖', sw:'#ebe6dc'},
  tile600: {name:'600 地砖', sw:'#dfe3e1'},
  marble:  {name:'大理石', sw:'#f1eee8'},
  antislip:{name:'300 防滑砖', sw:'#d3d8d4'},
  terrazzo:{name:'水磨石', sw:'#e6dfd3'},
  carpet:  {name:'满铺地毯', sw:'#c9c3d3'},
};
// 家具库：[类型, 名称, 宽, 深, 颜色]
const LIB = [
  {cat:'卧室', items:[
    ['bed','双人床 1.8m',1800,2000,'#c9d6df'],['bed','双人床 1.5m',1500,2000,'#d8c7dc'],['bed','单人床',1200,2000,'#e8d5b5'],
    ['crib','婴儿床',1250,700,'#efe3d0'],['nightstand','床头柜',450,400,'#e8dccb'],['wardrobe','衣柜',2000,600,'#efe6d8'],
    ['wardrobe','小衣柜',1200,550,'#efe6d8'],['dresser','梳妆台',1000,450,'#efe6d8'],['desk','书桌',1200,600,'#e2cfb4'],
    ['chair','椅子',450,480,'#cfc6b8'],['bookshelf','书架',800,300,'#e2cfb4'],['baycushion','飘窗垫',520,1800,'#e7dccd']]},
  {cat:'客厅', items:[
    ['sofa','三人沙发',2400,900,'#b7c4b0'],['sofa','双人沙发',1700,880,'#c3cbd6'],['cornersofa','转角沙发',2800,1700,'#b7c4b0'],
    ['armchair','单人沙发',850,850,'#d6b99a'],['beanbag','懒人沙发',800,800,'#e0b98f'],['coffeetable','茶几',1300,650,'#e8dccb'],['coffee','圆茶几',850,850,'#e8dccb'],['sofabed','沙发床（收起）',1500,820,'#c3cbd6'],
    ['sidetable','边几',500,500,'#d9c3a3'],['tvstand','电视柜',2400,400,'#e2cfb4'],['rug','地毯',2400,1700,'#d9cbb8'],
    ['shoecab','鞋柜',1000,350,'#efe6d8'],['shoecab','玄关柜',1400,380,'#e6dccc'],['floorlamp','落地灯',450,450,'#3d3a34'],
    ['plant','绿植',500,500,'#a9c39b'],['plant','大绿植',700,700,'#9dbb8c']]},
  {cat:'餐厨', items:[
    ['table','餐桌',1400,800,'#e2cfb4'],['table','六人餐桌',1800,900,'#d8c2a2'],['roundtable','圆桌',1000,1000,'#e2cfb4'],
    ['chair','餐椅',450,480,'#cfc6b8'],['island','岛台',1800,900,'#e9e5de'],['barstool','吧椅',420,420,'#6b5d4c'],
    ['counter','橱柜台面',1600,600,'#e9e5de'],['stove','燃气灶',750,450,'#dcdcdc'],['ksink','水槽',800,450,'#e1e6ea'],
    ['fridge','冰箱',700,700,'#dfe4e8'],['cabinet','餐边柜',1600,400,'#efe6d8']]},
  {cat:'卫浴', items:[
    ['toilet','马桶',400,700,'#ffffff'],['vanity','浴室柜',800,500,'#eef1f3'],['vanity','双盆浴室柜',1200,500,'#eef1f3'],
    ['shower','淋浴房',900,900,'#e4edf2'],['bathtub','浴缸',1600,750,'#eef3f6'],['washer','洗衣机',600,600,'#e6ebee'],
    ['waterheater','电热水器',800,450,'#f4f4f2'],['cabinet','储物柜',1000,400,'#efe6d8']]},
  {cat:'家电', items:[
    ['tv','65 寸电视',1450,35,'#1d1d1f'],['tv','55 寸电视',1230,35,'#1d1d1f'],['fridge','对开门冰箱',910,700,'#c9ced3'],
    ['aircon','柜机空调',500,380,'#f6f7f8'],['acwall','挂机空调',900,250,'#f6f7f8'],['dishwasher','洗碗机',600,600,'#c9ced3'],
    ['ovencol','蒸烤箱高柜',600,600,'#efe6d8'],['dryer','烘干机',600,600,'#e6ebee'],['purifier','空气净化器',400,300,'#f4f4f2']]},
  {cat:'书房 · 休闲', items:[
    ['desk','长书桌',1600,700,'#d8c2a2'],['officechair','办公椅',620,620,'#4a4f55'],['bookshelf','大书架',1600,350,'#e2cfb4'],
    ['piano','立式钢琴',1500,600,'#1f1d1b'],['treadmill','跑步机',800,1800,'#3a3a3c'],['armchair','阅读椅',750,800,'#c9a98a']]},
];
for(const [type,spec]of Object.entries(DIMENSIONS))nominalHeights[type]=spec.h;
LIB.find(g=>g.cat==='餐厨').items.push(...NEW_COMPONENTS.filter(c=>!['pendant','downlight','tracklight'].includes(c[0])));
LIB.push({cat:'顶面',items:NEW_COMPONENTS.filter(c=>['pendant','downlight','tracklight'].includes(c[0]))});
for(const c of RENOVATION_SPECS){DIMENSIONS[c.type]={label:c.name,h:c.h,elevation:c.elevation,min:15,max:DEFAULT.height,meaning:'装修构件本体高度'};nominalHeights[c.type]=c.h;}
LIB.find(g=>g.cat==='顶面').items.push(...RENOVATION_SPECS.filter(c=>c.mount==='ceiling').map(c=>[c.type,c.name,c.w,c.d,'#ece5db']));
LIB.push({cat:'装修 · 收口',items:RENOVATION_SPECS.filter(c=>c.mount!=='ceiling').map(c=>[c.type,c.name,c.w,c.d,'#ece5db'])});

// Keep the full registry and stable catalog keys for saved plans and cabinet geometry.
// These entries are no longer offered as standalone components in the library.
// Laundry cabinet and hard-plan utility points share the existing editable object system.
LIB.find(g=>g.cat==='卫浴').items.push(['laundrycab','洗衣机柜',1100,700,'#ece5db']);
LIB.push({cat:'水电点位',items:[['laundrypower','设备插座',86,30,'#a77745'],['waterinlet','上水点',80,30,'#4b88ac'],['drainoutlet','排水点',80,30,'#687b80']]});
Object.assign(DIMENSIONS,{laundrycab:{label:'洗衣机柜',h:1000,min:920,max:1200,meaning:'柜体及台面总高度',note:'内置洗衣机初值600×600×850mm；柜体最小800×680mm，尺寸需与产品安装余量核对。'},laundrypower:{label:'设备插座',h:86,min:15,max:150},waterinlet:{label:'上水点',h:80,min:15,max:150},drainoutlet:{label:'排水点',h:80,min:15,max:150}});
Object.assign(nominalHeights,{laundrycab:1000,laundrypower:86,waterinlet:80,drainoutlet:80});
for(const[type,name,h,elevation]of [['laundrypower','设备插座',86,1100],['waterinlet','上水点',80,550],['drainoutlet','排水点',80,200]])RENOVATION_MAP[type]={type,name,w:80,d:30,h,elevation,mount:'wall',role:'metal'};
const REMOVED_CATALOG_TYPES=new Set(CASE.presentation?.catalogHiddenTypes||[
 'accesshatch','floordrain','switchplate','socketplate','equipmentoutlet',
 'exhaustvent','towelrail','paperholder','aircon','acwall','spotlight',
 'endpanel','fridgecab','curtainrail','doortrim','windowtrim','skirting',
 'threshold','transition','backsplash','cabinetlight','slidingdoor','doubledoor'
]);
LIB.find(g=>g.cat==='家电').items.push(['boiler','壁挂炉',430,330,'#f1eee8']);
LIB.push({cat:'门窗',items:[['slidingdoor','推拉门',1600,2100,'#e4edef'],['doubledoor','对开门',1400,2100,'#ece5db']]});
DIMENSIONS.boiler={label:'壁挂炉',h:720,elevation:1300,min:400,max:1000,meaning:'机身及简化接口总高度',note:'可编辑概念初值，具体尺寸按所选产品设置。'};nominalHeights.boiler=720;
const UNNECESSARY_DISPLAY_TYPES=new Set(CASE.presentation?.editorHiddenTypes||['accesshatch','floordrain','switchplate','socketplate','equipmentoutlet','exhaustvent','towelrail','paperholder','aircon','acwall','spotlight']);
function availableCatalog(){return LIB.map(g=>({...g,items:g.items.filter(it=>!REMOVED_CATALOG_TYPES.has(it[0]))})).filter(g=>g.items.length);}

const typeColor = t => { for (const c of LIB) for (const i of c.items) if (i[0]===t) return i[4]; return '#eee'; };

let _n = 1;
const uid = () => 'f' + Date.now().toString(36) + (_n++);
const F = (type,name,cx,cy,w,d,rot=0,color) => ({id:uid(),type,name,cx,cy,w,d,rot,color:color||typeColor(type)});

function defaultFurniture(){return DEFAULT.furniture.map(caseFurniture).sort((a,b)=>(a.type==='rug'?0:1)-(b.type==='rug'?0:1));}
function defaultState(){const s=structuredClone(CASE.initialState);delete s.costSettings;s.ceilings??=[];s.wallFinishes??={};return s;}
const EXPORT_ID=document.getElementById('projectSeed').dataset.storageId;
const STORE='floor-visualization:'+CASE_ID+(EXPORT_ID?':export:'+EXPORT_ID:''),LEGACY_STORE=STORE,LANG_KEY_CASE=LANG_KEY;
function fixState(input){
  const d=defaultState(),s=structuredClone(input);
  if(!s||!Array.isArray(s.furniture)||s.furniture.length>1000)throw Error('无效家具数据');
  if(s.caseId&&s.caseId!==CASE_ID)throw Error('请导入本户型方案');
  if(Object.keys(s.rooms||{}).some(id=>!d.rooms[id]))throw Error('不是当前确认户型');
  s.rooms=Object.fromEntries(ROOMS.map(r=>{const v={...d.rooms[r.id],...(s.rooms||{})[r.id]};if(!MATS[v.mat]||typeof v.name!=='string')throw Error('无效房间材料');return[r.id,v];}));
  const types=new Set(LIB.flatMap(g=>g.items.map(i=>i[0]))),ids=new Set();
  s.furniture=s.furniture.map(f=>{if(!types.has(f.type)||typeof f.id!=='string'||ids.has(f.id))throw Error('无效家具');ids.add(f.id);for(const k of ['w','d','cx','cy','rot'])if(!Number.isFinite(f[k]))throw Error('无效家具尺寸');if(f.w<(f.type==='endpanel'?15:50)||f.d<30||f.w>15000||f.d>15000||Math.abs(f.cx)>50000||Math.abs(f.cy)>50000)throw Error('尺寸超出范围');if(!/^#[0-9a-f]{6}$/i.test(f.color)||typeof f.name!=='string')throw Error('无效家具颜色');f.h=Math.max(15,Math.min(DEFAULT.height,Number(f.h)||nominalHeights[f.type]||850));f.elevation=Math.max(0,Math.min(DEFAULT.height-f.h,Number(f.elevation)||0));if(f.fitToCeiling){f.h=DEFAULT.height;f.elevation=0;}return f;});
  const dem=Array.isArray(s.demolished)?s.demolished:[];s.demolished=dem.filter(id=>/^w\d+$/.test(id)&&WALLS[+id.slice(1)]?.[4]==='n');
  const pt=p=>Array.isArray(p)?{x:p[0],y:p[1]}:p;s.measures=(s.measures||[]).map(m=>({a:pt(m.a),b:pt(m.b)})).filter(m=>[m.a?.x,m.a?.y,m.b?.x,m.b?.y].every(Number.isFinite)).slice(0,500);
  s.doors=s.doors||{};delete s.costSettings;
  s.walls=validateWalls(s.walls||DEFAULT.walls,s.walls?[]:s.demolished);
  s.furniture.forEach(f=>Object.assign(f,componentSpec(f)));
  if(s.style&&!STYLE_PRESETS.some(p=>p.id===s.style))throw Error('未知装修风格');
  return {...d,...s,caseId:CASE_ID,version:s.version||12};
}
let recovery=null,storageNotice='';
function load(){
  let raw=null,key=STORE;
  try{const seed=JSON.parse(document.getElementById('projectSeed').textContent);
    // Exported documents own their cache. Unidentified legacy seeds never borrow a case cache.
    if(EXPORT_ID||(!seed&&CASE.readLocalStorage!==false)){try{raw=localStorage.getItem(STORE);}catch(e){if(!seed)throw e;storageNotice='本地存储不可用，已打开导出方案；请导出文件保留后续修改。';}}
    return restoreScheme(raw,seed,fixState);
  }catch(e){
    if(raw){recovery={raw,key,message:e.message};try{localStorage.setItem(STORE+'-recovery',raw);}catch{}}
    storageNotice='方案读取失败，原始数据已保留。请选择恢复方式。';return null;
  }
}
const PX_MM = 25.4 / 96;                       // 1 CSS px = 0.2646 mm
const COARSE = matchMedia('(pointer:coarse)').matches;   // iPad / 手机等触屏为主的设备
const TAP = COARSE ? 9 : 4;                    // 手指按下后移动超过该像素才算拖动
const narrow = () => matchMedia('(max-width:1100px)').matches;
const BOUNDS = {x:-1700,y:-1700,w:DEFAULT.width+3400,h:DEFAULT.depth+3500};
const $ = s => document.querySelector(s);
const svg = $('#plan');


/* ======================= 状态 / 历史 / 存储 ======================= */
const loadedState=load();
let state = loadedState || defaultState();
const ui = {tool:'select', sel:null, mA:null, mCur:null,
  layers:{dims:true, labels:true, furn:true, grid:false, bearing:false, wallSnap:true}};
let view = {x0:0, y0:0, s:.06};
const undoStack = [], redoStack = [];

function save(){
 try{const result=persistScheme(localStorage,STORE,state,fixState);if(result.backupWarning)toast('方案已保存，但备份未更新，请导出方案保留副本。');return true;}
 catch(e){toast('保存未成功：'+e.message+'。请导出方案保留当前编辑。');return false;}
}
const snap = () => JSON.stringify(state);
function commit(before){ undoStack.push(before); if (undoStack.length > 150) undoStack.shift(); redoStack.length = 0; save(); }
function mutate(fn){const b=snap();try{fn();fixState(state);}catch(e){state=JSON.parse(b);toast(e.message);renderAll();return false;}if(snap()!==b)commit(b);renderAll();return true;}
function undo(){ if (!undoStack.length) return toast(tr('没有可撤销的操作', 'Nothing to undo')); redoStack.push(snap()); state = JSON.parse(undoStack.pop()); validateSel(); save(); renderAll(); }
function redo(){ if (!redoStack.length) return; undoStack.push(snap()); state = JSON.parse(redoStack.pop()); validateSel(); save(); renderAll(); }
function validateSel(){ if (ui.sel?.kind==='furn' && !getF(ui.sel.id)) ui.sel = null; }
const getF = id => state.furniture.find(f => f.id === id);

/* ======================= 几何工具 ======================= */
const area = poly => Math.abs(poly.reduce((a,p,i) => { const q = poly[(i+1)%poly.length]; return a + p[0]*q[1] - q[0]*p[1]; }, 0)) / 2 / 1e6;
const perim = poly => poly.reduce((a,p,i) => { const q = poly[(i+1)%poly.length]; return a + Math.hypot(q[0]-p[0], q[1]-p[1]); }, 0) / 1000;
const bbox = poly => { const xs = poly.map(p=>p[0]), ys = poly.map(p=>p[1]); return [Math.min(...xs),Math.min(...ys),Math.max(...xs),Math.max(...ys)]; };
function aabb(f){ const a = f.rot*Math.PI/180, c = Math.abs(Math.cos(a)), s = Math.abs(Math.sin(a)); return {hw:f.w/2*c + f.d/2*s, hh:f.w/2*s + f.d/2*c}; }
const fmt = (n,d=2)=>Number.isFinite(n)?n.toFixed(d):'—';
const norm = a => ((Math.round(a) % 360) + 360) % 360;
function snapRects(){ return WALLS.filter((w,i) => !state.demolished.includes('w'+i)).concat(WINS.filter(r=>!wallRemoved(r[5]))); }

/* ======================= 颜色 / 材质图案 ======================= */
function hex2rgb(h){ h = h.replace('#',''); if (h.length===3) h = h.split('').map(c=>c+c).join(''); const n = parseInt(h,16); return [(n>>16)&255,(n>>8)&255,n&255]; }
function shade(h,k){ const f = v => Math.max(0,Math.min(255,Math.round(k>1 ? v+(255-v)*(k-1)*2 : v*k))); return '#'+hex2rgb(h).map(v=>f(v).toString(16).padStart(2,'0')).join(''); }

function buildDefs(){
  const plank = (id,base,line) => `<pattern id="m-${id}" patternUnits="userSpaceOnUse" width="1800" height="360">
      <rect width="1800" height="360" fill="${base}"/>
      <path d="M0 0H1800M0 180H1800M1200 0V180M600 180V360" stroke="${line}" stroke-width="10"/>
      <path d="M100 70Q500 60 900 85T1700 75M200 260Q700 250 1100 275T1750 262" stroke="${line}" stroke-width="5" fill="none" opacity=".45"/></pattern>`;
  const tile = (id,size,base,line) => `<pattern id="m-${id}" patternUnits="userSpaceOnUse" width="${size}" height="${size}">
      <rect width="${size}" height="${size}" fill="${base}"/><path d="M0 0H${size}M0 0V${size}" stroke="${line}" stroke-width="10"/></pattern>`;
  $('#defs').innerHTML =
    plank('wood',TEX.wood.base,shade(TEX.wood.base,.82)) + plank('walnut',TEX.walnut.base,shade(TEX.walnut.base,.78)) +
    tile('tile800',800,TEX.tile800.base,TEX.tile800.grout) + tile('tile600',600,TEX.tile600.base,TEX.tile600.grout) + tile('antislip',300,TEX.antislip.base,TEX.antislip.grout) +
    `<pattern id="m-marble" patternUnits="userSpaceOnUse" width="1200" height="1200">
      <rect width="1200" height="1200" fill="${TEX.marble.base}"/><path d="M0 0H1200M0 0V1200" stroke="${TEX.marble.grout}" stroke-width="10"/>
      ${marbleVeinSVG(CASE.presentation,shade(TEX.marble.base,.87))}</pattern>
    <pattern id="m-terrazzo" patternUnits="userSpaceOnUse" width="500" height="500">
      <rect width="500" height="500" fill="${TEX.terrazzo.base}"/>
      <circle cx="60" cy="80" r="22" fill="#b9a58c"/><circle cx="310" cy="140" r="16" fill="#8fa3a0"/><circle cx="190" cy="330" r="26" fill="#c9b7a2"/>
      <circle cx="420" cy="400" r="18" fill="#a88f76"/><circle cx="90" cy="440" r="12" fill="#8fa3a0"/><circle cx="440" cy="40" r="10" fill="#b9a58c"/></pattern>
    <pattern id="m-carpet" patternUnits="userSpaceOnUse" width="120" height="120">
      <rect width="120" height="120" fill="${TEX.carpet.base}"/><circle cx="30" cy="30" r="8" fill="#bab3c6"/><circle cx="90" cy="90" r="8" fill="#bab3c6"/></pattern>
    <pattern id="grid" patternUnits="userSpaceOnUse" width="1000" height="1000">
      <path d="M500 0V1000M0 500H1000" stroke="#e5dfd3" stroke-width="8"/><path d="M0 0V1000M0 0H1000" stroke="#d8d0c1" stroke-width="14"/></pattern>`;
}

/* ======================= 家具图例 ======================= */
const ST = 'stroke="#3d3a34" stroke-width="1" vector-effect="non-scaling-stroke"';
const rc = (x,y,w,h,f,ex='') => `<rect x="${x}" y="${y}" width="${Math.max(0,w)}" height="${Math.max(0,h)}" fill="${f}" ${ST} ${ex}/>`;
const ec = (cx,cy,rx,ry,f,ex='') => `<ellipse cx="${cx}" cy="${cy}" rx="${Math.max(0,rx)}" ry="${Math.max(0,ry)}" fill="${f}" ${ST} ${ex}/>`;
const ln = (x1,y1,x2,y2,ex='') => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" ${ST} ${ex}/>`;
const pa = (d,f='none',ex='') => `<path d="${d}" fill="${f}" ${ST} ${ex}/>`;
const DASH = 'stroke-dasharray="4 3"';

function furnSVG(t,w,d,c,component={}){
  const x = -w/2, y = -d/2, m = Math.min(w,d), p=component.finishes||{};
  switch (t){
    case 'bed': {
      let s = rc(x,y,w,d,p.bedFrame||'#fbf8f2','rx="30"') + rc(x,y,w,Math.min(90,d*.05),p.bedHead||shade(c,.62),'rx="20"');
      const ph = Math.min(360,d*.18), py = y+150;
      if (w >= 1300){ const pw = (w-240)/2; s += rc(x+80,py,pw,ph,p.pillow||'#fff','rx="70"') + rc(x+160+pw,py,pw,ph,p.pillow||'#fff','rx="70"'); }
      else s += rc(x+80,py,w-160,ph,p.pillow||'#fff','rx="70"');
      const by = py+ph+110, bh = y+d-15-by;
      s += rc(x+15,by,w-30,bh,c,'rx="40"') + pa(`M${x+15} ${by+300}H${x+w-15}`,'none',DASH);
      s += pa(`M${x+w-15-Math.min(420,w*.3)} ${by}L${x+w-15} ${by}L${x+w-15} ${by+Math.min(420,w*.3)}Z`, shade(c,1.12));
      s += rc(x+15,y+d-Math.min(320,d*.16)-15,w-30,Math.min(320,d*.16),p.bedRunner||shade(c,.75),'rx="20"');
      return s;
    }
    case 'sofabed': case 'sofa': case 'armchair': {
      const b = d*.24, a = Math.min(200,w*.13), n = t==='armchair' ? 1 : (w>2200 ? 3 : 2), cw = (w-2*a)/n, dk = shade(c,.85);
      let s = rc(x,y,w,d,dk,'rx="60"');
      for (let i=0;i<n;i++) s += rc(x+a+i*cw,y+b,cw,d-b-40,c,'rx="40"');
      const cushions = rc(x+a*.6,y+b*.2,Math.min(280,w*.18),b*.7,p.pillow||'#fbfaf7','rx="35"');
      const accentCushion=n>1?rc(x+w-a*.6-Math.min(280,w*.18),y+b*.2,Math.min(280,w*.18),b*.7,p.cushion||shade(c,.7),'rx="35"'):'';
      return s + rc(x,y,w,b,dk,'rx="50"') + rc(x,y,a,d,dk,'rx="50"') + rc(x+w-a,y,a,d,dk,'rx="50"')+cushions+accentCushion;
    }
    case 'cornersofa': {
      const k = Math.min(950,d*.56,w*.4), b = 220, dk = shade(c,.85);
      let s = pa(`M${x} ${y}H${x+w}V${y+k}H${x+k}V${y+d}H${x}Z`, dk);
      const cw = (w-b-200)/2;
      s += rc(x+b,y+b,cw,k-b-30,c,'rx="40"') + rc(x+b+cw,y+b,cw,k-b-30,c,'rx="40"') + rc(x+b,y+k,k-b-30,d-k-200,c,'rx="40"');
      return s + rc(x,y,w,b,dk,'rx="50"') + rc(x,y,b,d,dk,'rx="50"') + rc(x+w-200,y,200,k,dk,'rx="50"') + rc(x,y+d-200,k,200,dk,'rx="50"');
    }
    case 'nightstand': return rc(x,y,w,d,c,'rx="30"') + `<circle r="${m*.24}" fill="#fff6dd" ${ST}/>` + `<circle r="${m*.08}" fill="${shade(c,.8)}" ${ST}/>`;
    case 'wardrobe': {
      let s = rc(x,y,w,d,c) + ln(x+50,0,x+w-50,0);
      for (let hx = x+160; hx < x+w-100; hx += 180) s += ln(hx-45,-d*.28,hx+45,d*.28,'opacity=".6"');
      return s;
    }
    case 'cabinet': case 'shoecab': return rc(x,y,w,d,c) + ln(x,y+d,x+w,y);
    case 'dresser': return rc(x,y,w,d,c,'rx="20"') + rc(x+w*.3,y+30,w*.4,35,'#dfe9ee') + rc(x+w*.08,y+d*.28,w*.15,d*.4,shade(c,.93),'rx="12"') + rc(x,y,25,d,shade(c,.93)) + rc(w/2-25,y,25,d,shade(c,.93));
    case 'desk': return rc(x,y,w,d,c,'rx="20"') + rc(-w*.18,y+50,w*.36,45,'#555') + rc(-w*.14,y+d*.45,w*.28,d*.28,'#f4f4f4','rx="10"');
    case 'chair': return rc(x+25,y+d*.16,w-50,d*.84-10,c,'rx="60"') + rc(x,y,w,d*.2,shade(c,.78),'rx="40"');
    case 'bookshelf': { let s = rc(x,y,w,d,c); for (let bx = x+400; bx < x+w-50; bx += 400) s += ln(bx,y,bx,y+d); return s; }
    case 'baycushion': return rc(x,y,w,d,c,'rx="60"') + rc(x+60,y+80,w-120,Math.min(300,d*.2),'#fff','rx="60"') + rc(x+60,y+d-80-Math.min(300,d*.2),w-120,Math.min(300,d*.2),'#fff','rx="60"');
    case 'coffeetable': return rc(x,y,w,d,c,'rx="80"') + rc(x+60,y+60,w-120,d-120,shade(c,1.06),'rx="50"');
    case 'tvstand': return rc(x,y,w,d,c) + ln(x,y+d*.75,x+w,y+d*.75);
    case 'rug': return rc(x,y,w,d,c,'rx="40" fill-opacity=".96"') + rc(x+90,y+90,w-180,d-180,'none','rx="30" stroke-dasharray="3 3" opacity=".6"');
    case 'plant': {
      let s = `<circle r="${m/2}" fill="${c}" fill-opacity=".85" ${ST}/>`;
      for (let k=0;k<8;k++) s += `<ellipse cx="0" cy="${-m*.27}" rx="${m*.1}" ry="${m*.21}" transform="rotate(${k*45})" fill="${shade(c,.8)}" ${ST}/>`;
      return s + `<circle r="${m*.1}" fill="#8a6a4a" ${ST}/>`;
    }
    case 'table': return rc(x,y,w,d,c,'rx="30"') + rc(x+50,y+50,w-100,d-100,'none','rx="20" opacity=".4"');
    case 'coffee': case 'roundtable': return ec(0,0,w/2,d/2,c) + ec(0,0,w/2-50,d/2-50,'none','opacity=".4"');
    case 'counter': return rc(x,y,w,d,c) + ln(x,y+d-40,x+w,y+d-40,DASH);
    case 'stove': {
      let s = rc(x,y,w,d,'#2f2f2f','rx="20"'); const r = Math.min(w*.18,d*.27);
      const pts = [[-w/4,0],[w/4,0]];
      pts.forEach(([px,py]) => s += `<circle cx="${px}" cy="${py}" r="${r}" fill="none" stroke="#bbb" stroke-width="1" vector-effect="non-scaling-stroke"/><circle cx="${px}" cy="${py}" r="${r*.45}" fill="#666"/>`);
      return s;
    }
    case 'ksink': return rc(x,y,w,d,c,'rx="20"') + rc(x+w*.06,y+d*.18,w*.42,d*.66,'#fff','rx="50"') + rc(x+w*.52,y+d*.18,w*.42,d*.66,'#fff','rx="50"') + `<circle cx="0" cy="${y+d*.09}" r="22" fill="#999"/>`;
    case 'fridge': return rc(x,y,w,d,c,'rx="30"') + ln(x,y+d*.14,x+w,y+d*.14) + ln(0,y+d*.14,0,y+d) + rc(-70,y+d*.5,40,d*.25,'#aab') + rc(30,y+d*.5,40,d*.25,'#aab');
    case 'toilet': return rc(x+w*.04,y,w*.92,d*.27,c,'rx="30"') + ec(0,y+d*.27+d*.36,w*.47,d*.36,c) + ec(0,y+d*.27+d*.4,w*.3,d*.24,'#eef4f7');
    case 'vanity': return rc(x,y,w,d,c,'rx="20"') + ec(0,y+d*.57,Math.min(w*.32,260),d*.28,'#fff') + `<circle cx="0" cy="${y+d*.17}" r="26" fill="#999"/>`;
    case 'shower': return rc(x,y,w,d,c) + ln(x,y,x+w,y+d,DASH) + ln(x+w,y,x,y+d,DASH) + `<circle r="45" fill="#fff" ${ST}/>`;
    case 'bathtub': return rc(x,y,w,d,c,'rx="40"') + rc(x+80,y+80,w-160,d-160,'#fff',`rx="${m*.33}"`) + `<circle cx="${x+w-260}" cy="0" r="35" fill="#ccc" ${ST}/>`;
    case 'washer': case 'dryer': return rc(x,y,w,d,c,'rx="30"') + rc(x,y,w,d*.14,shade(c,.9)) + `<circle cy="${d*.06}" r="${m*.34}" fill="#fff" ${ST}/><circle cy="${d*.06}" r="${m*.24}" fill="${t==='dryer'?'#e9dccb':'#cfdde4'}" ${ST}/>`;
    case 'crib': {
      let s = rc(x,y,w,d,c,'rx="20"') + rc(x+45,y+45,w-90,d-90,'#fff','rx="20"');
      for (let sx = x+90; sx < x+w-60; sx += 90) s += ln(sx,y,sx,y+45,'opacity=".5"') + ln(sx,y+d-45,sx,y+d,'opacity=".5"');
      return s;
    }
    case 'beanbag': return ec(0,0,w/2,d/2,c) + ec(-w*.04,-d*.06,w*.3,d*.28,shade(c,1.12),'opacity=".9"');
    case 'sidetable': return ec(0,0,w/2,d/2,c) + ec(0,0,w*.12,d*.12,'none','opacity=".5"');
    case 'floorlamp': return `<circle r="${m*.5}" fill="#fff6dd" fill-opacity=".85" ${ST}/>` + `<circle r="${m*.32}" fill="none" ${ST} ${DASH}/>` + `<circle r="${m*.07}" fill="${c}" ${ST}/>`;
    case 'island': return rc(x,y,w,d,c) + ln(x,y+d-250,x+w,y+d-250,DASH);
    case 'barstool': return `<circle r="${m/2}" fill="${c}" ${ST}/><circle r="${m*.3}" fill="${shade(c,1.15)}" ${ST}/>`;
    case 'waterheater': return rc(x,y,w,d,c,`rx="${d/2}" ${DASH}`) + ln(x+w*.2,0,x+w*.8,0,DASH);
    case 'tv': return rc(x,y,w,d,c,'rx="10"') + rc(x+w*.3,y+d,w*.4,Math.min(40,d),'#666');
    case 'aircon': return rc(x,y,w,d,c,'rx="30"') + ln(x+40,y+d*.72,x+w-40,y+d*.72) + ln(x+40,y+d*.86,x+w-40,y+d*.86);
    case 'acwall': {
      let s = rc(x,y,w,d,c,`rx="30" ${DASH}`);
      [.25,.5,.75].forEach(k => s += ln(x+w*k,y+d,x+w*k,y+d+200,`${DASH} opacity=".6"`));
      return s;
    }
    case 'dishwasher': return rc(x,y,w,d,c,'rx="15"') + ln(x,y+d-70,x+w,y+d-70) + rc(x+w*.3,y+d-45,w*.4,25,'#888');
    case 'ovencol': return rc(x,y,w,d,c) + ln(x,y,x+w,y+d) + ln(x+w,y,x,y+d);
    case 'purifier': return rc(x,y,w,d,c,'rx="60"') + rc(x+45,y+45,w-90,d-90,'none',`rx="40" ${DASH}`);
    case 'officechair': {
      let s = '';
      for (let k = 0; k < 5; k++) s += `<line x1="0" y1="0" x2="0" y2="${m*.48}" transform="rotate(${k*72+36})" stroke="#555" stroke-width="2" vector-effect="non-scaling-stroke"/>`;
      return s + rc(x+w*.12,y+d*.22,w*.76,d*.66,c,'rx="80"') + rc(x+w*.15,y+d*.04,w*.7,d*.16,shade(c,.78),'rx="40"')
        + rc(x+w*.02,y+d*.3,w*.1,d*.45,shade(c,.7),'rx="30"') + rc(x+w*.88,y+d*.3,w*.1,d*.45,shade(c,.7),'rx="30"');
    }
    case 'piano': {
      let s = rc(x,y,w,d*.55,c,'rx="10"') + rc(x+40,y+d*.55,w-80,d*.4,shade(c,1.4),'rx="10"');
      const kx = x+90, kw = w-180, kd = d*.2;
      s += rc(kx,y+d*.55,kw,kd,'#faf8f3');
      for (let i = 1; i < 26; i++) s += ln(kx+kw*i/26,y+d*.55,kx+kw*i/26,y+d*.55+kd,'opacity=".5"');
      return s;
    }
    case 'treadmill': return rc(x,y,w,d,c,'rx="50"') + rc(x+90,y+320,w-180,d-400,'#1c1c1e','rx="25"') + rc(x,y,w,230,shade(c,1.4),'rx="40"');
    default: return rc(x,y,w,d,c);
  }
}

/* ======================= 渲染 ======================= */
const NOLABEL = ['rug','plant','floorlamp','sidetable','barstool','beanbag'];
function renderRooms(){
  let s = FLOOR_CONNECTIONS.map(c=>`<polygon data-floor-connection="${esc(c.id)}" points="${c.poly.map(p=>p.join(',')).join(' ')}" fill="url(#m-${connectionMat(c)})" pointer-events="none"/>`).join('');
  ROOMS.forEach(r => s += `<polygon class="room" data-room="${r.id}" points="${r.poly.map(p=>p.join(',')).join(' ')}" fill="url(#m-${state.rooms[r.id].mat})"/>`);
  const sill = ([a,b,c,d]) => `<rect data-plan-threshold="true" x="${a}" y="${b}" width="${c-a}" height="${d-b}" fill="#e2dacb" stroke="#b9b0a0" stroke-width="1" vector-effect="non-scaling-stroke" pointer-events="none"/>`;
  // 户型图保留空白门洞，不绘制门槛或轨道底色。
  if(planDrawingMode==='furniture'){DOORS.forEach(d => s += sill(d.rect)); SLIDES.forEach(d => s += sill(d.rect));}
  $('#gRooms').innerHTML = s;
}

function renderFurn(){
  const g = $('#gFurn');
  g.setAttribute('display', ui.layers.furn ? 'inline' : 'none');
  g.innerHTML = state.furniture.map(f => {
    return `<g class="furn" data-fid="${f.id}" transform="translate(${f.cx} ${f.cy}) rotate(${f.rot})">${furnSVG(f.type,f.w,f.d,f.color,f)}<title>${esc(f.name)} · ${f.w}×${f.d} mm</title></g>`;
  }).join('');
}

function renderWalls(){
  const rects=WALLS.map((w,i)=>{const parent=state.walls.find(p=>p.id===w[5]),ab=intervals(parent)[WALLS.filter(p=>p[5]===w[5]).indexOf(w)];return {...wallRect(parent,ab[0],ab[1],liveWalls()),id:'w'+i,bearing:parent.bearing,dem:wallRemoved(w[5])};});
  const active=rects.filter(r=>!r.dem);
  let s=`<path id="wallSolids" d="${solidPlanPath(active)}" fill="#35322d" fill-rule="nonzero" pointer-events="none"/>`;
  if(ui.layers.bearing)s+=`<path id="bearingOutline" d="${planOutline(active.filter(r=>r.bearing))}" fill="none" stroke="#b8412c" stroke-width="1.4" vector-effect="non-scaling-stroke" pointer-events="none"><title>红色描边：原图承重墙标记；黑色填充：连续实墙</title></path>`;
  s+=rects.map(r=>`<rect class="wall" data-wall="${r.id}" data-wall-id="${r.wall}" x="${r.x0}" y="${r.y0}" width="${r.x1-r.x0}" height="${r.y1-r.y0}" fill="${r.dem?'rgba(198,91,58,.12)':'transparent'}" ${r.dem?'stroke="#c65b3a" stroke-width="1.2" stroke-dasharray="5 3" vector-effect="non-scaling-stroke"':''}/>`).join('');
  $('#gWalls').innerHTML=s;
}

function renderOpenings(){
  const WS = 'stroke="#4f7394" stroke-width="1" vector-effect="non-scaling-stroke"';
  let s = '';
  WINS.filter(r=>!wallRemoved(r[5])).forEach(([x0,y0,x1,y1]) => {
    const w = x1-x0, h = y1-y0;
    s += `<rect x="${x0}" y="${y0}" width="${w}" height="${h}" fill="#f7fbfd" ${WS}/>`;
    if (w >= h) [1/3,2/3].forEach(t => s += `<line x1="${x0}" y1="${y0+h*t}" x2="${x1}" y2="${y0+h*t}" ${WS}/>`);
    else [1/3,2/3].forEach(t => s += `<line x1="${x0+w*t}" y1="${y0}" x2="${x0+w*t}" y2="${y1}" ${WS}/>`);
  });
  const DS = 'stroke="#3d3a34" stroke-width="1" vector-effect="non-scaling-stroke"';
  DOORS.filter(d=>!wallRemoved(d.wall)&&(planDrawingMode!=='structure'||d.entry)).forEach(d => {
    const [hx,hy] = d.h, L = d.len, T = 40;
    const vec=state.doors[d.id]===false?d.c:d.o; const ox = hx + vec[0]*L, oy = hy + vec[1]*L, cx = hx + d.c[0]*L, cy = hy + d.c[1]*L;
    const sweep = d.o[0]*d.c[1] - d.o[1]*d.c[0] > 0 ? 1 : 0;
    const col = d.entry ? '#b5653a' : '#3d3a34';
    s += `<polygon data-plan-door="${d.wall}" points="${hx},${hy} ${ox},${oy} ${ox+d.c[0]*T},${oy+d.c[1]*T} ${hx+d.c[0]*T},${hy+d.c[1]*T}" fill="#fff" stroke="${col}" stroke-width="${d.entry?1.8:1}" vector-effect="non-scaling-stroke"/>`;
    s += `<path data-plan-door="${d.wall}" data-door-swing="${d.wall}" d="M${ox} ${oy}A${L} ${L} 0 0 ${sweep} ${cx} ${cy}" fill="none" ${DS} stroke-dasharray="5 3" opacity=".7"/>`;
  });
  SLIDES.filter(d=>!wallRemoved(d.wall)&&(planDrawingMode!=='structure'||(CASE.entranceOpenings||[]).includes(d.wall))).forEach(slide=>s+=renderSlidingPlan(slide));
  // 入户标识
  s += `<path d="M3900 10700V9850M3750 10050L3900 9800L4050 10050" fill="none" stroke="#b5653a" stroke-width="2" vector-effect="non-scaling-stroke"/>
        <text x="3580" y="11000" font-size="200" fill="#b5653a">${tr('入户','Entry')}</text>`;
  $('#gOpen').innerHTML = s;
}

function renderLabels(){
  const g = $('#gLabels');
  g.setAttribute('display', ui.layers.labels ? 'inline' : 'none');
  g.innerHTML = ROOMS.filter(r => r.at).map(r => {
    const [x,y] = r.at, halo = 'stroke="#fbf9f4" stroke-width="45" paint-order="stroke" stroke-linejoin="round"';
    return `<text x="${x}" y="${y}" font-size="250" font-weight="600" text-anchor="middle" fill="#2b2824" ${halo}>${esc(nm(state.rooms[r.id].name))}</text>
      <text x="${x}" y="${y+260}" font-size="175" text-anchor="middle" fill="#7d7366" ${halo}>${fmt(area(r.poly))} m²</text>`;
  }).join('');
}

function renderDims(){
  const DC = '#7d7160', LS = `stroke="${DC}" stroke-width="1" vector-effect="non-scaling-stroke"`, TK = `stroke="${DC}" stroke-width="2" vector-effect="non-scaling-stroke"`;
  const txt = (x,y,v,rot) => `<text x="${x}" y="${y}" font-size="${v<400?140:200}" text-anchor="middle" fill="${DC}" ${rot?`transform="rotate(-90 ${x} ${y})"`:''}>${v}</text>`;
  const chain = (horiz, at, start, segs) => {
    const pts = [start]; segs.forEach(v => pts.push(pts[pts.length-1]+v));
    let s = horiz ? `<line x1="${pts[0]}" y1="${at}" x2="${pts.at(-1)}" y2="${at}" ${LS}/>` : `<line x1="${at}" y1="${pts[0]}" x2="${at}" y2="${pts.at(-1)}" ${LS}/>`;
    pts.forEach(p => s += horiz
      ? `<line x1="${p}" y1="${at-170}" x2="${p}" y2="${at+170}" ${LS}/><line x1="${p-80}" y1="${at+80}" x2="${p+80}" y2="${at-80}" ${TK}/>`
      : `<line x1="${at-170}" y1="${p}" x2="${at+170}" y2="${p}" ${LS}/><line x1="${at-80}" y1="${p+80}" x2="${at+80}" y2="${p-80}" ${TK}/>`);
    segs.forEach((v,i) => { const mid = (pts[i]+pts[i+1])/2; s += horiz ? txt(mid, at-70, v) : txt(at-70, mid, v, true); });
    return s;
  };
  const g = $('#gDims');
  g.innerHTML =
    chain(true,-750,CHAIN_STARTS.top||0,CHAINS.top)+chain(true,-1250,0,[DEFAULT.width])+chain(true,DEFAULT.depth+740,CHAIN_STARTS.bottom||0,CHAINS.bottom)+chain(true,DEFAULT.depth+1240,0,[DEFAULT.width])+chain(false,-800,CHAIN_STARTS.left||0,CHAINS.left)+chain(false,-1300,0,[DEFAULT.depth])+chain(false,DEFAULT.width+800,CHAIN_STARTS.right||0,CHAINS.right)+chain(false,DEFAULT.width+1300,0,[DEFAULT.depth]);
  g.setAttribute('display', ui.layers.dims ? 'inline' : 'none');
}

function renderGrid(){
  $('#gGrid').innerHTML = `<rect x="-20000" y="-20000" width="55000" height="55000" fill="${ui.layers.grid ? 'url(#grid)' : 'transparent'}" data-bg="1"/>`;
}

function renderMeasure(){
  const k = 1/view.s, fs = 12*k;
  const one = (a,b,tmp) => {
    const L = Math.hypot(b.x-a.x, b.y-a.y); if (L < 1) return '';
    let ang = Math.atan2(b.y-a.y, b.x-a.x)*180/Math.PI; if (ang > 90 || ang < -90) ang += 180;
    const mx = (a.x+b.x)/2, my = (a.y+b.y)/2, nx = -(b.y-a.y)/L*5*k, ny = (b.x-a.x)/L*5*k;
    const col = tmp ? '#2f5d62' : '#b5653a', S = `stroke="${col}" stroke-width="1.5" vector-effect="non-scaling-stroke"`;
    return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" ${S}/>
      <line x1="${a.x-nx}" y1="${a.y-ny}" x2="${a.x+nx}" y2="${a.y+ny}" ${S}/><line x1="${b.x-nx}" y1="${b.y-ny}" x2="${b.x+nx}" y2="${b.y+ny}" ${S}/>
      <text x="${mx}" y="${my-5*k}" font-size="${fs}" text-anchor="middle" fill="${col}" font-weight="600" transform="rotate(${ang} ${mx} ${my})"
        stroke="#fff" stroke-width="${3.5*k}" paint-order="stroke">${Math.round(L)} mm</text>`;
  };
  let s = state.measures.map(m => one(m.a,m.b)).join('');
  if (ui.mA && ui.mCur) s += one(ui.mA, ui.mCur, true);
  if (ui.mA) s += `<circle cx="${ui.mA.x}" cy="${ui.mA.y}" r="${3*k}" fill="#2f5d62"/>`;
  $('#gMeasure').innerHTML = s;
}

function renderSel(){
  const k = 1/view.s; let s = '';
  if (ui.sel?.kind === 'furn'){
    const f = getF(ui.sel.id);
    if (f){
      // 触屏上手柄更大、离家具更远，并各带一圈透明的大热区
      const p = 5*k, A = 'stroke="#b5653a" vector-effect="non-scaling-stroke"', hs = COARSE ? 1.7 : 1, ro = (COARSE ? 40 : 26)*k, hit = (COARSE ? 24 : 11)*k;
      // Only the selection UI gets a minimum size; object dimensions stay exact.
      const minFrame=(COARSE?64:44)*k,sx=Math.max(f.w/2+p,minFrame/2),sy=Math.max(f.d/2+p,minFrame/2),ry=-sy-(ro-p);
      s += `<g transform="translate(${f.cx} ${f.cy}) rotate(${f.rot})">
        <rect x="${-sx}" y="${-sy}" width="${sx*2}" height="${sy*2}" fill="none" ${A} stroke-width="1.5" stroke-dasharray="5 3" pointer-events="none"/>
        <line x1="0" y1="${-sy}" x2="0" y2="${ry}" ${A} stroke-width="1" pointer-events="none"/>
        <circle data-handle="rot" cx="0" cy="${ry}" r="${hit}" fill="transparent"/>
        <circle data-handle="rot" cx="0" cy="${ry}" r="${6*hs*k}" fill="#fff" ${A} stroke-width="1.5"><title>${tr('拖动旋转（Shift 自由角度）','Drag to rotate (Shift for free angle)')}</title></circle>
        <circle data-handle="widthLeft" cx="${-sx}" cy="0" r="${hit}" fill="transparent"/>
        <rect data-handle="widthLeft" x="${-sx-4*hs*k}" y="${-6*hs*k}" width="${8*hs*k}" height="${12*hs*k}" rx="${2*hs*k}" fill="#fff" ${A} stroke-width="1.5"><title>${tr('拖动调整宽度，固定右侧边','Drag to change width; right edge stays fixed')}</title></rect>
        <circle data-handle="width" cx="${sx}" cy="0" r="${hit}" fill="transparent"/>
        <rect data-handle="width" x="${sx-4*hs*k}" y="${-6*hs*k}" width="${8*hs*k}" height="${12*hs*k}" rx="${2*hs*k}" fill="#fff" ${A} stroke-width="1.5"><title>${tr('拖动调整宽度，固定对侧边','Drag to change width; opposite edge stays fixed')}</title></rect>
        <circle data-handle="depth" cx="0" cy="${sy}" r="${hit}" fill="transparent"/>
        <rect data-handle="depth" x="${-6*hs*k}" y="${sy-4*hs*k}" width="${12*hs*k}" height="${8*hs*k}" rx="${2*hs*k}" fill="#fff" ${A} stroke-width="1.5"><title>${tr('拖动调整进深，固定对侧边','Drag to change depth; opposite edge stays fixed')}</title></rect>
        <circle data-handle="size" cx="${sx}" cy="${sy}" r="${hit}" fill="transparent"/>
        <rect data-handle="size" x="${sx-5*hs*k}" y="${sy-5*hs*k}" width="${10*hs*k}" height="${10*hs*k}" fill="#b5653a"><title>${tr('拖动调整尺寸','Drag to resize')}</title></rect></g>`;
      const {hh} = aabb({...f,w:2*sx,d:2*sy});
      s += `<text x="${f.cx}" y="${f.cy+hh+24*k}" font-size="${12*k}" text-anchor="middle" fill="#b5653a" font-weight="600" pointer-events="none"
        stroke="#fff" stroke-width="${3*k}" paint-order="stroke">${f.w} × ${f.d}</text>`;
    }
  } else if (ui.sel?.kind === 'room'){
    const r = ROOMS.find(r => r.id === ui.sel.id);
    s += `<polygon points="${r.poly.map(p=>p.join(',')).join(' ')}" fill="rgba(181,101,58,.08)" stroke="#b5653a" stroke-width="2" vector-effect="non-scaling-stroke" pointer-events="none"/>`;
  }
  $('#gSel').innerHTML = s;
}

function renderAll(){
  syncGeometry();
  renderGrid(); renderRooms(); renderFurn(); renderWalls(); renderOpenings(); renderLabels(); renderMeasure(); renderSel(); renderPanel(); updateHeader();
  window.View3D?.sync();
}

function updateHeader(){
  $('#undo').disabled = !undoStack.length; $('#redo').disabled = !redoStack.length;
  $('#undo').style.opacity = undoStack.length ? 1 : .4; $('#redo').style.opacity = redoStack.length ? 1 : .4;
}

/* ======================= 右侧面板 ======================= */
const esc = s => String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

function renderPanel(){
  renderFab();
  const p = $('#panel');
  if (ui.sel?.kind === 'furn'){ const f = getF(ui.sel.id); if (f){ p.innerHTML = furnPanel(f); bindFurnPanel(f); return; } }
  if (ui.sel?.kind === 'room'){ p.innerHTML = roomPanel(ROOMS.find(r => r.id === ui.sel.id)); bindRoomPanel(); return; }
  p.innerHTML=overviewPanel();bindOverview();
}

// The final overview implementation below contains quantities only.
function overviewPanel(){return '';}
function bindOverview(){
  document.querySelectorAll('#panel tr[data-room]').forEach(tr => tr.onclick = () => { select({kind:'room', id:tr.dataset.room}); if (is3D()) window.View3D.flyToRoom(tr.dataset.room); });
  $('#clearMeasure').onclick = () => state.measures.length && mutate(() => state.measures = []);
  $('#clearFurn').onclick = clearLayout;
}

// 底部浮动工具条：触屏没有键盘，旋转 / 复制 / 删除都放在这里
function renderFab(){
  const fab = $('#fab'), f = ui.sel?.kind === 'furn' && getF(ui.sel.id), r = ui.sel?.kind === 'room' && ROOMS.find(r => r.id === ui.sel.id);
  if (!f && !r){ fab.classList.remove('show'); return; }
  fab.innerHTML = f
    ? `<span class="name">${esc(nm(f.name))}</span><button class="btn" data-a="rotL">↺</button><button class="btn" data-a="rotR">↻ ${tr('旋转','Rotate')}</button>
       <button class="btn" data-a="dup">${tr('复制','Duplicate')}</button><button class="btn danger" data-a="del">${tr('删除','Delete')}</button><span class="sep"></span>
       <button class="btn narrow-only" data-a="prop">${tr('属性','Properties')}</button><button class="btn" data-a="done">${tr('完成','Done')}</button>`
    : `<span class="name">${esc(nm(state.rooms[r.id].name))}</span><button class="btn narrow-only" data-a="prop">${tr('地面 / 属性','Floor / Properties')}</button><button class="btn" data-a="done">${tr('完成','Done')}</button>`;
  fab.classList.add('show');
  fab.querySelectorAll('[data-a]').forEach(b => b.onclick = () => ({
    rotL:() => rotateSel(-45), rotR:() => rotateSel(45), dup:duplicateSel, del:deleteSel,
    prop:() => drawer('panel', true), done:() => { select(null); closeDrawers(); },
  })[b.dataset.a]());
}

function clearLayout(){
  const n = state.furniture.length;
  if (!n) return toast(tr('当前没有布置任何家具', 'There is no furniture to clear'));
  if (!confirm(tr(`确定清空全部 ${n} 件家具 / 家电吗？\n墙体、地面材料和测量线会保留，可点「撤销」恢复。`, `Remove all ${n} furniture / appliance items?\nWalls, flooring and measurements are kept. You can Undo this.`))) return;
  ui.sel = null; mutate(() => state.furniture = []);
  toast(tr('已清空布置，可点「撤销」恢复', 'Layout cleared — Undo to restore'));
}

/* 侧栏开合：which = 'lib' | 'panel' | null，open 不传则切换。
 * 宽屏：侧栏在布局中收起 / 展开（记住选择）；窄屏：侧栏是浮层抽屉，一次只开一个，which = null 表示全部关闭 */
const PANES = STORE+':panes';
const panes = (() => { try { return JSON.parse(localStorage.getItem(PANES)) || {}; } catch(e) { return {}; } })();
function drawer(which, open){
  const app = $('.app'), els = {lib:$('aside.lib'), panel:$('aside.right')}, n = narrow();
  if (n){
    Object.entries(els).forEach(([k, el]) => el.classList.toggle('open', k === which && (open ?? !el.classList.contains('open'))));
  } else {
    Object.values(els).forEach(el => el.classList.remove('open'));
    if (which){
      const k = which === 'lib' ? 'hideLib' : 'hidePanel';
      panes[k] = open === undefined ? !panes[k] : !open;
      try { localStorage.setItem(PANES, JSON.stringify(panes)); } catch(e) {}
    }
  }
  app.classList.toggle('hide-lib', !!panes.hideLib); app.classList.toggle('hide-panel', !!panes.hidePanel);
  syncPaneBtns();
}
function syncPaneBtns(){
  const els = {lib:$('aside.lib'), panel:$('aside.right')}, n = narrow();
  $('#tgLib').textContent=tr('◧ 家具','◧ Furniture');
  const vis = k => n ? els[k].classList.contains('open') : !panes[k === 'lib' ? 'hideLib' : 'hidePanel'];
  $('#tgLib').classList.toggle('on', vis('lib')); $('#tgPanel').classList.toggle('on', vis('panel'));
  $('#tgLib').title = vis('lib') ? tr('收起家具 ( [ )', 'Hide furniture ( [ )') : tr('展开家具 ( [ )', 'Show furniture ( [ )');
  $('#tgPanel').title = vis('panel') ? tr('收起属性面板 ( ] )', 'Hide properties ( ] )') : tr('展开属性面板 ( ] )', 'Show properties ( ] )');
  $('#stage').classList.toggle('drawer-panel', n && vis('panel'));   // 属性抽屉盖住画面时让出底部工具条
}
function closeDrawers(){ if (narrow()) drawer(null); }

function roomPanel(r){
  const st = state.rooms[r.id], a = area(r.poly), [x0,y0,x1,y1] = bbox(r.poly), inside = state.furniture.filter(f => inPolygon([f.cx,f.cy],r.poly));
  const mats = Object.entries(MATS).map(([k,m]) => `<button class="mat ${k===st.mat?'on':''}" data-mat="${k}"><i style="background:${m.sw}"></i><span>${nm(m.name)}</span></button>`).join('');
  return `<section><h3>${tr('房间','Room')}</h3>
    <div class="form"><label class="full">${tr('名称','Name')}<input id="rName" value="${esc(nm(st.name))}"></label></div>
    <div class="stats" style="margin-top:10px">
      <div><small>${tr('使用面积','Floor area')}</small><span class="big">${fmt(a)}</span> m²</div>
      <div><small>${tr('周长','Perimeter')}</small><span class="big">${fmt(perim(r.poly),1)}</span> m</div>
      <div><small>${tr('开间','Width')}</small><span class="big">${x1-x0}</span> mm</div>
      <div><small>${tr('进深','Depth')}</small><span class="big">${y1-y0}</span> mm</div></div>
    <div class="muted">${tr(`墙面面积（层高 ${H}m，未扣门窗）约 ${fmt(perim(r.poly)*H,1)} m²`, `Wall area (${H}m ceiling, openings not deducted) ≈ ${fmt(perim(r.poly)*H,1)} m²`)}</div></section>
  <section><h3>${tr('地面材料','Flooring')}</h3><div class="mats">${mats}</div>
    </section>
  <section><h3>${tr('房间内家具','Furniture in room')} <small>${tr(`${inside.length} 件`, `${inside.length} items`)}</small></h3>
    <table>${inside.map(f => `<tr class="click" data-fid="${f.id}"><td>${esc(nm(f.name))}</td><td class="r muted">${f.w}×${f.d}</td></tr>`).join('') || `<tr><td class="muted">${tr('暂无','None')}</td></tr>`}</table>
    </section>`;
}
function bindRoomPanel(){
  const id = ui.sel.id;
  $('#rName').onchange = e => mutate(() => state.rooms[id].name = e.target.value.trim() || state.rooms[id].name);
  document.querySelectorAll('#panel [data-mat]').forEach(b => b.onclick = () => mutate(() => state.rooms[id].mat = b.dataset.mat));
  document.querySelectorAll('#panel tr[data-fid]').forEach(tr => tr.onclick = () => select({kind:'furn', id:tr.dataset.fid},{parent:ui.sel}));
}

function furnPanel(f){
  return `<section><h3>${tr('家具属性','Furniture')}</h3>
    <div class="form">
      <label class="full">${tr('名称','Name')}<input id="fName" value="${esc(nm(f.name))}"></label>
      <label>${tr('宽','Width')} (mm)<input type="number" id="fW" value="${f.w}" min="50" max="15000" step="10"></label>
      <label>${tr('深','Depth')} (mm)<input type="number" id="fD" value="${f.d}" min="50" max="15000" step="10"></label>
      <label>${tr('中心','Center')} X (mm)<input type="number" id="fX" value="${Math.round(f.cx)}" step="10"></label>
      <label>${tr('中心','Center')} Y (mm)<input type="number" id="fY" value="${Math.round(f.cy)}" step="10"></label>
      <label>高度 (mm)<input type=number id=fH min=15 max=${DEFAULT.height} step=10 value="${f.h||nominalHeights[f.type]||850}"></label><label>${f.type==='ksink'||f.type==='stove'?'台面标高':'离地'} (mm)<input type=number id=fE min=0 max=${DEFAULT.height} step=10 value="${f.elevation||0}"></label>${['wardrobe','bookshelf'].includes(f.type)?`<label class=full><span><input id=fCeiling type=checkbox ${f.fitToCeiling?'checked':''}> 顶到天花板 · ${DEFAULT.height} mm</span></label>`:''}<label>${tr('旋转','Rotation')} (°)<input type="number" id="fR" value="${f.rot}" step="15"></label>
      <label>${tr('颜色','Color')}<input type="color" id="fC" value="${f.color}"></label>
    </div>
    <div class="muted" style="margin-top:8px">${tr('占地面积','Footprint')} ${fmt(f.w*f.d/1e6)} m²</div>
    <div class="actions">
      <button class="btn" id="aRot">${tr('旋转 45°','Rotate 45°')}</button>
      <button class="btn" id="aTop" title="上移一层" ${layerTarget(f,1)?'':'disabled'}>${tr('上移','Move up')}</button><button class="btn" id="aBot" title="下移一层" ${layerTarget(f,-1)?'':'disabled'}>${tr('下移','Move down')}</button>
      <button class="btn danger" id="aDel">${tr('删除','Delete')}</button>
    </div></section>
  <section class="muted" style="font-size:12px">${tr('拖动家具移动；拖动上方圆点旋转；拖动右下角方块自由调整宽度和进深；左右两侧中点调整宽度，下侧中点调整进深。开启「贴墙吸附」后靠近墙面会自动贴齐。', 'Drag to move; drag the top dot to rotate; drag the corner to resize, the left and right midpoints to change width, and the bottom midpoint to change depth. With "Wall snap" on, items snap flush to nearby walls.')}</section>`;
}
function bindFurnPanel(f){
  const upd = (fn) => mutate(() => { const g = getF(f.id); if (g) fn(g); });
  const num = (id, fn) => $(id).onchange = e => { const v=Number(e.target.value);if(e.target.value!==''&&Number.isFinite(v))upd(g=>fn(g,v));else{toast('请输入有效数字');renderPanel();} };
  $('#fName').onchange = e => upd(g => g.name = e.target.value.trim() || g.name);
  num('#fW', (g,v) => g.w = checkedSize(v));
  num('#fD', (g,v) => g.d = checkedSize(v));
  num('#fX', (g,v) => g.cx = v); num('#fY', (g,v) => g.cy = v); num('#fR', (g,v) => g.rot = norm(v));
  num('#fH',(g,v)=>{g.fitToCeiling=false;g.h=Math.max(15,Math.min(DEFAULT.height-(g.elevation||0),Math.round(v)));});num('#fE',(g,v)=>{g.elevation=Math.max(0,Math.min(DEFAULT.height-(g.h||850),v));});if($('#fCeiling'))$('#fCeiling').onchange=e=>upd(g=>{g.fitToCeiling=e.target.checked;if(g.fitToCeiling){g.h=DEFAULT.height;g.elevation=0;}});
  $('#fC').onchange = e => upd(g => g.color = e.target.value);
  $('#aRot').onclick = () => rotateSel(45);
  $('#aDel').onclick = deleteSel;
  $('#aTop').onclick = () => moveLayer(1);
  $('#aBot').onclick = () => moveLayer(-1);
}

/* ======================= 操作 ======================= */
function select(sel){ ui.sel = sel; renderSel(); renderPanel(); }
function rotateSel(d){ if (ui.sel?.kind==='furn') mutate(() => { const f = getF(ui.sel.id); f.rot = norm(f.rot + d); }); }
function deleteSel(){ if (ui.sel?.kind==='furn'){ const id = ui.sel.id; ui.sel = null; mutate(() => state.furniture = state.furniture.filter(f => f.id !== id)); } }
function duplicateSel(){
  if (ui.sel?.kind !== 'furn') return;
  const f = getF(ui.sel.id), n = {...f, id:uid(), cx:f.cx+200, cy:f.cy+200};
  ui.sel = {kind:'furn', id:n.id}; mutate(() => state.furniture.push(n));
}
// 新放下的家具若压在墙 / 窗上，沿穿透较浅的方向推出来，刚好贴墙
function pushOut(f){
  for (let n = 0; n < 4; n++){
    let moved = false;
    for (const r of snapRects()){
      const {hw, hh} = aabb(f), ox = Math.min(f.cx+hw, r[2]) - Math.max(f.cx-hw, r[0]), oy = Math.min(f.cy+hh, r[3]) - Math.max(f.cy-hh, r[1]);
      if (ox <= 0 || oy <= 0) continue;
      if (ox < oy) f.cx = f.cx < (r[0]+r[2])/2 ? r[0]-hw : r[2]+hw;
      else f.cy = f.cy < (r[1]+r[3])/2 ? r[1]-hh : r[3]+hh;
      moved = true;
    }
    if (!moved) return;
  }
}
function addItem(it, x, y){
  const [type,name,w,d,color] = it, f = F(type,name,Math.round(x/10)*10,Math.round(y/10)*10,w,d,0,color);
  f.h=nominalHeights[type]||850;f.catalogKey=LIB.flatMap((g,ci)=>g.items.flatMap((v,ii)=>v===it?[ci+':'+ii]:[]))[0];f.elevation=type==='ksink'||type==='stove'?900:type==='tv'?750:type==='acwall'?2050:type==='waterheater'?1550:0;f.fitToCeiling=['wardrobe','bookshelf'].includes(type);Object.assign(f,catalogSpec(it));
  pushOut(f);
  ui.sel = {kind:'furn', id:f.id};
  mutate(() => type==='rug' ? state.furniture.unshift(f) : state.furniture.push(f));
  toast(tr(`已添加「${name}」${w}×${d}`, `Added "${nm(name)}" ${w}×${d}`));
}
function toggleWall(id){const w=WALLS[+id.slice(1)];if(!w||w[4]!=='n')return toast('原图黑填墙与建筑外墙不可拆改');const group=WALLS.flatMap((r,i)=>r[5]===w[5]?['w'+i]:[]),removed=wallRemoved(w[5]);mutate(()=>state.demolished=removed?state.demolished.filter(x=>!group.includes(x)):[...new Set([...state.demolished,...group])]);toast(removed?'已恢复整段隔墙':'已标记拆除整段非承重墙（可撤销）');}

function setTool(t){
  ui.tool = t; ui.mA = null; ui.mCur = null;
  svg.setAttribute('class', 'tool-' + t);
  document.querySelectorAll('#tools [data-tool]').forEach(b => b.classList.toggle('on', b.dataset.tool === t));
  syncModeHint();
  renderMeasure();
}
function syncModeHint(){
  const hints = {select:'',
    measure:COARSE ? tr('按住拖出测量线，或依次点两点 · 靠近墙面自动吸附 · 点「选择」退出', 'Hold and drag a line, or tap two points · snaps to walls · tap "Select" to exit')
      : tr('点击两点（或按住拖动）测量距离 · 靠近墙面自动吸附 · Shift 锁定水平/垂直 · Esc 取消', 'Click two points (or drag) to measure · snaps to walls · Shift locks horizontal/vertical · Esc cancels'),
    demolish:tr('点击普通墙标记拆除，再次点击恢复 · 原图承重墙锁定，可开启承重描边查看', 'Click a partition to remove or restore it · Bearing walls are locked; use the bearing outline to identify them')};
  const h = $('#modehint'); h.textContent = hints[ui.tool]; h.classList.toggle('show', !!hints[ui.tool]);
}

/* ======================= 视图 ======================= */
function applyView(){
  const W = svg.clientWidth, H = svg.clientHeight;
  svg.setAttribute('viewBox', `${view.x0} ${view.y0} ${W/view.s} ${H/view.s}`);
  const ratio = 1/(view.s*PX_MM);
  $('#ratio').textContent = '1:' + Math.round(ratio);
  renderSel(); renderMeasure();
}
function fitView(){
  const W = svg.clientWidth, H = Math.max(120,svg.clientHeight-64);
  view.s = Math.min(W/BOUNDS.w, H/BOUNDS.h);
  view.x0 = BOUNDS.x - (W/view.s - BOUNDS.w)/2; view.y0 = BOUNDS.y - (H/view.s - BOUNDS.h)/2;
  applyView();
}
function zoomAt(ns, mx, my){
  ns = Math.max(.012, Math.min(2, ns));
  const px = view.x0 + mx/view.s, py = view.y0 + my/view.s;
  view.s = ns; view.x0 = px - mx/ns; view.y0 = py - my/ns; applyView();
}
const zoomCenter = k => zoomAt(view.s*k, svg.clientWidth/2, svg.clientHeight/2);
const setRatio = r => zoomAt(1/(r*PX_MM), svg.clientWidth/2, svg.clientHeight/2);

function toMM(e){
  const pt = svg.createSVGPoint(); pt.x = e.clientX; pt.y = e.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

/* ======================= 吸附 ======================= */
const grid = () => 10;
function snapMove(f, cx, cy){
  let nx = Math.round(cx/grid())*grid(), ny = Math.round(cy/grid())*grid();
  if (!ui.layers.wallSnap) return [nx, ny];
  const {hw, hh} = aabb(f), tol = 10/view.s;
  let bx = tol, by = tol;
  for (const r of snapRects()){
    if (!(r[3] < cy-hh-tol || r[1] > cy+hh+tol)) for (const ex of [r[0], r[2]]) for (const c of [ex+hw, ex-hw]) if (Math.abs(c-cx) < bx){ bx = Math.abs(c-cx); nx = c; }
    if (!(r[2] < cx-hw-tol || r[0] > cx+hw+tol)) for (const ey of [r[1], r[3]]) for (const c of [ey+hh, ey-hh]) if (Math.abs(c-cy) < by){ by = Math.abs(c-cy); ny = c; }
  }
  return [nx, ny];
}
function snapPoint(p, shift){
  let x = Math.round(p.x/10)*10, y = Math.round(p.y/10)*10;
  const tol = 8/view.s; let bx = tol, by = tol;
  for (const r of snapRects()){
    if(p.y>=r[1]-tol&&p.y<=r[3]+tol)for (const ex of [r[0], r[2]]) if (Math.abs(ex-p.x) < bx){ bx = Math.abs(ex-p.x); x = ex; }
    if(p.x>=r[0]-tol&&p.x<=r[2]+tol)for (const ey of [r[1], r[3]]) if (Math.abs(ey-p.y) < by){ by = Math.abs(ey-p.y); y = ey; }
  }
  if (shift && ui.mA){ if (Math.abs(x-ui.mA.x) > Math.abs(y-ui.mA.y)) y = ui.mA.y; else x = ui.mA.x; }
  return {x, y};
}

/* ======================= 指针交互 ======================= */
let drag = null, pinch = null;
const touches = new Map();                     // 当前按在平面图上的手指
const svgXY = (x, y) => { const r = svg.getBoundingClientRect(); return [x - r.left, y - r.top]; };
function pinchInfo(){
  const [a, b] = [...touches.values()];
  return {d:Math.max(1, Math.hypot(b.x-a.x, b.y-a.y)), c:svgXY((a.x+b.x)/2, (a.y+b.y)/2)};
}
// 结束当前拖动：移动过的家具记入撤销栈
function endDrag(cancel){
  const d = drag; drag = null; svg.classList.remove('panning');
  if (!d) return;
  if (d.kind === 'measure'){
    if (cancel){ ui.mA = ui.mCur = null; renderMeasure(); return; }
    if (d.moved && ui.mA && ui.mCur && Math.hypot(ui.mCur.x-ui.mA.x, ui.mCur.y-ui.mA.y) > 20){
      const a = ui.mA, b = ui.mCur; ui.mA = ui.mCur = null; mutate(() => state.measures.push({a, b}));
    }
    renderMeasure(); return;                   // 没拖动：保留起点，等第二次点击
  }
  if (d.kind === 'pan'){
    if (!cancel && !d.moved && ui.tool === 'select') select(d.room ? {kind:'room', id:d.room} : null);
    return;
  }
  if(cancel&&(d.resizeStart||d.kind==='opening'||d.kind==='wallResize')){state=JSON.parse(d.before);renderAll();return;}
  if(d.moved){try{fixState(state);commit(d.before);}catch(e){state=JSON.parse(d.before);toast(e.message);}renderAll();}
}

svg.addEventListener('pointerdown', e => {
  if (e.button === 1 || e.button === 2) return;
  closeDrawers(); $('details.menu').open = false;
  if (e.pointerType !== 'mouse'){
    touches.set(e.pointerId, {x:e.clientX, y:e.clientY});
    svg.setPointerCapture(e.pointerId);
    if (touches.size >= 2){                    // 第二根手指落下：取消单指操作，进入双指缩放 / 平移
      endDrag(drag?.kind === 'measure' || drag?.kind === 'pan');
      const {d, c} = pinchInfo();
      pinch = {d, c, s:view.s, px:view.x0 + c[0]/view.s, py:view.y0 + c[1]/view.s};
      return;
    }
  }
  if (pinch) return;
  const p = toMM(e), t = e.target;
  if (ui.tool === 'measure'){
    const q = snapPoint(p, e.shiftKey);
    if (!ui.mA){ ui.mA = q; ui.mCur = q; drag = {kind:'measure', sx:e.clientX, sy:e.clientY, moved:false}; svg.setPointerCapture(e.pointerId); }
    else { const a = ui.mA; ui.mA = null; ui.mCur = null; if (Math.hypot(q.x-a.x, q.y-a.y) > 20) mutate(() => state.measures.push({a, b:q})); }
    renderMeasure(); return;
  }
  const h = t.closest('[data-handle]');
  if (h && ui.sel?.kind === 'furn'){
    drag = {kind:h.dataset.handle, id:ui.sel.id, sx:e.clientX, sy:e.clientY, before:snap(), moved:false};
    if (['size','width','widthLeft','depth'].includes(drag.kind)) drag.resizeStart = {...getF(drag.id), pointer:p};
  } else if (ui.tool === 'demolish' && t.closest('[data-wall]')){
    toggleWall(t.closest('[data-wall]').dataset.wall); return;
  } else if (ui.tool === 'select' && t.closest('[data-fid]')){
    const f = getF(t.closest('[data-fid]').dataset.fid);
    if (ui.sel?.id !== f.id) select({kind:'furn', id:f.id});
    drag = {kind:'move', id:f.id, sx:e.clientX, sy:e.clientY, ox:p.x-f.cx, oy:p.y-f.cy, before:snap(), moved:false};
  } else {
    const room = t.closest('[data-room]');
    drag = {kind:'pan', sx:e.clientX, sy:e.clientY, x0:view.x0, y0:view.y0, room:room && room.dataset.room, moved:false};
  }
  svg.setPointerCapture(e.pointerId);
});

svg.addEventListener('pointermove', e => {
  if (touches.has(e.pointerId)) touches.set(e.pointerId, {x:e.clientX, y:e.clientY});
  if (pinch){
    if (touches.size < 2) return;
    const {d, c} = pinchInfo(), ns = Math.max(.012, Math.min(2, pinch.s * d / pinch.d));
    view.s = ns; view.x0 = pinch.px - c[0]/ns; view.y0 = pinch.py - c[1]/ns; applyView();
    return;
  }
  const p = toMM(e);
  $('#cx').textContent = Math.round(p.x) + ' mm'; $('#cy').textContent = Math.round(p.y) + ' mm';
  if (!drag){
    const room = e.target.closest && e.target.closest('[data-room]');
    $('#hover').innerHTML = room ? `<b>${esc(state.rooms[room.dataset.room].name)}</b> ${fmt(area(ROOMS.find(r=>r.id===room.dataset.room).poly))} m²` : '';
    if (ui.tool === 'measure' && ui.mA){ ui.mCur = snapPoint(p, e.shiftKey); renderMeasure(); }
    return;
  }
  const far = Math.hypot(e.clientX-drag.sx, e.clientY-drag.sy) >= TAP;
  if (drag.kind === 'measure'){
    if (far) drag.moved = true;
    ui.mCur = snapPoint(p, e.shiftKey); renderMeasure(); return;
  }
  if (drag.kind === 'pan'){
    if (!drag.moved && !far) return;
    drag.moved = true; svg.classList.add('panning');
    view.x0 = drag.x0 - (e.clientX-drag.sx)/view.s; view.y0 = drag.y0 - (e.clientY-drag.sy)/view.s; applyView(); return;
  }
  if(drag.kind==='wallResize'){
    if(e.pointerId!==drag.pointerId)return;
    if(!drag.moved&&!far)return;
    const w=state.walls.find(w=>w.id===drag.id);if(!w)return;
    const changed=resizeWallFromPointer(w,drag,p);
    if(!changed)return;
    drag.moved=true;clearOpeningDoorPose(w.id);
    syncGeometry();renderWalls();renderOpenings();renderSel();renderFab();
    if($('#wLength'))$('#wLength').value=Math.round(Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]));
    for(const [id,v]of [['wAx',w.a[0]],['wAy',w.a[1]],['wBx',w.b[0]],['wBy',w.b[1]],['wThickness',w.t]])if($('#'+id))$('#'+id).value=v;
    return;
  }
  if(drag.kind==='opening'){
    if(e.pointerId!==drag.pointerId)return;
    const delta=(p.x-drag.point.x)*drag.axis[0]+(p.y-drag.point.y)*drag.axis[1];
    if(!drag.moved&&Math.abs(delta)*view.s<TAP)return;
    const hit=selectedOpening(drag.selection);if(!hit)return;
    const next=clampOpeningAt(drag.at+Math.round(delta/10)*10,drag.range);
    if(next===hit.o.at)return;
    hit.o.at=next;drag.moved=true;clearOpeningDoorPose(hit.w.id);
    syncGeometry();renderWalls();renderOpenings();renderSel();renderFab();
    if($('#openingAt'))$('#openingAt').value=next;
    return;
  }
  const f = getF(drag.id); if (!f) return;
  if (!drag.moved && !far) return;             // 轻点家具不应让它抖动一下
  drag.moved = true;
  if (drag.kind === 'move'){
    [f.cx, f.cy] = snapMove(f, p.x-drag.ox, p.y-drag.oy);
  } else if (drag.kind === 'rot'){
    let a = Math.atan2(p.y-f.cy, p.x-f.cx)*180/Math.PI + 90;
    f.rot = norm(e.shiftKey ? a : Math.round(a/15)*15);
  } else if (['size','width','widthLeft','depth'].includes(drag.kind)){
    // Keep the original axes and pointer offset throughout the resize gesture.
    const start=drag.resizeStart,a=start.rot*Math.PI/180,c=Math.cos(a),s=Math.sin(a);
    const dx=p.x-start.pointer.x,dy=p.y-start.pointer.y,lx=dx*c+dy*s,ly=-dx*s+dy*c;
    const size=v=>Math.min(15000,Math.max(100,Math.round(v/10)*10));
    const sign=drag.kind==='widthLeft'?-1:1;
    const nw=drag.kind==='depth'?start.w:size(start.w+lx*sign),nd=['width','widthLeft'].includes(drag.kind)?start.d:size(start.d+ly);
    const mx=(nw-start.w)/2*sign,my=(nd-start.d)/2;
    f.cx=start.cx+mx*c-my*s;f.cy=start.cy+mx*s+my*c;f.w=nw;f.d=nd;
  }
  renderFurn(); renderSel();
});

function onPointerEnd(e){
  touches.delete(e.pointerId);
  if (pinch){ if (touches.size < 2) pinch = null; return; }   // 双指结束后，剩下的手指不再触发操作
  endDrag(e.type === 'pointercancel');
}
svg.addEventListener('pointerup', onPointerEnd);
svg.addEventListener('pointercancel', onPointerEnd);
// 阻止 iPad Safari 把双指手势当成整页缩放
['gesturestart','gesturechange','gestureend'].forEach(t => document.addEventListener(t, e => e.preventDefault()));

svg.addEventListener('wheel', e => {
  e.preventDefault();
  const r = svg.getBoundingClientRect();
  zoomAt(view.s*Math.exp(-e.deltaY*(e.ctrlKey ? .01 : .0015)), e.clientX-r.left, e.clientY-r.top);
}, {passive:false});
svg.addEventListener('dblclick', e => { if (ui.tool==='select' && e.target.closest('[data-fid]')) rotateSel(45); });
svg.addEventListener('contextmenu', e => { if (ui.tool==='measure'){ e.preventDefault(); ui.mA = null; renderMeasure(); } });


/* ======================= 键盘 ======================= */
document.addEventListener('keydown', e => {
  if (e.target.matches('input,select,textarea')) return;
  if (window.View3D?.walking()) return;
  const mod = e.metaKey || e.ctrlKey, k = e.key.toLowerCase();
  if (mod && k === 'z'){ e.preventDefault(); e.shiftKey ? redo() : undo(); return; }
  if (mod && k === 'y'){ e.preventDefault(); redo(); return; }
  if (mod && k === 'd'){ e.preventDefault(); duplicateSel(); return; }
  if (mod) return;
  if (k === '[' || k === ']'){ drawer(k === '[' ? 'lib' : 'panel'); return; }
  if (k === 'f' && e.shiftKey){ toggleFullscreen(); return; }
  if (k === 't') setView(is3D() ? '2d' : '3d');
  else if (is3D() && ['v','m','x','f','+','=','-'].includes(k)) return;
  else if (k === 'v') setTool('select');
  else if (k === 'm') setTool('measure');
  else if (k === 'x') setTool('demolish');
  else if (k === 'f') fitView();
  else if (k === 'r') rotateSel(e.shiftKey ? -45 : 45);
  else if (k === 'delete' || k === 'backspace'){ e.preventDefault(); deleteSel(); }
  else if (k === 'escape'){ if (ui.mA){ ui.mA = null; renderMeasure(); } else { if (ui.tool !== 'select') setTool('select'); select(null); } }
  else if (k.startsWith('arrow') && ui.sel?.kind === 'furn'){
    e.preventDefault(); const st = e.shiftKey ? 100 : 10;
    mutate(() => { const f = getF(ui.sel.id); if (k==='arrowleft') f.cx -= st; if (k==='arrowright') f.cx += st; if (k==='arrowup') f.cy -= st; if (k==='arrowdown') f.cy += st; });
  }
  else if (k === '+' || k === '=') zoomCenter(1.25);
  else if (k === '-') zoomCenter(.8);
});

/* ======================= 家具库 ======================= */
function buildLib(){
  $('#lib').innerHTML = '<div class=library-filter hidden><input id=libSearch type=search placeholder="搜索家具 / 家电" aria-label="搜索家具"><select id=libCategory aria-label="家具分类"><option value="">全部分类</option>'+LIB.map((g,i)=>`<option value=${i}>${nm(g.cat)}</option>`).join('')+'</select></div>'+LIB.map((c,ci) => !c.items.some(it=>!REMOVED_CATALOG_TYPES.has(it[0]))?'':`<h4>${nm(c.cat)}</h4><div class="lib-grid">${c.items.map((it,ii) => {
    if(REMOVED_CATALOG_TYPES.has(it[0]))return '';
    const [t,n,w,d,col] = it, pad = Math.max(w,d)*.08;
    return `<div class="item" data-key="${ci}:${ii}" title="${tr('点击添加，或拖到平面图中的指定位置', 'Click to add, or drag onto the plan')}">
      <svg viewBox="${-w/2-pad} ${-d/2-pad} ${w+2*pad} ${d+2*pad}">${furnSVG(t,w,d,col,catalogSpec(it))}</svg><b>${esc(nm(n))}</b><small>${w}×${d}</small></div>`;
  }).join('')}</div>`).join('') + `<div class="hint">${tr(
    `家具按真实尺寸（mm）绘制。${COARSE ? '点一下放到画面中央，或按住向右拖到平面图 / 3D 地面上的指定位置（上下滑动为滚动列表）。' : '点击添加到画面中央，或直接拖到平面图 / 3D 地面上。'}添加后可在右侧修改宽深与颜色。`,
    `Furniture is drawn at real size (mm). ${COARSE ? 'Tap to place at the center, or hold and drag right onto the plan / 3D floor (swipe up/down to scroll).' : 'Click to add at the center, or drag onto the plan / 3D floor.'} Edit size and color in the right panel afterwards.`)}</div>`;
  bindLibraryFilters();
  document.querySelectorAll('.item').forEach(el => el.addEventListener('pointerdown', e => {
    if (e.button) return;
    libDrag = {el, id:e.pointerId, sx:e.clientX, sy:e.clientY, it:itemOf(el), ghost:null};
  }));
}
const itemOf = el => { const [ci, ii] = el.dataset.key.split(':').map(Number); return LIB[ci].items[ii]; };

// 家具库拖放：用 pointer 事件实现（iPad 上 HTML5 拖放不可靠）。
// 列表设置了 touch-action:pan-y，竖向滑动交给浏览器滚动（会触发 pointercancel），横向拖动才开始拖放。
let libDrag = null;
// 屏幕坐标 → 户型坐标（mm）。2D 取平面图坐标，3D 取射线与地面的交点；s = 该处每 mm 的屏幕像素数
function dropPoint(x, y){
  const r = $('#stage').getBoundingClientRect();
  if (x < r.left || x > r.right || y < r.top || y > r.bottom) return null;
  if (document.elementFromPoint(x, y)?.closest('aside.open,#fab,#joy,#walkExit,#viewportActions')) return null;
  if (is3D()) return window.View3D?.groundAt(x, y) || null;
  const p = toMM({clientX:x, clientY:y}); return {x:p.x, y:p.y, s:view.s};
}
addEventListener('pointermove', e => {
  if (!libDrag || e.pointerId !== libDrag.id) return;
  const {it} = libDrag;
  if (!libDrag.ghost){
    if (Math.hypot(e.clientX-libDrag.sx, e.clientY-libDrag.sy) < TAP) return;
    const g = libDrag.ghost = document.createElement('div'); g.id = 'ghost';
    g.innerHTML = `<svg viewBox="${-it[2]/2} ${-it[3]/2} ${it[2]} ${it[3]}">${furnSVG(it[0],it[2],it[3],it[4],catalogSpec(it))}</svg>`;
    document.body.appendChild(g); libDrag.el.classList.add('dragging');
  }
  // 幽灵图按落点处的比例显示真实大小（3D 中近大远小）
  const g = libDrag.ghost, s = Math.max(dropPoint(e.clientX, e.clientY)?.s || (is3D() ? .05 : view.s), .02);
  Object.assign(g.style, {width:Math.max(28, it[2]*s)+'px', height:Math.max(20, it[3]*s)+'px', left:e.clientX+'px', top:e.clientY+'px'});
  const lib = $('aside.lib');
  if (narrow() && lib.classList.contains('open') && e.clientX > lib.getBoundingClientRect().right) drawer(null);   // 拖出抽屉后自动收起
});
function endLibDrag(e, ok){
  if (!libDrag || e.pointerId !== libDrag.id) return;
  const d = libDrag; libDrag = null;
  d.el.classList.remove('dragging');
  if (d.ghost){
    d.ghost.remove();
    if (!ok) return;
    const p = dropPoint(e.clientX, e.clientY);
    if (p) addItem(d.it, p.x, p.y);
    else if (is3D() && e.clientX > $('#stage').getBoundingClientRect().left) toast(tr('请拖到地面上', 'Drop it on the floor'));
    return;
  }
  if (!ok) return;
  if(DOOR_COMPONENTS[d.it[0]]){armDoorComponent(d.it[0]);closeDrawers();return;}
  // 轻点：放到选中房间中心，否则放到画面中心（3D 取屏幕中心对应的地面位置）
  let p = null;
  if (ui.sel?.kind === 'room'){ const b = bbox(ROOMS.find(r => r.id===ui.sel.id).poly); p = {x:(b[0]+b[2])/2, y:(b[1]+b[3])/2}; }
  else if (is3D()){ const r = $('#stage').getBoundingClientRect(); p = window.View3D.groundAt(r.left + r.width/2, r.top + r.height/2); }
  if (!p) p = {x:view.x0 + svg.clientWidth/2/view.s, y:view.y0 + svg.clientHeight/2/view.s};
  addItem(d.it, p.x, p.y);
  closeDrawers();
}
addEventListener('pointerup', e => endLibDrag(e, true));
addEventListener('pointercancel', e => endLibDrag(e, false));

/* ======================= 导入导出 ======================= */
function download(name, blob){ const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = name; a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000); }
function exportPNG(){
  if (is3D()) return window.View3D.shot();
  const clone = svg.cloneNode(true), W = 3200, H = Math.round(W*BOUNDS.h/BOUNDS.w);
  clone.setAttribute('viewBox', `${BOUNDS.x} ${BOUNDS.y} ${BOUNDS.w} ${BOUNDS.h}`);
  clone.setAttribute('width', W); clone.setAttribute('height', H);
  clone.querySelector('#gSel').innerHTML = '';
  clone.querySelector('#gGrid').innerHTML = `<rect x="-20000" y="-20000" width="55000" height="55000" fill="${ui.layers.grid?'url(#grid)':'#f7f4ee'}"/>`;
  const bg = document.createElementNS('http://www.w3.org/2000/svg','rect');
  Object.entries({x:-20000,y:-20000,width:55000,height:55000,fill:'#f7f4ee'}).forEach(([k,v]) => bg.setAttribute(k,v));
  clone.insertBefore(bg, clone.querySelector('#gGrid'));
  const img = new Image();
  img.onload = () => {
    const cv = document.createElement('canvas'); cv.width = W; cv.height = H;
    cv.getContext('2d').drawImage(img, 0, 0, W, H);
    cv.toBlob(b => download(tr('户型装修方案', 'floor-plan-design') + '.png', b));
  };
  img.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(new XMLSerializer().serializeToString(clone));
}

/* ======================= 杂项 ======================= */
let toastT;
function toast(msg){ const t = $('#toast'); t.textContent = msg; t.classList.add('show'); clearTimeout(toastT); toastT = setTimeout(() => t.classList.remove('show'), 1800); }

/* ======================= 2D / 3D 切换 ======================= */
let viewMode = '2d', switching = false;
const is3D = () => viewMode === '3d';
const TIPS = () => COARSE
  ? {'2d':tr('点或拖动家具库添加 · 单指拖动平移 · 双指缩放 · 选中家具后底部工具条可旋转 / 复制 / 删除', 'Tap or drag from the library · 1 finger pans · pinch zooms · bottom bar rotates / duplicates / deletes'),
     '3d':tr('单指旋转 · 双指缩放 / 平移 · 点家具或地面编辑 · 点门开关', '1 finger orbits · 2 fingers zoom / pan · tap furniture or floor to edit · tap doors to open')}
  : {'2d':tr('拖动左侧家具到平面图 · 滚轮缩放 · 拖动空白处平移 · T 切换 3D', 'Drag furniture onto the plan · scroll to zoom · drag empty space to pan · T for 3D'),
     '3d':tr('3D 场景与平面方案实时同步 · 右侧面板修改会立即生效 · T 返回 2D', '3D stays in sync with the plan · panel edits apply instantly · T for 2D')};
async function setView(m){if(m===viewMode||switching)return;$('#toolbarMore').open=false;document.querySelector('aside.lib').scrollTop=0;document.querySelector('aside.right').scrollTop=0;switching=true;document.body.classList.add('busy');try{if(previewMode)setPreview(false);viewMode=m;if(m==='3d'){if(ui.tool!=='select')setTool('select');ui.mA=null;document.body.classList.add('m3d');await window.View3D.enter();}else{document.body.classList.remove('m3d');await window.View3D.exit();applyView();}$('#tip').textContent=TIPS()[m];renderPanel();syncPaneBtns();}catch(e){console.error(e);viewMode='2d';document.body.classList.remove('m3d');stage.classList.remove('is3d','animating');toast('3D 初始化失败，请检查浏览器是否启用 WebGL');}finally{switching=false;document.body.classList.remove('busy');}}

document.querySelectorAll('.menu-pop .btn').forEach(b => b.addEventListener('click', () => b.closest('details').open = false));
document.querySelectorAll('#viewSeg .btn').forEach(b => b.onclick = () => setView(b.dataset.view));

document.querySelectorAll('#tools [data-tool]').forEach(b => b.onclick = () => setTool(b.dataset.tool));
document.querySelectorAll('#layers .btn').forEach(b => b.onclick = () => {
  const k = b.dataset.layer; ui.layers[k] = !ui.layers[k]; b.classList.toggle('on', ui.layers[k]);
  if (k === 'dims') $('#gDims').setAttribute('display', ui.layers.dims ? 'inline' : 'none');
  else if (k !== 'wallSnap') renderAll();
  syncQuickActions();
});
$('#zoomIn').onclick = () => zoomCenter(1.25);
$('#zoomOut').onclick = () => zoomCenter(.8);
$('#fit').onclick = fitView;
$('#s60') && ($('#s60').onclick = () => { setRatio(60); toast(tr('已按 1:60 显示（与原始户型图同比例）', 'Showing at 1:60 (same scale as the original plan)')); });
$('#s100') && ($('#s100').onclick = () => setRatio(100));
$('#undo').onclick = undo; $('#redo').onclick = redo;
$('#clearAll').onclick = clearLayout;

/* 全屏：标准 API + Safari（iPad）的 webkit 前缀版本 */
const fsEl = () => document.fullscreenElement || document.webkitFullscreenElement;
function toggleFullscreen(){
  const de = document.documentElement;
  if (fsEl()) (document.exitFullscreen || document.webkitExitFullscreen).call(document);
  else {
    const req = de.requestFullscreen || de.webkitRequestFullscreen;
    if (!req) return toast(tr('当前浏览器不支持网页全屏，可在 Safari 中「添加到主屏幕」后以全屏方式打开', 'Fullscreen is not supported here — in Safari, use "Add to Home Screen" to open it fullscreen'));
    Promise.resolve(req.call(de)).catch(() => toast(tr('无法进入全屏', 'Could not enter fullscreen')));
  }
}
function syncFullscreen(){
  const on = !!fsEl(), b = $('#fullscreen');
  b.textContent = '⛶ ' + (on ? tr('退出全屏', 'Exit fullscreen') : tr('全屏', 'Fullscreen'));
  b.title = (on ? tr('退出全屏', 'Exit fullscreen') : tr('全屏', 'Fullscreen')) + ' (Shift+F)';
}
$('#fullscreen').onclick = toggleFullscreen;
['fullscreenchange', 'webkitfullscreenchange'].forEach(t => document.addEventListener(t, syncFullscreen));
// 已从主屏幕以独立 App 方式打开时本就是全屏，隐藏按钮
if (navigator.standalone || matchMedia('(display-mode: standalone)').matches) $('#fullscreen').hidden = true;
$('#tgLib').onclick = () => drawer('lib');
$('#tgPanel').onclick = () => drawer('panel');
// 触屏上点菜单以外的地方收起「文件」菜单
document.addEventListener('pointerdown', e => { const m = $('details.menu'); if (m.open && !m.contains(e.target)) m.open = false; });
matchMedia('(max-width:1100px)').addEventListener('change', () => drawer(null));
drawer(null);                                  // 恢复上次的面板收起状态
$('#exportPng').onclick = exportPNG;
$('#exportJson').onclick = () => download(tr('户型装修方案', 'floor-plan-design') + '.json', new Blob([JSON.stringify(state, null, 2)], {type:'application/json'}));
$('#importJson').onclick = () => $('#fileIn').click();
$('#fileIn').onchange = e => {
  const file = e.target.files[0]; if (!file) return;
  file.text().then(txt => {
    try { const s = JSON.parse(txt); if (!Array.isArray(s.furniture)) throw 0; const b = snap(); state = fixState(s); ui.sel = null; commit(b); renderAll(); toast(tr('方案已导入', 'Plan imported')); }
    catch(err){ toast(tr('导入失败：'+(err.message||'文件格式不正确'), 'Import failed: '+(err.message||'Invalid file format'))); }
  });
  e.target.value = '';
};
$('#reset').onclick = () => { if (confirm(tr('恢复为默认设计方案？（可撤销）', 'Reset to the default design? (undoable)'))){ const b = snap(); state = defaultState(); ui.sel = null; commit(b); renderAll(); } };
// 横竖屏切换、表头换行等都会改变画布尺寸；尺寸从 0 恢复（如首次布局）时重新适应窗口
// 其余尺寸变化（收起 / 展开面板等）保持画面中心不动
let lastW = 0, lastH = 0;
new ResizeObserver(() => {
  const w = svg.clientWidth, h = svg.clientHeight; if (!w) return;
  if (!lastW) fitView();
  else { view.x0 -= (w - lastW)/2/view.s; view.y0 -= (h - lastH)/2/view.s; applyView(); }
  lastW = w; lastH = h;
}).observe(svg);

function setLang(l){
  LANG = l; try { localStorage.setItem(LANG_KEY, l); } catch(e) {}
  applyStaticLang(); syncFullscreen(); syncModeHint(); syncPaneBtns();
  buildLib(); renderOpenings(); renderAll();
  $('#tip').textContent = TIPS()[viewMode];
  window.View3D?.relang();
}
$('#langBtn').onclick = () => setLang(LANG === 'en' ? 'zh' : 'en');




/* ============================================================
 *  3D 场景（three.js）—— 与 2D 共用 state / ui，切换时带过渡动画：
 *  2D → 3D：3D 相机先以正俯视对齐当前 2D 视口（比例、位置一致），
 *           交叉淡入后镜头倾斜环绕、墙体从地面升起、家具随后立起；
 *  3D → 2D：反向——家具收起、墙体下沉、镜头回到正俯视并淡出到平面图。
 * ============================================================ */
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {CSS2DRenderer, CSS2DObject} from 'three/addons/renderers/CSS2DRenderer.js';

const stage = $('#stage'), host = $('#view3d');
const OX = DEFAULT.width/2, OY = DEFAULT.depth/2, H = DEFAULT.height/1000, FOV = 45;       // 户型中心放在世界原点，层高来自案例数据
const wx = x => (x - OX) / 1000, wz = y => (y - OY) / 1000, M = v => v / 1000;
const SW = () => stage.clientWidth, SH = () => stage.clientHeight;
const opt = {grid:false,cut:H, furn:true, labels:false, night:false, hour:10, mode:'orbit'};

let inited = false, active = false, raf = 0, anim = null, fly = null;
let renderer, labelRenderer, scene, camera, orbit, hemi, sun, ground, glassMat, wallMat, capMat, frameMat;
let archFloor, archUp, furnG, labelG, lampG, colliders = [], selKey = null, selHelper = null;
let sigArch = '', sigFurn = '', sigLabels = '', grow = 1, furnGrow = 1;
const doors = [], keys = {};

/* ======================= 初始化 ======================= */
function init(){
  if (inited) return; inited = true;
  renderer = new THREE.WebGLRenderer({antialias:true, preserveDrawingBuffer:true});
  renderer.setPixelRatio(devicePixelRatio);
  renderer.setSize(SW(), SH());
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap; renderer.shadowMap.autoUpdate=false;
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  host.prepend(renderer.domElement);
  labelRenderer = new CSS2DRenderer();
  labelRenderer.setSize(SW(), SH());
  Object.assign(labelRenderer.domElement.style, {position:'absolute', inset:'0', pointerEvents:'none'});
  host.appendChild(labelRenderer.domElement);

  scene = new THREE.Scene();
  camera = new THREE.PerspectiveCamera(FOV, SW()/SH(), .05, 300);
  orbit = new OrbitControls(camera, renderer.domElement);
  orbit.enableDamping = true; orbit.maxPolarAngle = Math.PI*.495; orbit.minDistance = 1.5; orbit.maxDistance = 45;
  hemi = new THREE.HemisphereLight(0xfff8ee, 0xb9a88f, 1.1);
  sun = new THREE.DirectionalLight(0xfff1dd, 2.6);
  const sceneGrid=new THREE.GridHelper(Math.ceil(Math.max(DEFAULT.width,DEFAULT.depth)/1000+8),Math.ceil((Math.max(DEFAULT.width,DEFAULT.depth)/1000+8)*2),0xc4b9a8,0xe4dccf);sceneGrid.position.y=.004;sceneGrid.visible=false;sceneGrid.userData.grid=true;scene.add(sceneGrid);
  sun.castShadow = true; sun.shadow.mapSize.setScalar(2048);   // 平板 GPU 用小一点的阴影贴图
  Object.assign(sun.shadow.camera, {left:-(DEFAULT.width/1000+2), right:DEFAULT.width/1000+2, top:DEFAULT.depth/1000+2, bottom:-(DEFAULT.depth/1000+2), near:1, far:60});
  sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
  ground = new THREE.Mesh(new THREE.PlaneGeometry(160, 160), new THREE.MeshStandardMaterial({color:0xf2eee7, roughness:1}));
  ground.rotation.x = -Math.PI/2; ground.position.y = -0.015; ground.receiveShadow = true;
  scene.add(hemi, sun, sun.target, ground);

  const pm = new THREE.PMREMGenerator(renderer); envTex = pm.fromScene(new RoomEnvironment(), .04).texture; pm.dispose();
  glassMat = new THREE.MeshPhysicalMaterial({color:0xcfe6ef, roughness:.05, transparent:true, opacity:.28, depthWrite:false, side:THREE.DoubleSide});
  wallMat = mat('#f4f1eb', {roughness:.92}); capMat = new THREE.MeshBasicMaterial({color:'#111111',toneMapped:false}); capMat.userData.finishRole='wall-cut'; frameMat = mat('#5d6166', {roughness:.5, metalness:.4});

  archFloor = new THREE.Group(); archUp = new THREE.Group(); furnG = new THREE.Group(); labelG = new THREE.Group(); lampG = new THREE.Group();
  scene.add(archFloor, archUp, furnG, labelG, lampG);

  const cv = renderer.domElement; let downAt = null, look = null;
  cv.addEventListener('pointerdown', e => {
    downAt = [e.clientX, e.clientY]; window.closeDrawers();
    if (opt.mode==='walk'&&!touchWalk&&!walkCtl?.isLocked)startTouchWalk();
    if (touchWalk && !look){ look = {id:e.pointerId, x:e.clientX, y:e.clientY}; cv.setPointerCapture(e.pointerId); }
  });
  cv.addEventListener('pointermove', e => {
    if (!look || e.pointerId !== look.id) return;
    lookBy(e.clientX - look.x, e.clientY - look.y); look.x = e.clientX; look.y = e.clientY;
  });
  cv.addEventListener('pointercancel', e => { if (look?.id === e.pointerId) look = null; });

  // 按住已选中的家具拖动：沿地面摆放（与 2D 共用网格和贴墙吸附）。
  // 在父元素上用捕获阶段监听，赶在 OrbitControls 之前关掉它，避免同时旋转镜头
  let fdrag = null;
  host.addEventListener('pointerdown', e => {
    if (e.target !== cv || !e.isPrimary || anim || opt.mode !== 'orbit' || ui.sel?.kind !== 'furn') return;
    const h = pick(e), f = h?.fid === ui.sel.id && getF(h.fid), g = f && groundAt(e.clientX, e.clientY);
    if (!g) return;
    fdrag = {id:f.id, pid:e.pointerId, sx:e.clientX, sy:e.clientY, ox:g.x - f.cx, oy:g.y - f.cy, before:snap(), moved:false};
    orbit.enabled = false; fly = null; cv.setPointerCapture(e.pointerId);
  }, true);
  cv.addEventListener('pointermove', e => {
    if (!fdrag || e.pointerId !== fdrag.pid) return;
    if (!fdrag.moved && Math.hypot(e.clientX - fdrag.sx, e.clientY - fdrag.sy) < TAP) return;
    const f = getF(fdrag.id), g = groundAt(e.clientX, e.clientY); if (!f || !g) return;
    fdrag.moved = true; cv.style.cursor = 'grabbing';
    [f.cx, f.cy] = snapMove(f, g.x - fdrag.ox, g.y - fdrag.oy);
    furnG.children.find(o => o.userData.fid === f.id)?.position.set(wx(f.cx), M(f.elevation||0), wz(f.cy));syncAssemblyModels();   // 拖动中只挪模型，松手再整体同步
  });
  const endF = e => {
    if (!fdrag || e.pointerId !== fdrag.pid) return;
    const d = fdrag; fdrag = null; orbit.enabled = true; cv.style.cursor = '';
    if(d.moved){try{fixState(state);commit(d.before);}catch(e){state=JSON.parse(d.before);toast(e.message);}renderAll();}
  };
  cv.addEventListener('pointerup', endF); cv.addEventListener('pointercancel', endF);

  cv.addEventListener('pointerup', e => {
    const tap = downAt && Math.hypot(e.clientX-downAt[0], e.clientY-downAt[1]) <= TAP;
    if(tap&&opt.mode==='walk')revealWalkControls();
    if (look?.id === e.pointerId){
      look = null;
      if (tap){ const h = pick(e); if (h?.door && h.dist < 3.5) toggleDoor(h.door); }   // 漫游时点门开关
      return;
    }
    if (anim || opt.mode !== 'orbit' || !tap) return;
    const h = pick(e);
    if (h?.opening && !previewMode) window.select(h.opening);
    else if (h?.wall && !previewMode) window.select({kind:'wall',id:h.wall});
    else if (h?.door) toggleDoor(h.door);
    else if (h?.fid) window.select({kind:'furn', id:h.fid});
    else if (h?.room) window.select({kind:'room', id:h.room});
    else window.select(null);
  });
  new ResizeObserver(() => {
    renderer.setSize(SW(), SH()); labelRenderer.setSize(SW(), SH());
    camera.aspect = SW()/SH(); camera.updateProjectionMatrix();
  }).observe(stage);
  bindUI();
}

/* ======================= 材质 ======================= */
const matCache = new Map();
let envTex = null, envK = 1;
function mat(color, o = {}){
  const key = color + JSON.stringify(o);
  if (!matCache.has(key)){
    const m = new THREE.MeshStandardMaterial({color, roughness:.7, ...o});
    // 金属 / 光滑表面挂环境反射，墙面等哑光材质不挂，避免整体变亮
    if (envTex && (m.metalness > 0 || m.roughness < .4)){ m.envMap = envTex; m.userData.env = m.metalness > .5 ? 1 : .5; m.envMapIntensity = m.userData.env*envK; }
    matCache.set(key, m);
  }
  return matCache.get(key);
}
// A dedicated ceiling finish keeps every visible top surface neutral and identifiable on export.
function ceilingFinishMaterial(textured=false){
 const m=textured?surfaceMaterial(finishPalette().ceiling,'plaster'):mat(finishPalette().ceiling,{roughness:1}).clone();
 m.userData.finishRole='ceiling';m.roughness=.94;m.metalness=0;
 // Small local finish lift avoids a charcoal-looking underside without washing out the whole room.
 m.emissive=new THREE.Color(finishPalette().ceiling);m.emissiveIntensity=LIGHTING_PROFILE.ceilingLift;return m;
}
function rng(seed){ return () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const rgbK = (hex, k) => { const n = parseInt(hex.slice(1), 16); const f = v => Math.max(0, Math.min(255, Math.round(v*k))); return `rgb(${f(n>>16&255)},${f(n>>8&255)},${f(n&255)})`; };
// 地面贴图按真实尺寸平铺（UV 单位 = 米）
const TEX = {
  wood:{sx:1.8, sy:.36, base:'#c8b59a', rough:.6}, walnut:{sx:1.8, sy:.36, base:'#9a6f4b', rough:.5},
  tile800:{sx:.8, sy:.8, base:'#ebe6dd', grout:'#cfc6b7', rough:.3}, tile600:{sx:.6, sy:.6, base:'#dfe3e0', grout:'#bfc6c1', rough:.35},
  antislip:{sx:.3, sy:.3, base:'#d3d8d4', grout:'#aab2ac', rough:.8}, marble:{sx:1.2, sy:1.2, base:'#f2efe9', grout:'#d9d2c4', rough:.18},
  terrazzo:{sx:.5, sy:.5, base:'#e6dfd3', rough:.4}, carpet:{sx:.3, sy:.3, base:'#c6bfd2', rough:1},
};
const floorMats = {};
function floorMat(kind){
  if (floorMats[kind]) return floorMats[kind];
  const s = TEX[kind] || TEX.tile800, R = rng(kind.length*977 + 13), cv = document.createElement('canvas');
  const wood = kind === 'wood' || kind === 'walnut';
  cv.width = wood ? 1024 : 512; cv.height = wood ? 205 : 512;
  const g = cv.getContext('2d'), W = cv.width, Hh = cv.height;
  g.fillStyle = s.base; g.fillRect(0, 0, W, Hh);
  if (wood){
    const rowH = Hh/2, joints = [[W*2/3], [W/3]];
    for (let r = 0; r < 2; r++){
      let x0 = 0;
      [...joints[r], W].forEach(x1 => {
        g.fillStyle = rgbK(s.base, .9 + R()*.2); g.fillRect(x0, r*rowH, x1-x0, rowH);
        g.strokeStyle = rgbK(s.base, .8); g.globalAlpha = .35; g.lineWidth = 1.2;
        for (let k = 0; k < 7; k++){ const y = r*rowH + 6 + R()*(rowH-12); g.beginPath(); g.moveTo(x0, y);
          for (let x = x0; x <= x1; x += 40) g.lineTo(x, y + Math.sin(x*.02 + k)*2.5); g.stroke(); }
        g.globalAlpha = 1; g.fillStyle = rgbK(s.base, .62); g.fillRect(x1-1.5, r*rowH, 3, rowH); x0 = x1;
      });
      g.fillStyle = rgbK(s.base, .62); g.fillRect(0, r*rowH, W, 2.5);
    }
  } else if (kind === 'marble'){
    paintMarbleVeins(g,W,Hh,R,CASE.presentation);
  } else if (kind === 'terrazzo'){
    const cs = ['#b9a58c','#8fa3a0','#c9b7a2','#a88f76','#7e8a86'];
    for (let k = 0; k < 160; k++){ g.fillStyle = cs[k%5]; g.beginPath(); g.arc(R()*W, R()*Hh, 2 + R()*7, 0, 7); g.fill(); }
  } else {
    for (let k = 0; k < 1500; k++){ g.fillStyle = `rgba(0,0,0,${R()*.04})`; g.fillRect(R()*W, R()*Hh, 2, 2); }
  }
  if (s.grout){ g.fillStyle = s.grout; g.fillRect(0, 0, W, 3); g.fillRect(0, 0, 3, Hh); }
  const t = new THREE.CanvasTexture(cv);
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1/s.sx, 1/s.sy);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = renderer.capabilities.getMaxAnisotropy();
  return floorMats[kind] = new THREE.MeshStandardMaterial({map:t, roughness:s.rough});
}

/* ======================= 几何小工具（y = 底面高度） ======================= */
const asMat = m => typeof m === 'string' ? mat(m) : m;
const sh = o => { o.castShadow = o.receiveShadow = true; return o; };
const mesh = (geo, m) => sh(new THREE.Mesh(geo, asMat(m)));
const rot = (o, x = 0, y = 0, z = 0) => { o.rotation.set(x, y, z); return o; };
function box(w, h, d, m, x = 0, y = 0, z = 0){
  const o = mesh(new THREE.BoxGeometry(w, h, d), m); o.position.set(x, y + h/2, z); return o;
}
function rbox(w, h, d, m, x = 0, y = 0, z = 0, r = .04){
  const o = mesh(new RoundedBoxGeometry(w, h, d, 3, Math.min(r, w/2-.001, h/2-.001, d/2-.001)), m); o.position.set(x, y + h/2, z); return o;
}
function cyl(rt, rb, h, m, x = 0, y = 0, z = 0, seg = 28){
  const o = mesh(new THREE.CylinderGeometry(rt, rb, h, seg), m); o.position.set(x, y + h/2, z); return o;
}
// 旋转体：pts = [[半径, 高度], …] 自下而上，y = 底面
function lathe(pts, m, x = 0, y = 0, z = 0, seg = 40){
  const o = mesh(new THREE.LatheGeometry(pts.map(([r, h]) => new THREE.Vector2(Math.max(r, 1e-4), h)), seg), m); o.position.set(x, y, z); return o;
}
// 两点之间的圆杆，r0 在 a 端、r1 在 b 端（收分椅腿、斜撑）
function rod(a, b, r0, m, r1 = r0, seg = 12){
  const A = new THREE.Vector3(...a), B = new THREE.Vector3(...b), o = mesh(new THREE.CylinderGeometry(r1, r0, A.distanceTo(B), seg), m);
  o.position.copy(A).add(B).multiplyScalar(.5); o.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), B.sub(A).normalize()); return o;
}
// 沿曲线的圆管（水龙头、扶手、灯臂）
const tube = (pts, r, m, seg = 40) => mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p)), false, 'centripetal'), seg, r, 10), m);
// 椭球（靠垫、叶片、豆袋），y = 中心
function blob(rx, ry, rz, m, x = 0, y = 0, z = 0, seg = 24){
  const o = mesh(new THREE.SphereGeometry(1, seg, Math.round(seg*.7)), m); o.scale.set(rx, ry, rz); o.position.set(x, y, z); return o;
}
// 水平圆环，y = 中心
function ring(R, r, m, x = 0, y = 0, z = 0){ const o = mesh(new THREE.TorusGeometry(R, r, 10, 48), m); o.rotation.x = Math.PI/2; o.position.set(x, y, z); return o; }
function rrect(w, d, r){
  const s = new THREE.Shape(), x = -w/2, y = -d/2; r = Math.min(r, w/2 - .001, d/2 - .001);
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r); s.lineTo(x + w, y + d - r); s.quadraticCurveTo(x + w, y + d, x + w - r, y + d);
  s.lineTo(x + r, y + d); s.quadraticCurveTo(x, y + d, x, y + d - r); s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y); return s;
}
// 中空圆角框（浴缸、水槽沿、椅背框）：外 w×d、壁厚 t、高 h
function shell(w, d, h, t, r, m, x = 0, y = 0, z = 0){
  const s = rrect(w, d, r); s.holes.push(rrect(w - 2*t, d - 2*t, Math.max(.004, r - t)));
  const geo = new THREE.ExtrudeGeometry(s, {depth:h, bevelEnabled:false, curveSegments:10}); geo.rotateX(-Math.PI/2);
  const o = mesh(geo, m); o.position.set(x, y, z); return o;
}
const darker = (hex, k = .8) => '#' + new THREE.Color(hex).multiplyScalar(k).getHexString();
const lighter = (hex, k = .2) => '#' + new THREE.Color(hex).lerp(new THREE.Color('#ffffff'), k).getHexString();
// 四条收分腿：inset 为距边距离，r 为腿底半径（顶部略粗）
const legs = (g, w, d, h, m, inset = .05, r = .02) => [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(([a, b]) => g.add(rod([a*(w/2-inset), 0, b*(d/2-inset)], [a*(w/2-inset), h, b*(d/2-inset)], r*.7, m, r)));
const metal = () => themedMaterial('metal');
const chrome = () => mat('#eef0f2', {metalness:1, roughness:.08});
const hwMat = () => themedMaterial('metal');
const blackMetal = () => mat('#2b2b2d', {metalness:.6, roughness:.4});
const mirror = () => mat('#dfeaee', {metalness:.55, roughness:.06});
const ceramic = (o = {}) => mat('#fbfbf9', {roughness:.12, ...o});
const fabric = c => themedMaterial('fabric',c);
const woodM = c => themedMaterial('wood',c);
const screenMat = (glow = '#1a2636') => mat('#0b0e13', {roughness:.1, metalness:.3, emissive:glow, emissiveIntensity:.35});
const glowMat = (c = '#fff4dc', e = '#ffdca0', k = .5) => mat(c, {emissive:e, emissiveIntensity:k, roughness:.9, side:THREE.DoubleSide});

// 拉手：y 为拉手中心，z 为门板正面
function pull(g, len, vert, x, y, z){
  const m = hwMat(), o = new THREE.Group();
  o.add(vert ? box(.01, len, .01, m, 0, -len/2, .028) : box(len, .01, .01, m, 0, -.005, .028));
  [-1, 1].forEach(s => o.add(vert ? box(.008, .008, .028, m, 0, s*(len/2 - .015) - .004, .014) : box(.008, .008, .028, m, s*(len/2 - .015), -.004, .014)));
  o.position.set(x, y, z); g.add(o);
}
function knob(g, x, y, z){ const k = cyl(.011, .014, .02, hwMat(), x, y - .01, z + .01, 16); k.rotation.x = Math.PI/2; g.add(k, blob(.014, .014, .008, hwMat(), x, y, z + .022, 12)); }
// 柜门 / 抽屉面板：x0..x0+w、y0..y0+h 区域内 nx 列 × ny 行，正面朝 +z（z = 柜体正面）
// hd：'bar' 金属拉手 | 'knob' 圆钮 | 'edge' 顶部隐形拉槽 | 'none'；hy：门拉手中心高度（null = 面板中部）
function fronts(g, x0, y0, w, h, z, nx, ny, m, hd = 'bar', hy = null){
  const gap = .005, pw = w/nx, ph = h/ny, fz = z + .018;
  g.add(box(w, h, .002, '#2a2724', x0 + w/2, y0, z + .001));                     // 缝隙里透出的暗色
  for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++){
    const cx = x0 + pw*(i + .5), yb = y0 + ph*j, drawer = ph < .4 && pw >= ph;
    g.add(rbox(pw - gap, ph - gap, .018, m, cx, yb + gap/2, z + .009, .003));
    if (hd === 'none') continue;
    if (hd === 'edge'){ g.add(box(pw - .05, .01, .006, '#3c3a37', cx, yb + ph - gap - .018, fz)); continue; }
    if (drawer){ hd === 'knob' ? knob(g, cx, yb + ph/2, fz) : pull(g, Math.min(.3, pw*.45), false, cx, yb + ph/2, fz); continue; }
    const len = Math.min(.45, ph*.35), hx = nx === 1 ? cx + pw/2 - .045 : (i % 2 ? cx - pw/2 + .04 : cx + pw/2 - .04);
    const y = Math.min(yb + ph - .05 - len/2, Math.max(yb + .05 + len/2, hy ?? yb + ph/2));
    hd === 'knob' ? knob(g, hx, y, fz) : pull(g, len, true, hx, y, fz);
  }
}
const vasePts = (r, h) => [[0, 0], [r*.65, 0], [r, h*.32], [r*.92, h*.62], [r*.42, h*.86], [r*.5, h]];
function vase(g, x, y, z, r, h, c, R, flowers = true){
  g.add(lathe(vasePts(r, h), mat(c, {roughness:.35, side:THREE.DoubleSide}), x, y, z, 32));
  if (!flowers) return;
  const cols = ['#f3e6d8', '#e8b4a0', '#f6d27a', '#ffffff'];
  for (let k = 0; k < 5; k++){
    const a = k*1.26 + R()*.4, s = .03 + R()*.05, top = [x + Math.cos(a)*s, y + h + .12 + R()*.14, z + Math.sin(a)*s];
    g.add(rod([x, y + h*.6, z], top, .003, '#6f8f4a', .003, 6), blob(.022, .018, .022, cols[k % 4], ...top, 12));
  }
}
function tableLamp(g, x, y, z, s = 1){const start=g.children.length;
  g.add(lathe([[0, 0], [.06*s, 0], [.075*s, .05*s], [.08*s, .12*s], [.055*s, .2*s], [.018*s, .25*s], [.012*s, .3*s]], ceramic({roughness:.3}), x, y, z, 32));
  g.add(lathe([[.13*s, 0], [.1*s, .18*s]], glowMat('#f6ecd9', '#ffdca0', .35), x, y + .26*s, z, 40), blob(.03*s, .03*s, .03*s, glowMat('#fff', '#ffe2b0', 1), x, y + .31*s, z, 12));
 for(const o of g.children.slice(start))o.userData.legacyTableLamp=true;
}
const plate = (g, r, x, y, z) => g.add(lathe([[0, 0], [r*.6, 0], [r*.72, .008], [r, .02]], ceramic({side:THREE.DoubleSide}), x, y, z, 32));

/* ======================= 家具模型（局部坐标：背面朝 -z） ======================= */
function referenceFurniture(f){
  const g = new THREE.Group(), w = M(f.w), d = M(f.d), c = f.color || '#ddd', p=f.finishes||{}, bz = -d/2, R = rng(Math.round(f.w*7 + f.d*13 + f.cx + f.cy));
  switch (f.type){
    case 'bed': {
      const fr = woodM(p.bedFrame||'#8d7258'), fab = fabric(c), fh = .3, mt = .22, top = fh + mt, n = Math.max(3, Math.round(w/.28)), sw = (w - .04)/n;
      g.add(box(w - .12, .06, d - .14, '#4a3e33', 0, 0, .03), rbox(w, fh - .06, d - .08, fr, 0, .06, .04, .015));        // 内缩踢脚 + 床箱
      g.add(rbox(w, 1.08, .06, fr, 0, 0, bz + .03, .012));                                                                 // 床头板
      for (let i = 0; i < n; i++) g.add(rbox(sw - .006, .62, .06, fabric(p.bedHead||darker(c, .8)), -w/2 + .02 + sw*(i + .5), .42, bz + .08, .025));   // 竖向软包
      const md = d - .13, dd = md*.66, dz = d/2 - .015 - dd/2;
      g.add(rbox(w - .06, mt, md, '#f6f3ee', 0, fh, bz + .11 + md/2, .07));                                              // 床垫
      g.add(rbox(w + .02, .27, dd, fab, 0, top - .2, dz, .04), rbox(w + .024, .06, .22, fabric(p.pillow||'#fbfaf7'), 0, top + .025, dz - dd/2 + .11, .025));   // 被子 + 翻边
      g.add(rbox(w + .05, .285, .42, fabric(p.bedRunner||darker(c, .62)), 0, top - .205, d/2 - .35, .03));                               // 床尾巾
      const np = w >= 1.3 ? 2 : 1, pw = (w - .16 - (np-1)*.06)/np;
      for (let i = 0; i < np; i++){
        const x = -w/2 + .08 + pw/2 + i*(pw + .06);
        g.add(rot(rbox(pw, .15, .42, fabric(p.pillow||'#ffffff'), x, top - .01, bz + .34, .07), -.28), rot(rbox(pw*.62, .3, .1, fabric(i ? (p.pillow||'#efe7da') : (p.bedRunner||darker(c, .7))), x, top, bz + .54, .045), -.3));
      }
      break;
    }
    case 'sofabed': case 'sofa': case 'armchair': {
      const fab = fabric(c), dk = fabric(darker(c, .88)), a = Math.min(.18, w*.14), n = f.type === 'armchair' ? 1 : (w > 2.2 ? 3 : 2), cw = (w - 2*a)/n, bd = Math.min(.2, d*.24), lh = .12, sd = d - bd - .02;
      legs(g, w, d, lh, woodM('#3a3027'), .07, .018);
      g.add(rbox(w, .16, d, dk, 0, lh, 0, .03), rbox(w, .73, bd, dk, 0, lh, bz + bd/2, .06));
      [-1, 1].forEach(s => g.add(rbox(a, .5, d, dk, s*(w/2 - a/2), lh, 0, .07)));
      for (let i = 0; i < n; i++){
        const x = -w/2 + a + cw/2 + i*cw;
        g.add(rbox(cw - .012, .15, sd, fab, x, lh + .16, bz + bd + sd/2, .055), rot(rbox(cw - .03, .44, .16, fab, x, lh + .3, bz + bd + .08, .07), -.16));
      }
      if (n > 1) [-1, 1].forEach(s => g.add(rot(rbox(.42, .42, .12, fabric(s < 0 ? (p.pillow||'#ece5d8') : (p.cushion||darker(c, .7))), s*(w/2 - a - .26), lh + .32, bz + bd + .22, .06), -.3, s*-.25)));
      else g.add(rot(rbox(.4, .26, .1, fabric(p.pillow||'#ece5d8'), 0, lh + .33, bz + bd + .2, .05), -.25));
      break;
    }
    case 'cornersofa': {
      const k = Math.min(.95, d*.56, w*.4), b = .2, fab = fabric(c), dk = fabric(darker(c, .88)), lh = .1, sw = (w - b - .2)/2;
      [[-w/2+.07, bz+.07], [w/2-.07, bz+.07], [w/2-.07, bz+k-.07], [-w/2+.07, d/2-.07], [-w/2+k-.07, d/2-.07], [-w/2+k-.07, bz+k-.07]]
        .forEach(([x, z]) => g.add(rod([x, 0, z], [x, lh, z], .012, woodM('#3a3027'), .018)));
      g.add(rbox(w, .18, k, dk, 0, lh, bz + k/2, .03), rbox(k, .18, d - k + .02, dk, -w/2 + k/2, lh, bz + k + (d - k)/2 - .01, .03));
      g.add(rbox(w, .72, b, dk, 0, lh, bz + b/2, .06), rbox(b, .72, d, dk, -w/2 + b/2, lh, 0, .06), rbox(.2, .5, k, dk, w/2 - .1, lh, bz + k/2, .07), rbox(k, .5, .2, dk, -w/2 + k/2, lh, d/2 - .1, .07));
      for (let i = 0; i < 2; i++){
        const x = -w/2 + b + sw/2 + i*sw;
        g.add(rbox(sw - .012, .15, k - b - .02, fab, x, lh + .18, bz + b + (k - b)/2, .055), rot(rbox(sw - .04, .42, .16, fab, x, lh + .3, bz + b + .07, .07), -.16));
      }
      g.add(rbox(k - b - .02, .15, d - k - .22, fab, -w/2 + b + (k - b)/2, lh + .18, bz + k + (d - k - .2)/2, .055));
      const L = d - .2 - b - .18, nl = Math.max(1, Math.round(L/.75));
      for (let i = 0; i < nl; i++) g.add(rot(rbox(.16, .42, L/nl - .03, fab, -w/2 + b + .07, lh + .3, bz + b + .18 + L/nl*(i + .5), .07), 0, 0, .16));
      g.add(rot(rbox(.42, .42, .12, fabric(p.pillow||'#ece5d8'), -w/2 + b + .3, lh + .34, bz + b + .24, .06), -.35, .6), rot(rbox(.4, .4, .12, fabric(p.cushion||darker(c, .7)), w/2 - .5, lh + .34, bz + b + .2, .06), -.3, -.25));
      break;
    }
    case 'nightstand': {
      const wm = woodM(c);
      legs(g, w, d, .1, woodM('#5a4a3b'), .04, .014);
      g.add(rbox(w, .4, d - .02, wm, 0, .1, -.01, .012));
      fronts(g, -w/2 + .02, .12, w - .04, .36, d/2 - .02, 1, 2, wm, 'bar');
      tableLamp(g, -w*.12, .5, -d*.12);
      g.add(box(.16, .025, .22, '#2f5d62', w*.24, .5, .04), box(.14, .02, .2, '#e6dccd', w*.24, .525, .04));
      break;
    }
    case 'wardrobe': case 'cabinet': case 'shoecab': {
      const cm = mat(c, {roughness:.55}), fz = d/2 - .02;
      if (f.type === 'wardrobe'){
        const h = (f.h||DEFAULT.height)/1000, n = Math.max(1, Math.round(w/.5));
        g.add(box(w - .02, .08, d - .06, '#4a4641', 0, 0, -.03), box(w, h - .08, d - .02, cm, 0, .08, -.01));
        fronts(g, -w/2, .08, w, h - .1, fz, n, 1, cm, 'bar', 1.05);
        g.add(box(w, .02, d - .02, darker(c, .9), 0, h - .02, -.01));
      } else if (f.type === 'shoecab'){
        const h = 1.0, y0 = .16, n = Math.max(1, Math.round(w/.45));
        g.add(box(w, h - y0, d - .02, cm, 0, y0, -.01), box(w - .04, .01, .03, glowMat('#fff7e6', '#ffe9c4', .8), 0, y0 - .01, fz - .06));   // 悬空 + 底部灯带
        fronts(g, -w/2, y0, w, h - y0, fz, n, 1, cm, 'edge');
        g.add(rbox(w + .01, .025, d, woodM(darker(c, .8)), 0, h, 0, .006));
        g.add(rbox(.22, .015, .14, woodM('#6b543f'), -w*.25, h + .025, 0, .006));
        vase(g, w*.28, h + .025, -.03, .05, .2, '#d8cfc2', R);
      } else {
        const h = .85, n = Math.max(1, Math.round(w/.5));
        legs(g, w, d, .1, woodM('#3a3027'), .05, .016);
        g.add(box(w, h - .13, d - .02, cm, 0, .1, -.01));
        fronts(g, -w/2, .62, w, .2, fz, n, 1, cm, 'bar');
        fronts(g, -w/2, .1, w, .52, fz, n, 1, cm, 'bar', .52);
        g.add(rbox(w + .02, .03, d + .01, woodM(darker(c, .78)), 0, h - .03, 0, .008));
        vase(g, w*.3, h, 0, .07, .24, '#e9e2d6', R);
        g.add(rot(box(.3, .38, .02, woodM('#3a3027'), -w*.25, h, bz + .06), -.12), rot(box(.25, .33, .005, '#d9cfbf', -w*.25, h + .03, bz + .075), -.12));   // 靠墙画框
        g.add(lathe([[0, 0], [.05, 0], [.12, .06], [.13, .07]], mat('#b8a58c', {roughness:.5, side:THREE.DoubleSide}), 0, h, .02, 32));
        for (let k = 0; k < 3; k++) g.add(blob(.035, .035, .035, ['#d98c4a', '#c9ad4f', '#b5463a'][k], Math.cos(k*2.1)*.04, h + .045, .02 + Math.sin(k*2.1)*.04, 14));
      }
      break;
    }
    case 'dresser': {
      const wm = woodM(c), r = Math.min(.34, w*.3);
      [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(([a, b]) => g.add(rod([a*(w/2 - .04), 0, b*(d/2 - .04)], [a*(w/2 - .05), .58, b*(d/2 - .05)], .012, wm, .02)));
      g.add(box(w - .04, .14, d - .04, wm, 0, .58), rbox(w, .03, d, wm, 0, .72, 0, .008));
      fronts(g, -w/2 + .03, .585, w - .06, .13, d/2 - .02, 2, 1, wm, 'knob');
      const mr = new THREE.Mesh(new THREE.TorusGeometry(r, .018, 12, 64), woodM(darker(c, .7))); mr.position.set(0, .77 + r, bz + .04); sh(mr);
      const mg = new THREE.Mesh(new THREE.CircleGeometry(r, 64), mirror()); mg.position.set(0, .77 + r, bz + .035);
      g.add(mr, mg, box(.08, .03, .06, woodM(darker(c, .7)), 0, .75, bz + .04));
      [['#e7c9b5', .03, .09], ['#b9d0d8', .025, .12], ['#f0e3cf', .02, .07]].forEach(([cc, rr, hh], i) => g.add(cyl(rr, rr, hh, mat(cc, {roughness:.15, transparent:true, opacity:.8}), w*.25 + i*.06, .75, .02)));
      g.add(rbox(.16, .06, .1, woodM('#6b543f'), -w*.28, .75, .03, .01));
      const sz = d/2 + .25;
      [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(([a, b]) => g.add(rod([a*.13, 0, sz + b*.13], [a*.12, .4, sz + b*.12], .01, wm, .014)));
      g.add(rbox(.34, .08, .34, fabric('#e8ddd0'), 0, .4, sz, .035));
      break;
    }
    case 'desk': {
      const tm = woodM(c), bm = blackMetal();
      g.add(rbox(w, .025, d, tm, 0, .72, 0, .006));
      [-1, 1].forEach(s => {
        const x = s*(w/2 - .06);
        g.add(box(.03, .72, .03, bm, x, 0, d/2 - .06), box(.03, .72, .03, bm, x, 0, bz + .06), box(.03, .03, d - .1, bm, x, 0, 0), box(.03, .03, d - .1, bm, x, .69, 0));
      });
      g.add(box(w - .12, .04, .015, bm, 0, .66, bz + .06), box(.4, .09, d - .12, tm, w/2 - .32, .63, 0));
      pull(g, .16, false, w/2 - .32, .675, d/2 - .06);
      const my = .745, mz = bz + .15;
      g.add(rbox(.22, .012, .16, bm, 0, my, mz, .004), rod([0, my, mz - .02], [0, my + .2, mz - .03], .012, bm));
      g.add(rbox(.62, .37, .02, '#1d1d1f', 0, my + .12, mz - .04, .006), box(.6, .33, .002, screenMat('#27405c'), 0, my + .15, mz - .029));
      g.add(rbox(.42, .015, .13, '#e8e8ea', 0, my, .06, .004), rbox(.4, .004, .11, '#d2d2d6', 0, my + .014, .06, .002), blob(.03, .015, .05, '#e8e8ea', .3, my + .012, .07, 16));
      const lx = -w/2 + .15, lz = bz + .12;
      g.add(cyl(.07, .075, .02, bm, lx, my, lz, 28), tube([[lx, my + .02, lz], [lx, my + .3, lz + .03], [lx + .12, my + .42, lz + .1]], .008, bm));
      const hd = cyl(.02, .06, .1, bm, lx + .14, my + .34, lz + .12, 24); hd.rotation.x = .5; g.add(hd);
      g.add(cyl(.04, .038, .09, ceramic({roughness:.3}), w/2 - .15, my, .05, 20), rbox(.2, .015, .28, '#3b5566', -w/2 + .3, my, .1, .004));
      break;
    }
    case 'chair': {
      const lw = woodM('#6b543f'), fab = fabric(c), sy = .44;
      [[-1, 1], [1, 1]].forEach(([s]) => g.add(rod([s*(w/2 - .04), 0, d/2 - .05], [s*(w/2 - .05), sy, d/2 - .07], .012, lw, .018)));
      [-1, 1].forEach(s => g.add(rod([s*(w/2 - .04), 0, bz + .03], [s*(w/2 - .05), .86, bz + .07], .012, lw, .018)));
      g.add(box(w - .08, .025, .02, lw, 0, .15, d/2 - .06), box(w - .08, .025, .02, lw, 0, .15, bz + .05));
      [-1, 1].forEach(s => g.add(box(.02, .025, d - .12, lw, s*(w/2 - .045), .18, 0)));
      g.add(box(w - .06, .04, d - .1, lw, 0, sy - .03, 0), rbox(w - .04, .05, d - .08, fab, 0, sy, .005, .022));
      g.add(rot(rbox(w - .08, .15, .025, lw, 0, .66, bz + .065, .012), -.12), rot(box(w - .08, .025, .02, lw, 0, .52, bz + .055), -.12));
      break;
    }
    case 'bookshelf': {
      const h = (f.h||DEFAULT.height)/1000, t = .022, ns = 5, wm = woodM(c), sh0 = (h - .06 - t)/ns, cols = ['#b88a6a','#6f8f8a','#d9c08c','#9aa58c','#a8675e','#e6dccd','#7d8ea3','#c9bfae'];
      g.add(box(w, h, .012, woodM(darker(c, .85)), 0, 0, bz + .006), box(t, h, d, wm, -w/2 + t/2), box(t, h, d, wm, w/2 - t/2), box(w - 2*t, .06, d - .03, wm, 0, 0, .0));
      for (let s = 0; s <= ns; s++){
        const y = s < ns ? .06 + s*sh0 : h - t; g.add(box(w - 2*t, t, d - .012, wm, 0, y, .006));
        if (s === ns) break;
        const yb = y + t, end = w/2 - t - .01; let x = -w/2 + t + .01, deco = R() < .55 ? x + R()*(w - .45) : 99;
        while (x < end - .03){
          if (x >= deco){
            deco = 99;
            if (R() < .5) vase(g, x + .07, yb, 0, .045, .16, cols[Math.floor(R()*8)], R, false);
            else for (let k = 0; k < 3; k++) g.add(box(.2 - k*.02, .028, d*.7, mat(cols[Math.floor(R()*8)], {roughness:.8}), x + .1, yb + k*.028, .01));
            x += .2; continue;
          }
          if (R() < .07){ x += .03 + R()*.05; continue; }
          const bw = .018 + R()*.03, bh = Math.min(sh0 - t - .03, .17 + R()*.13), bd = d*(.62 + R()*.22);
          if (x + bw > end) break;
          g.add(box(bw, bh, bd, mat(cols[Math.floor(R()*8)], {roughness:.75}), x + bw/2, yb, d/2 - .015 - bd/2));
          x += bw + .002;
        }
      }
      break;
    }
    case 'baycushion':
      g.add(rbox(w, .08, d, fabric(c), 0, .45, 0, .03));
      g.add(rot(rbox(w - .1, .34, .14, fabric('#ffffff'), 0, .52, bz + .14, .06), .25), rot(rbox(w - .1, .34, .14, fabric('#f0e6d6'), 0, .52, d/2 - .14, .06), -.25));
      g.add(rbox(w*.8, .04, .3, fabric(darker(c, .7)), 0, .53, d*.12, .02), rbox(.28, .015, .2, woodM('#8d7258'), 0, .53, -d*.15, .006), cyl(.035, .03, .06, ceramic(), 0, .545, -d*.15, 20));
      break;
    case 'coffeetable': {
      const tm = mat(c, {roughness:.35}), lw = woodM('#3a3027');
      [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(([a, b]) => g.add(rod([a*(w/2 - .05), 0, b*(d/2 - .05)], [a*(w/2 - .07), .365, b*(d/2 - .07)], .012, lw, .02)));
      g.add(rbox(w, .035, d, tm, 0, .365, 0, .015), rbox(w - .12, .02, d - .12, woodM(darker(c, .85)), 0, .12, 0, .006));
      g.add(box(.3, .03, .22, '#2f5d62', w*.2, .14, 0), box(.26, .025, .19, '#d9b36c', w*.2, .17, .01));
      g.add(rbox(.38, .015, .24, woodM('#6b543f'), -w*.2, .4, 0, .006), box(.22, .025, .16, '#e6dccd', -w*.22, .415, 0));
      g.add(lathe([[0, 0], [.025, 0], [.035, .07], [.034, .08]], ceramic({side:THREE.DoubleSide}), -w*.12, .415, .06, 20));
      vase(g, w*.24, .4, -.05, .055, .18, '#e9e2d6', R);
      break;
    }
    case 'tvstand': {
      const sm = mat(c, {roughness:.5}), n = Math.max(2, Math.round(w/.6));
      legs(g, w, d, .1, blackMetal(), .08, .012);
      g.add(rbox(w, .4, d - .02, sm, 0, .1, -.01, .01));
      fronts(g, -w/2 + .005, .105, w - .01, .39, d/2 - .02, n, 1, sm, 'edge');
      g.add(rbox(1.45, .84, .025, mat('#18181a', {roughness:.4, metalness:.3}), 0, .95, bz + .03, .004), box(1.43, .81, .002, screenMat(), 0, .962, bz + .0435));
      g.add(rbox(.9, .06, .09, '#2a2a2c', 0, .5, -.02, .02), box(.86, .045, .002, fabric('#3a3a3c'), 0, .507, .026));
      vase(g, w/2 - .25, .5, 0, .06, .26, '#d8cfc2', R);
      g.add(box(.25, .035, .18, '#a9433b', -w/2 + .3, .5, 0), box(.22, .03, .16, '#e6dccd', -w/2 + .3, .535, 0));
      break;
    }
    case 'rug':
      [[w, d, .01, c, 0], [w - .16, d - .16, .002, darker(c, .82), .01], [w - .26, d - .26, .002, lighter(c, .12), .0115]].forEach(([a, b, h, cc, y]) => {
        const r = box(a, h, b, mat(cc, {roughness:1}), 0, y + .002); r.castShadow = false; g.add(r);
      });
      break;
    case 'plant': {
      const r = Math.min(w, d)/2, H = .9 + r*1.6, pot = mat('#d9d2c5', {roughness:.6}), lm = [mat('#5f8f4e', {roughness:.6, side:THREE.DoubleSide}), mat('#79a862', {roughness:.6, side:THREE.DoubleSide})];
      g.add(lathe([[0, 0], [r*.4, 0], [r*.44, .02], [r*.54, .36], [r*.57, .4], [r*.52, .4], [r*.5, .37], [0, .37]], pot, 0, 0, 0, 36), cyl(r*.49, r*.49, .005, '#4a3a2c', 0, .368, 0, 28));
      g.add(rod([0, .37, 0], [.02, H*.62, -.01], .016, '#6b5540', .009));
      const N = 20 + Math.round(r*36), sc = Math.sqrt(r/.25);
      for (let k = 0; k < N; k++){
        const t = k/N, a = k*2.399 + R()*.3, len = (.14 + R()*.08)*(1.1 - t*.4)*sc, s0 = .03 + R()*.08*sc, p = new THREE.Group();
        p.position.set(0, H*(.42 + .58*t), 0); p.rotation.set(0, -a, .1 + t*.5 + R()*.3, 'YXZ');
        const lf = blob(len/2, .005, len*.27, lm[k % 2], s0 + len/2, 0, 0, 16); lf.rotation.z = -.3;
        p.add(box(s0, .005, .005, '#6f8f4a', s0/2, 0, 0), lf); g.add(p);
      }
      break;
    }
    case 'table': {
      const tm = mat(c, {roughness:.4}), lw = woodM(darker(c, .55)), ns = Math.max(1, Math.round(w/.62)), top = .75;
      [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(([a, b]) => g.add(rod([a*(w/2 - .08), 0, b*(d/2 - .08)], [a*(w/2 - .1), .715, b*(d/2 - .1)], .016, lw, .026)));
      g.add(rbox(w, .035, d, tm, 0, .715, 0, .012), box(w - .22, .07, d - .22, lw, 0, .645));
      g.add(box(w*.7, .003, .32, fabric('#b9a58c'), 0, top, 0));
      for (let i = 0; i < ns; i++) [-1, 1].forEach(s => {
        const x = -w/2 + w/ns*(i + .5), z = s*(d/2 - .17);
        g.add(box(.38, .003, .28, fabric('#e7dfd1'), x, top, z)); plate(g, .12, x, top + .003, z);
        g.add(cyl(.03, .026, .1, mat('#dfeef3', {transparent:true, opacity:.35, roughness:.05}), x + .15, top + .003, z - s*.1, 16));
      });
      vase(g, 0, top + .003, 0, .06, .2, '#e9e2d6', R);
      break;
    }
    case 'roundtable': {
      const b = Math.min(.25, w*.3), lw = woodM('#4a3e33'), top = .75;
      g.add(lathe([[b, 0], [b, .015], [b*.8, .035], [.06, .12], [.045, .35], [.05, .6], [.12, .69], [.18, .715]], lw, 0, 0, 0, 40), cyl(w/2, w/2, .035, mat(c, {roughness:.4}), 0, .715, 0, 64));
      for (let k = 0; k < 4; k++){ const a = k*Math.PI/2 + .4, rr = w/2 - .17; plate(g, .11, Math.cos(a)*rr, top, Math.sin(a)*rr); }
      vase(g, 0, top, 0, .05, .18, '#e9e2d6', R);
      break;
    }
    case 'counter': {
      const cm = mat(c, {roughness:.45}), stone = mat('#dcd7cf', {roughness:.22}), n = Math.max(1, Math.round(w/.6)), fz = d/2 - .04;
      g.add(box(w - .01, .1, d - .1, '#4a4641', 0, 0, -.05), box(w, .72, d - .04, cm, 0, .1, -.02));
      fronts(g, -w/2, .64, w, .18, fz, n, 1, cm, 'bar'); fronts(g, -w/2, .1, w, .54, fz, n, 1, cm, 'bar', .56);
      g.add(rbox(w + .01, .04, d, stone, 0, .82, 0, .004), box(w, .62, .01, mat('#efece6', {roughness:.3}), 0, .86, bz + .005));
      g.add(box(w, .7, .33, cm, 0, 1.48, bz + .165)); fronts(g, -w/2, 1.48, w, .7, bz + .33, n, 1, cm, 'bar', 1.56);
      g.add(box(w - .04, .01, .02, glowMat('#fff7e6', '#ffe9c4', .8), 0, 1.47, bz + .29));
      if (w >= .8){
        g.add(rbox(.36, .018, .25, woodM('#c9a27a'), -w/2 + .3, .86, .0, .005));
        [.07, .06, .05].forEach((r, i) => g.add(cyl(r, r, .16 - i*.03, mat(['#e9e2d6', '#d6cfc3', '#bfb6a8'][i], {roughness:.4}), w/2 - .15 - i*.15, .86, bz + .1, 24)));
        g.add(cyl(.05, .045, .14, ceramic({roughness:.3}), w/2 - .6, .86, bz + .1, 20));
        for (let k = 0; k < 4; k++) g.add(rod([w/2 - .6, .9, bz + .1], [w/2 - .6 + (k - 1.5)*.018, 1.1, bz + .1 + (k % 2 - .5)*.02], .005, woodM('#8d7258'), .006, 6));
      }
      break;
    }
    case 'stove': {
      const sm = mat('#b9bec3', {metalness:.8, roughness:.3});
      g.add(rbox(w, .012, d, mat('#0d0d0e', {roughness:.06, metalness:.3}), 0, .862, 0, .004));
      [[-w/4, 0], [w/4, 0]].forEach(([x, z]) => {
        g.add(cyl(.085, .09, .008, '#2b2b2b', x, .874, z, 32), cyl(.045, .05, .014, mat('#6b5a45', {metalness:.7, roughness:.35}), x, .874, z, 28), cyl(.028, .028, .022, '#1a1a1a', x, .874, z, 20));
        for (let k = 0; k < 5; k++){ const a = k*Math.PI*2/5; g.add(rot(box(.07, .014, .012, '#1c1c1c', x + Math.cos(a)*.1, .874, z + Math.sin(a)*.1), 0, -a)); }
        g.add(cyl(.02, .022, .018, '#222', x, .874, d/2 - .04, 20));
      });
      g.add(rbox(w, .06, .5, sm, 0, 1.55, bz + .25, .01), box(.3, .72, .26, sm, 0, 1.61, bz + .13));
      g.add(rot(box(w - .02, .3, .008, mat('#15181b', {roughness:.05, metalness:.5}), 0, 1.58, bz + .38), -.9), box(.16, .012, .003, mat('#101214', {emissive:'#6fd0ff', emissiveIntensity:.6}), 0, 1.575, bz + .502));
      break;
    }
    case 'ksink': {
      const st = mat('#c7ccd1', {metalness:.85, roughness:.28}), inner = mat('#9aa1a8', {metalness:.8, roughness:.35}), two = w >= .75, bw = two ? w*.42 : w*.7, bd = d*.66;
      g.add(box(w, .008, d, st, 0, .862, 0));
      (two ? [-w*.23, w*.23] : [0]).forEach(x => g.add(shell(bw, bd, .02, .015, .04, st, x, .862, .03), box(bw - .03, .002, bd - .03, inner, x, .87, .03), cyl(.03, .03, .003, chrome(), x, .872, .03, 20)));
      const fx = two ? 0 : w*.3, cm = chrome();
      g.add(cyl(.025, .028, .03, cm, fx, .87, bz + .06, 20), tube([[fx, .9, bz + .06], [fx, 1.12, bz + .06], [fx, 1.17, bz + .1], [fx, 1.14, bz + .18], [fx, 1.08, bz + .2]], .012, cm));
      g.add(rot(box(.012, .012, .09, cm, fx + .035, .98, bz + .09), -.3));
      break;
    }
    case 'fridge': {
      const fm = mat(c, {metalness:.45, roughness:.28}), h = 1.8, fz = d/2 - .05;
      g.add(box(w - .02, .06, d - .06, '#2a2c2e', 0, 0, -.03), rbox(w, h - .06, d - .05, fm, 0, .06, -.025, .02), box(w - .01, h - .07, .003, '#2a2c2e', 0, .065, fz + .0015));
      if (w > .85){
        [-1, 1].forEach(s => { g.add(rbox(w/2 - .004, h - .08, .04, fm, s*w/4, .07, fz + .023, .012)); pull(g, .8, true, s*.035, 1.05, fz + .043); });
        g.add(box(.1, .14, .003, screenMat('#2a6f8f'), -w/4, 1.25, fz + .044));
      } else {
        g.add(rbox(w - .006, 1.06, .04, fm, 0, .72, fz + .023, .012), rbox(w - .006, .64, .04, fm, 0, .07, fz + .023, .012));
        pull(g, .5, true, -w/2 + .06, 1.05, fz + .043); pull(g, w*.5, false, 0, .64, fz + .043);
        g.add(box(.08, .1, .003, screenMat('#2a6f8f'), w*.22, 1.4, fz + .044));
      }
      break;
    }
    case 'toilet': {
      const cer = ceramic(), Rb = w*.45, zc = bz + d*.62, kz = (d*.37)/Rb, cm = chrome();
      g.add(rbox(w*.88, .4, d*.24, cer, 0, .36, bz + d*.12, .04), rbox(w*.92, .03, d*.27, cer, 0, .76, bz + d*.135, .012), cyl(.022, .022, .006, cm, 0, .79, bz + d*.135, 20));
      const ped = lathe([[0, 0], [Rb*.62, 0], [Rb*.66, .02], [Rb*.56, .12], [Rb*.62, .22], [Rb*.92, .33], [Rb, .37]], cer, 0, 0, zc, 40);
      const seat = cyl(Rb*1.01, Rb*1.01, .022, mat('#f4f4f2', {roughness:.2}), 0, .37, zc, 40), lid = cyl(Rb*.97, Rb*.99, .02, mat('#f4f4f2', {roughness:.2}), 0, .392, zc, 40);
      ped.scale.z = seat.scale.z = lid.scale.z = kz; g.add(ped, seat, lid);
      [-1, 1].forEach(s => g.add(box(.03, .02, .03, cm, s*w*.18, .39, zc - Rb*kz - .005)));
      break;
    }
    case 'vanity': {
      const vm = mat(c, {roughness:.5}), stone = mat('#fafafa', {roughness:.18}), nb = w >= 1.1 ? 2 : 1, cd = d - .04, cm = chrome();
      g.add(rbox(w, .45, cd, vm, 0, .33, bz + cd/2, .008));
      fronts(g, -w/2 + .005, .335, w - .01, .44, d/2 - .04, nb, 2, vm, 'edge');
      g.add(rbox(w, .03, d, stone, 0, .78, 0, .006));
      const rb = Math.min(.19, w/nb*.36);
      for (let i = 0; i < nb; i++){
        const x = nb === 1 ? 0 : (i ? w/4 : -w/4);
        g.add(lathe([[0, 0], [rb*.55, 0], [rb*.85, .03], [rb, .1], [rb*.97, .12]], ceramic({side:THREE.DoubleSide}), x, .81, .03, 40), cyl(.018, .018, .003, cm, x, .812, .03, 16));
        g.add(cyl(.02, .022, .02, cm, x, .81, bz + .06, 16), tube([[x, .83, bz + .06], [x, 1.03, bz + .06], [x, 1.07, bz + .11], [x, 1.03, bz + .15]], .01, cm), rot(box(.01, .01, .06, cm, x, 1.05, bz + .04), .4));
      }
      const mw = Math.min(w*.9, nb*.7);
      g.add(rbox(mw + .02, .82, .02, glowMat('#fff7e6', '#ffe9c4', .9), 0, 1.14, bz + .01, .01), box(mw, .8, .01, mirror(), 0, 1.15, bz + .025));
      g.add(cyl(.028, .028, .12, mat('#c8b8a6', {roughness:.3}), w/2 - .08, .81, bz + .1, 16), rbox(.18, .03, .12, fabric('#e9e2d6'), -w/2 + .12, .81, .05, .012));
      break;
    }
    case 'shower': {
      const cm = chrome(), x = -w/4;
      g.add(rbox(w, .05, d, mat('#f4f4f2', {roughness:.3}), 0, 0, 0, .01), box(w*.6, .003, .05, mat('#9aa1a8', {metalness:.8, roughness:.3}), 0, .05, bz + .08));
      [[w, .01, 0, d/2 - .005], [.01, d, w/2 - .005, 0]].forEach(([gw, gd, px, pz]) => { const p = box(gw, 1.95, gd, glassMat, px, .05, pz); p.castShadow = false; g.add(p); });
      g.add(box(.02, 1.95, .02, frameMat, w/2 - .01, .05, d/2 - .01), box(.02, 1.95, .03, frameMat, -w/2 + .01, .05, d/2 - .005), box(.03, 1.95, .02, frameMat, w/2 - .005, .05, bz + .01));
      g.add(box(w, .015, .02, frameMat, 0, 1.985, d/2 - .005), box(.02, .015, d, frameMat, w/2 - .005, 1.985, 0));
      g.add(rbox(.14, .1, .04, cm, x, 1.0, bz + .02, .01), rod([x, 1.1, bz + .03], [x, 1.95, bz + .03], .012, cm));
      g.add(tube([[x, 1.95, bz + .03], [x, 2.02, bz + .06], [x, 2.03, bz + .22]], .01, cm), rbox(.24, .012, .24, cm, x, 2.02, bz + .25, .004));
      g.add(rot(cyl(.015, .02, .2, cm, x + .1, 1.25, bz + .05, 16), .25), blob(.03, .012, .03, cm, x + .1, 1.47, bz + .08, 16));
      g.add(box(.26, .012, .1, ceramic(), w/2 - .2, 1.2, bz + .05));
      [['#e6dccd', .03, .18], ['#2f5d62', .025, .15], ['#f4f4f2', .028, .12]].forEach(([cc, r, hh], i) => g.add(cyl(r, r, hh, mat(cc, {roughness:.3}), w/2 - .28 + i*.07, 1.212, bz + .05, 16)));
      break;
    }
    case 'bathtub': {
      const cer = ceramic(), h = .56, t = .07, cm = chrome();
      g.add(shell(w, d, h, t, .14, cer), box(w - .1, .12, d - .1, cer, 0, 0, 0), box(w - 2*t + .004, .004, d - 2*t + .004, mat('#bfe0ea', {roughness:.03, transparent:true, opacity:.6}), 0, .4, 0));
      const fx = w/2 - t/2;
      g.add(tube([[fx, h - .02, 0], [fx, h + .1, 0], [fx - .06, h + .13, 0], [fx - .13, h + .09, 0]], .014, cm));
      [-1, 1].forEach(s => g.add(cyl(.02, .02, .04, cm, fx, h, s*.1, 16)));
      g.add(rot(rbox(.08, .16, .3, cer, -w/2 + t + .06, h - .12, 0, .04), 0, 0, -.5), rbox(.22, .05, .16, fabric('#e9e2d6'), fx - .05, h, d/2 - .1, .02));
      break;
    }
    case 'washer': case 'dryer': {
      const bm = mat(c, {roughness:.35}), R0 = Math.min(w, d)*.25, fz = d/2 - .02;
      g.add(box(w - .02, .04, d - .04, '#8f969b', 0, 0, -.02), rbox(w, .81, d - .02, bm, 0, .04, -.01, .025));
      g.add(box(w - .04, .1, .006, lighter(c, .3), 0, .72, fz + .003), rbox(.18, .07, .01, bm, -w/2 + .12, .735, fz + .006, .004));
      g.add(box(.12, .035, .003, screenMat('#1f6f6a'), w*.14, .745, fz + .007));
      const kn = cyl(.03, .03, .02, chrome(), -w*.02, .75, fz + .016, 28); kn.rotation.x = Math.PI/2; g.add(kn);
      const dr = new THREE.Mesh(new THREE.CircleGeometry(R0, 40), mat('#1b1f22', {roughness:.6})); dr.position.set(0, .4, fz + .004); g.add(dr);
      const rg = new THREE.Mesh(new THREE.TorusGeometry(R0 + .02, .022, 14, 48), mat('#c7cfd5', {metalness:.7, roughness:.25})); rg.position.set(0, .4, fz + .016); sh(rg); g.add(rg);
      const Rs = R0*1.42, cap = new THREE.Mesh(new THREE.SphereGeometry(Rs, 32, 12, 0, Math.PI*2, 0, .78), mat(f.type === 'dryer' ? '#4a4038' : '#26343d', {roughness:.04, metalness:.2, transparent:true, opacity:.8}));
      cap.rotation.x = Math.PI/2; cap.position.set(0, .4, fz + .012 - Rs*Math.cos(.78)); g.add(cap);
      g.add(box(w - .06, .004, .003, '#b9c3ca', 0, .08, fz + .002));
      break;
    }
    case 'crib': {
      const wm = woodM(c);
      g.add(rbox(w - .09, .12, d - .09, fabric('#ffffff'), 0, .3, 0, .04), box(w - .06, .025, d - .06, wm, 0, .28));
      [[-1,-1],[1,-1],[-1,1],[1,1]].forEach(([a, b]) => g.add(rbox(.045, .95, .045, wm, a*(w/2 - .022), 0, b*(d/2 - .022), .008), blob(.028, .028, .028, wm, a*(w/2 - .022), .97, b*(d/2 - .022), 14)));
      [-1, 1].forEach(s => {
        const z = s*(d/2 - .022), x = s*(w/2 - .022);
        g.add(rbox(w - .05, .035, .03, wm, 0, .88, z, .008), rbox(w - .05, .035, .03, wm, 0, .25, z, .008), rbox(.03, .035, d - .05, wm, x, .88, 0, .008), rbox(.03, .035, d - .05, wm, x, .25, 0, .008));
        for (let p = -w/2 + .09; p < w/2 - .05; p += .075) g.add(rod([p, .28, z], [p, .88, z], .009, wm, .009, 8));
        for (let p = -d/2 + .09; p < d/2 - .05; p += .075) g.add(rod([x, .28, p], [x, .88, p], .009, wm, .009, 8));
      });
      g.add(rbox(w*.5, .03, d - .14, fabric('#f3d9c9'), w*.12, .42, 0, .015), rbox(.3, .06, .2, fabric('#fbfaf7'), -w/2 + .22, .42, 0, .03));
      const bx = -w*.3 + .1, bear = '#c9a27a';
      g.add(blob(.05, .06, .045, bear, bx, .5, .12), blob(.045, .042, .04, bear, bx, .59, .12), blob(.016, .016, .01, bear, bx - .032, .625, .12), blob(.016, .016, .01, bear, bx + .032, .625, .12));
      break;
    }
    case 'beanbag': {
      const fab = mat(c, {roughness:.95});
      g.add(blob(w*.5, .3, d*.5, fab, 0, .3, 0, 40), blob(w*.42, .22, d*.22, fab, 0, .5, bz + d*.26, 32));
      break;
    }
    case 'sidetable': {
      const r = Math.min(w, d)/2, bm = blackMetal();
      g.add(lathe([[r*.55, 0], [r*.55, .012], [.03, .035], [.018, .3], [.025, .5], [.08, .52]], bm, 0, 0, 0, 40), cyl(r, r*.98, .025, mat(c, {roughness:.35}), 0, .52, 0, 48));
      g.add(box(.16, .02, .12, '#4f6b8a', -r*.25, .545, 0));
      vase(g, r*.35, .545, -r*.1, .035, .12, '#e9e2d6', R, false);
      break;
    }
    case 'floorlamp': {
      const r = Math.min(w, d)/2, lm = mat(c, {roughness:.35, metalness:.5});
      g.add(lathe([[0, 0], [r*.55, 0], [r*.58, .012], [r*.5, .03], [.02, .035]], lm, 0, 0, 0, 40), rod([0, .03, 0], [0, 1.36, 0], .011, lm));
      g.add(lathe([[r*.85, 0], [r*.55, .36]], glowMat('#f6ecd9', '#ffdca0', .45), 0, 1.22, 0, 48), blob(.035, .035, .035, glowMat('#fff', '#ffe2b0', 1.2), 0, 1.36, 0, 12));
      g.add(ring(r*.85, .004, lm, 0, 1.22, 0), ring(r*.55, .004, lm, 0, 1.58, 0));
      break;
    }
    case 'island': {
      const cm = mat(c, {roughness:.45}), stone = mat('#dcd7cf', {roughness:.2}), cd = d - .3, n = Math.max(1, Math.round((w - .1)/.6)), cab = new THREE.Group(), fz = cd/2 - .03;
      cab.add(box(w - .12, .1, cd - .08, '#4a4641', 0, 0, -.04), box(w - .1, .74, cd - .03, cm, 0, .1, -.015));
      fronts(cab, -w/2 + .05, .64, w - .1, .2, fz, n, 1, cm, 'bar'); fronts(cab, -w/2 + .05, .1, w - .1, .54, fz, n, 1, cm, 'bar', .56);
      cab.rotation.y = Math.PI; cab.position.z = bz + cd/2; g.add(cab);                    // 柜门朝 -z，+z 侧留出吧台挑空
      g.add(rbox(w, .05, d, stone, 0, .84, 0, .006));
      [-1, 1].forEach(s => g.add(box(.04, .84, d, stone, s*(w/2 - .02), 0, 0)));             // 瀑布式侧板
      g.add(lathe([[0, 0], [.06, 0], [.14, .06], [.15, .07]], mat('#6b543f', {roughness:.5, side:THREE.DoubleSide}), w*.22, .89, 0, 32));
      for (let k = 0; k < 4; k++) g.add(blob(.04, .04, .04, ['#d98c4a', '#9fbf5a', '#b5463a', '#e6c14f'][k], w*.22 + Math.cos(k*1.6)*.05, .935 + (k === 3 ? .04 : 0), Math.sin(k*1.6)*.05, 14));
      vase(g, -w*.25, .89, -.05, .05, .22, '#e9e2d6', R);
      break;
    }
    case 'barstool': {
      const r = Math.min(w, d)/2, bm = blackMetal(), sy = .7;
      [[1,1],[1,-1],[-1,1],[-1,-1]].forEach(([a, b]) => g.add(rod([a*r*.72, 0, b*r*.72], [a*r*.4, sy, b*r*.4], .011, bm)));
      g.add(ring(Math.SQRT2*r*(.72 - .32*.4), .008, bm, 0, .28, 0), cyl(r*.55, r*.55, .02, bm, 0, sy - .01, 0, 32));
      g.add(lathe([[0, 0], [r*.85, 0], [r*.95, .02], [r*.97, .045], [r*.9, .07], [0, .075]], mat(c, {roughness:.6}), 0, sy, 0, 40));
      break;
    }
    case 'waterheater': {
      const r = Math.min(d/2, .23), L = w - .06, yc = 1.95, zc = bz + r + .02, tm = mat(c, {roughness:.35}), cp = mat('#cfd4d8', {roughness:.4});
      const tank = mesh(new THREE.CylinderGeometry(r, r, L, 40), tm); tank.rotation.z = Math.PI/2; tank.position.set(0, yc, zc); g.add(tank);
      [-1, 1].forEach(s => g.add(blob(.035, r*.99, r*.99, cp, s*L/2, yc, zc, 32), box(.05, r*1.1, .02, '#9a9ea3', s*L*.3, yc - r*.55, bz + .01)));
      g.add(rbox(.2, .09, .02, '#e7eaec', L*.18, yc - .05, zc + r*.93, .008), box(.07, .03, .002, screenMat('#2f8f7a'), L*.18 - .04, yc - .02, zc + r*.93 + .011));
      [[-L*.3, '#3b7bbf'], [-L*.18, '#c0463a']].forEach(([x, cc]) => g.add(rod([x, yc - r*.8, zc], [x, 1.3, zc], .012, metal()), cyl(.02, .02, .03, cc, x, 1.5, zc, 12)));
      break;
    }
    case 'tv': {
      const th = w*.5625, yb = 1.2 - th/2, z = bz + .03;
      g.add(rbox(w*.6, th*.6, .03, '#222', 0, yb + th*.2, bz + .015, .01));
      g.add(rbox(w, th, .025, mat('#18181a', {roughness:.4, metalness:.3}), 0, yb, z + .01, .004), box(w - .016, th - .022, .002, screenMat('#1f2b3a'), 0, yb + .014, z + .0235), box(.04, .006, .002, '#8a8a8e', 0, yb + .004, z + .0235));
      break;
    }
    case 'aircon': {
      const am = mat(c, {roughness:.3}), h = 1.8, fz = d/2 - .005;
      g.add(rbox(w, .06, d, '#cfd3d6', 0, 0, 0, .015), rbox(w - .01, h - .06, d - .01, am, 0, .06, 0, .06));
      g.add(rbox(w - .06, 1.0, .01, mat(lighter(c, .4), {roughness:.12}), 0, .22, fz, .005), box(w - .1, .42, .01, '#3d4145', 0, 1.28, fz));
      for (let i = 0; i < 8; i++) g.add(rot(box(w - .11, .012, .03, '#e4e7ea', 0, 1.3 + i*.05, fz + .008), -.35));
      g.add(box(.1, .035, .003, mat('#101214', {emissive:'#4fb3a5', emissiveIntensity:.7}), 0, 1.12, fz + .006));
      for (let i = 0; i < 8; i++) g.add(box(w - .12, .005, .004, '#b9bfc4', 0, .09 + i*.015, fz + .002));
      break;
    }
    case 'acwall': {
      const h = .3, am = mat(c, {roughness:.3}), s = new THREE.Shape();
      s.moveTo(0, .02); s.lineTo(0, h); s.lineTo(d*.75, h); s.quadraticCurveTo(d, h, d, h*.55); s.quadraticCurveTo(d, 0, d*.55, 0); s.lineTo(.02, 0); s.lineTo(0, .02);
      const geo = new THREE.ExtrudeGeometry(s, {depth:w - .02, bevelEnabled:true, bevelThickness:.01, bevelSize:.006, bevelSegments:3, curveSegments:16});
      geo.rotateY(-Math.PI/2); geo.translate((w - .02)/2, 2.2, bz); g.add(mesh(geo, am));
      g.add(box(w - .12, .004, .07, '#3a3d40', 0, 2.19, bz + d*.55), rot(box(w - .12, .008, .06, am, 0, 2.18, bz + d*.72), .35));
      g.add(box(.06, .018, .002, mat('#101214', {emissive:'#4fb3a5', emissiveIntensity:.7}), w*.3, 2.2 + h*.5, bz + d + .007));
      for (let i = 0; i < 6; i++) g.add(box(w - .12, .003, .008, '#d5d9dc', 0, 2.2 + h + .006, bz + .03 + i*.022));
      break;
    }
    case 'dishwasher': {
      const dm = mat(c, {metalness:.55, roughness:.28}), fz = d/2 - .02;
      g.add(box(w - .01, .08, d - .07, '#3a3834', 0, 0, -.035), box(w - .005, .76, d - .03, '#8b9095', 0, .08, -.015));
      g.add(rbox(w - .006, .7, .02, dm, 0, .085, fz, .004), box(w - .006, .055, .02, '#26282a', 0, .785, fz));
      for (let i = 0; i < 4; i++) g.add(box(.012, .006, .002, mat('#101214', {emissive:i ? '#6fd0ff' : '#7fe08a', emissiveIntensity:.8}), w*.1 + i*.03, .81, fz + .011));
      pull(g, w*.6, false, 0, .74, fz + .01);
      break;
    }
    case 'ovencol': {
      const cm = mat(c, {roughness:.5}), h = 2.1, fz = d/2 - .02, frm = mat('#1c1d1f', {roughness:.3, metalness:.5}), gl = mat('#0b0c0d', {roughness:.03, metalness:.6});
      g.add(box(w - .02, .08, d - .06, '#4a4641', 0, 0, -.03), box(w, h - .08, d - .02, cm, 0, .08, -.01));
      fronts(g, -w/2, .08, w, .6, fz, 1, 2, cm, 'bar'); fronts(g, -w/2, 1.78, w, h - 1.8, fz, 1, 1, cm, 'bar', 1.84);
      [[.7, .58], [1.3, .46]].forEach(([y, ah]) => {
        g.add(box(w - .02, ah - .01, .02, frm, 0, y, fz + .01), box(w - .1, ah*.52, .003, gl, 0, y + ah*.1, fz + .021), box(w - .04, .06, .003, '#2a2c2e', 0, y + ah - .075, fz + .021));
        g.add(box(.08, .022, .002, mat('#101214', {emissive:'#ff9a3c', emissiveIntensity:.7}), 0, y + ah - .056, fz + .023));
        pull(g, w*.7, false, 0, y + ah*.72, fz + .02);
      });
      break;
    }
    case 'purifier': {
      const pm = mat(c, {roughness:.45}), h = .72;
      g.add(rbox(w, h, d, pm, 0, 0, 0, Math.min(w, d)*.2), rbox(w - .05, .006, d - .05, '#8d959b', 0, h - .002, 0, .02));
      for (let i = 0; i < 7; i++) g.add(box(w - .07, .004, .006, '#6f777d', 0, h + .002, -d/2 + .05 + i*(d - .1)/6));
      g.add(rbox(w - .06, .42, .006, fabric('#c8ccd0'), 0, .06, d/2 - .001, .01));
      const rg = new THREE.Mesh(new THREE.TorusGeometry(.03, .004, 8, 32), mat('#101214', {emissive:'#4fb3a5', emissiveIntensity:.8})); rg.position.set(0, .6, d/2 + .002); g.add(rg);
      break;
    }
    case 'officechair': {
      const r = Math.min(w, d)*.46, dk = darker(c, .75), bm = mat('#2b2b2d', {roughness:.45}), cm = chrome();
      for (let k = 0; k < 5; k++){
        const a = k*Math.PI*2/5, tx = Math.sin(a)*r*.95, tz = Math.cos(a)*r*.95;
        g.add(rod([0, .1, 0], [tx, .07, tz], .022, bm, .014, 10), cyl(.008, .008, .03, bm, tx, .04, tz, 8), rot(cyl(.026, .026, .03, '#111', tx, .026 - .015, tz, 16), 0, a, Math.PI/2));
      }
      g.add(cyl(.05, .06, .05, bm, 0, .08, 0, 20), cyl(.025, .025, .22, cm, 0, .12, 0, 16), cyl(.036, .036, .12, bm, 0, .12, 0, 16), rbox(.22, .05, .22, bm, 0, .34, .02, .01));
      g.add(rbox(w*.78, .03, d*.72, bm, 0, .38, .04, .01), rbox(w*.8, .08, d*.74, fabric(c), 0, .4, .05, .035));
      g.add(tube([[0, .36, 0], [0, .38, bz + .12], [0, .6, bz + .07]], .02, bm));
      const bf = shell(w*.72, .6, .03, .025, .08, bm); bf.rotation.x = Math.PI/2 - .12; bf.position.set(0, .88, bz + .06); g.add(bf);
      g.add(rot(box(w*.68, .56, .006, mat(dk, {roughness:.85, transparent:true, opacity:.88, side:THREE.DoubleSide}), 0, .6, bz + .085), -.12), rot(rbox(w*.5, .08, .03, fabric(c), 0, .66, bz + .11, .015), -.12));
      g.add(rod([-.05, 1.14, bz + .025], [-.05, 1.22, bz + .015], .008, bm), rod([.05, 1.14, bz + .025], [.05, 1.22, bz + .015], .008, bm), rbox(w*.45, .12, .05, fabric(dk), 0, 1.2, bz + .02, .025));
      [-1, 1].forEach(s => g.add(box(.035, .22, .035, bm, s*w*.4, .42, .04), rbox(.07, .03, d*.4, bm, s*w*.4, .63, .04, .012)));
      break;
    }
    case 'piano': {
      const pk = mat(c, {roughness:.12, metalness:.1}), bd = d*.5, kz = bz + bd, h = 1.25, kd = d*.22 - .03, iv = mat('#faf8f3', {roughness:.3}), eb = mat('#111', {roughness:.25}), kw = (w - .12)/52;
      g.add(box(w, h, bd, pk, 0, 0, bz + bd/2), rbox(w + .02, .03, bd + .03, pk, 0, h, bz + bd/2 + .01, .008));
      [-1, 1].forEach(s => g.add(rbox(.06, .13, kd + .06, pk, s*(w/2 - .03), .6, kz + (kd + .06)/2, .01), box(.05, .6, .05, pk, s*(w/2 - .08), 0, kz + kd + .01), box(.06, .04, d - bd, pk, s*(w/2 - .08), 0, kz + (d - bd)/2)));
      g.add(box(w - .12, .08, kd + .05, pk, 0, .6, kz + (kd + .05)/2), box(w - .12, .1, .03, pk, 0, .68, kz + .015));
      for (let i = 0; i < 52; i++){
        const x = -w/2 + .06 + kw*(i + .5); g.add(box(kw - .0015, .022, kd, iv, x, .68, kz + .03 + kd/2));
        if (i < 51 && 'ACDFG'.includes('ABCDEFG'[i % 7])) g.add(box(kw*.58, .02, kd*.62, eb, x + kw/2, .7, kz + .03 + kd*.31));
      }
      g.add(rot(box(w*.42, .18, .012, pk, 0, .84, kz + .012), -.25));
      [-.06, 0, .06].forEach(x => g.add(box(.025, .012, .07, mat('#c9a35a', {metalness:.9, roughness:.3}), x, .05, kz + .03)));
      const mt = cyl(.0, .05, .2, woodM('#5a3e2b'), w*.3, h + .03, bz + bd/2, 4); mt.rotation.y = Math.PI/4; g.add(mt);
      g.add(rot(box(.14, .18, .015, woodM('#c9a27a'), -w*.3, h + .03, bz + .06), -.15), rot(box(.11, .14, .002, '#9fb3c2', -w*.3, h + .05, bz + .07), -.15));
      break;
    }
    case 'treadmill': {
      const tm = mat(c, {roughness:.55}), bm = mat('#2a2a2c', {roughness:.5}), al = mat('#9a9ea3', {metalness:.6, roughness:.4});
      g.add(rbox(w, .14, d - .25, tm, 0, .03, .125, .03), box(w - .16, .006, d - .5, '#141414', 0, .17, .15));
      [-1, 1].forEach(s => g.add(box(.07, .008, d - .45, al, s*(w/2 - .05), .17, .15)));
      [bz + .06, d/2 - .06].forEach(z => [-1, 1].forEach(s => g.add(box(.06, .03, .06, bm, s*(w/2 - .06), 0, z))));
      g.add(rbox(w, .22, .32, tm, 0, 0, bz + .16, .05));
      [-1, 1].forEach(s => g.add(rod([s*(w/2 - .06), .15, bz + .2], [s*(w/2 - .06), 1.15, bz + .3], .025, bm, .022), tube([[s*(w/2 - .06), 1.0, bz + .28], [s*(w/2 - .06), 1.0, bz + .5], [s*(w/2 - .07), .97, bz + .62]], .018, bm)));
      const cg = new THREE.Group(); cg.position.set(0, 1.2, bz + .31); cg.rotation.x = -.5;
      cg.add(rbox(w*.8, .2, .08, bm, 0, -.1, 0, .02), box(w*.4, .11, .004, screenMat('#2a5d8f'), 0, -.055, .041)); g.add(cg);
      break;
    }
    default: g.add(box(w, .8, d, c));
  }
  g.position.set(wx(f.cx), M(f.elevation||0), wz(f.cy));
  g.rotation.y = -f.rot * Math.PI/180;       // 平面顺时针旋转 → 绕 Y 轴负向
  g.userData.fid = f.id;
  return g;
}

/* ======================= 建筑 ======================= */
function clearGroup(g){ g.traverse(o => { if (o.geometry) o.geometry.dispose(); }); g.clear(); }
function wallBox([x0, y0, x1, y1], yb, yt, m){
  if (yt - yb <= .001) return;
  const o = new THREE.Mesh(new THREE.BoxGeometry(M(x1-x0), yt-yb, M(y1-y0)), m || [wallMat, wallMat, capMat, wallMat, wallMat, wallMat]);
  o.position.set(wx((x0+x1)/2), (yb+yt)/2, wz((y0+y1)/2)); o.castShadow = o.receiveShadow = true; archUp.add(o);
  // 漫游辅助：墙体棱线 + 踢脚线，让相邻墙面、墙角一眼可分（仅漫游模式显示）
  const ln = new THREE.LineSegments(new THREE.EdgesGeometry(o.geometry), edgeMat); ln.position.copy(o.position); ln.userData.walkOnly = true; ln.visible = opt.mode === 'walk'; archUp.add(ln);
  if (yb <= .001){
    const p = o.geometry.parameters, sh = Math.min(.12, yt), sk = new THREE.Mesh(new THREE.BoxGeometry(p.width + .02, sh, p.depth + .02), skirtMat);
    sk.position.set(o.position.x, sh/2, o.position.z); sk.userData.walkOnly = true; sk.visible = opt.mode === 'walk'; archUp.add(sk);
  }
}
const edgeMat = new THREE.LineBasicMaterial({color:0x6f675b}), skirtMat = new THREE.MeshStandardMaterial({color:'#8b7f6e', roughness:.6});
function shapeOf(poly, flip){ const s = new THREE.Shape(); poly.forEach(([x, y], i) => s[i ? 'lineTo' : 'moveTo'](wx(x), flip ? wz(y) : -wz(y))); return s; }

function buildArch(){
  wallMat.color.set(finishPalette().wall);frameMat.color.set(finishPalette().frame);
  clearGroup(archFloor);clearGroup(archUp);lampG.clear();doors.length=0;colliders=[];
  const top=opt.cut,all=liveWalls().map(w=>({...w,height:Math.min(w.height,top*1000)}));
  // One joined wall surface: internal intersections disappear; jambs and window heads remain.
  const union=unionWalls(all,[wallMat,capMat]);
  const geo=union.geometry,sides=[],caps=[];
  for(let i=0;i<geo.attributes.position.count;i+=3){const list=geo.attributes.normal.getY(i)>.9?caps:sides;list.push(i,i+1,i+2);}
  geo.setIndex([...sides,...caps]);geo.clearGroups();geo.addGroup(0,sides.length,0);geo.addGroup(sides.length,caps.length,1);
  union.userData.wallSurface=true;archUp.add(union);
  const slab=new THREE.Mesh(new THREE.ShapeGeometry(shapeOf(FOOTPRINT)),mat('#e6e0d5',{roughness:.8}));slab.geometry.rotateX(-Math.PI/2);slab.position.y=-.008;slab.receiveShadow=true;archFloor.add(slab);
  FLOOR_CONNECTIONS.forEach(c=>{const fl=new THREE.Mesh(new THREE.ShapeGeometry(shapeOf(c.poly)),floorMat(connectionMat(c)));fl.geometry.rotateX(-Math.PI/2);fl.position.y=.002;fl.receiveShadow=true;fl.userData.floorConnection=c.id;archFloor.add(fl);});
  ROOMS.forEach(r=>{
    const fl=new THREE.Mesh(new THREE.ShapeGeometry(shapeOf(r.poly)),floorMat(state.rooms[r.id].mat));fl.geometry.rotateX(-Math.PI/2);fl.position.y=.002;fl.receiveShadow=true;fl.userData.room=r.id;archFloor.add(fl);
    const cg=new THREE.ShapeGeometry(shapeOf(r.poly,true));cg.rotateX(Math.PI/2);const ceil=new THREE.Mesh(cg,ceilingFinishMaterial());ceil.position.y=H;ceil.userData.baseCeiling=true;ceil.userData.room=r.id;ceil.visible=top>=H;archUp.add(ceil);
    const lamp=new THREE.Mesh(new THREE.CylinderGeometry(.22,.22,.02,32),new THREE.MeshStandardMaterial({color:'#fff',emissive:'#fff2d6',emissiveIntensity:.3}));lamp.position.set(wx(r.at[0]),H-.012,wz(r.at[1]));lamp.visible=top>=H;lampG.add(lamp);
    const pl=new THREE.PointLight(0xffd9a8,0,7,1.6);pl.position.set(wx(r.at[0]),H-.25,wz(r.at[1]));lampG.add(pl);
  });
  for(const p of wallPrisms(all))if(p.z0===0)colliders.push([wx(p.x0),wz(p.y0),wx(p.x1),wz(p.y1)]);
  [...DOORS,...SLIDES].filter(d=>!d.hiddenLeaf&&!wallRemoved(d.wall)&&!state.furniture.some(f=>f.type==='threshold'&&f.openingId===d.id)).forEach(d=>{const[x0,y0,x1,y1]=d.rect;const threshold=box(M(x1-x0),.012,M(y1-y0),mat('#d8d0c0',{roughness:.3}),wx((x0+x1)/2),0,wz((y0+y1)/2));archFloor.add(threshold);});
  WINS.filter(r=>!wallRemoved(r[5])).forEach(r=>{
    const winGroup=new THREE.Group();winGroup.userData.opening=r.opening;archUp.add(winGroup);
    const sill=M(r.sillHeight??850),head=Math.min(sill+M(r.windowHeight??1350),top);if(head<=sill)return;
    const[x0,y0,x1,y1]=r,hz=x1-x0>=y1-y0,L=M(hz?x1-x0:y1-y0),gh=head-sill,cx=wx((x0+x1)/2),cz=wz((y0+y1)/2);
    const pane=new THREE.Mesh(new THREE.BoxGeometry(hz?L:.01,gh,hz?.01:L),glassMat);pane.position.set(cx,sill+gh/2,cz);winGroup.add(pane);
    const n=Math.max(1,Math.round(L/.9));for(let k=0;k<=n;k++){const t=-L/2+k*L/n,m=box(hz?.04:.06,gh,hz?.06:.04,frameMat,cx+(hz?t:0),sill,cz+(hz?0:t));winGroup.add(m);}
    [sill,...(top>=sill+M(r.windowHeight??1350)?[head-.04]:[])].forEach(y=>winGroup.add(box(hz?L:.06,.04,hz?.06:L,frameMat,cx,y,cz)));
  });
  DOORS.filter(d=>!wallRemoved(d.wall)).forEach(d=>{
    const pivot=new THREE.Group(),L=M(d.len),dh=Math.min(M(d.height||2100),top);pivot.position.set(wx(d.h[0]),0,wz(d.h[1]));
    const leaf=box(L,dh,.04,d.hiddenLeaf?surfaceMaterial(finishPalette().wall,'plaster'):mat(d.entry?finishPalette().entry:finishPalette().door,{roughness:.5}),L/2);leaf.userData.hiddenDoor=!!d.hiddenLeaf;
    const handle=rod([L-.12,1,.032],[L-.055,1,.032],.009,metal());if(d.hiddenLeaf){pivot.add(leaf);handle.visible=false;}else pivot.add(leaf,handle);
    const ang=v=>Math.atan2(-v[1],v[0]),door={id:d.id,len:L,pivot,a0:ang(d.c),a1:ang(d.o),open:state.doors[d.id]!==false};if(door.a1-door.a0>Math.PI)door.a1-=Math.PI*2;if(door.a0-door.a1>Math.PI)door.a1+=Math.PI*2;door.cur=door.open?door.a1:door.a0;pivot.rotation.y=door.cur;leaf.userData.door=handle.userData.door=door;leaf.userData.opening=handle.userData.opening=d.opening;doors.push(door);archUp.add(pivot);
    if(d.hiddenLeaf||d.secondLeaf||state.furniture.some(f=>f.type==='doortrim'&&f.assemblyOwner&&f.openingId===d.id))return;
    const[x0,y0,x1,y1]=d.rect,hz=x1-x0>y1-y0,m=mat(finishPalette().wood,{roughness:.6}),a=[wx(x0),wz(y0)],b=[wx(x1),wz(y1)],cx=(a[0]+b[0])/2,cz=(a[1]+b[1])/2;
    if(top>M(d.height||2100))archUp.add(box(hz?M(x1-x0):.06,.05,hz?.06:M(y1-y0),m,cx,M(d.height||2100),cz));
    for(const s of [-1,1])archUp.add(box(.045,dh,.045,m,hz?cx+s*M(x1-x0)/2:cx,0,hz?cz:cz+s*M(y1-y0)/2));
  });
  SLIDES.filter(s=>!wallRemoved(s.wall)).forEach(slide=>archUp.add(buildSliding3D(slide,top)));
  applyLight();applyGrow();
}

function buildFurn(){
  clearGroup(furnG);
  state.furniture.forEach(f => furnG.add(buildFurniture(f)));
  furnG.visible = opt.furn; selKey = null; applyGrow();
}

function buildLabels(){
  labelG.children.slice().forEach(o => { o.element.remove(); labelG.remove(o); });
  ROOMS.filter(r => r.at).forEach(r => {
    const el = document.createElement('div'); el.className = 'rlabel';
    el.innerHTML = `${esc(nm(state.rooms[r.id].name))}<small>${area(r.poly).toFixed(1)}m²</small>`;
    const o = new CSS2DObject(el); o.position.set(wx(r.at[0]), opt.cut + .15, wz(r.at[1])); o.visible = labelG.visible; labelG.add(o);
  });
  $('#roomList').replaceChildren();
}

// 只重建变化的部分
function sync(force){
  if (!inited || (!active && !force)) return;
  const a = JSON.stringify([state.style,state.rooms, state.walls,state.doorStyles, state.demolished,state.ceilings,state.wallFinishes, opt.cut]), f = JSON.stringify([state.style,state.furniture]), l = JSON.stringify([state.rooms, opt.cut,state.furniture.map(f=>[f.cx,f.cy,f.w,f.d,f.rot])]);
  if (force || a !== sigArch){ sigArch = a; buildArch(); }
  if (force || f !== sigFurn){ sigFurn = f; buildFurn(); }
  if (force || l !== sigLabels){ sigLabels = l; buildLabels(); }
  doors.forEach(d=>d.open=state.doors[d.id]!==false);
}

// CSS2DRenderer 只看标签自身的 visible，不继承父级，所以逐个设置
function showLabels(v){ labelG.visible = v; labelG.children.forEach(o => o.visible = v); }
function applyGrow(){
  if (!inited) return;
  archUp.scale.y = Math.max(grow, .001);
  furnG.scale.y = Math.max(furnGrow, .001);
  lampG.visible = grow > .99;
}

/* ======================= 日照 / 夜景 ======================= */
function applyLight(){
  const t = (opt.hour - 6) / 12, az = Math.PI * (.15 + t*.7), el = Math.sin(Math.PI*t) * 1.05 + .15, warm = 1 - Math.sin(Math.PI*t);
  sun.position.set(Math.cos(az)*18, Math.sin(el)*20 + 3, -Math.sin(az)*10 + 8); sun.target.position.set(0, 0, 0);
  sun.color.setHSL(.09, .5 + warm*.4, .92 - warm*.12);
  sun.intensity = opt.night ? .05 : 1.4 + Math.sin(Math.PI*t)*1.6;
  hemi.intensity = opt.night ? .12 : 1.1;
  scene.background = new THREE.Color(opt.night ? 0x1c2130 : 0xf7f4ee);
  ground.material.color.set(opt.night ? 0x2a2e38 : 0xf2eee7);
  lampG.children.forEach(o => { if (o.isLight) o.intensity = opt.night ? 6 : 0; else if(o.material?.emissive) o.material.emissiveIntensity = opt.night ? 2 : .3; });
  renderer.toneMappingExposure = opt.night ? 1.25 : 1.05;
  envK = opt.night ? .15 : 1; matCache.forEach(m => { if (m.envMap) m.envMapIntensity = m.userData.env*envK; });
  const h = Math.floor(opt.hour), m = Math.round((opt.hour - h)*60);
  $('#sunT').textContent = `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
}

/* ======================= 相机位姿 / 动画 ======================= */
const ease = t => t < .5 ? 4*t*t*t : 1 - (-2*t + 2)**3/2;
const clamp01 = t => Math.max(0, Math.min(1, t));
const pose = (t, p) => ({t, p});
// 与当前 2D 视口完全重合的正俯视位姿：透视相机在该高度下，地面可视高度 = 2D 视口高度
function planPose(){
  const cx = view.x0 + SW()/2/view.s, cy = view.y0 + SH()/2/view.s, visH = SH()/view.s/1000;
  const dist = visH / 2 / Math.tan(FOV/2*Math.PI/180), t = new THREE.Vector3(wx(cx), 0, wz(cy));
  return pose(t, new THREE.Vector3(t.x, dist, t.z + 1e-4));
}
function isoFrom(P){
  const d = THREE.MathUtils.clamp(P.p.y, 5, 30), dir = new THREE.Vector3(.3, .82, .49).normalize();
  return pose(P.t.clone(), P.t.clone().addScaledVector(dir, d));
}
const isoWhole = () => {const P=topWhole(),d=P.p.y;return pose(P.t,new THREE.Vector3(d*.28,d*.97,d*.43));};
const topWhole = () => {const d=Math.max(DEFAULT.depth/1000+2, (DEFAULT.width/1000+2)/Math.max(.35,SW()/SH()))/(2*Math.tan(FOV/2*Math.PI/180));return pose(new THREE.Vector3(0,0,0),new THREE.Vector3(0,d,1e-4));};
const curPose = () => pose(orbit.target.clone(), camera.position.clone());
// 以目标点为中心做球坐标插值：镜头沿弧线倾斜环绕，而不是直线穿越
function camTween(A, B, e){
  const t = A.t.clone().lerp(B.t, e);
  const sa = new THREE.Spherical().setFromVector3(A.p.clone().sub(A.t)), sb = new THREE.Spherical().setFromVector3(B.p.clone().sub(B.t));
  let dth = sb.theta - sa.theta; dth = Math.atan2(Math.sin(dth), Math.cos(dth));
  const s = new THREE.Spherical(sa.radius + (sb.radius - sa.radius)*e, sa.phi + (sb.phi - sa.phi)*e, sa.theta + dth*e);
  camera.position.copy(t).add(new THREE.Vector3().setFromSpherical(s)); camera.lookAt(t); orbit.target.copy(t);
}
function setPose(P){ camera.position.copy(P.p); orbit.target.copy(P.t); camera.lookAt(P.t); }
function animate(dur, fn){ return new Promise(res => { anim = {t0:performance.now(), dur, fn, res}; }); }
const wait = ms => new Promise(r => setTimeout(r, ms));
function flyTo(B, dur = 900){ fly = {t0:performance.now(), dur, A:curPose(), B}; }
function flyToRoom(id){
  const r = ROOMS.find(r => r.id === id), xs = r.poly.map(p => p[0]), ys = r.poly.map(p => p[1]);
  const t = new THREE.Vector3(wx((Math.min(...xs)+Math.max(...xs))/2), .6, wz((Math.min(...ys)+Math.max(...ys))/2));
  const size = M(Math.max(Math.max(...xs)-Math.min(...xs), Math.max(...ys)-Math.min(...ys)));
  const dir = camera.position.clone().sub(orbit.target).setY(0); if (dir.lengthSq() < .01) dir.set(.6, 0, .8); dir.normalize();
  const dist = size*1.3 + 2.2;
  flyTo(pose(t, new THREE.Vector3(t.x + dir.x*dist*.7, dist*1.05, t.z + dir.z*dist*.7)));
}

/* ======================= 进入 / 退出 3D ======================= */
async function enter(){
  init(); active = true;
  renderer.setSize(SW(), SH()); labelRenderer.setSize(SW(), SH()); camera.aspect = SW()/SH(); camera.updateProjectionMatrix();
  sync(true);
  opt.mode = 'orbit'; orbit.enabled = false; showLabels(false);
  const A = planPose(), B = isoWhole();
  grow = 0; furnGrow = 0; applyGrow(); setPose(A);
  stage.classList.add('animating');
  startLoop(); renderer.render(scene, camera);
  stage.classList.add('is3d');                       // 交叉淡入：此刻 3D 画面与 2D 平面完全重合
  await wait(420);
  await animate(1700, t => {
    camTween(A, B, ease(clamp01(t/.85)));
    grow = ease(clamp01((t - .1)/.55));
    furnGrow = ease(clamp01((t - .45)/.5));
    applyGrow();
  });
  orbit.enabled = true; showLabels(opt.labels);
  stage.classList.remove('animating');
}
async function exit(){
  if (opt.mode === 'walk'){ stopTouchWalk(); $('#hint3d').textContent = HINT_ORBIT(); $('#cross').style.display = 'none';
    const dir = new THREE.Vector3(); camera.getWorldDirection(dir); orbit.target.copy(camera.position).addScaledVector(dir, 3).setY(0); opt.mode = 'orbit'; syncModeBtns(); }
  fly = null; orbit.enabled = false; showLabels(false); stage.classList.add('animating');
  const A = curPose(), B = planPose();
  await animate(1300, t => {
    camTween(A, B, ease(clamp01((t - .1)/.9)));
    furnGrow = 1 - ease(clamp01(t/.45));
    grow = 1 - ease(clamp01((t - .2)/.6));
    applyGrow();
  });
  stage.classList.remove('is3d');                    // 此刻 3D 已压平为正俯视，与 2D 重合后淡出
  await wait(450);
  active = false; cancelAnimationFrame(raf); raf = 0;
  stage.classList.remove('animating');
  grow = furnGrow = 1; applyGrow();
}

/* ======================= 选择 / 拾取 ======================= */
const ray = new THREE.Raycaster(), ptr = new THREE.Vector2();
function pick(e){
  if (!e) ptr.set(0, 0);
  else { const r = renderer.domElement.getBoundingClientRect(); ptr.set((e.clientX - r.left)/r.width*2 - 1, -(e.clientY - r.top)/r.height*2 + 1); }
  ray.setFromCamera(ptr, camera);
  const hits = ray.intersectObjects([...(opt.furn ? [furnG] : []), archUp, archFloor], true);
  for (const h of hits){
    if(opt.cut<H&&h.point.y>opt.cut+.001&&(Array.isArray(h.object.material)?h.object.material:[h.object.material]).some(m=>m?.clippingPlanes?.length))continue;
    let o = h.object,visible=true;for(let parent=o;parent;parent=parent.parent)if(!parent.visible){visible=false;break;}if(!visible)continue;
    let tagged=o;while(tagged && !tagged.userData.opening && tagged!==scene)tagged=tagged.parent;
    if(tagged?.userData.opening && !previewMode && opt.mode==='orbit')return {opening:tagged.userData.opening,dist:h.distance};
    if (o.material === glassMat) continue;
    if(o.userData.wallSurface && !previewMode && opt.mode==='orbit'){const wallHit=nearestWall({x:h.point.x*1000+OX,y:h.point.z*1000+OY});if(wallHit)return {wall:wallHit.w.id};}
    if (o.userData.door) return {door:o.userData.door, dist:h.distance};
    if (o.userData.room) return {room:o.userData.room};
    while (o && !o.userData.fid && o !== scene) o = o.parent;
    if(o?.userData.assemblyOwner?.kind==='furn')return {fid:o.userData.assemblyOwner.id};
    if (o?.userData.fid) return {fid:o.userData.fid};
    return null;                                     // 被墙体挡住
  }
  return null;
}
// 屏幕点 → 地面（y = 0）上的户型坐标 mm；s = 该处每 mm 对应的屏幕像素，用于拖放时的幽灵图大小
const ground0 = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
function groundAt(x, y){
  if (!active || anim) return null;
  const r = renderer.domElement.getBoundingClientRect(), hit = new THREE.Vector3();
  ptr.set((x - r.left)/r.width*2 - 1, -(y - r.top)/r.height*2 + 1);
  ray.setFromCamera(ptr, camera);
  if (!ray.ray.intersectPlane(ground0, hit) || hit.distanceTo(camera.position) > 60) return null;
  // 视线先碰到墙体（或飘窗台）时，落点取碰到的位置，而不是穿过墙落到看不见的墙后
  const wall = ray.intersectObjects([archUp, archFloor], true).find(h => h.object.material !== glassMat && (()=>{for(let o=h.object;o;o=o.parent)if(!o.visible)return false;return true;})());
  if (wall && wall.distance < hit.distanceTo(camera.position) - .01) hit.set(wall.point.x, 0, wall.point.z);
  const px = v => new THREE.Vector2(v.x*r.width/2, v.y*r.height/2), a = px(hit.clone().project(camera));
  const s = Math.max(a.distanceTo(px(hit.clone().add(new THREE.Vector3(1, 0, 0)).project(camera))),
                     a.distanceTo(px(hit.clone().add(new THREE.Vector3(0, 0, 1)).project(camera)))) / 1000;
  return {x:hit.x*1000 + OX, y:hit.z*1000 + OY, s};
}
function updateSel(){
  const key = ui.sel?.kind === 'furn' ? ui.sel.id : '';
  if (key !== selKey){
    selKey = key;
    if (selHelper){ scene.remove(selHelper); selHelper.geometry.dispose(); selHelper = null; }
    const g = key && furnG.children.find(g => g.userData.fid === key);
    if (g){ selHelper = new THREE.BoxHelper(g, 0xb5653a); scene.add(selHelper); }
  }
  if (selHelper){selHelper.update();const selected=furnG.children.find(g=>g.userData.fid===key);selHelper.visible=!!selected?.visible&&furnG.visible;}
}

/* ======================= 漫游 ======================= */
// 触屏漫游：左下虚拟摇杆移动，在画面上拖动转向（iPad 不支持鼠标指针锁定）
const HINT_ORBIT = () => COARSE ? tr('单指旋转 · 双指缩放 / 平移 · 点选家具后可拖动摆放 · 点门开关', '1 finger orbits · 2 fingers zoom / pan · select furniture to drag it · tap doors to open')
  : tr('左键旋转 · 右键平移 · 滚轮缩放 · 选中家具后拖动可摆放 · 点击门开关', 'Left-drag orbits · right-drag pans · scroll zooms · select furniture to drag it · click doors to open');
const HINT_TOUCHWALK = () => tr('左下摇杆移动 · 拖动画面转向 · 点门开关', 'Joystick moves · drag to look · tap doors to open');
const HINT_WALK = () => tr('WASD / 方向键移动 · 拖动转向 · E 开关门 · Esc 暂停', 'WASD moves · mouse looks · Shift runs · E opens doors · Esc pauses');
function syncHint3d(){ $('#hint3d').textContent = opt.mode === 'orbit' ? (previewMode?tr('拖动旋转 · 滚轮缩放 · 点击门开关','Drag to orbit · Scroll to zoom · Click doors'):HINT_ORBIT()) : touchWalk ? HINT_TOUCHWALK() : HINT_WALK(); }
let touchWalk = false;
const joy = {x:0, y:0, id:null}, eul = new THREE.Euler(0, 0, 0, 'YXZ');
function lookBy(dx, dy){
  eul.setFromQuaternion(camera.quaternion);
  eul.y += dx * .0025 * (opt.lookSensitivity||1); eul.x = THREE.MathUtils.clamp(eul.x + dy * .0025 * (opt.lookSensitivity||1), -1.15, 1.15);
  camera.quaternion.setFromEuler(eul);
}
function startTouchWalk(){
  touchWalk = true;
  $('#cross').style.display='block';
  $('#joy').style.display = 'block'; $('#walkExit').style.display = 'block';
  syncHint3d();
}
function stopTouchWalk(){
  touchWalk = false;Object.keys(keys).forEach(k=>keys[k]=false);$('#cross').style.display='none';
  joy.x = joy.y = 0; joy.id = null; $('#joy i').style.transform = '';
  $('#joy').style.display = 'none'; $('#walkExit').style.display = 'none';
  syncHint3d();
}
function bindJoystick(){
  const el = $('#joy'), knob = $('#joy i'), R = 50;
  const upd = e => {
    const r = el.getBoundingClientRect();
    let dx = e.clientX - (r.left + r.width/2), dy = e.clientY - (r.top + r.height/2);
    const L = Math.hypot(dx, dy); if (L > R){ dx *= R/L; dy *= R/L; }
    joy.x = dx/R; joy.y = dy/R; knob.style.transform = `translate(${dx}px,${dy}px)`;
  };
  el.addEventListener('pointerdown', e => { e.preventDefault(); e.stopPropagation(); if(!touchWalk)startTouchWalk(); joy.id = e.pointerId; el.setPointerCapture(e.pointerId); upd(e); });
  el.addEventListener('pointermove', e => { if (e.pointerId === joy.id) upd(e); });
  const end = e => { if (e.pointerId !== joy.id) return; joy.id = null; joy.x = joy.y = 0; knob.style.transform = ''; };
  el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
}
function setMode(m){
  if (anim) return;
  opt.mode = m; syncModeBtns();scene.children.find(o=>o.userData.grid).visible=opt.grid&&m==='orbit';
  if (m === 'walk'){
    window.select(null);
    if (opt.cut < H){ opt.cut = H; syncCutBtns(); sync(); }
    orbit.enabled = false; fly = null;
    const initial=CASE.walkStart;const room=ROOMS.find(r=>r.id===initial?.roomId)||ROOMS[0];const point=initial?.point||findWalkLanding(room);if(!point){toast('没有可用的漫游落点');opt.mode='orbit';orbit.enabled=true;return;}const aim=initial?.lookAt||roomViewingTarget(room).point,eye=(initial?.eyeMm||1600)/1000;camera.position.set(wx(point[0]),eye,wz(point[1]));camera.lookAt(wx(aim[0]),eye,wz(aim[1]));
    startTouchWalk();
  } else {
    stopTouchWalk(); orbit.enabled = true;
    $('#cross').style.display = 'none';
    syncHint3d();
    orbit.target.set(0, 0, 0); flyTo(isoWhole());
  }
  showLabels(opt.labels && m === 'orbit');
  archUp.traverse(o => { if (o.userData.walkOnly) o.visible = m === 'walk'; });
}
function blocked(x, z, r = .18){
  for(const f of state.furniture){if(furnitureBlocksPoint(f,x,z,{originX:OX,originY:OY,radius:r,eyeHeight:opt.mode==='walk'?camera.position.y:M(CASE.walkStart?.eyeMm||1600),heightMm:nominalHeights[f.type]||750,ignoredTypes:Object.keys(RENOVATION_MAP)}))return true;}
  for (const [x0, z0, x1, z1] of colliders) if (x > x0 - r && x < x1 + r && z > z0 - r && z < z1 + r) return true;
  for (const d of doors){
    const a = d.pivot.rotation.y, px = d.pivot.position.x, pz = d.pivot.position.z, ex = px + Math.cos(a)*d.len, ez = pz - Math.sin(a)*d.len;
    const t = clamp01(((x-px)*(ex-px) + (z-pz)*(ez-pz)) / ((ex-px)**2 + (ez-pz)**2));
    if (Math.hypot(x - (px + t*(ex-px)), z - (pz + t*(ez-pz))) < r*.8) return true;
  }
  return false;
}
function stepWalk(dt){
  if (!touchWalk) return;
  const sp = (keys.ShiftLeft || keys.ShiftRight ? 1.8 : .95) * dt, fwd = new THREE.Vector3();
  camera.getWorldDirection(fwd); fwd.y = 0; fwd.normalize();
  const right = new THREE.Vector3(-fwd.z, 0, fwd.x), mv = new THREE.Vector3();
  if (keys.KeyW || keys.ArrowUp) mv.add(fwd); if (keys.KeyS || keys.ArrowDown) mv.sub(fwd);
  if (keys.KeyD || keys.ArrowRight) mv.add(right); if (keys.KeyA || keys.ArrowLeft) mv.sub(right);
  if (touchWalk){ mv.addScaledVector(fwd, -joy.y).addScaledVector(right, joy.x); }
  const mag = Math.min(1, mv.length());        // 摇杆推得越远走得越快
  if (mag < .05) return;
  mv.normalize().multiplyScalar(sp * mag);
  const p = camera.position;
  if (!blocked(p.x + mv.x, p.z)) p.x += mv.x;
  if (!blocked(p.x, p.z + mv.z)) p.z += mv.z;
}
addEventListener('keydown', e => {
  if (!active || e.target.matches('input,select,textarea')) return;
  keys[e.code] = true;
  if(opt.mode==='walk'&&['KeyW','KeyA','KeyS','KeyD','ArrowUp','ArrowDown','ArrowLeft','ArrowRight','Space'].includes(e.code))e.preventDefault();
  if(opt.mode==='walk'&&e.code==='Escape'){stopTouchWalk();keys[e.code]=false;}
  if(opt.mode==='walk'&&e.code==='Space'&&!touchWalk)startTouchWalk();
  if (opt.mode === 'walk' && e.code === 'KeyE'){ const h = pick(); if (h?.door && h.dist < 2.5) toggleDoor(h.door); }
});
addEventListener('keyup', e => keys[e.code] = false);
addEventListener('blur',()=>{if(active&&opt.mode==='walk')stopTouchWalk();});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&active&&opt.mode==='walk')stopTouchWalk();});

/* ======================= 工具栏 ======================= */
function syncModeBtns(){ document.querySelectorAll('#modes3d .btn').forEach(b => b.classList.toggle('on', b.dataset.mode === opt.mode)); }
function syncCutBtns(){ document.querySelectorAll('[data-cut]').forEach(b => b.classList.toggle('on', +b.dataset.cut === opt.cut)); }
function syncWalkTexts(){syncHint3d();}
function bindUI(){
  document.querySelectorAll('#modes3d .btn').forEach(b => b.onclick = () => setMode(b.dataset.mode));
  // Mouse and touch both use drag-to-look plus joystick or keyboard movement.
  $('#walkExit').onclick = () => setMode('orbit');
  bindJoystick();
  syncWalkTexts();
  $('#vIso').onclick = () => { if (opt.mode === 'walk') setMode('orbit'); else flyTo(isoWhole()); };
  $('#vTop').onclick = () => { if (opt.mode === 'walk') setMode('orbit'); flyTo(topWhole()); };
  document.querySelectorAll('[data-cut]').forEach(b => b.onclick = () => { if (opt.mode === 'walk') return; opt.cut = +b.dataset.cut; syncCutBtns(); sync();renderPanel(); });
  document.querySelectorAll('#toggles3d .btn').forEach(b => b.onclick = () => {
    const k = b.dataset.t; opt[k] = !opt[k]; b.classList.toggle('on', opt[k]);
    if (k === 'furn'){ furnG.visible = opt.furn; if (!opt.furn && ui.sel?.kind === 'furn') window.select(null); }
    if (k === 'labels') showLabels(opt.labels && opt.mode === 'orbit' && !anim);
    if(k==='grid')scene.children.find(o=>o.userData.grid).visible=opt.grid&&opt.mode==='orbit';
    if (k === 'night') applyLight();
    syncQuickActions();
  });
  $('#sun').oninput = e => updateDaylight(e.target.value);
}

/* ======================= 主循环 ======================= */
let sceneRevision=0,lastRenderedPose='',lastShadowPose='';
const renderMetrics={rendered:0,skipped:0,savedDrawCalls:0,batches:0};
const clock = new THREE.Clock();
function startLoop(){ if (!raf){ clock.getDelta(); raf = requestAnimationFrame(loop); } }
function loop(){
  raf = requestAnimationFrame(loop);
  const dt = Math.min(clock.getDelta(), .05), now = performance.now();
  if (anim){ const t = clamp01((now - anim.t0)/anim.dur); anim.fn(t); if (t >= 1){ const r = anim.res; anim = null; r(); } }
  else if (fly){ const t = clamp01((now - fly.t0)/fly.dur); camTween(fly.A, fly.B, ease(t)); if (t >= 1) fly = null; }
  else if (opt.mode === 'orbit') orbit.update();
  else stepWalk(dt);
  doors.forEach(d => { const tg = d.open ? d.a1 : d.a0; d.cur = Math.abs(tg-d.cur)<.0001?tg:d.cur+(tg-d.cur)*Math.min(1,dt*6); d.pivot.rotation.y = d.cur; });
  updatePerformanceLighting(dt);
  // Keep input/damping responsive, but avoid GPU/DOM rendering an unchanged scene.
  const physical=[sceneRevision,sigArch,sigFurn,opt.hour,opt.night,opt.lamps,grow,furnGrow,performanceLighting.status().revision,doors.map(d=>d.cur.toFixed(6)).join(','),furnG.children.map(g=>[g.visible,...g.position.toArray(),...g.rotation.toArray().slice(0,3)]).join('|')].join(';');
  const pose=[physical,...camera.position.toArray().map(n=>n.toFixed(6)),...camera.quaternion.toArray().map(n=>n.toFixed(6)),camera.fov,camera.aspect,SW(),SH(),renderer.getPixelRatio(),opt.grid,opt.furn,opt.labels,topView,JSON.stringify(ui.sel)].join(';');
  if(pose!==lastRenderedPose||anim||fly){
    if(physical!==lastShadowPose){renderer.shadowMap.needsUpdate=true;lastShadowPose=physical;}
    updateSel();renderer.render(scene,camera);labelRenderer.render(scene,camera);lastRenderedPose=pose;renderMetrics.rendered++;
  }else renderMetrics.skipped++;
}

function shot(){ const a = document.createElement('a'); a.download = tr('户型装修方案', 'floor-plan-design') + '-3D.png'; a.href = renderer.domElement.toDataURL('image/png'); a.click(); }

function relang(){ syncWalkTexts(); if (inited) buildLabels(); }

window.View3D = {enter, exit, relang, sync:() => sync(), shot, groundAt, flyToRoom:id => active && !anim && flyToRoom(id), walking:() => active && opt.mode === 'walk'};

// Extensions preserve the reference UI conventions; authoritative case features stay independent.
let previewMode=false;
function inPolygon([x,y],poly){let on=false;for(let i=0,j=poly.length-1;i<poly.length;j=i++){const[a,b]=poly[i],[c,d]=poly[j];if(((b>y)!==(d>y))&&x<(c-a)*(y-b)/(d-b)+a)on=!on;}return on;}
function buildFurniture(f){
  const genuine=f.originalType,override=['sink','basin','counter','hob','coffee','tv'].includes(genuine)||['ksink','vanity','stove','tv','counter','tvstand','coffee','sofabed'].includes(f.type)||f.standOnly;
  let g;
  if(override){g=detailedFurniture({...f,type:f.type==='ksink'?'sinkInsert':genuine||({vanity:'basin',stove:'hob'}[f.type]||f.type),...componentSpec(f),cutouts:f.type==='counter'?counterCutouts(f):[],h:f.h||nominalHeights[f.type]||850});g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-f.rot*Math.PI/180;g.userData.fid=f.id;g.traverse(o=>{const list=Array.isArray(o.material)?o.material:[o.material];for(const m of list)if(m?.isMeshStandardMaterial&&m.metalness>.1){m.envMap=envTex;m.needsUpdate=true;}});}
  else{
    g=referenceFurniture(f);
    // Reference furniture was hardcoded in height. Editing now changes the same 3D model.
    const h=f.fitToCeiling?DEFAULT.height:(f.h||nominalHeights[f.type]||850),basis=['wardrobe','bookshelf'].includes(f.type)?h:nominalHeights[f.type];
    if(!basis)throw Error('缺少组件高度定义：'+f.type);g.scale.y=h/basis;
    if(['acwall','waterheater'].includes(f.type)){
      // Normalize the legacy local mounting offset before applying the configured elevation.
      // A world-space minimum already includes elevation and must never cancel it.
      g.position.y=0;g.updateMatrixWorld(true);
      const bb=new THREE.Box3().setFromObject(g),height=bb.max.y-bb.min.y;
      if(!Number.isFinite(height)||height<=0)throw Error('壁挂模型高度无效：'+f.type);
      const ratio=M(h)/height;g.scale.y*=ratio;
      g.position.y=M(f.elevation||0)-bb.min.y*ratio;
    }else g.position.y=M(f.elevation||0);
  }
  g.updateMatrixWorld(true);const bound=new THREE.Box3().setFromObject(g);
  g.userData.caseHeight=f.h;g.userData.fitToCeiling=!!f.fitToCeiling;return g;
}
function toggleDoor(d){mutate(()=>state.doors[d.id]=!d.open);}
function bindLibraryFilters(){
  const search=$('#libSearch'),cat=$('#libCategory');
  const filter=()=>{const q=search.value.toLowerCase().trim();document.querySelectorAll('#lib .item').forEach(el=>{const[ci]=el.dataset.key.split(':');el.hidden=(cat.value!==''&&cat.value!==ci)||!el.textContent.toLowerCase().includes(q);el.style.display=el.hidden?'none':'';});document.querySelectorAll('#lib .lib-grid').forEach(el=>{const show=[...el.children].some(c=>!c.hidden);el.style.display=show?'':'none';el.previousElementSibling.style.display=show?'':'none';});};
  search.oninput=filter;cat.onchange=filter;
}
function setPreview(on){previewMode=on;document.body.classList.toggle('preview',on);$('#previewBtn').classList.toggle('on',on);$('#previewBtn').textContent=on?'返回编辑':'参观预览';ui.sel=null;renderPanel();document.querySelector('aside.right').scrollTop=0;if(on&&inited)flyTo(isoWhole());$('#tip').textContent=on?'参观预览 · 旋转、缩放或第一人称漫游':TIPS()[viewMode];$('#tgLib').disabled=on;$('#tgPanel').textContent=on?'参观导航 ◨':'属性 ◨';$('#lib').inert=on;if(inited)syncHint3d();requestAnimationFrame(()=>{if(inited){renderer.setSize(SW(),SH());labelRenderer.setSize(SW(),SH());camera.aspect=SW()/SH();camera.updateProjectionMatrix();}});}
$('#previewBtn').onclick=()=>setPreview(!previewMode);
$('#referencesBtn').onclick=()=>$('#referencesDialog').showModal();$('#closeRefs').onclick=()=>$('#referencesDialog').close();
$('#saveHtml').onclick=()=>{
  const clone=document.documentElement.cloneNode(true);
  clone.querySelector('#projectSeed').dataset.storageId=globalThis.crypto?.randomUUID?.()||Array.from(crypto.getRandomValues(new Uint32Array(4)),n=>n.toString(16)).join('-');
  clone.querySelector('#projectSeed').textContent=JSON.stringify(state).replace(/</g,'\\u003c');
  // Runtime WebGL and CSS2D nodes belong to the session, never to the saved document.
  const h=clone.querySelector('#view3d');h.querySelectorAll('canvas,.rlabel').forEach(n=>n.remove());
  for(const n of [...h.children])if(n.tagName==='DIV'&&n.style.pointerEvents==='none')n.remove();
  clone.querySelector('#stage').classList.remove('is3d','animating','drawer-panel');clone.querySelector('body').classList.remove('m3d','preview','busy','walking','pointer-locked','walk-ui-idle','walk-paused');clone.querySelector('#previewBtn').textContent='浏览模式';clone.querySelector('#previewBtn').classList.remove('on');clone.querySelector('#lib').removeAttribute('inert');clone.querySelector('#tgLib').removeAttribute('disabled');clone.querySelector('#referencesDialog').removeAttribute('open');
  for(const sel of ['#cross','#joy','#walkExit'])clone.querySelector(sel).style.display='none';
  for(const n of [...clone.querySelector('#toolbarOverflow').children])clone.querySelector('#toolbarMore').before(n);clone.querySelector('#toolbarMore').removeAttribute('open');
  clone.querySelectorAll('.quick-menu,.work-menu,.viewport-menu,.menu-sub').forEach(n=>n.removeAttribute('open'));clone.querySelector('#returnEdit').hidden=true;clone.querySelector('body').classList.remove('walking');clone.querySelector('#savedState').textContent='就绪';clone.querySelector('#savedState').dataset.status='ready';
  download('Floor-Visualization-plan.html',new Blob(['<!doctype html>\n'+clone.outerHTML],{type:'text/html;charset=utf-8'}));toast('已保存独立 HTML；断网也可打开当前方案');
};
// Development verification API: matches visible controls and never substitutes for UI testing.
window.homeStudio={floorTotals:()=>floorTotals(),getState:()=>structuredClone(state),getModel:()=>structuredClone(DEFAULT),getRooms:()=>structuredClone(ROOMS),getCatalog:()=>structuredClone(availableCatalog()),select,undo,redo,setView,validate:fixState,toggleWall,toggleDoor:id=>{const d=doors.find(d=>d.id===id);if(d)toggleDoor(d);},get3D:()=>({scene,camera,renderer,archUp,archFloor,furnG,doors,opt,blocked}),inspect:()=>({mode:viewMode,preview:previewMode,switching,wallHeight:H,area:ROOMS.reduce((n,r)=>n+area(r.poly),0),furniture:state.furniture.length,doors:DOORS.map(d=>({id:d.id,hinge:d.h,direction:d.o,len:d.len})),bounds:BOUNDS}),audit3D:()=>{if(!inited)return null;scene.updateMatrixWorld(true);return furnG.children.map(g=>{const b=new THREE.Box3().setFromObject(g);return{id:g.userData.fid,minY:b.min.y,maxY:b.max.y,fit:g.userData.fitToCeiling};});}};

// Preview is a viewing mode: object clicks cannot change the scheme. Door opening remains available.
const originalSelect=select;select=function(sel){if(previewMode)return;originalSelect(sel);};
document.addEventListener('keydown',e=>{if(!previewMode||opt.mode==='walk'||e.target.matches('input,select,textarea'))return;if(['delete','backspace','r','x','m','v'].includes(e.key.toLowerCase())||((e.metaKey||e.ctrlKey)&&['z','d'].includes(e.key.toLowerCase()))){e.preventDefault();e.stopImmediatePropagation();}},true);

// V6: shared component semantics and editable architecture, using the confirmed case geometry.
function checkedSize(n){if(!Number.isFinite(n)||n<50||n>15000)throw Error('家具宽深须在 50–15000 mm 之间');return Math.round(n);}
function catalogSpec(it){const[type,name,w]=it;return type==='vanity'?{basins:name.includes('双盆')?2:1,mirror:true}:type==='ksink'?{basins:1,fixtureOnly:true}:type==='counter'?{upperCabinet:true,accessories:true}:{};}
function componentSpec(f){
 const s={};if(f.type==='ksink')s.fixtureOnly=true;if(['vanity','ksink'].includes(f.type)){s.basins=f.basins??(f.type==='vanity'&&f.name?.includes('双盆')?2:1);if(![1,2].includes(s.basins))throw Error('台盆数量无效');if(s.basins===2&&f.w<700)throw Error('双盆组件宽度至少为 700 mm');}
 if(f.type==='vanity')s.mirror=f.mirror!==false;
 if(f.type==='counter'){s.upperCabinet=f.upperCabinet??!f.originalType;s.accessories=f.accessories!==false;}
 return s;
}
function validateWalls(input,legacyDem=[]){
 if(!Array.isArray(input)||input.length<DEFAULT.walls.length||input.length>100)throw Error('墙体数据无效');
 const walls=structuredClone(input),ids=new Set();
 for(const w of walls){
  if(typeof w.id!=='string'||ids.has(w.id))throw Error('墙体编号无效');ids.add(w.id);
  if(![...(w.a||[]),...(w.b||[])].every(n=>Number.isFinite(n)&&Math.abs(n)<=50000)||w.a?.length!==2||w.b?.length!==2)throw Error('墙体坐标无效');
  const l=Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]);if(l<200||l>30000||Math.abs(w.a[0]-w.b[0])>.1&&Math.abs(w.a[1]-w.b[1])>.1)throw Error('墙体须为至少 200 mm 的水平或垂直墙');
  if(!Number.isFinite(w.t)||w.t<60||w.t>500||w.height!==DEFAULT.height)throw Error(`墙厚须为 60–500 mm，墙高须为 ${DEFAULT.height} mm`);
  const original=DEFAULT.walls.find(o=>o.id===w.id);
  if(!original&&w.bearing)throw Error('新增隔墙必须为非承重墙');
  if(original&&original.bearing!==w.bearing)throw Error('不能修改原墙的结构属性');
  if(original?.bearing){for(const k of ['a','b','t','height','opens'])if(JSON.stringify(w[k])!==JSON.stringify(original[k]))throw Error('原图黑填墙的墙体和洞口已锁定');if(w.demolished)throw Error('承重墙不可拆除');}
  if(!Array.isArray(w.opens)||w.opens.length>20)throw Error('洞口数据无效');
  let end=-1;for(const o of [...w.opens].sort((a,b)=>a.at-b.at)){
   if(!['door','window','sliding'].includes(o.kind)||!Number.isFinite(o.at)||!Number.isFinite(o.width)||o.width<300||o.at<0||o.at+o.width>l+.1||o.at<end)throw Error('洞口须在墙内且不能重叠');
   if(o.kind==='door'&&(![1,-1].includes(o.swing)||!['start','end',undefined].includes(o.hingeEnd)||!Number.isFinite(o.angle??90)||(o.angle??90)<5||(o.angle??90)>100))throw Error('门轴或开启方向无效');
   if(o.height!==undefined&&(!Number.isFinite(o.height)||o.height<(o.kind==='window'?300:1800)||o.height>DEFAULT.height))throw Error(o.kind==='window'?'窗高须为有效尺寸且不超过层高':'门高须至少 1800 mm 且不超过层高');
   if(o.kind==='window'&&o.sillHeight!==undefined&&(!Number.isFinite(o.sillHeight)||o.sillHeight<0||o.sillHeight+(o.height||1350)>DEFAULT.height))throw Error('窗台高度与窗高之和不能超过层高');
   if(o.doorModel!==undefined&&!['single','sliding','double','hidden'].includes(o.doorModel))throw Error('门型无效');
   if(o.doorModel==='double'&&(o.width<600||!Number.isFinite(o.leafRatio??.5)||(o.leafRatio??.5)<.3||(o.leafRatio??.5)>.7))throw Error('对开门净宽至少 600 mm，门扇比例为 30%–70%');
   if(o.kind==='sliding'&&((o.leaves!==undefined&&![2,3].includes(o.leaves))||o.width<(o.leaves||2)*300||!Number.isFinite(o.slideOpen??0)||(o.slideOpen??0)<0||(o.slideOpen??0)>1||![1,-1].includes(o.slideDirection??1)))throw Error('推拉门扇数、净宽或开启程度无效');
   end=o.at+o.width;
  }
 }
 if(DEFAULT.walls.some(w=>!ids.has(w.id)))throw Error('原户型墙体不能移除；请使用拆除标记');
 // V5 indexed demolition flags only apply during one-time migration.
 for(const id of legacyDem){const old=initialWallSegments()[Number(id.slice(1))];if(old){const w=walls.find(w=>w.id===old[5]);if(w&&!w.bearing)w.demolished=true;}}
 return walls;
}
function initialWallSegments(){return DEFAULT.walls.flatMap(w=>intervals(w).map(([a,b])=>{const r=wallRect(w,a,b,DEFAULT.walls);return[r.x0,r.y0,r.x1,r.y1,w.bearing?'b':'n',w.id];}));}
function syncGeometry(){
 WALLS.length=WINS.length=DOORS.length=SLIDES.length=0;
 for(const w of state.walls){
  for(const[a,b]of intervals(w)){const r=wallRect(w,a,b,state.walls);WALLS.push([r.x0,r.y0,r.x1,r.y1,w.bearing?'b':'n',w.id]);}
  w.opens.forEach((raw,i)=>{const o=effectiveDoorOpening(state,w,raw,i);const a=wallRect(w,o.at,o.at+o.width,[]),r=[a.x0,a.y0,a.x1,a.y1,w.bearing?'b':'n',w.id];
   r.opening={kind:'opening',wallId:w.id,index:i,openingId:o.id||null};
   if(o.kind==='window'){r.sillHeight=o.sillHeight??850;r.windowHeight=o.height??1350;WINS.push(r);}
   if(o.kind==='sliding')SLIDES.push({rect:r,v:Math.abs(w.b[1]-w.a[1])>1,wall:w.id,opening:r.opening});
   if(o.kind==='door'){const p=doorPose(w,{...o,angle:o.angle??90});DOORS.push({name:o.label||'房门',rect:r,h:p.hinge,c:p.closed,o:p.leaf,len:p.leafWidth,wall:w.id,id:i===0?w.id:w.id+':'+(o.id||i),entry:isEntrance(w,o),opening:r.opening});}
  });
 }
 // Indexed flags are retained for V5-compatible audit output, but wall IDs are authoritative.
 state.demolished=WALLS.flatMap((w,i)=>wallRemoved(w[5])?['w'+i]:[]);
}
const oldToggleWall=toggleWall;
toggleWall=function(id){const w=state.walls.find(w=>w.id===id)||state.walls.find(w=>w.id===WALLS[+id.slice(1)]?.[5]);if(!w||w.bearing)return toast('原图黑填墙不可拆改');mutate(()=>{w.demolished=!w.demolished;state.demolished=[];});};
const oldValidateSel=validateSel;
validateSel=function(){oldValidateSel();if(ui.sel?.kind==='wall'&&!state.walls.some(w=>w.id===ui.sel.id))ui.sel=null;};
const oldRenderSel=renderSel;
renderSel=function(){oldRenderSel();if(ui.sel?.kind==='wall'){const w=state.walls.find(w=>w.id===ui.sel.id);if(w)$('#gSel').innerHTML+=`<path d="M${w.a.join(' ')}L${w.b.join(' ')}" fill=none stroke="#b5653a" stroke-width=3 vector-effect="non-scaling-stroke" pointer-events="none"/>`;}};
function wallPanel(w){const locked=w.bearing,l=Math.round(Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]));
 const field=(id,label,v,extra='')=>`<label>${label}<input id=${id} type=number value=${v} ${extra} ${locked?'disabled':''}></label>`;
 return `<section><h3>${locked?'承重墙 · 锁定':'普通隔墙'} · ${esc(w.id)}</h3><p class=scene-mode-note>长度 ${l} mm · 墙高 ${DEFAULT.height} mm</p><div class=form>${field('wAx','起点 X',w.a[0])}${field('wAy','起点 Y',w.a[1])}${field('wBx','终点 X',w.b[0])}${field('wBy','终点 Y',w.b[1])}${field('wThickness','厚度 / mm',w.t,'min=60 max=500')}</div><div class=actions>${locked?'':`<button class="btn danger" id=wallRemove>${w.demolished?'恢复隔墙':'拆除隔墙'}</button>`}<button class=btn id=back>返回</button></div></section><section><h3>门窗洞口 · ${w.opens.length}</h3>${w.opens.map((o,i)=>`<div class=opening-editor><b>${esc(o.label||({door:'平开门',window:'窗洞',sliding:'推拉门'}[o.kind]))}</b><div class=form><label>沿墙位置 / mm<input type=number data-opening-at=${i} value=${o.at} ${locked?'disabled':''}></label><label>净宽 / mm<input type=number data-opening-width=${i} value=${o.width} min=300 ${locked?'disabled':''}></label>${o.kind==='door'?`<label>门轴<select data-opening-hinge=${i} ${locked?'disabled':''}><option value=start ${o.hingeEnd!=='end'?'selected':''}>起点侧</option><option value=end ${o.hingeEnd==='end'?'selected':''}>终点侧</option></select></label><label>开启侧<select data-opening-swing=${i} ${locked?'disabled':''}><option value=1 ${o.swing===1?'selected':''}>墙左侧</option><option value=-1 ${o.swing===-1?'selected':''}>墙右侧</option></select></label><label>开启角度<input type=number data-opening-angle=${i} value=${o.angle??90} min=5 max=100 ${locked?'disabled':''}></label>`:''}</div>${locked?'':`<button class="btn danger" data-opening-delete=${i}>移除洞口</button>`}</div>`).join('')}<p class=scene-mode-note>${locked?'承重墙及原有洞口锁定。':'选“新增门洞 / 窗洞”，点击普通墙放置。门轴、开启侧可在此调整。'}</p></section>`;
}
function bindWallPanel(w){
 const update=fn=>mutate(()=>{fn();state.demolished=[];});
 for(const[id,k,index]of [['wAx','a',0],['wAy','a',1],['wBx','b',0],['wBy','b',1]])$('#'+id).onchange=e=>update(()=>w[k][index]=Number(e.target.value));
 $('#wThickness').onchange=e=>update(()=>w.t=Number(e.target.value));$('#wallRemove')?.addEventListener('click',()=>toggleWall(w.id));$('#back').onclick=()=>select(null);
 for(const [attr,key,number]of [['at','at',true],['width','width',true],['hinge','hingeEnd',false],['swing','swing',true],['angle','angle',true]])document.querySelectorAll(`[data-opening-${attr}]`).forEach(el=>el.onchange=e=>update(()=>w.opens[Number(el.getAttribute('data-opening-'+attr))][key]=number?Number(e.target.value):e.target.value));
 document.querySelectorAll('[data-opening-delete]').forEach(el=>el.onclick=()=>update(()=>w.opens.splice(+el.dataset.openingDelete,1)));
}
const basePanel=renderPanel;
renderPanel=function(){if(ui.sel?.kind==='wall'&&!previewMode){renderFab();const w=state.walls.find(w=>w.id===ui.sel.id);if(w){$('#panel').innerHTML=wallPanel(w);bindWallPanel(w);return;}}basePanel();};
function nearestWall(p){let best=null,dist=Infinity;for(const w of state.walls){if(w.demolished)continue;const dx=w.b[0]-w.a[0],dy=w.b[1]-w.a[1],l=Math.hypot(dx,dy),at=Math.max(0,Math.min(l,((p.x-w.a[0])*dx+(p.y-w.a[1])*dy)/l)),d=Math.hypot(p.x-w.a[0]-dx*at/l,p.y-w.a[1]-dy*at/l);if(d<dist&&d<w.t/2+100){best={w,at,l};dist=d;}}return best;}
function addOpeningAt(p,kind){const hit=nearestWall(p);if(!hit)return toast('请点击一段普通墙');const{w,at,l}=hit;if(w.bearing)return toast('承重墙不允许开洞');const width=kind==='door'?900:1200;if(l<width+100)return toast('墙段太短，无法放置默认洞口');const o={id:uid(),kind,at:Math.max(50,Math.min(l-width-50,Math.round((at-width/2)/10)*10)),width,swing:1,hingeEnd:'start',angle:90};if(mutate(()=>{w.opens.push(o);state.demolished=[];})){select({kind:'opening',wallId:w.id,index:w.opens.length-1,openingId:o.id});setTool('select');}}
let wallDraft=null;
function draftPoint(p,a){const x=Math.round(p.x/10)*10,y=Math.round(p.y/10)*10;return a?(Math.abs(x-a.x)>Math.abs(y-a.y)?{x,y:a.y}:{x:a.x,y}):{x,y};}
function renderDraft(p){$('#gDraft').innerHTML=wallDraft&&p?`<path d="M${wallDraft.x} ${wallDraft.y}L${p.x} ${p.y}" stroke="#b5653a" stroke-width=120 opacity=.5 fill=none/><text x=${p.x} y=${p.y-120} font-size=160 fill="#965b36">${Math.round(Math.hypot(p.x-wallDraft.x,p.y-wallDraft.y))} mm</text>`:'';}
svg.addEventListener('pointerdown',e=>{
 if(e.button!==0||previewMode)return;
 if(['wall','door','window'].includes(ui.tool)){e.preventDefault();e.stopImmediatePropagation();closeDrawers();const p=toMM(e);
  if(ui.tool==='wall'){const q=draftPoint(p,wallDraft);if(!wallDraft){wallDraft=q;renderDraft(q);}else{const a=wallDraft,b=q;const success=mutate(()=>{state.walls.push({id:'N'+uid(),a:[a.x,a.y],b:[b.x,b.y],t:120,height:DEFAULT.height,bearing:false,demolished:false,opens:[],source:'新增普通隔墙'});state.demolished=[];});if(success){wallDraft=null;renderDraft(null);select({kind:'wall',id:state.walls.at(-1).id});setTool('select');}}}else addOpeningAt(p,ui.tool);return;
 }
 if(ui.tool==='select'&&e.target.closest('[data-wall]')){e.preventDefault();e.stopImmediatePropagation();const segment=WALLS[Number(e.target.closest('[data-wall]').dataset.wall.slice(1))];select({kind:'wall',id:segment[5]});}
},true);
svg.addEventListener('pointermove',e=>{if(wallDraft)renderDraft(draftPoint(toMM(e),wallDraft));});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){wallDraft=null;renderDraft(null);$('#toolbarMore').open=false;}},true);
const baseTool=setTool;setTool=function(t){wallDraft=null;renderDraft(null);baseTool(t);$('#toolbarMore').open=false;};
const baseHint=syncModeHint;syncModeHint=function(){baseHint();const hints={wall:'点击两端新建普通隔墙 · 自动水平 / 垂直 · Esc 取消',door:'点击普通墙新增 900 mm 门洞 · 右侧调整门轴和开启侧',window:'点击普通墙新增 1200 mm 窗洞 · 右侧调整位置和净宽'};if(hints[ui.tool]){$('#modehint').textContent=hints[ui.tool];$('#modehint').classList.add('show');}};
const baseDelete=deleteSel;deleteSel=function(){if(ui.sel?.kind==='wall')toggleWall(ui.sel.id);else baseDelete();};

// One semantic description drives both SVG and true recessed 3D basin construction.
const baseSymbol=furnSVG;
furnSVG=function(t,w,d,c,f={}){if(!['ksink','vanity'].includes(t))return baseSymbol(t,w,d,c,f);const spec=componentSpec({...f,type:t,w,d}),x=-w/2,y=-d/2,count=spec.basins;
 const bw=Math.min(t==='ksink'?780:550,(w-100)/count-(count===2?45:0)),bd=Math.min(360,d*.66),centers=count===2?[-w*.24,w*.24]:[0];let s=rc(x,y,w,d,c,'rx="20"');
 for(const cx of centers){s+=rc(cx-bw/2,-bd/2,bw,bd,t==='ksink'?'#dbe2e3':'#fff','rx="35"')+`<circle cx=${cx} cy=0 r=18 fill="#b3b7b5"/>`;
  if(t==='vanity'||cx===centers[0])s+=`<circle cx=${t==='ksink'?0:cx} cy=${y+d*.1} r=22 fill="#b7a284"/>`;
 }
 if(t==='vanity'&&spec.mirror)s+=ln(x+35,y+12,x+w-35,y+12,'stroke-width="3"');return s;
};
const baseFurnPanel=furnPanel;
furnPanel=function(f){let s=baseFurnPanel(f);const spec=componentSpec(f);if(['ksink','vanity'].includes(f.type))s+=`<section><h3>台盆配置</h3><label>盆槽数量 <select id=basinCount><option value=1 ${spec.basins===1?'selected':''}>单盆</option><option value=2 ${spec.basins===2?'selected':''}>双盆</option></select></label>${f.type==='vanity'?`<p><label><input id=componentMirror type=checkbox ${spec.mirror?'checked':''}> 镜面与镜前灯</label></p>`:''}<p class=scene-mode-note>${f.type==='ksink'?'水槽独立于地柜，可单独拖动、旋转和改尺寸；台面开孔随水槽位置同步。':'2D 图例与 3D 盆腔同步；龙头位于柜体背面。'}</p></section>`;
 if(f.type==='counter')s+=`<section><h3>橱柜组合</h3><label><input id=upperCabinet type=checkbox ${spec.upperCabinet?'checked':''}> 上柜、背板与台下灯</label><p><label><input id=counterAccessories type=checkbox ${spec.accessories?'checked':''}> 台面附件</label></p><p class=scene-mode-note>高度为地柜台面高度；上柜作为可选组合。窗下台面保持地柜形式。</p></section>`;return s;};
const baseBindFurn=bindFurnPanel;
bindFurnPanel=function(f){baseBindFurn(f);for(const[id,key]of [['basinCount','basins'],['componentMirror','mirror'],['upperCabinet','upperCabinet'],['counterAccessories','accessories']]){const el=$('#'+id);if(el)el.onchange=()=>mutate(()=>getF(f.id)[key]=el.type==='checkbox'?el.checked:Number(el.value));}};

// Palette changes only affect new defaults. Imported user colors stay intact.
const baseCaseFurniture=caseFurniture;
caseFurniture=function(f){const n=baseCaseFurniture(f);Object.assign(n,componentSpec(n));return n;};
function arrangeMobileToolbar(){}

if(!loadedState)state=defaultState();
arrangeMobileToolbar();matchMedia('(max-width:600px)').addEventListener('change',arrangeMobileToolbar);
document.addEventListener('pointerdown',e=>{if($('#toolbarMore').open&&!$('#toolbarMore').contains(e.target))$('#toolbarMore').open=false;});
function showRecovery(){if(!recovery){if(storageNotice)toast(storageNotice);return;}$('#recoveryMessage').textContent='原因：'+recovery.message;const raw=recovery.raw;
 $('#downloadRecovery').onclick=()=>download('三室两厅两卫-读取失败的原始方案.json',new Blob([raw],{type:'application/json'}));
 let backup=null;try{const text=localStorage.getItem(STORE+'-backup');if(text)backup=fixState(JSON.parse(text));}catch{}
 $('#restoreBackup').disabled=!backup;$('#restoreBackup').onclick=()=>{state=backup;recovery=null;save();$('#recoveryDialog').close();renderAll();toast('已恢复有效备份');};
 $('#startDefault').onclick=()=>{recovery=null;save();$('#recoveryDialog').close();toast('开始默认方案；原始数据仍在恢复备份中');};$('#recoveryDialog').showModal();
}
requestAnimationFrame(showRecovery);
$('#recoveryDialog').addEventListener('cancel',e=>e.preventDefault());
Object.assign(window.homeStudio,{setTool,getWalls:()=>structuredClone(state.walls),componentSpec,modelAudit:f=>{const g=buildFurniture(f);let basins=0,faucets=0,mirrors=0,upper=0;g.traverse(o=>{if(o.userData.basin)basins++;if(o.userData.faucet)faucets++;if(o.userData.mirror)mirrors++;if(o.userData.upperCabinet)upper++;});return{basins,faucets,mirrors,upper};}});

// Model definitions and catalog/property symbols use the same object semantics.
function counterCutouts(counter){
 const a=counter.rot*Math.PI/180,c=Math.cos(a),s=Math.sin(a),holes=[];
 for(const sink of state.furniture.filter(f=>f.type==='ksink')){
  if(Math.abs((sink.elevation??900)-((counter.elevation||0)+(counter.h||900)))>35)continue;
  const dx=sink.cx-counter.cx,dy=sink.cy-counter.cy,x=dx*c+dy*s,z=-dx*s+dy*c,rot=(sink.rot-counter.rot)*Math.PI/180;
  const w=Math.max(30,sink.w-20),d=Math.max(30,sink.d-20);
  const corners=[[-w/2,-d/2],[w/2,-d/2],[w/2,d/2],[-w/2,d/2]].map(([u,v])=>[x+u*Math.cos(rot)-v*Math.sin(rot),z+u*Math.sin(rot)+v*Math.cos(rot)]);
  if(corners.every(([u,v])=>Math.abs(u)<=counter.w/2-5&&Math.abs(v)<=counter.d/2-5))holes.push({x:x/1000,z:z/1000,w:w/1000,d:d/1000,rot,source:sink.id});
 }
 return holes;
}
function componentIdentity(f){
 const[keyCi,keyIi]=(f.catalogKey||'').split(':').map(Number),preset=LIB[keyCi]?.items[keyIi];
 if(preset&&preset[0]===f.type)return{key:f.catalogKey,name:preset[1],type:f.type};
 const names={bed:f.w>=1700?'双人床 1.8m':f.w>=1400?'双人床 1.5m':'单人床',sofabed:'沙发床（收起）',coffee:f.w<650?'圆边几':'圆茶几',sofa:f.originalType==='sofabed'?'沙发床（收起）':f.w>2200?'三人沙发':'双人沙发',roundtable:f.originalType==='coffee'?(f.w<650?'圆边几':'圆茶几'):'圆桌',counter:'橱柜台面与地柜',ksink:'独立水槽',stove:'双眼燃气灶',tvstand:'电视柜',vanity:(f.basins||1)===2?'双盆浴室柜':'浴室柜',wardrobe:'衣柜',bookshelf:'书架',chair:'椅子',nightstand:'床头柜',desk:'书桌',tv:'电视'};
 const fallback=LIB.flatMap(g=>g.items).find(it=>it[0]===f.type);
 const matches=LIB.flatMap((g,ci)=>g.items.flatMap((it,ii)=>it[0]===f.type?[{key:ci+':'+ii,it,score:Math.abs(it[2]-f.w)+Math.abs(it[3]-f.d)}]:[])).sort((a,b)=>a.score-b.score);
 return{type:f.type,name:matches[0]?.it[1]||names[f.type]||fallback?.[1]||f.name,key:matches[0]?.key||null};
}
const identityPanel=furnPanel;
furnPanel=function(f){const info=componentIdentity(f),pad=Math.max(f.w,f.d)*.08;
 document.querySelectorAll('#lib .item').forEach(el=>el.classList.toggle('selected',el.dataset.key===info.key));
 const preview=`<div class=component-preview data-component-type="${esc(f.type)}"><svg viewBox="${-f.w/2-pad} ${-f.d/2-pad} ${f.w+pad*2} ${f.d+pad*2}">${furnSVG(f.type,f.w,f.d,f.color,f)}</svg><div><b>${esc(info.name)}</b><small>${f.w} × ${f.d} mm</small><small>对象编号 ${esc(f.id)}</small></div></div>`;
 return identityPanel(f).replace('<div class="form">',preview+'<div class="form">');
};
Object.assign(window.homeStudio,{componentIdentity,counterCutouts});

const clearCatalogSelection=select;select=function(sel){if(!sel||sel.kind!=='furn')document.querySelectorAll('#lib .item.selected').forEach(el=>el.classList.remove('selected'));return clearCatalogSelection(sel);};
Object.assign(window.homeStudio,{select,componentAudit:f=>{const g=buildFurniture(f);let burners=0,holes=0;g.traverse(o=>{if(o.userData.burner)burners++;if(o.geometry?.type==='ExtrudeGeometry')holes+=o.geometry.parameters.shapes.holes.length;});const bounds=new THREE.Box3().setFromObject(g);return{burners,holes,meshes:g.children.length,maxY:bounds.max.y,minY:bounds.min.y};}});

// V8: conventional workspace and complete reversible object lifecycles.
let propertyPage='properties',panelPointer=false,panelRefreshPending=false,propertyParent=null;
// Do not replace a button between pointerdown and click when a field blurs.
document.addEventListener('pointerdown',e=>{if(e.target.closest('#panel button,#fab button,#propertyBack')&&document.activeElement?.matches('#panel input,#panel select'))panelPointer=true;},true);
for(const event of ['pointerup','pointercancel'])document.addEventListener(event,()=>{if(panelPointer)setTimeout(()=>{panelPointer=false;if(panelRefreshPending){panelRefreshPending=false;renderPanel();}},0);},true);
function openingSelection(w,index){return {kind:'opening',wallId:w.id,index,openingId:w.opens[index]?.id||null};}
function selectedOpening(sel=ui.sel){if(sel?.kind!=='opening')return null;const w=state.walls.find(w=>w.id===sel.wallId);const index=sel.openingId?w?.opens.findIndex(o=>o.id===sel.openingId):sel.index;return w&&index>=0&&w.opens[index]?{w,o:w.opens[index],index}:null;}
function selectedWall(){return ui.sel?.kind==='wall'?state.walls.find(w=>w.id===ui.sel.id):null;}
function newWall(w){return w&&!DEFAULT.walls.some(o=>o.id===w.id);}
function deletionAllowed(){if(previewMode||opt.mode==='walk'&&is3D())return false;if(ui.sel?.kind==='furn')return !!getF(ui.sel.id);if(ui.sel?.kind==='opening')return !!selectedOpening()&&!selectedOpening().w.bearing;if(ui.sel?.kind==='measure')return !!state.measures[ui.sel.index];const w=selectedWall();return !!w&&newWall(w)&&!w.bearing;}
const v8ValidateSel=validateSel;
validateSel=function(){v8ValidateSel();if(ui.sel?.kind==='opening'&&!selectedOpening())ui.sel=null;if(ui.sel?.kind==='measure'&&!state.measures[ui.sel.index])ui.sel=null;};
deleteSel=function(){
 if(!deletionAllowed())return;
 const sel={...ui.sel};
 const ok=mutate(()=>{
  if(sel.kind==='furn')state.furniture=state.furniture.filter(f=>f.id!==sel.id);
  else if(sel.kind==='measure')state.measures.splice(sel.index,1);
  else if(sel.kind==='opening'){
   const{w,index}=selectedOpening(sel);w.opens.splice(index,1); // Removing the opening fills the same wall in both views.
   for(const k of Object.keys(state.doors))if(k===w.id||k.startsWith(w.id+':'))delete state.doors[k];
  }else if(sel.kind==='wall'){
   state.walls=state.walls.filter(w=>w.id!==sel.id); // Openings belong to the removed wall; undo restores them together.
   for(const k of Object.keys(state.doors))if(k===sel.id||k.startsWith(sel.id+':'))delete state.doors[k];
  }
  ui.sel=null;state.demolished=[];
 });
 if(ok)toast('已删除 · 可撤销');
};
const v8Rotate=rotateSel,v8Duplicate=duplicateSel,v8Clear=clearLayout;
rotateSel=function(n){if(!previewMode)v8Rotate(n);};duplicateSel=function(){if(!previewMode)v8Duplicate();};clearLayout=function(){if(!previewMode)v8Clear();};
const v8Undo=undo,v8Redo=redo;
undo=function(){if(previewMode)return;ui.sel=null;v8Undo();syncWorkbench();};redo=function(){if(previewMode)return;ui.sel=null;v8Redo();syncWorkbench();};

// Plan picking uses generous invisible targets while the drawing itself stays fine.
const v8Openings=renderOpenings;
renderOpenings=function(){v8Openings();let hits='';for(const w of state.walls){if(w.demolished)continue;w.opens.forEach((o,i)=>{const r=wallRect(w,o.at,o.at+o.width,[]);hits+=`<rect x="${r.x0-35}" y="${r.y0-35}" width="${r.x1-r.x0+70}" height="${r.y1-r.y0+70}" fill="transparent" data-opening-wall="${esc(w.id)}" data-opening-index="${i}" cursor="${w.bearing?'default':Math.abs(w.b[0]-w.a[0])>Math.abs(w.b[1]-w.a[1])?'ew-resize':'ns-resize'}" pointer-events="${ui.tool==='select'&&!previewMode?'all':'none'}"/>`;if(o.kind==='door'&&(planDrawingMode!=='structure'||isEntrance(w,o))){const p=doorPose(w,o),x=p.hinge[0],y=p.hinge[1],ex=x+p.leaf[0]*p.leafWidth,ey=y+p.leaf[1]*p.leafWidth;hits+=`<path d="M${x} ${y}L${ex} ${ey}" fill="none" stroke="transparent" stroke-width="12" vector-effect="non-scaling-stroke" data-opening-wall="${esc(w.id)}" data-opening-index="${i}" cursor="${w.bearing?'default':Math.abs(w.b[0]-w.a[0])>Math.abs(w.b[1]-w.a[1])?'ew-resize':'ns-resize'}" pointer-events="${ui.tool==='select'&&!previewMode?'stroke':'none'}"/>`;}});}$('#gOpen').insertAdjacentHTML('beforeend',hits);};
const v8Measures=renderMeasure;
renderMeasure=function(){v8Measures();$('#gMeasure').insertAdjacentHTML('beforeend',state.measures.map((m,i)=>`<path d="M${m.a.x} ${m.a.y}L${m.b.x} ${m.b.y}" fill="none" stroke="transparent" stroke-width="14" vector-effect="non-scaling-stroke" data-measure="${i}" pointer-events="${ui.tool==='select'&&!previewMode?'stroke':'none'}"/>`).join(''));};
const v8Sel=renderSel;
renderSel=function(){v8Sel();const op=selectedOpening();if(op){const r=wallRect(op.w,op.o.at,op.o.at+op.o.width,[]);$('#gSel').insertAdjacentHTML('beforeend',`<rect x="${r.x0-45}" y="${r.y0-45}" width="${r.x1-r.x0+90}" height="${r.y1-r.y0+90}" fill="#ad7951" fill-opacity=".12" stroke="#ad7951" stroke-width="2" vector-effect="non-scaling-stroke" pointer-events="none"/>`);}if(ui.sel?.kind==='measure'){const m=state.measures[ui.sel.index];if(m)$('#gSel').insertAdjacentHTML('beforeend',`<path d="M${m.a.x} ${m.a.y}L${m.b.x} ${m.b.y}" stroke="#2f5d62" stroke-width="3" vector-effect="non-scaling-stroke" pointer-events="none"/>`);}};
// Openings move along their host wall; keep the pointer offset and neighbour interval.
function openingMoveRange({w,o,index}){
 const length=Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]);let min=0,max=length-o.width;
 w.opens.forEach((n,i)=>{if(i===index)return;if(n.at+n.width<=o.at)min=Math.max(min,n.at+n.width);else if(n.at>=o.at+o.width)max=Math.min(max,n.at-o.width);});
 return {min,max};
}
function clampOpeningAt(at,{min,max}){return Math.max(min,Math.min(max,at));}
function clearOpeningDoorPose(wallId){for(const key of Object.keys(state.doors))if(key===wallId||key.startsWith(wallId+':'))delete state.doors[key];}
svg.addEventListener('pointerdown',e=>{
 if(e.button!==0||ui.tool!=='select'||previewMode)return;
 const hit=e.target.closest('[data-opening-wall],[data-measure]');if(!hit)return;
 e.preventDefault();e.stopImmediatePropagation();closeDrawers();
 if(hit.dataset.measure!==undefined){select({kind:'measure',index:+hit.dataset.measure});return;}
 const w=state.walls.find(w=>w.id===hit.dataset.openingWall);if(!w)return;
 if(e.pointerType!=='mouse'){
  touches.set(e.pointerId,{x:e.clientX,y:e.clientY});
  if(touches.size>=2){endDrag(true);const {d,c}=pinchInfo();pinch={d,c,s:view.s,px:view.x0+c[0]/view.s,py:view.y0+c[1]/view.s};svg.setPointerCapture(e.pointerId);return;}
 }
 const selection=openingSelection(w,+hit.dataset.openingIndex);select(selection);
 if(w.bearing||w.demolished||pinch)return;
 const op=selectedOpening(selection),length=Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]);
 drag={kind:'opening',selection,at:op.o.at,point:toMM(e),axis:[(w.b[0]-w.a[0])/length,(w.b[1]-w.a[1])/length],range:openingMoveRange(op),pointerId:e.pointerId,before:snap(),moved:false};
 svg.setPointerCapture(e.pointerId);
},true);
document.addEventListener('keydown',e=>{
 if(!e.key.startsWith('Arrow')||e.metaKey||e.ctrlKey||e.altKey||e.isComposing||e.target.matches('input,select,textarea,[contenteditable="true"]')||previewMode||is3D()&&opt.mode==='walk')return;
 const hit=selectedOpening();if(!hit)return;
 e.preventDefault();e.stopImmediatePropagation();if(hit.w.bearing||hit.w.demolished)return;
 const dx=hit.w.b[0]-hit.w.a[0],dy=hit.w.b[1]-hit.w.a[1],length=Math.hypot(dx,dy),step=e.shiftKey?100:10;
 const delta=({'ArrowLeft':-dx,'ArrowRight':dx,'ArrowUp':-dy,'ArrowDown':dy}[e.key]/length)*step;
 const at=clampOpeningAt(hit.o.at+delta,openingMoveRange(hit));
 if(at!==hit.o.at)mutate(()=>{hit.o.at=at;clearOpeningDoorPose(hit.w.id);});
},true);

// New partitions have a real wall footprint, with endpoint and side grips.
function wallAxes(w){const length=Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]),u=[(w.b[0]-w.a[0])/length,(w.b[1]-w.a[1])/length];return {length,u,n:[-u[1],u[0]]};}
function resizeWallFromPointer(w,d,p){
 const start=d.wallStart,{length,u,n}=wallAxes(start),dx=p.x-d.point.x,dy=p.y-d.point.y;
 let a=[...start.a],b=[...start.b],t=start.t,opens=structuredClone(start.opens);
 if(d.handle==='start'){
  const limit=Math.min(length-200,...start.opens.map(o=>o.at)),delta=Math.max(length-30000,Math.min(limit,Math.round((dx*u[0]+dy*u[1])/10)*10));
  a=a.map((v,i)=>v+u[i]*delta);opens.forEach(o=>o.at-=delta);
 }else if(d.handle==='end'){
  const min=Math.max(200,...start.opens.map(o=>o.at+o.width)),newLength=Math.max(min,Math.min(30000,length+Math.round((dx*u[0]+dy*u[1])/10)*10));
  b=a.map((v,i)=>v+u[i]*newLength);
 }else{
  const side=d.handle==='sidePositive'?1:-1;
  t=Math.max(60,Math.min(500,start.t+side*Math.round((dx*n[0]+dy*n[1])/10)*10));
  const shift=side*(t-start.t)/2;a=a.map((v,i)=>v+n[i]*shift);b=b.map((v,i)=>v+n[i]*shift);
 }
 if(JSON.stringify([a,b,t,opens])===JSON.stringify([w.a,w.b,w.t,w.opens]))return false;
 Object.assign(w,{a,b,t,opens});return true;
}
function setWallLength(w,length){
 const {u}=wallAxes(w),min=Math.max(200,...w.opens.map(o=>o.at+o.width));
 if(!Number.isFinite(length)||length<min||length>30000)throw Error('墙体长度须在 '+min+'–30000 mm 之间，不能截断洞口');
 w.b=w.a.map((v,i)=>v+u[i]*length);clearOpeningDoorPose(w.id);
}
const wallResizeSelection=renderSel;
renderSel=function(){
 wallResizeSelection();const w=selectedWall();if(!w||!newWall(w)||w.bearing||w.demolished||previewMode||ui.tool!=='select')return;
 const {length,u,n}=wallAxes(w),k=1/view.s,mid=w.a.map((v,i)=>(v+w.b[i])/2),horizontal=Math.abs(u[0])>.5,rect=wallRect(w,0,length,[]);
 let html=`<rect x="${rect.x0}" y="${rect.y0}" width="${rect.x1-rect.x0}" height="${rect.y1-rect.y0}" fill="none" stroke="#b5653a" stroke-width="1.5" stroke-dasharray="5 3" vector-effect="non-scaling-stroke" pointer-events="none"/>`;
 const points=[['start',w.a,w.a.map((v,i)=>v-u[i]*10*k),horizontal?'ew-resize':'ns-resize','调整长度，固定另一端'],['end',w.b,w.b.map((v,i)=>v+u[i]*10*k),horizontal?'ew-resize':'ns-resize','调整长度，固定另一端'],...[-1,1].map(side=>{const edge=mid.map((v,i)=>v+n[i]*side*w.t/2),point=mid.map((v,i)=>v+n[i]*side*(w.t/2+12*k));return [side>0?'sidePositive':'sideNegative',edge,point,horizontal?'ns-resize':'ew-resize','调整宽度（墙厚），固定对侧边'];})];
 for(const [handle,edge,point,cursor,label]of points){html+=`<line x1="${edge[0]}" y1="${edge[1]}" x2="${point[0]}" y2="${point[1]}" stroke="#b5653a" stroke-width="1" vector-effect="non-scaling-stroke" pointer-events="none"/><circle data-wall-resize="${handle}" data-wall-id="${esc(w.id)}" cx="${point[0]}" cy="${point[1]}" r="${(COARSE?18:9)*k}" fill="transparent" style="cursor:${cursor}"/><rect data-wall-resize="${handle}" data-wall-id="${esc(w.id)}" x="${point[0]-4*k}" y="${point[1]-4*k}" width="${8*k}" height="${8*k}" rx="${1.5*k}" fill="#fff" stroke="#b5653a" stroke-width="1.5" vector-effect="non-scaling-stroke" style="cursor:${cursor}"><title>${label}</title></rect>`;}
 html+=`<text x="${mid[0]}" y="${rect.y1+34*k}" text-anchor="middle" font-size="${11*k}" fill="#b5653a" stroke="#fff" stroke-width="${3*k}" paint-order="stroke" pointer-events="none">${Math.round(length)} × ${w.t} mm</text>`;
 $('#gSel').insertAdjacentHTML('beforeend',html);
};
svg.addEventListener('pointerdown',e=>{
 if(e.button!==0||ui.tool!=='select'||previewMode)return;
 const grip=e.target.closest('[data-wall-resize]');if(!grip)return;
 const w=state.walls.find(w=>w.id===grip.dataset.wallId);if(!w||!newWall(w)||w.bearing||w.demolished)return;
 e.preventDefault();e.stopImmediatePropagation();closeDrawers();
 if(e.pointerType!=='mouse'){touches.set(e.pointerId,{x:e.clientX,y:e.clientY});if(touches.size>=2){endDrag(true);const {d,c}=pinchInfo();pinch={d,c,s:view.s,px:view.x0+c[0]/view.s,py:view.y0+c[1]/view.s};svg.setPointerCapture(e.pointerId);return;}}
 if(pinch)return;
 drag={kind:'wallResize',id:w.id,handle:grip.dataset.wallResize,wallStart:structuredClone(w),point:toMM(e),pointerId:e.pointerId,sx:e.clientX,sy:e.clientY,before:snap(),moved:false};svg.setPointerCapture(e.pointerId);
},true);

// Keep property pages short; capabilities are explicit for originals and new objects.
wallPanel=function(w){const locked=w.bearing,isNew=newWall(w),len=Math.round(Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]));const field=(id,label,n)=>`<label>${label}<input type="number" id="${id}" value="${n}" ${locked?'disabled':''}></label>`;
 return `<section><h3>${locked?'承重墙 · 锁定':isNew?'新增隔墙':'普通墙'}</h3><div class="stats"><div><small>长度</small><span class="big">${len}</span> mm</div><div><small>高度</small><span class="big">${DEFAULT.height}</span> mm</div></div><div class="form">${isNew?field('wLength','长度 / mm',len)+field('wThickness','宽度（墙厚）/ mm',w.t):''}${field('wAx','起点 X / mm',w.a[0])}${field('wAy','起点 Y / mm',w.a[1])}${field('wBx','终点 X / mm',w.b[0])}${field('wBy','终点 Y / mm',w.b[1])}${isNew?'':field('wThickness','厚度 / mm',w.t)}</div><div class="actions">${locked?'':`<button class="btn danger" id="wallRemove">${isNew?'删除':w.demolished?'恢复':'拆除'}</button>`}</div>${locked?'<p class="scene-mode-note">原户型承重墙及洞口锁定。</p>':''}</section><section><h3>洞口 <small>${w.opens.length}</small></h3>${w.opens.length?`<table>${w.opens.map((o,i)=>`<tr class="click" data-inspect-opening="${i}"><td>${esc(o.label||({door:'门洞',window:'窗洞',sliding:'推拉门'}[o.kind]))}</td><td class="r muted">${o.width} mm ›</td></tr>`).join('')}</table>`:'<p class="scene-mode-note">无洞口</p>'}${locked||w.demolished?'':`<div class="actions only2d"><button class="btn" data-start-opening="door">门洞</button><button class="btn" data-start-opening="window">窗洞</button></div>`}</section>`;
};
bindWallPanel=function(w){if($('#wLength'))$('#wLength').onchange=e=>mutate(()=>setWallLength(w,Number(e.target.value)));for(const [id,k,index]of [['wAx','a',0],['wAy','a',1],['wBx','b',0],['wBy','b',1]])$('#'+id).onchange=e=>mutate(()=>w[k][index]=Number(e.target.value));$('#wThickness').onchange=e=>mutate(()=>w.t=Number(e.target.value));$('#wallRemove')?.addEventListener('click',()=>newWall(w)?deleteSel():toggleWall(w.id));document.querySelectorAll('[data-inspect-opening]').forEach(b=>b.onclick=()=>select(openingSelection(w,+b.dataset.inspectOpening),{parent:ui.sel}));document.querySelectorAll('[data-start-opening]').forEach(b=>b.onclick=()=>setTool(b.dataset.startOpening));};
function openingPanel({w,o,index}){const locked=w.bearing,horiz=Math.abs(w.a[1]-w.b[1])<.1;const forward=(horiz?w.b[0]-w.a[0]:w.b[1]-w.a[1])>0;const start=horiz?(forward?'左侧':'右侧'):(forward?'上侧':'下侧'),end=horiz?(forward?'右侧':'左侧'):(forward?'下侧':'上侧');const field=(id,label,v)=>`<label>${label}<input id="${id}" type="number" value="${v}" ${locked?'disabled':''}></label>`;
 return `<section><h3>${esc(o.label||({door:'门洞',window:'窗洞',sliding:'推拉门'}[o.kind]))}${locked?' · 锁定':''}</h3><p class="scene-mode-note">所属墙体 ${esc(w.id)}</p><div class="form">${field('openingAt','沿墙位置 / mm',o.at)}${field('openingWidth','净宽 / mm',o.width)}${o.kind==='door'?`<label>门轴<select id="openingHinge" ${locked?'disabled':''}><option value="start" ${o.hingeEnd!=='end'?'selected':''}>${start}</option><option value="end" ${o.hingeEnd==='end'?'selected':''}>${end}</option></select></label><label>开启侧<select id="openingSwing" ${locked?'disabled':''}><option value="1" ${o.swing===1?'selected':''}>${horiz?(forward?'下侧':'上侧'):(forward?'左侧':'右侧')}</option><option value="-1" ${o.swing===-1?'selected':''}>${horiz?(forward?'上侧':'下侧'):(forward?'右侧':'左侧')}</option></select></label>${field('openingAngle','开启角度 / °',o.angle??90)}`:''}</div><div class="actions">${locked?'':`<button class="btn danger" id="deleteOpening">删除</button>`}<button class="btn" id="inspectParent">查看墙体</button></div>${locked?'':`<p class="scene-mode-note">沿墙拖动 · 方向键微调 10 mm · Shift 100 mm。删除后补回墙体，可撤销。</p>`}</section>`;
}
function bindOpeningPanel(hit){const upd=fn=>mutate(()=>{const current=selectedOpening();fn(current.o);for(const k of Object.keys(state.doors))if(k===hit.w.id||k.startsWith(hit.w.id+':'))delete state.doors[k];});for(const [id,key,number]of [['openingAt','at',true],['openingWidth','width',true],['openingHinge','hingeEnd',false],['openingSwing','swing',true],['openingAngle','angle',true]]){const el=$('#'+id);if(el)el.onchange=e=>upd(o=>o[key]=number?Number(e.target.value):e.target.value);}$('#deleteOpening')?.addEventListener('click',deleteSel);$('#inspectParent').onclick=()=>select({kind:'wall',id:hit.w.id});}
function measurePanel(m){return `<section><h3>测量线</h3><div class="stats"><div><small>长度</small><span class="big">${Math.round(Math.hypot(m.b.x-m.a.x,m.b.y-m.a.y))}</span> mm</div></div><div class="form">${[['maX','起点 X',m.a.x],['maY','起点 Y',m.a.y],['mbX','终点 X',m.b.x],['mbY','终点 Y',m.b.y]].map(([id,n,v])=>`<label>${n} / mm<input id="${id}" type="number" value="${v}"></label>`).join('')}</div><div class="actions"><button class="btn danger" id="deleteMeasure">删除</button></div></section>`;}
function bindMeasurePanel(){for(const [id,point,axis]of [['maX','a','x'],['maY','a','y'],['mbX','b','x'],['mbY','b','y']])$('#'+id).onchange=e=>mutate(()=>{const n=Number(e.target.value);if(!Number.isFinite(n))throw Error('请输入有效坐标');state.measures[ui.sel.index][point][axis]=n;});$('#deleteMeasure').onclick=deleteSel;}

// Design overview shows material quantities without pricing or budget controls.
overviewPanel=function(){const totals=floorTotals(),sum=totals.total,byMat={};ROOMS.forEach(r=>byMat[state.rooms[r.id].mat]=(byMat[state.rooms[r.id].mat]||0)+area(r.poly));FLOOR_CONNECTIONS.forEach(c=>byMat[connectionMat(c)]=(byMat[connectionMat(c)]||0)+area(c.poly));const mats=Object.entries(byMat).map(([k,a])=>`<tr><td><span class="sw" style="background:${MATS[k].sw}"></span>${esc(MATS[k].name)}</td><td class="r">${fmt(a,1)} m²</td></tr>`).join('');
 return `<section><h3>方案</h3><div class="stats"><div><small>建筑面积 · 用户提供</small><span class="big">${(Number.isFinite(DEFAULT.areaEstimate.gross)?fmt(DEFAULT.areaEstimate.gross,1):'—')}</span> m²</div><div><small>套内概算约</small><span class="big">${fmt(DEFAULT.areaEstimate.suite,1)}</span> m²</div></div><div class="total"><span>地面合计约</span><b>${fmt(sum)} m²</b></div>${totals.connections?`<p class="scene-mode-note">房间分区 ${fmt(totals.rooms)}㎡ + 连接带 ${fmt(totals.connections)}㎡；连接带不计入单个房间面积</p>`:""}<p class="scene-mode-note">套内按外轮廓含墙、阳台及飘窗概算，未作产权折算 · 层高 ${DEFAULT.height} mm</p><div class="total"><span>风格</span><b style="font-size:12px;font-weight:500;color:#896747">${esc(styleLabel())}</b></div></section><section><h3>房间面积</h3><div class="room-area-grid">${ROOMS.map(r=>`<button type="button" class="room-area-card" data-room="${r.id}" aria-label="${esc(state.rooms[r.id].name)}，${fmt(area(r.poly))} 平方米，查看属性"><span class="room-card-heading"><span class="sw" style="background:${MATS[state.rooms[r.id].mat].sw}"></span><span class="room-card-name">${esc(state.rooms[r.id].name)}</span></span><span class="room-card-area">${fmt(area(r.poly))}<small> m²</small></span></button>`).join('')}</div></section><section><h3>地面材料</h3><table>${mats}</table></section><section><h3>方案统计</h3><div class="stats"><div><small>家具</small><span class="big">${state.furniture.length}</span> 件</div><div><small>新增隔墙</small><span class="big">${state.walls.filter(newWall).length}</span> 段</div><div><small>测量</small><span class="big">${state.measures.length}</span> 条</div><div><small>拆除墙体</small><span class="big">${state.walls.filter(w=>w.demolished).length}</span> 段</div></div></section>`;
};
bindOverview=function(){document.querySelectorAll('#panel [data-room]').forEach(b=>b.onclick=()=>{select({kind:'room',id:b.dataset.room});if(is3D())flyToRoom(b.dataset.room);});};
function readOnlyOverviewPanel(){const totals=floorTotals(),sum=totals.total;return `<section><h3>方案</h3><div class="stats"><div><small>建筑面积 · 用户提供</small><span class="big">${(Number.isFinite(DEFAULT.areaEstimate.gross)?fmt(DEFAULT.areaEstimate.gross,1):'—')}</span> m²</div><div><small>套内概算约</small><span class="big">${fmt(DEFAULT.areaEstimate.suite,1)}</span> m²</div></div><div class="total"><span>地面合计约</span><b>${fmt(sum)} m²</b></div>${totals.connections?`<p class="scene-mode-note">房间分区 ${fmt(totals.rooms)}㎡ + 连接带 ${fmt(totals.connections)}㎡；连接带不计入单个房间面积</p>`:""}<p class="scene-mode-note">套内按外轮廓含墙、阳台及飘窗概算，未作产权折算 · 层高 ${DEFAULT.height} mm</p></section>`;}
const v8FurnPanel=furnPanel,v8RoomPanel=roomPanel;
furnPanel=function(f){return v8FurnPanel(f).replace('家具属性','家具').replace('置于顶层','置顶').replace('置于底层','置底').replace(/<section class="muted"[\s\S]*?<\/section>/,'').replace(/<p class=scene-mode-note>[\s\S]*?<\/p>/g,'');};
roomPanel=function(r){return v8RoomPanel(r).replace('房间内家具','家具');};
renderPanel=function(){if(panelPointer){panelRefreshPending=true;syncWorkbench();return;}validateSel();renderFab();const p=$('#panel');$('#propertyTab').textContent='属性';$('#propertyTab').classList.add('on');
 if(is3D()&&(previewMode||opt.mode==='walk')){p.innerHTML=readOnlyOverviewPanel();syncWorkbench();return;}
 const op=selectedOpening(),w=selectedWall();
 if(op){p.innerHTML=openingPanel(op);bindOpeningPanel(op);}
 else if(w){p.innerHTML=wallPanel(w);bindWallPanel(w);}
 else if(ui.sel?.kind==='measure'){p.innerHTML=measurePanel(state.measures[ui.sel.index]);bindMeasurePanel();}
 else if(ui.sel?.kind==='furn'){const f=getF(ui.sel.id);p.innerHTML=furnPanel(f);bindFurnPanel(f);}
 else if(ui.sel?.kind==='room'){p.innerHTML=roomPanel(ROOMS.find(r=>r.id===ui.sel.id));bindRoomPanel();}
 else{p.innerHTML=overviewPanel();bindOverview();}
 syncWorkbench();
};

// Property navigation follows panel links, rather than unrelated canvas selections.
function propertySelectionExists(sel){
 if(!sel)return false;
 if(sel.kind==='room')return ROOMS.some(r=>r.id===sel.id)&&!!state.rooms[sel.id];
 if(sel.kind==='furn')return !!getF(sel.id);
 if(sel.kind==='wall')return state.walls.some(w=>w.id===sel.id);
 if(sel.kind==='opening')return !!selectedOpening(sel);
 if(sel.kind==='measure')return !!state.measures[sel.index];
 return false;
}
function syncPropertyNavigation(){
 const back=$('#propertyBack'),editable=!previewMode&&(!is3D()||opt.mode!=='walk');
 if(!ui.sel)propertyParent=null;
 if(propertyParent&&!propertySelectionExists(propertyParent))propertyParent=null;
 back.hidden=!editable||!propertySelectionExists(ui.sel);
 const label=propertyParent?.kind==='room'?'返回房间':propertyParent?.kind==='wall'?'返回墙体':'返回方案总览';
 back.title=label;back.setAttribute('aria-label',label);
}
function backProperties(){
 if(previewMode||is3D()&&opt.mode==='walk')return;
 const parent=propertySelectionExists(propertyParent)?structuredClone(propertyParent):null;
 propertyParent=null;select(parent);
}
const v8Select=select;
select=function(sel,options={}){
 if(previewMode){v8Select(sel);return;}
 const changed=JSON.stringify(sel)!==JSON.stringify(ui.sel);
 if(!sel||changed||options.parent)propertyParent=propertySelectionExists(options.parent)?structuredClone(options.parent):null;
 propertyPage='properties';v8Select(sel);syncWorkbench();
 if(changed)$('aside.right').scrollTop=0;
};
const v8SetTool=setTool;
setTool=function(t){if(previewMode||is3D()&&t!=='select')return;if(!['select','measure','wall','door','window','demolish'].includes(t))return;v8SetTool(t);renderOpenings();renderMeasure();renderSel();renderFab();syncWorkbench();};

// One pane layout for every mode, with mobile drawers sharing the same controls.
function paneShown(k){return narrow()?document.querySelector(k==='lib'?'aside.lib':'aside.right').classList.contains('open'):!panes[k==='lib'?'hideLib':'hidePanel'];}
syncPaneBtns=function(){const app=$('.app');$('#tgLib').textContent='家具库';$('#tgPanel').textContent='属性栏';for(const[k,id]of [['lib','tgLib'],['panel','tgPanel']])$('#'+id).classList.toggle('on',paneShown(k));$('#toolbarFurniture').classList.toggle('on',paneShown('lib')&&!previewMode);syncQuickActions();$('#stage').classList.toggle('drawer-panel',narrow()&&paneShown('panel'));app.classList.toggle('hide-tools',!!panes.hideTools);};
const v8Drawer=drawer;
drawer=function(which,open){if(which==='lib'&&previewMode)return;v8Drawer(which,open);syncWorkbench();};
const v8Header=updateHeader;
updateHeader=function(){v8Header();syncWorkbench();};
const v8Save=save;
save=function(){const ok=v8Save();showSaveStatus(ok?'saved':'error');return ok;};
const v8Hint=syncHint3d;
syncHint3d=function(){v8Hint();syncWorkbench();};
const v8Preview=setPreview;
setPreview=function(on){if(!on&&is3D()&&inited&&opt.mode==='walk')setMode('orbit');v8Preview(on);renderSel();renderFab();$('#previewBtn').textContent='浏览模式';syncWorkbench();};
const v8View=setView;
setView=async function(m){if(m!==viewMode&&!switching)$('#railActions').scrollTop=0;const task=v8View(m);syncQuickActions();await task;syncWorkbench();};
function syncWorkbench(){
 syncPropertyNavigation();
 if(inited)$('#walkExit').style.display=is3D()&&opt.mode==='walk'?'block':'none';
 syncQuickActions();$('#previewBtn').textContent='浏览模式';$('#previewBtn').setAttribute('aria-pressed',String(previewMode));
 const hints={select:'选择对象 · 拖动空白平移',measure:'点击两点测量 · Esc 取消',wall:'点击起点、终点画墙 · Esc 取消',door:'点击普通墙放置门洞',window:'点击普通墙放置窗洞',demolish:'点击普通墙拆除 / 恢复'};
 $('#tip').textContent=is3D()?(opt.mode==='walk'?(touchWalk?'W/S 前后 · A/D 左右 · 拖动转向 · E 开关门 · Esc 暂停':'已暂停 · 空格或点击画面继续'):previewMode?'拖动旋转 · 滚轮缩放':'拖动旋转 · 滚轮缩放 · 点击对象编辑'):hints[ui.tool]||hints.select;$('#tip').title=$('#tip').textContent;
 const editing=!previewMode&&(!is3D()||opt.mode!=='walk');$('#undo').disabled=!editing||!undoStack.length;$('#redo').disabled=!editing||!redoStack.length;$('#clearAll').disabled=!editing||!state.furniture.length;$('#toolbarFurniture').disabled=!editing||switching;$('#tgLib').disabled=previewMode;
 document.querySelectorAll('#tools [data-tool]').forEach(b=>b.disabled=!editing||switching);document.querySelectorAll('[data-command]').forEach(b=>{const c=b.dataset.command;if(c==='delete')b.disabled=!deletionAllowed();else if(['rotate','copy'].includes(c))b.disabled=!editing||ui.sel?.kind!=='furn';else if(c==='clearMeasures')b.disabled=!editing||!state.measures.length;else if(c==='toolrail')b.classList.toggle('on',!panes.hideTools);else if(c==='view2d')b.classList.toggle('on',!is3D());else if(c==='view3d')b.classList.toggle('on',is3D());});
 $('#reset').disabled=previewMode;$('#importJson').disabled=previewMode;document.querySelectorAll('[data-cut]').forEach(b=>b.disabled=opt.mode==='walk'&&is3D());
}
function closeMenus(){document.querySelectorAll('.work-menu[open],.menu-sub[open]').forEach(m=>m.open=false);}
function command(c){if(c==='copy')duplicateSel();else if(c==='rotate')rotateSel(45);else if(c==='delete')deleteSel();else if(c==='clearMeasures'){if(!previewMode)mutate(()=>{state.measures=[];if(ui.sel?.kind==='measure')ui.sel=null;});}else if(c==='view2d')setView('2d');else if(c==='view3d')setView('3d');else if(c==='toolrail'){panes.hideTools=!panes.hideTools;try{localStorage.setItem(PANES,JSON.stringify(panes));}catch{}syncPaneBtns();syncWorkbench();}else if(c==='restoreLayout'){Object.assign(panes,{hideLib:false,hidePanel:false,hideTools:false});drawer(null);closeDrawers();propertyPage='properties';renderPanel();fitView();try{localStorage.setItem(PANES,JSON.stringify(panes));}catch{}toast('已恢复界面布局');}else if(c==='help'||c==='shortcuts'){const d=$('#helpDialog');d.showModal();if(c==='shortcuts')$('#shortcutsSection').scrollIntoView({block:'center'});}}
function initWorkbench(){
 initQuickActions();
 window.closeDrawers=closeDrawers;$('#undo').onclick=undo;$('#redo').onclick=redo;$('#clearAll').onclick=clearLayout;
 // Restore the library once for layouts created while it defaulted to hidden.
 if(!panes.libraryDefaultVisible){panes.hideLib=false;panes.libraryDefaultVisible=true;try{localStorage.setItem(PANES,JSON.stringify(panes));}catch{}}
 if(panes.hideLib===undefined)panes.hideLib=false;if(panes.hidePanel===undefined)panes.hidePanel=false;drawer(null);
 $('#toolbarFurniture').onclick=()=>drawer('lib');$('#closeLibrary').onclick=()=>drawer('lib',false);$('#closeProperties').onclick=()=>drawer('panel',false);$('#propertyBack').onclick=backProperties;$('#propertyTab').onclick=()=>{propertyPage='properties';renderPanel();};$('#statusWhole').onclick=()=>{if(opt.mode==='walk')setMode('orbit');else flyTo(isoWhole());};$('#closeHelp').onclick=()=>$('#helpDialog').close();
 document.querySelectorAll('[data-command]').forEach(b=>b.onclick=()=>command(b.dataset.command));
 document.querySelectorAll('.work-menu').forEach(m=>m.addEventListener('toggle',()=>{if(m.open){document.querySelectorAll('.work-menu').forEach(n=>{if(n!==m)n.open=false;});syncWorkbench();}}));
 document.addEventListener('pointerdown',e=>{if(!e.target.closest('.work-menu'))closeMenus();});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.querySelector('.work-menu[open],.menu-sub[open]')){e.preventDefault();e.stopImmediatePropagation();closeMenus();return;}const menu=e.target.closest('.work-menu');if(menu&&menu.open&&['ArrowDown','ArrowUp'].includes(e.key)){e.preventDefault();e.stopImmediatePropagation();const items=[...menu.querySelectorAll('.menu-pop .btn')].filter(b=>!b.disabled&&b.getClientRects().length);const i=items.indexOf(document.activeElement);items[(i+(e.key==='ArrowDown'?1:-1)+items.length)%items.length]?.focus();}},true);
 document.querySelectorAll('.menu-pop .btn').forEach(b=>b.addEventListener('click',syncWorkbench));
 Object.assign(window.homeStudio,{select,undo,redo,setView,setTool,deleteSelected:deleteSel,backProperties,getSelection:()=>structuredClone(ui.sel),capabilities:()=>({delete:deletionAllowed(),newWall:!!newWall(selectedWall()),preview:previewMode}),layout:()=>({panes:structuredClone(panes),propertyPage,view:viewMode})});
 syncWorkbench();fitView();renderAll();
 try{const raw=localStorage.getItem(STORE);if(raw&&!recovery&&snap()===JSON.stringify(fixState(JSON.parse(raw))))showSaveStatus('saved');else showSaveStatus(recovery?'error':'ready');}catch{showSaveStatus('ready');}
}
// Architectural selections stay identifiable in the scene as well as in properties.
let architectureSelection=null,architectureSelectionKey='';
const v8UpdateSel=updateSel;
updateSel=function(){v8UpdateSel();const w=selectedWall(),op=selectedOpening();const key=!previewMode&&opt.mode==='orbit'&&active&&(op?JSON.stringify([op.w.id,op.w.a,op.w.b,op.w.t,op.o]):w?JSON.stringify([w.id,w.a,w.b,w.t,w.demolished]):'');if(key===architectureSelectionKey)return;architectureSelectionKey=key;if(architectureSelection){scene.remove(architectureSelection);architectureSelection.geometry.dispose();architectureSelection.material.dispose();architectureSelection=null;}if(!key)return;const wall=op?.w||w,length=Math.hypot(wall.b[0]-wall.a[0],wall.b[1]-wall.a[1]),r=wallRect(wall,op?op.o.at:0,op?op.o.at+op.o.width:length,state.walls),lo=op?.o.kind==='window'?.85:0,hi=op?(op.o.kind==='window'?2.2:2.1):H;const bound=new THREE.Box3(new THREE.Vector3(wx(r.x0),lo,wz(r.y0)),new THREE.Vector3(wx(r.x1),hi,wz(r.y1)));architectureSelection=new THREE.Box3Helper(bound,0xad7951);architectureSelection.material.depthTest=false;architectureSelection.material.transparent=true;architectureSelection.material.opacity=.85;architectureSelection.renderOrder=20;scene.add(architectureSelection);};

// Sidebar and floating-panel shortcuts share the established menu actions.
function showSaveStatus(status){
 const el=$('#savedState');el.dataset.status=status;
 el.textContent=status==='saved'?'已保存':status==='error'?'保存失败':'就绪';
 el.title=status==='saved'?'当前修改已保存到浏览器':status==='error'?'请通过文件菜单导出 JSON 保留当前方案':'修改后自动保存';
}
function syncQuickActions(){
 const walking=is3D()&&opt.mode==='walk',busy=switching;
 document.body.classList.toggle('walking',walking);
 document.querySelectorAll('[data-rail-view]').forEach(b=>{const on=b.dataset.railView===(is3D()?'3d':'2d');b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=busy;});
 const furniture=$('#toolbarFurniture');furniture.classList.toggle('on',paneShown('lib')&&!previewMode);furniture.setAttribute('aria-pressed',String(paneShown('lib')&&!previewMode));furniture.disabled=previewMode||walking||busy;
 document.querySelectorAll('[data-quick-layer]').forEach(b=>{const on=!!ui.layers[b.dataset.quickLayer];b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=previewMode||busy;});
 document.querySelectorAll('[data-quick-toggle]').forEach(b=>{const on=!!opt[b.dataset.quickToggle];b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=!inited||walking||busy;});
 document.querySelectorAll('[data-quick-pane]').forEach(b=>{const on=paneShown(b.dataset.quickPane);b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=busy||b.dataset.quickPane==='lib'&&(previewMode||walking);});
 $('#quickFullscreen').classList.toggle('on',!!fsEl());$('#quickFullscreen').setAttribute('aria-pressed',String(!!fsEl()));
 document.querySelectorAll('[data-quick-mode]').forEach(b=>{const on=b.dataset.quickMode===opt.mode;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=!inited||busy;});
 document.querySelectorAll('[data-quick-cut]').forEach(b=>{const on=Number(b.dataset.quickCut)===opt.cut;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=!inited||busy||walking;});
 if(!is3D())$('#viewportLighting').open=false;
 $('#viewportLighting').inert=!inited||busy;$('#viewportSun').value=String(opt.hour??10);$('#viewportSun').disabled=!inited||busy||opt.night;$('#viewportSunLabel').hidden=!!opt.night;$('#menuSunLabel').hidden=!!opt.night;$('#viewportSunTime').textContent=$('#sunT').textContent||'10:00';
 document.querySelectorAll('[data-light-mode]').forEach(b=>{const night=b.dataset.lightMode==='night',on=night===!!opt.night;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=!inited||busy;});
 $('#returnEdit').hidden=!previewMode;
 document.querySelectorAll('#toggles3d [data-t]').forEach(b=>b.classList.toggle('on',!!opt[b.dataset.t]));
}
function invokeQuick(button){
 if(button.disabled||switching)return;
 const d=button.dataset;let target;
 if(d.quickLayer)target=document.querySelector('#layers [data-layer="'+d.quickLayer+'"]');
 else if(d.quickToggle)target=document.querySelector('#toggles3d [data-t="'+d.quickToggle+'"]');
 else if(d.quickMode)target=document.querySelector('#modes3d [data-mode="'+d.quickMode+'"]');
 else if(d.quickCut)target=document.querySelector('.menubar [data-cut="'+d.quickCut+'"]');
 else if(d.quickPane)target=$('#'+(d.quickPane==='lib'?'tgLib':'tgPanel'));
 else if(button.id==='quickFullscreen')target=$('#fullscreen');
 if(target&&!target.disabled)target.click();
 syncQuickActions();
}
function setLightingMode(mode){
 if(!inited||switching||!['day','night'].includes(mode))return;
 opt.night=mode==='night';applyLight();syncQuickActions();
}
function updateDaylight(value){if(!inited||switching)return;const hour=Number(value);if(!Number.isFinite(hour))return;opt.hour=Math.max(7,Math.min(18,hour));$('#sun').value=String(opt.hour);applyLight();syncQuickActions();}
function initQuickActions(){
 document.querySelectorAll('[data-rail-view]').forEach(b=>b.onclick=()=>{if(!b.disabled&&!switching)setView(b.dataset.railView);});
 document.querySelectorAll('[data-quick-layer],[data-quick-toggle],[data-quick-mode],[data-quick-cut],[data-quick-pane],#quickFullscreen').forEach(b=>b.onclick=()=>invokeQuick(b));
 document.querySelectorAll('[data-light-mode]').forEach(b=>b.onclick=()=>setLightingMode(b.dataset.lightMode));
 $('#returnEdit').onclick=()=>setPreview(false);$('#viewportSun').oninput=e=>updateDaylight(e.target.value);
 document.querySelectorAll('.viewport-menu').forEach(m=>m.addEventListener('toggle',()=>{if(m.open)closeMenus();}));
 document.addEventListener('pointerdown',e=>{if(!e.target.closest('.viewport-menu'))document.querySelectorAll('.viewport-menu[open]').forEach(m=>m.open=false);});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&document.querySelector('.viewport-menu[open]')){e.preventDefault();e.stopImmediatePropagation();document.querySelectorAll('.viewport-menu[open]').forEach(m=>m.open=false);}},true);
 ['fullscreenchange','webkitfullscreenchange'].forEach(event=>document.addEventListener(event,syncQuickActions));
}

const shortcutMode=setMode,shortcutModeBtns=syncModeBtns,shortcutCutBtns=syncCutBtns;
setMode=function(mode){shortcutMode(mode);renderPanel();syncQuickActions();};
syncModeBtns=function(){shortcutModeBtns();syncQuickActions();};
syncCutBtns=function(){shortcutCutBtns();syncQuickActions();};

// Context actions stay beside the selected object, in viewport pixels.
function objectMenuPlanBounds(){
 const f=ui.sel?.kind==='furn'&&getF(ui.sel.id),op=selectedOpening(),w=op?.w||selectedWall();
 if(f){const {hw,hh}=aabb(f);return{x0:f.cx-hw,y0:f.cy-hh,x1:f.cx+hw,y1:f.cy+hh};}
 if(w)return wallRect(w,op?op.o.at:0,op?op.o.at+op.o.width:Math.hypot(w.b[0]-w.a[0],w.b[1]-w.a[1]),state.walls);
 const m=ui.sel?.kind==='measure'&&state.measures[ui.sel.index];
 return m?{x0:Math.min(m.a.x,m.b.x),y0:Math.min(m.a.y,m.b.y),x1:Math.max(m.a.x,m.b.x),y1:Math.max(m.a.y,m.b.y)}:null;
}
function projectObjectMenuBox(box,cam,width,height){
 if(box.isEmpty())return null;
 cam.updateMatrixWorld();
 const points=[];
 for(const x of [box.min.x,box.max.x])for(const y of [box.min.y,box.max.y])for(const z of [box.min.z,box.max.z]){
  const p=new THREE.Vector3(x,y,z);
  // Hide objects crossing the near plane instead of pinning their menu to an edge.
  if(p.clone().applyMatrix4(cam.matrixWorldInverse).z>=-cam.near)return null;
  p.project(cam);if(p.z>1)return null;
  points.push({x:(p.x+1)*width/2,y:(1-p.y)*height/2});
 }
 return{x0:Math.min(...points.map(p=>p.x)),y0:Math.min(...points.map(p=>p.y)),x1:Math.max(...points.map(p=>p.x)),y1:Math.max(...points.map(p=>p.y))};
}
function objectMenuScreenBounds(){
 const sr=stage.getBoundingClientRect();
 if(!is3D()){
  if(ui.layers.furn===false&&ui.sel?.kind==='furn')return null;
  const b=objectMenuPlanBounds(),r=svg.getBoundingClientRect();if(!b)return null;
  const bounds={x0:(b.x0-view.x0)*view.s+r.left-sr.left,y0:(b.y0-view.y0)*view.s+r.top-sr.top,x1:(b.x1-view.x0)*view.s+r.left-sr.left,y1:(b.y1-view.y0)*view.s+r.top-sr.top};
  // Keep the nearby action bar outside every resize target, including tiny lamps.
  if(['furn','wall'].includes(ui.sel?.kind))for(const grip of document.querySelectorAll('#gSel [data-handle]:not([data-handle="rot"]),#gSel [data-wall-resize]')){
   const q=grip.getBoundingClientRect();bounds.x0=Math.min(bounds.x0,q.left-sr.left);bounds.y0=Math.min(bounds.y0,q.top-sr.top);bounds.x1=Math.max(bounds.x1,q.right-sr.left);bounds.y1=Math.max(bounds.y1,q.bottom-sr.top);
  }
  return bounds;
 }
 if(!inited||!active||anim||opt.mode!=='orbit')return null;
 let box;
 if(ui.sel?.kind==='furn'){
  if(!opt.furn)return null;
  const g=furnG.children.find(g=>g.userData.fid===ui.sel.id);if(!g)return null;
  box=new THREE.Box3().setFromObject(g);
 }else{
  const b=objectMenuPlanBounds();if(!b)return null;
  const op=selectedOpening(),lo=op?.o.kind==='window'?.85:0,hi=op?(op.o.kind==='window'?2.2:2.1):ui.sel?.kind==='measure'?.02:H;
  box=new THREE.Box3(new THREE.Vector3(wx(b.x0),lo,wz(b.y0)),new THREE.Vector3(wx(b.x1),hi,wz(b.y1)));
 }
 return projectObjectMenuBox(box,camera,sr.width,sr.height);
}
function placeObjectMenu(b,m,W,V,obstacle){
 const pad=8,gap=12;
 if(!b||W<m.width+pad*2||V<m.height+pad*2||b.x1<0||b.y1<0||b.x0>W||b.y0>V)return null;
 const visible={x0:Math.max(0,b.x0),y0:Math.max(0,b.y0),x1:Math.min(W,b.x1),y1:Math.min(V,b.y1)};
 const cx=(visible.x0+visible.x1)/2,cy=(visible.y0+visible.y1)/2;
 const clamp=(n,a,z)=>Math.max(a,Math.min(z,n));
 const overlap=(a,r)=>r?Math.max(0,Math.min(a.x+m.width,r.x1)-Math.max(a.x,r.x0))*Math.max(0,Math.min(a.y+m.height,r.y1)-Math.max(a.y,r.y0)):0;
 const candidates=[{x:b.x1+gap,y:cy-m.height/2},{x:b.x0-gap-m.width,y:cy-m.height/2},{x:cx-m.width/2,y:b.y0-gap-m.height},{x:cx-m.width/2,y:b.y1+gap}].map(p=>({x:clamp(p.x,pad,W-pad-m.width),y:clamp(p.y,pad,V-pad-m.height)}));
 // Prefer the right side, then the left; avoid the object and floating controls.
 return candidates.reduce((best,p)=>{const cost=overlap(p,visible)+overlap(p,obstacle)*2;return !best||cost<best.cost?{...p,cost}:best;},null);
}
function positionObjectMenu(){
 const fab=$('#fab');
 if(!fab.childElementCount||!ui.sel||ui.sel.kind==='room'||previewMode||switching||is3D()&&opt.mode==='walk')return fab.classList.remove('show');
 const sr=stage.getBoundingClientRect(),panel=$('#viewportActions'),pr=panel.getBoundingClientRect();
 const obstacle=panel.getClientRects().length?{x0:pr.left-sr.left-6,y0:pr.top-sr.top-6,x1:pr.right-sr.left+6,y1:pr.bottom-sr.top+6}:null;
 const pos=placeObjectMenu(objectMenuScreenBounds(),{width:fab.offsetWidth,height:fab.offsetHeight},sr.width,sr.height,obstacle);
 if(!pos)return fab.classList.remove('show');
 fab.style.left=pos.x+'px';fab.style.top=pos.y+'px';fab.classList.add('show');
}
function layerTarget(f,delta){
 if(!f)return null;
 // SVG has separate furniture and overhead stacks; skip currently hidden details.
 const peers=state.furniture.filter(g=>!g.assemblyOwner&&!UNNECESSARY_DISPLAY_TYPES.has(g.type)&&TOP_TYPES.has(g.type)===TOP_TYPES.has(f.type)&&(is3D()?topView||!constructionDetail(g):planItemVisible(g))),index=peers.findIndex(g=>g.id===f.id);
 return index<0?null:peers[index+delta]||null;
}
function moveLayer(delta){
 if(previewMode||switching||is3D()&&opt.mode==='walk'||ui.sel?.kind!=='furn')return;
 const f=getF(ui.sel.id),target=layerTarget(f,delta);if(!target)return;
 mutate(()=>{const i=state.furniture.findIndex(g=>g.id===f.id),j=state.furniture.findIndex(g=>g.id===target.id);[state.furniture[i],state.furniture[j]]=[state.furniture[j],state.furniture[i]];});
}
renderFab=function(){
 const fab=$('#fab'),f=ui.sel?.kind==='furn'&&getF(ui.sel.id),w=selectedWall();
 if(!ui.sel||ui.sel.kind==='room'||previewMode||is3D()&&opt.mode==='walk'){fab.replaceChildren();fab.classList.remove('show');return;}
 fab.innerHTML=`${f?`<button class="btn" data-context="rotate" title="旋转 45°">旋转</button><button class="btn" data-context="up" title="上移一层" ${layerTarget(f,1)?'':'disabled'}>上移</button><button class="btn" data-context="down" title="下移一层" ${layerTarget(f,-1)?'':'disabled'}>下移</button>`:''}${deletionAllowed()?'<button class="btn danger" data-context="delete">删除</button>':''}${w&&!w.bearing&&!newWall(w)?`<button class="btn danger" data-context="demolish">${w.demolished?'恢复':'拆除'}</button>`:''}`;
 fab.setAttribute('role','toolbar');fab.setAttribute('aria-label','对象操作');
 fab.querySelectorAll('[data-context]').forEach(b=>b.onclick=()=>({rotate:()=>rotateSel(45),up:()=>moveLayer(1),down:()=>moveLayer(-1),delete:deleteSel,demolish:()=>toggleWall(w.id)})[b.dataset.context]());
 positionObjectMenu();
};
// Position-only updates avoid rebuilding action buttons during a drag or camera orbit.
const objectMenuRenderSel=renderSel;
renderSel=function(){objectMenuRenderSel();positionObjectMenu();};
const objectMenuUpdateSel=updateSel;
updateSel=function(){objectMenuUpdateSel();positionObjectMenu();};
const objectMenuSync=syncWorkbench;
syncWorkbench=function(){objectMenuSync();positionObjectMenu();};
new ResizeObserver(positionObjectMenu).observe(stage);

// This module controls finishes only; architecture and furniture geometry remain in the case data.
let libraryPage='furniture',styleResourceKey='',applyingStyle=false,themedFurniture=null;
const STYLE_COLOR_REVISION=3;
const styleFinishRevision=id=>id==='champagne_pearl'?6:STYLE_COLOR_REVISION;
function currentStyle(){return getStyle(state.style);}
function finishPalette(){return currentStyle().palette;}
function styleLabel(){return currentStyle().name+(state.styleCustom?' · 已自定义':'');}
function themedMaterial(kind,color){
 const s=currentStyle(),p=s.palette;
 const c=kind==='metal'?p.metal:kind==='wood'&&color!==themedFurniture?.color&&![p.bedFrame,p.wood,p.walnut].includes(color)?p.wood:kind==='fabric'&&['#ffffff','#fbfaf7','#efe7da','#ece5d8','#f0e6d6','#e9e2d6'].includes(color)?(p.pillow||p.ceramic):color;
 const m=mat(c,{roughness:kind==='metal'?s.metalRoughness:kind==='wood'?(s.furnitureWoodFinish==='lacquer'?s.lacquerRoughness:s.woodRoughness):s.fabricRoughness,metalness:kind==='metal'?.8:0});m.userData.finishRole=kind;return m;
}
function applyStyle(id){
 if(previewMode||switching||is3D()&&opt.mode==='walk')return;
 const style=STYLE_PRESETS.find(s=>s.id===id);if(!style)return;
 applyingStyle=true;
 try{mutate(()=>{state.style=id;state.styleCustom=false;state.styleColorRevision=styleFinishRevision(id);for(const f of state.furniture)f.color=styleFurnitureColor(style,f.type,f.color);for(const r of ROOMS)state.rooms[r.id].mat=styleRoomMaterial(style,r,r.mat);});}finally{applyingStyle=false;}
}
const styleFixState=fixState;
fixState=function(input){const s=styleFixState(input);if(s.style&&!STYLE_PRESETS.some(p=>p.id===s.style))throw Error('未知装修风格');s.style=s.style||CASE.initialState.style||'champagne_pearl';s.styleCustom=!!s.styleCustom;
 // Upgrade template defaults once; explicit user color/material choices remain intact.
 if(s.style==='champagne_pearl'&&!s.styleCustom&&(s.styleColorRevision??0)<6){for(const f of s.furniture)f.color=styleFurnitureColor(getStyle(s.style),f.type,f.color);s.styleColorRevision=6;}
 for(const f of s.furniture)if(CASE.presentation?.tabletopDecorById?.[f.id]&&!f.tabletopDecor)f.tabletopDecor=structuredClone(CASE.presentation.tabletopDecorById[f.id]);
 for(const f of s.furniture)if(f.type==='tv'&&!f.thinDisplayRevision&&[80,90].includes(f.d)){f.d=35;f.thinDisplayRevision=1;}
 const finishes=CASE.presentation?.finishOverrides;if(finishes&&s.caseFinishRevision!==finishes.revision){for(const [rid,mat]of Object.entries(finishes.rooms||{}))if(s.rooms[rid])s.rooms[rid].mat=mat;for(const f of s.furniture)if(finishes.furnitureColors?.[f.id])f.color=finishes.furnitureColors[f.id];s.caseFinishRevision=finishes.revision;}
 s.styleColorRevision??=styleFinishRevision(s.style);
 return s;};
const styleDefaultState=defaultState;defaultState=function(){return styleDefaultState();};
let initialStyleUpgradePending=(state.styleColorRevision||0)<styleFinishRevision(state.style)&&!state.styleCustom;
state=fixState(state);
const styleMutate=mutate;
mutate=function(fn){const beforeState=state,beforeStyle=state.style,colors=new Map(state.furniture.map(f=>[f.id,f.color])),rooms=JSON.stringify(Object.entries(state.rooms).map(([id,r])=>[id,r.mat]));return styleMutate(()=>{fn();if(!applyingStyle&&state===beforeState&&state.style===beforeStyle&&(state.furniture.some(f=>colors.has(f.id)&&colors.get(f.id)!==f.color)||rooms!==JSON.stringify(Object.entries(state.rooms).map(([id,r])=>[id,r.mat]))))state.styleCustom=true;});};
const styleAddItem=addItem;
addItem=function(it,x,y){const original=it[4];try{it[4]=styleFurnitureColor(currentStyle(),it[0],original);return styleAddItem(it,x,y);}finally{it[4]=original;}};
const styleFurniture=buildFurniture;
buildFurniture=function(f){themedFurniture=f;try{return styleFurniture({...f,finishes:finishPalette(),finishSpec:currentStyle()});}finally{themedFurniture=null;}};
const styleSymbol=furnSVG;
furnSVG=function(t,w,d,c,f={}){const p=finishPalette();if(!f.id)c=styleFurnitureColor(currentStyle(),t,c);return styleSymbol(t,w,d,c,{...f,finishes:p}).replace(/(fill=")[#]([0-9a-f]{6})(")/gi,(all,a,h,b)=>{const original='#'+h.toLowerCase(),color=({'#b7a284':p.metal,'#e8dccb':p.cabinet,'#efe6d8':p.cabinet,'#e2cfb4':p.wood,'#fbf8f2':p.ceramic,'#dbe2e3':'#dbe2e3'})[original];return color&&original!==c?a+color+b:all;});};
function buildStyleCards(){
 const host=$('#styleLibrary');
 host.innerHTML=`<p class="style-intro">点击应用全屋配色与材质</p><div class="style-cards">${STYLE_PRESETS.map(s=>`<button class="style-card" data-style-id="${s.id}" aria-pressed="false"><span class="style-swatch-row">${['wall','wood','upholstery','accent','metal'].map(k=>`<i style="background:${s.palette[k]}"></i>`).join('')}</span><b>${s.name}</b><small>${s.description}</small><span class="style-samples"><i style="background:${s.palette.floorWood}">木</i><i style="background:${s.palette.tile}">砖</i><i style="background:${s.palette.stone}">石</i></span></button>`).join('')}</div><p id="activeStyleLabel" class="style-intro"></p>`;
 host.querySelectorAll('[data-style-id]').forEach(b=>b.onclick=()=>applyStyle(b.dataset.styleId));
 const menu=$('#menuStyleList');
 if(menu){
  menu.innerHTML=STYLE_PRESETS.map(s=>`<button type="button" class="btn" data-style-id="${s.id}" aria-pressed="false"><span>${s.name}</span></button>`).join('');
  menu.querySelectorAll('[data-style-id]').forEach(b=>b.onclick=()=>{applyStyle(b.dataset.styleId);closeMenus();});
 }
 syncStyleUI();
}
function syncStyleUI(){
 const editing=!previewMode&&(!is3D()||opt.mode!=='walk')&&!switching,shown=paneShown('lib');
 for(const[id,page]of [['railFurniture','furniture'],['toolbarFurniture','furniture'],['railStyles','styles']]){const b=$('#'+id);b.classList.toggle('on',shown&&libraryPage===page&&!previewMode);b.setAttribute('aria-pressed',String(shown&&libraryPage===page&&!previewMode));b.disabled=!editing;}
 $('#lib').hidden=libraryPage!=='furniture';$('#styleLibrary').hidden=libraryPage!=='styles';$('aside.lib .pane-heading b').textContent=libraryPage==='styles'?'风格':'家具';
 $('#activeStyleLabel')?.replaceChildren(document.createTextNode(styleLabel()));
 document.querySelectorAll('[data-style-id]').forEach(b=>{const on=b.dataset.styleId===state.style;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=!editing;});
}
function openLibraryPage(page){const same=libraryPage===page,shown=paneShown('lib');libraryPage=page;drawer('lib',!(same&&shown));syncStyleUI();}
function updateStyleResources(){
 if(styleResourceKey===state.style)return;
 styleResourceKey=state.style;
 for(const kind of Object.keys(TEX)){const f=styleFloorFinish(currentStyle(),kind);Object.assign(TEX[kind],f);MATS[kind].sw=f.base;const m=floorMats[kind];if(m){m.map?.dispose();m.dispose();delete floorMats[kind];}}
 buildDefs();buildLib();buildStyleCards();
 if(inited){wallMat.color.set(finishPalette().wall);frameMat.color.set(finishPalette().frame);}
}
const styleRenderAll=renderAll;
renderAll=function(){updateStyleResources();styleRenderAll();syncStyleUI();};
const styleQuickSync=syncQuickActions;
syncQuickActions=function(){styleQuickSync();syncStyleUI();};
const styleInitWorkbench=initWorkbench;
initWorkbench=function(){styleInitWorkbench();$('#railStyles').onclick=()=>openLibraryPage('styles');$('#railFurniture').onclick=$('#toolbarFurniture').onclick=$('#tgLib').onclick=()=>openLibraryPage('furniture');syncStyleUI();if(initialStyleUpgradePending){initialStyleUpgradePending=false;save();}};
Object.assign(window.homeStudio,{applyStyle,getStyles:()=>structuredClone(STYLE_PRESETS),getStyle:()=>({id:state.style,name:styleLabel(),custom:!!state.styleCustom}),validate:fixState});

// Confirmed stages are checked against live content; changed scopes become stale.
const productionStageLabels={structure:'结构',layout:'布局',style:'风格'};
let productionStatusKey='',productionSync=0;
async function syncProductionUI(){
 const key=canonical(productionScopes(state,{...DEFAULT,footprint:FOOTPRINT},ROOMS,currentStyle()))+canonical(state.productionApprovals||{});if(key===productionStatusKey)return;productionStatusKey=key;
 const seq=++productionSync,result=await productionStatus(state,{...DEFAULT,footprint:FOOTPRINT},ROOMS,currentStyle());if(seq!==productionSync)return;
 for(const [stage,value]of Object.entries(result)){const b=document.querySelector(`[data-confirm-stage="${stage}"]`);if(b){b.classList.toggle('on',value.status==='confirmed');b.title=value.status==='stale'?'方案已变更，需要重新确认':value.status==='confirmed'?'当前版本已确认':'确认当前版本';}}
}
async function confirmProductionStage(stage){
 if(previewMode||switching||is3D()&&opt.mode==='walk')return;
 const current=await productionStatus(state,{...DEFAULT,footprint:FOOTPRINT},ROOMS,currentStyle()),previous={layout:'structure',style:'layout'}[stage];
 if(previous&&current[previous].status!=='confirmed'){toast(`请先确认${productionStageLabels[previous]}`);return;}
 const label=productionStageLabels[stage];if(!confirm(`确认当前${label}方案？后续修改会使相关确认失效。`))return;
 const hash=current[stage].sha256;mutate(()=>{state.productionApprovals={...state.productionApprovals,[stage]:{sha256:hash,confirmedAt:new Date().toISOString(),source:'explicit_user_ui_confirmation',evidence:`用户点击确认${label}并接受当前版本`}};});syncProductionUI();closeMenus();toast(`已确认${label}`);
}
async function exportProductionBundle(){
 const bundle=await createProductionBundle(state,{...DEFAULT,footprint:FOOTPRINT},ROOMS,currentStyle());
 if(Object.values(bundle.confirmations).some(s=>s.status!=='confirmed')){toast('请先在文件菜单确认结构、布局和风格');return;}
 const oldView=viewMode,oldCut=opt.cut;try{if(!is3D())await setView('3d');opt.cut=H;buildArch();buildFurn();if((await createProductionBundle(state,{...DEFAULT,footprint:FOOTPRINT},ROOMS,currentStyle())).schemeSha256!==bundle.schemeSha256)throw Error('方案在导出期间发生变化，请重试');bundle.scene=serializeProductionMeshes({floor:archFloor,architecture:archUp,furniture:furnG});download('装修方案-制作包.json',new Blob([JSON.stringify(bundle)],{type:'application/json'}));toast('已导出制作包');}finally{opt.cut=oldCut;if(inited){buildArch();buildFurn();}if(oldView==='2d')await setView('2d');}
}
const productionInit=initWorkbench;
initWorkbench=function(){productionInit();document.querySelectorAll('[data-confirm-stage]').forEach(b=>b.onclick=()=>confirmProductionStage(b.dataset.confirmStage));$('#exportProduction').onclick=()=>exportProductionBundle().catch(e=>toast('导出失败：'+e.message));syncProductionUI();};
const productionRender=renderAll;
renderAll=function(){productionRender();syncProductionUI();};
Object.assign(window.homeStudio,{getProductionBundle:()=>createProductionBundle(state,{...DEFAULT,footprint:FOOTPRINT},ROOMS,currentStyle()),getProductionStatus:()=>productionStatus(state,{...DEFAULT,footprint:FOOTPRINT},ROOMS,currentStyle())});


// V9: dimension contract, independent overhead components and editable finishes.
function ceilingFootprint(c){return c.poly||ROOMS.find(r=>r.id===c.roomId).poly;}
function finishedCeiling(f,s=state){
 let height=DEFAULT.height;const point=[f.cx,f.cy];
 for(const c of s.ceilings||[]){const poly=ceilingFootprint(c);if(!inPolygon(point,poly))continue;if(c.mode==='perimeter'&&inPolygon(point,insetPoly(poly,c.band)))continue;height=Math.min(height,DEFAULT.height-c.drop);}
 return height;
}
function syncCeilingAnchors(s){for(const f of s.furniture){if(f.fitToCeiling&&['wardrobe','bookshelf','endpanel'].includes(f.type)){f.h=finishedCeiling(f,s);f.elevation=0;}else if(f.topToCeiling&&['wallcab','fridgecab'].includes(f.type))f.h=finishedCeiling(f,s)-(f.elevation||0);}return s;}
const v9Fix=fixState;
fixState=function(input){
 input.furniture?.forEach(f=>validateDimensions(f,DEFAULT.height));
 const s=v9Fix(structuredClone(input));
 const keys=new Set();
 for(const c of s.ceilings||[]){if(keys.has(c.id)||!ROOMS.some(r=>r.id===c.roomId)||!['flat','perimeter'].includes(c.mode)||!Number.isFinite(c.drop)||c.drop<0||c.drop>300||!Number.isFinite(c.band)||c.band<100||c.band>800)throw Error('吊顶参数无效');keys.add(c.id);}
 for(const [id,faces]of Object.entries(s.wallFinishes||{})){if(!s.walls.some(w=>w.id===id))continue;for(const f of Object.values(faces))if(!WALL_FINISHES[f.kind]||(f.color&&!/^#[0-9a-f]{6}$/i.test(f.color)))throw Error('墙面材料无效');}
 syncCeilingAnchors(s);s.version=9;return s;
};
state=fixState(state);
const ceilingMutate=mutate;mutate=function(fn){return ceilingMutate(()=>{fn();syncCeilingAnchors(state);});};
const v9Add=addItem;
addItem=function(it,x,y){
 if(!NEW_COMPONENTS.some(c=>c[0]===it[0]))return v9Add(it,x,y);
 const spec=DIMENSIONS[it[0]],f=F(it[0],it[1],Math.round(x/10)*10,Math.round(y/10)*10,it[2],it[3],0,styleFurnitureColor(currentStyle(),it[0],it[4]));
 Object.assign(f,{h:spec.h,elevation:spec.elevation||0,fitToCeiling:it[0]==='endpanel',catalogKey:LIB.flatMap((g,ci)=>g.items.flatMap((v,ii)=>v===it?[ci+':'+ii]:[]))[0]});
 if(!['pendant','downlight','tracklight'].includes(f.type))pushOut(f);
 ui.sel={kind:'furn',id:f.id};mutate(()=>state.furniture.push(f));
};
const v9Symbol=furnSVG;
furnSVG=function(t,w,d,c,f={}){
 if(!NEW_COMPONENTS.some(x=>x[0]===t))return v9Symbol(t,w,d,c,f);
 const x=-w/2,y=-d/2,S='stroke="#666158" stroke-width="1.2" vector-effect="non-scaling-stroke"';
 if(['pendant','downlight'].includes(t))return '<ellipse cx="0" cy="0" rx="'+w/2+'" ry="'+d/2+'" fill="'+c+'" '+S+'/><ellipse cx="0" cy="0" rx="'+w*.36+'" ry="'+d*.36+'" fill="#fff6de" '+S+'/>';
 if(t==='tracklight')return '<rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+d+'" fill="'+c+'" '+S+'/>'+[-.3,0,.3].map(a=>'<circle cx="'+w*a+'" cy="0" r="'+d*.7+'" fill="#fff6de" '+S+'/>').join('');
 return '<rect x="'+x+'" y="'+y+'" width="'+w+'" height="'+d+'" fill="'+c+'" fill-opacity=".8" stroke-dasharray="4 2" '+S+'/>'+ (t==='hood'?'<rect x="'+(-w*.35)+'" y="'+(-d*.35)+'" width="'+w*.7+'" height="'+d*.7+'" fill="#53605b" '+S+'/>'+[-.2,0,.2].map(a=>'<path d="M'+w*a+' '+(-d*.25)+'v'+d*.5+'" '+S+'/>').join(''):'<path d="M0 '+y+'v'+d+'" '+S+'/>');
};
const v9Furniture=buildFurniture;
buildFurniture=function(f){
 const independent=NEW_COMPONENTS.some(c=>c[0]===f.type),appliance=['fridge','shower','washer','dryer','dishwasher'].includes(f.type);
 if(!independent&&!appliance)return v9Furniture(f);
 const p=finishPalette(),h=M(f.h||DIMENSIONS[f.type].h),w=M(f.w),d=M(f.d);let g;
 if(appliance){
  g=detailedFurniture({...f,type:appliance?(f.type==='dryer'?'washer':f.type):'cabinet',finishes:p,finishSpec:currentStyle(),upperCabinet:false,accessories:false});
 }else{
  g=new THREE.Group();const m=mat(f.color,{roughness:.38,metalness:.35}),dark=mat('#59605b',{roughness:.5,metalness:.4}),glow=mat('#ffffff',{emissive:'#ffffff',emissiveIntensity:1,roughness:.6});
  if(['wallcab','fridgecab'].includes(f.type)){
   const t=.018,body=surfaceMaterial(f.color,'lacquer');
   [-1,1].forEach(s=>g.add(box(t,h,d,body,s*(w/2-t/2))));
   g.add(box(w-2*t,t,d,body,0,0),box(w-2*t,t,d,body,0,h-t),box(w-2*t,h-2*t,t,body,0,t,-d/2+t/2));
   const n=Math.max(1,Math.round(w/.6));for(let i=0;i<n;i++){const x=-w/2+(i+.5)*w/n;g.add(box(w/n-.004,h-.004,.018,body,x,.002,d/2),box(w/n*.6,.007,.015,m,x,.06,d/2+.018));}
  }else if(f.type==='endpanel'){g.add(box(w,h,d,surfaceMaterial(f.color,'lacquer')));}
  else if(f.type==='hood'){
   g.add(box(w,h*.18,d,m,0,0,0),box(w*.45,h*.82,d*.4,m,0,h*.18,-d*.28),box(w*.75,.012,d*.65,dark,0,.007,0));
   [-.27,0,.27].forEach(a=>g.add(box(w*.21,.014,d*.6,m,w*a,.023,0)));
  }else if(f.type==='pendant'){
   g.add(box(w,.12,d,m,0,0,0),box(w*.91,.012,d*.87,glow,0,-.0006,0));
   [-.26,.26].forEach(a=>g.add(cyl(.003,.003,h-.12,dark,w*a,.12,0)));
   g.add(box(w*.66,.016,d*.3,m,0,h-.016,0));
  }else if(f.type==='downlight'){
   g.add(cyl(w/2,w/2,h,m),cyl(w*.39,w*.39,.004,glow));
  }else{
   g.add(box(w,.03,d,dark,0,h-.03,0));
   [-.3,0,.3].forEach(a=>{g.add(cyl(.04,.04,h-.03,dark,w*a,0,0),cyl(.035,.035,.004,glow,w*a,0,0));});
  }
 }
 g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-f.rot*Math.PI/180;g.userData.fid=f.id;g.userData.caseHeight=f.h;g.userData.fitToCeiling=!!f.fitToCeiling;
 g.traverse(o=>{if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.metalness>.1){m.envMap=envTex;m.envMapIntensity=.5;}}});
 return g;
};
function insetPoly(poly,dist){
 const signed=poly.reduce((n,p,i)=>{const q=poly[(i+1)%poly.length];return n+p[0]*q[1]-q[0]*p[1]},0),sign=signed>0?1:-1;
 return poly.map((p,i)=>{const a=poly[(i+poly.length-1)%poly.length],b=poly[(i+1)%poly.length],v=[p[0]-a[0],p[1]-a[1]],u=[b[0]-p[0],b[1]-p[1]],vl=Math.hypot(...v),ul=Math.hypot(...u),n=[-v[1]/vl*sign,-u[1]/ul*sign],m=[v[0]/vl*sign,u[0]/ul*sign];const den=1+n[0]*n[1]+m[0]*m[1];return[p[0]+dist*(n[0]+n[1])/den,p[1]+dist*(m[0]+m[1])/den];});
}
function ceilingShape(c){
 const poly=ceilingFootprint(c),s=shapeOf(poly,true);
 if(c.mode==='perimeter'){const inner=insetPoly(poly,c.band),hole=new THREE.Path();inner.forEach(([x,y],i)=>hole[i?'lineTo':'moveTo'](wx(x),wz(y)));s.holes.push(hole);}
 return s;
}
function applyWallSurfaces(){
 const joined=archUp.children.find(o=>o.userData.wallSurface);if(!joined)return;
 const geo=joined.geometry,pos=geo.attributes.position,norm=geo.attributes.normal,idx=geo.index.array,mats=[wallMat,capMat],groups=new Map(),materials=new Map();
 for(let i=0;i<idx.length;i+=3){
  const k=idx[i],ny=norm.getY(k);let mi=ny>.9?1:0;
  if(Math.abs(ny)<.2){
   let x=0,y=0,z=0;for(let j=0;j<3;j++){const v=idx[i+j];x+=pos.getX(v);y+=pos.getY(v);z+=pos.getZ(v);}x=x/3*1000+DEFAULT.width/2;z=z/3*1000+DEFAULT.depth/2;y=y/3;
   let best=null;
   for(const wall of state.walls){if(wall.demolished)continue;const dx=wall.b[0]-wall.a[0],dy=wall.b[1]-wall.a[1],l2=dx*dx+dy*dy,t=((x-wall.a[0])*dx+(z-wall.a[1])*dy)/l2;if(t<-.02||t>1.02)continue;const dist=Math.abs((x-wall.a[0])*dy-(z-wall.a[1])*dx)/Math.sqrt(l2),score=Math.abs(dist-wall.t/2);if(!best||score<best.score)best={wall,score,side:((x-wall.a[0])*dy-(z-wall.a[1])*dx)>0?'right':'left'};}
   const finish=best&&best.score<12&&state.wallFinishes?.[best.wall.id]?.[best.side];
   if(finish){const spec=WALL_FINISHES[finish.kind],color=finish.color||finishPalette()[spec.role],key=finish.kind+color;
    if(!materials.has(key)){const m=surfaceMaterial(color,spec.kind);m.userData.finishRole='wall-'+finish.kind;mats.push(m);materials.set(key,mats.length-1);}mi=materials.get(key);}
  }
  if(!groups.has(mi))groups.set(mi,[]);groups.get(mi).push(idx[i],idx[i+1],idx[i+2]);
 }
 const indices=[];geo.clearGroups();for(const[mi,list]of groups){geo.addGroup(indices.length,list.length,mi);indices.push(...list);}geo.setIndex(indices);joined.material=mats;
 // World metre UVs preserve texture scale across joined walls.
 const uv=new Float32Array(pos.count*2);for(let i=0;i<pos.count;i++){uv[i*2]=Math.abs(norm.getX(i))>.5?pos.getZ(i):pos.getX(i);uv[i*2+1]=pos.getY(i);}geo.setAttribute('uv',new THREE.BufferAttribute(uv,2));
}
const v9Arch=buildArch;
buildArch=function(){
 v9Arch();applyWallSurfaces();for(const o of lampG.children.slice())if(o.isMesh){lampG.remove(o);o.geometry.dispose();}
 for(const c of state.ceilings||[]){
  if(c.drop<=0)continue;
  // Original ceiling remains at structural height; finish region lowers only the intended polygon.
  const mesh=new THREE.Mesh(new THREE.ExtrudeGeometry(ceilingShape(c),{depth:M(c.drop),bevelEnabled:false}),ceilingFinishMaterial(true));
  mesh.geometry.rotateX(Math.PI/2);mesh.position.y=H;mesh.name='Ceiling-'+c.id;mesh.userData.ceilingId=c.id;mesh.userData.room=c.roomId;mesh.userData.walkOnly=true;mesh.visible=opt.cut>=H&&opt.mode==='walk';mesh.receiveShadow=true;archUp.add(mesh);
 }
};
const v9Sync=sync;
sync=function(force){const ceils=JSON.stringify([state.ceilings,state.wallFinishes]);if(ceils!==sync.ceils){sigArch='';sync.ceils=ceils;}v9Sync(force);};
const v9WallPanel=wallPanel,v9BindWall=bindWallPanel;
wallPanel=function(w){
 const options=Object.entries(WALL_FINISHES).map(([id,s])=>[id,s.label]),faces=state.wallFinishes?.[w.id]||{};
 return v9WallPanel(w)+'<section><h3>墙面材料</h3><p class="scene-mode-note">沿墙起点 → 终点区分左右侧；不改变墙体结构。</p><div class="form">'+['left','right'].map(side=>'<label>'+({'left':'左侧墙面','right':'右侧墙面'}[side])+'<select data-wall-finish="'+side+'">'+options.map(([id,label])=>'<option value="'+id+'" '+((faces[side]?.kind||'paint')===id?'selected':'')+'>'+label+'</option>').join('')+'</select></label>').join('')+'</div><div class="actions"><button class="btn" id="resetWallFinish">恢复墙面</button></div></section>';
};
bindWallPanel=function(w){v9BindWall(w);document.querySelectorAll('[data-wall-finish]').forEach(el=>el.onchange=()=>mutate(()=>{state.wallFinishes[w.id]??={};state.wallFinishes[w.id][el.dataset.wallFinish]={kind:el.value};}));$('#resetWallFinish').onclick=()=>mutate(()=>delete state.wallFinishes[w.id]);};
const v9RoomPanel=roomPanel,v9BindRoom=bindRoomPanel;
roomPanel=function(r){
 const c=state.ceilings?.find(c=>c.roomId===r.id);
 return v9RoomPanel(r)+'<section><h3>顶面</h3>'+(c?'<div class="form"><label>吊顶<select id="ceilingMode"><option value="flat" '+(c.mode==='flat'?'selected':'')+'>平顶</option><option value="perimeter" '+(c.mode==='perimeter'?'selected':'')+'>周边吊顶</option></select></label><label>下降 / mm<input id="ceilingDrop" type="number" min="0" max="300" value="'+c.drop+'"></label><label>边带 / mm<input id="ceilingBand" type="number" min="100" max="800" value="'+c.band+'" '+(c.mode==='flat'?'disabled':'')+'></label><label>净高 / mm<input disabled value="'+(DEFAULT.height-c.drop)+'"></label></div><div class="actions"><button class="btn danger" id="removeCeiling">删除吊顶</button></div>':'<button class="btn" id="addCeiling">添加吊顶</button>')+'<p class="scene-mode-note">灯具可在家具库「顶面」中独立添加、移动和删除。</p></section>';
};
bindRoomPanel=function(){v9BindRoom();const id=ui.sel.id;
 const c=()=>state.ceilings.find(c=>c.roomId===id);
 $('#addCeiling')?.addEventListener('click',()=>mutate(()=>state.ceilings.push({id:uid(),roomId:id,mode:'perimeter',drop:120,band:300})));
 $('#removeCeiling')?.addEventListener('click',()=>mutate(()=>state.ceilings=state.ceilings.filter(c=>c.roomId!==id)));
 for(const[k,field]of [['ceilingMode','mode'],['ceilingDrop','drop'],['ceilingBand','band']])$('#'+k)?.addEventListener('change',e=>mutate(()=>c()[field]=field==='mode'?e.target.value:Number(e.target.value)));
};
const v9FurnPanel=furnPanel,v9BindFurn=bindFurnPanel;
furnPanel=function(f){const s=DIMENSIONS[f.type];return v9FurnPanel(f)+(s?'<section><h3>尺寸基准</h3><p class="scene-mode-note">'+(s.meaning||'组件高度')+' · 初值 '+s.h+' mm<br>设计范围 '+s.min+'–'+s.max+' mm'+(s.note?'<br>'+s.note:'')+'</p></section>':'');};
bindFurnPanel=function(f){v9BindFurn(f);
 if(f.type==='endpanel')$('#fW').onchange=e=>mutate(()=>{const g=getF(f.id),w=Number(e.target.value);if(w<15||w>500)throw Error('侧板厚度为 15–500 mm');g.w=w;});
 $('#fH').onchange=e=>{const h=Number(e.target.value);mutate(()=>{const g=getF(f.id);g.h=h;g.fitToCeiling=false;g.topToCeiling=false;});};
 $('#fE').onchange=e=>mutate(()=>getF(f.id).elevation=Number(e.target.value));
};
const v9Walls=renderWalls;
renderWalls=function(){v9Walls();const marks=[];
 for(const w of state.walls){if(w.demolished)continue;const dx=w.b[0]-w.a[0],dy=w.b[1]-w.a[1],len=Math.hypot(dx,dy),nx=-dy/len,ny=dx/len;
 for(const [side,f]of Object.entries(state.wallFinishes?.[w.id]||{})){if(f.kind==='paint')continue;const s=side==='left'?1:-1,col=f.color||finishPalette()[WALL_FINISHES[f.kind].role];for(const[a,b]of intervals(w)){marks.push('<path d="M'+(w.a[0]+dx*a/len+nx*s*(w.t/2+12))+' '+(w.a[1]+dy*a/len+ny*s*(w.t/2+12))+'L'+(w.a[0]+dx*b/len+nx*s*(w.t/2+12))+' '+(w.a[1]+dy*b/len+ny*s*(w.t/2+12))+'" fill="none" stroke="'+col+'" stroke-width="3" vector-effect="non-scaling-stroke" pointer-events="none" '+(f.kind==='wallpaper'?'stroke-dasharray="3 2"':'')+'/>');}}}
 $('#gWalls').insertAdjacentHTML('beforeend',marks.join(''));
};
const v9RenderRooms=renderRooms;
renderRooms=function(){v9RenderRooms();if(ui.sel?.kind==='room'){const c=state.ceilings?.find(c=>c.roomId===ui.sel.id);if(c){const r=ROOMS.find(r=>r.id===c.roomId),inner=c.mode==='perimeter'?insetPoly(r.poly,c.band):r.poly;$('#gRooms').insertAdjacentHTML('beforeend','<polygon points="'+inner.map(p=>p.join(',')).join(' ')+'" fill="none" stroke="#ad7951" stroke-width="1" stroke-dasharray="6 4" vector-effect="non-scaling-stroke" pointer-events="none"/>');}}};
const v9Select=select;
select=function(sel,opts){v9Select(sel,opts);renderRooms();};
function dimensionAudit(){
 scene.updateMatrixWorld(true);
 const rows=state.furniture.map(f=>{const g=furnG.children.find(g=>g.userData.fid===f.id),bb=g?new THREE.Box3().setFromObject(g):null,s=DIMENSIONS[f.type],exact=(f.detailModel===DETAIL_REVISION)||['fridge','washer','dryer','dishwasher','wallcab','fridgecab','endpanel','hood','pendant','downlight','tracklight'].includes(f.type),actual=bb?(bb.max.y-bb.min.y)*1000:null,expected=f.h||nominalHeights[f.type]||850;
  return{id:f.id,type:f.type,name:f.name,bodyHeightMm:expected,elevationMm:f.elevation||0,meshHeightMm:actual==null?null:Math.round(actual*10)/10,topMm:bb?Math.round(bb.max.y*10000)/10:null,exactHeightCheck:exact,match:!exact||actual!==null&&Math.abs(actual-expected)<2,finishedCeilingMm:finishedCeiling(f),ceilingExceeded:!!bb&&bb.max.y>M(finishedCeiling(f))+.002,definition:s?.meaning||'组件高度'};});
 const hood=state.furniture.find(f=>f.type==='hood'),stove=state.furniture.find(f=>f.type==='stove');
 return {version:10,units:'mm',height:DEFAULT.height,rows,errors:rows.filter(r=>!r.match||r.ceilingExceeded),hoodClearanceMm:hood&&stove?(hood.elevation||0)-(stove.elevation+stove.h):null,notes:['尺寸为概念设计初值，非产品最大尺寸标准','装饰物外包络与家具本体高度分开检查；精确检查类型见 exactHeightCheck']};
}
async function captureActualBundle(){
 if(!is3D())await setView('3d');
 const cut=opt.cut;try{opt.cut=H;grow=furnGrow=1;buildArch();buildFurn();scene.updateMatrixWorld(true);
  const bundle=await createProductionBundle(state,{...DEFAULT,footprint:FOOTPRINT},ROOMS,currentStyle());
  bundle.dimensionAudit=dimensionAudit();if(bundle.dimensionAudit.errors.length)throw Error('模型尺寸不一致：'+bundle.dimensionAudit.errors.map(r=>r.id).join(','));
  archUp.traverse(o=>{if(o.userData.ceilingId)o.visible=true;});bundle.scene=serializeProductionMeshes({floor:archFloor,architecture:archUp,furniture:furnG,lights:lampG});
  bundle.replay={basis:'actual browser scene',notLiveUserBrowserState:true,generatedOutputsAccepted:false};
  return bundle;
 }finally{opt.cut=cut;buildArch();buildFurn();}
}
const oldProductionExport=exportProductionBundle;
exportProductionBundle=async function(){const bundle=await captureActualBundle();if(Object.values(bundle.confirmations).some(s=>s.status!=='confirmed'))return toast('请先在文件菜单确认结构、布局和风格');download('装修方案-制作包.json',new Blob([JSON.stringify(bundle)],{type:'application/json'}));toast('已导出制作包');};
Object.assign(window.homeStudio,{
 select,validate:fixState,addCatalogItem:(type,x,y)=>{const it=LIB.flatMap(g=>g.items).find(i=>i[0]===type);if(!it)throw Error('未知组件');addItem(it,x,y);},
 updateObject:(id,patch)=>mutate(()=>Object.assign(getF(id),patch)),
 setWallFinish:(id,side,kind)=>mutate(()=>{state.wallFinishes[id]??={};state.wallFinishes[id][side]={kind};}),
 setCeiling:(roomId,patch)=>mutate(()=>{let c=state.ceilings.find(c=>c.roomId===roomId);if(patch===null){state.ceilings=state.ceilings.filter(c=>c.roomId!==roomId);return;}if(!c){c={id:uid(),roomId,mode:'perimeter',drop:120,band:300};state.ceilings.push(c);}Object.assign(c,patch);}),
 dimensionAudit,captureActualBundle,getDimensionStandards:()=>structuredClone(DIMENSIONS),
 exportPlanSVG:()=>{const c=svg.cloneNode(true);c.setAttribute('xmlns','http://www.w3.org/2000/svg');c.setAttribute('viewBox',[BOUNDS.x,BOUNDS.y,BOUNDS.w,BOUNDS.h].join(' '));c.setAttribute('width','1500');c.setAttribute('height',String(Math.round(1500*BOUNDS.h/BOUNDS.w)));c.querySelector('#gSel')?.remove();return new XMLSerializer().serializeToString(c);}
});


// Two review samples retain their source IDs and dimensional envelopes.
const sampleDefaults=defaultState,sampleFix=fixState;
function markDetailSamples(s){if(CASE.presentation?.preserveImportedDetailModels)return s;for(const f of s.furniture){if(['bed','sofabed'].includes(f.type))f.detailModel=DETAIL_REVISION;}return s;}
defaultState=()=>markDetailSamples(sampleDefaults());
fixState=s=>markDetailSamples(sampleFix(s));
state=fixState(state);
const beforeDetailFurniture=buildFurniture;
buildFurniture=function(f){
 if(f.detailModel!==DETAIL_REVISION||!['bed','sofabed'].includes(f.type))return beforeDetailFurniture(f);
 const g=refinedFurniture({...f,finishes:finishPalette(),finishSpec:currentStyle()});
 g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-(f.rot||0)*Math.PI/180;
 g.userData.fid=f.id;g.userData.caseHeight=f.h;g.userData.fitToCeiling=!!f.fitToCeiling;
 return g;
};
Object.assign(window.homeStudio,{validate:fixState,detailRevision:DETAIL_REVISION});

const fullDefaults=defaultState,fullFix=fixState;
function markWholeHome(s){for(const f of s.furniture)if(FULL_TYPES.includes(f.type))f.detailAssembly=FULL_REVISION;return s;}
defaultState=()=>markWholeHome(fullDefaults());fixState=s=>markWholeHome(fullFix(s));state=fixState(state);
const beforeFullFurniture=buildFurniture;
buildFurniture=function(f){
 const base=beforeFullFurniture(f);
 if(f.detailModel===DETAIL_REVISION&&['bed','sofabed'].includes(f.type)){base.traverse(o=>{for(const m of o.material?(Array.isArray(o.material)?o.material:[o.material]):[])m.userData.ownedFurnitureDetail=true;});return base;}
 if(f.detailAssembly!==FULL_REVISION)return base;
 const g=wholeHomeFurniture({...f,finishes:finishPalette(),finishSpec:currentStyle()},base);
 if(!g)return base;
 g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-(f.rot||0)*Math.PI/180;g.userData.fid=f.id;g.userData.caseHeight=f.h;g.userData.fitToCeiling=!!f.fitToCeiling;
 g.traverse(o=>{if(o.material)for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.metalness>.1){m.envMap=envTex;m.envMapIntensity=.5;}});
 // The temporary reference builder is used only to carry existing accessories.
 // Release replaced geometry while retaining reused plumbing/glazing geometries.
 const retained=new Set();g.traverse(o=>{if(o.geometry)retained.add(o.geometry);});base.traverse(o=>{if(o.geometry&&!retained.has(o.geometry))o.geometry.dispose();});
 return g;
};
const detailClear=clearGroup;
clearGroup=function(g){const materials=new Set();g.traverse(o=>{for(const m of o.material?(Array.isArray(o.material)?o.material:[o.material]):[])if(m.userData.ownedFurnitureDetail)materials.add(m);});for(const m of materials)m.dispose();detailClear(g);};
const beforeFullAudit=dimensionAudit;
dimensionAudit=function(){const a=beforeFullAudit();a.version=11;
 for(const row of a.rows){const group=furnG.children.find(g=>g.userData.fid===row.id),b=group?.children.find(g=>g.userData.bodyForDimensions);
  if(b){const bb=new THREE.Box3().setFromObject(b,true);row.meshHeightMm=Math.round((bb.max.y-bb.min.y)*10000)/10;row.exactHeightCheck=true;row.match=Math.abs(row.meshHeightMm-row.bodyHeightMm)<2;row.accessoryTopMm=row.topMm;row.bodyTopMm=Math.round(bb.max.y*10000)/10;row.definition+=' · 家具本体与桌面附件分开校验';}
 }
 a.errors=a.rows.filter(r=>!r.match||r.ceilingExceeded);return a;
};
Object.assign(window.homeStudio,{validate:fixState,dimensionAudit,fullDetailRevision:FULL_REVISION});

// Cursor direction follows the selected object's local axes.
const beforeAxisCursor=renderSel;
renderSel=function(){beforeAxisCursor();const f=ui.sel?.kind==='furn'?getF(ui.sel.id):null;if(!f)return;
 const cursor=angle=>['ew-resize','nwse-resize','ns-resize','nesw-resize'][((Math.round(angle/45)%4)+4)%4];
 for(const el of document.querySelectorAll('#gSel [data-handle]')){const kind=el.dataset.handle;if(['width','widthLeft','depth','size'].includes(kind))el.style.cursor=cursor(f.rot+(kind==='depth'?90:kind==='size'?45:0));}
};
// V12: independent renovation components and fixture-bound illumination.
let topView=false,constructionExporting=false;
// Follow the catalog categories so new finishing accessories cannot escape this switch.
const CONSTRUCTION_DETAIL_TYPES=new Set([...TOP_TYPES,...RENOVATION_SPECS.map(c=>c.type),'acwall','aircon','endpanel']);
const constructionDetail=f=>!!f&&CONSTRUCTION_DETAIL_TYPES.has(f.type);
function applyConstruction2D(){applyPlanDrawingLayers();}
const constructionRenderFurn=renderFurn;renderFurn=function(){constructionRenderFurn();applyConstruction2D();};
const mountedLabel={ceiling:'贴顶',wall:'墙面',opening:'洞口',floor:'地面',surface:'台面','under-cabinet':'柜底'};
function renColor(type,style=currentStyle()){return style.palette[RENOVATION_MAP[type]?.role]||style.palette.ceiling;}
function renItem(id,type,name,cx,cy,w,d,h,elevation,rot=0,extra={}){
 const spec=RENOVATION_MAP[type];return {id,type,name,cx,cy,w:w||spec.w,d:d||spec.d,h:h||spec.h,elevation:elevation??spec.elevation,rot,color:renColor(type,getStyle(state?.style||'champagne_pearl')),mount:spec.mount,lightOn:true,lightIntensity:spec.lit?3:0,lightTemperature:3000,renovationRevision:12,source:'装修构件设计初值；未标安装位置与尺寸为编辑初值',...extra};
}
const beforeRenAnchor=syncCeilingAnchors;
syncCeilingAnchors=function(s){beforeRenAnchor(s);for(const f of s.furniture){if(['pendant','downlight','tracklight'].includes(f.type)&&!f.mount)f.mount='ceiling';if(['acwall','waterheater'].includes(f.type))f.mountGeometryRevision='wall-mounted-v12.1';if(f.mount==='ceiling')f.elevation=Math.max(0,finishedCeiling(f,s)-(f.recessedCeiling?1:f.type==='cove'?18:f.h));
 if(f.followCeiling){if(f.type==='curtainrail')f.elevation=Math.max(0,finishedCeiling(f,s)-(f.ceilingOffset||115)-f.h);if(f.type==='curtain')f.h=Math.max(15,finishedCeiling(f,s)-(f.ceilingTopOffset||150)-f.elevation);}
 if(f.supportId){const support=s.furniture.find(x=>x.id===f.supportId);if(support){const pose=[support.cx,support.cy,support.rot,support.w,support.d,support.h,support.elevation||0],angle=support.rot*Math.PI/180,c=Math.cos(angle),n=Math.sin(angle);if(f.supportPose&&JSON.stringify(pose)===JSON.stringify(f.supportPose)){const dx=f.cx-support.cx,dy=f.cy-support.cy;f.supportOffset=[Math.round((dx*c+dy*n)/support.w*1e9)/1e9,Math.round((-dx*n+dy*c)/support.d*1e9)/1e9];}const [u,v]=f.supportOffset||[0,0],x=u*support.w,y=v*support.d;f.cx=Math.round((support.cx+x*c-y*n)*1e6)/1e6;f.cy=Math.round((support.cy+x*n+y*c)*1e6)/1e6;f.elevation=(support.elevation||0)+(f.supportUnder?-f.h:support.h);f.supportPose=pose;}}
f.lightTemperature=LIT_TYPES.has(f.type)?Math.max(2200,Math.min(6500,Number(f.lightTemperature)||3000)):f.lightTemperature;f.lightIntensity=LIT_TYPES.has(f.type)?Math.max(0,Math.min(8,(Number.isFinite(Number(f.lightIntensity))?Number(f.lightIntensity):3))):f.lightIntensity;}return s;};
const renDefault=defaultState,renFix=fixState;
defaultState=()=>syncCeilingAnchors(renDefault());
fixState=input=>{const s=renFix(structuredClone(input));syncCeilingAnchors(s);s.version=12;return s;};
state=fixState(state);
const renSymbol=furnSVG;
furnSVG=function(type,w,d,c,f){if(type==='nightstand'&&f?.independentLampRevision)return `<rect x="${-w/2}" y="${-d/2}" width="${w}" height="${d}" rx="20" fill="${c}" stroke="#666158" stroke-width="1" vector-effect="non-scaling-stroke"/>`;return RENOVATION_MAP[type]?renovationSymbol(type,w,d,c):renSymbol(type,w,d,c,f);};
const renModel=buildFurniture;
buildFurniture=function(f){if(!RENOVATION_MAP[f.type]){const g=renModel(f);if(f.independentLampRevision){const remove=[];g.traverse(o=>{if(o.userData.legacyTableLamp)remove.push(o);});for(const o of remove){o.removeFromParent();o.geometry?.dispose();}}return g;}const g=renovationModel(f,finishPalette(),opt.night);g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-f.rot*Math.PI/180;g.userData.fid=f.id;g.userData.caseHeight=f.h;return g;};
const renAdd=addItem;
addItem=function(it,x,y){const spec=RENOVATION_MAP[it[0]];if(!spec)return renAdd(it,x,y);const f=renItem(uid(),it[0],it[1],Math.round(x/10)*10,Math.round(y/10)*10,it[2],it[3]);f.catalogKey=LIB.flatMap((g,ci)=>g.items.flatMap((v,ii)=>v===it?[ci+':'+ii]:[]))[0];ui.sel={kind:'furn',id:f.id};mutate(()=>state.furniture.push(f));};
const renDuplicate=duplicateSel;duplicateSel=function(){const id=ui.sel?.kind==='furn'?ui.sel.id:null,links=id?state.furniture.filter(f=>f.supportId===id):[];if(!links.length)return renDuplicate();const source=getF(id),n={...source,id:uid(),cx:source.cx+200,cy:source.cy+200};ui.sel={kind:'furn',id:n.id};return mutate(()=>{state.furniture.push(n,...links.map(f=>({...structuredClone(f),id:uid(),supportId:n.id,supportPose:null})));});};
const renDelete=deleteSel;deleteSel=function(){const id=ui.sel?.kind==='furn'?ui.sel.id:null;if(id){const links=state.furniture.filter(f=>f.supportId===id).map(f=>f.id);if(links.length){ui.sel=null;return mutate(()=>state.furniture=state.furniture.filter(f=>f.id!==id&&!links.includes(f.id)));}}return renDelete();};
const renSnap=snapMove;
snapMove=function(f,x,y){return f.mount==='ceiling'||f.mount==='opening'?[Math.round(x/10)*10,Math.round(y/10)*10]:renSnap(f,x,y);};
function renderTop(){
 const layer=$('#gTop');if(!layer)return;const shown=is3D()?topView:planDrawingMode==='hard';layer.style.display=shown?'':'none';applyConstruction2D();
 if(!shown){layer.replaceChildren();return;}
 const k=1/view.s;
 let html=state.ceilings.map(c=>{const poly=ceilingFootprint(c),inner=c.mode==='perimeter'?insetPoly(poly,c.band):poly;return `<polygon data-ceiling-zone="${c.id}" points="${inner.map(p=>p.join(',')).join(' ')}" fill="none" stroke="#a9957b" stroke-dasharray="5 3" stroke-width="1" vector-effect="non-scaling-stroke" pointer-events="none"/>`;}).join('');
 const items=state.furniture.filter(f=>TOP_TYPES.has(f.type)&&!UNNECESSARY_DISPLAY_TYPES.has(f.type));
 items.forEach((f,i)=>{const spec=RENOVATION_MAP[f.type],label=f.lightingTag?f.lightingTag+' 筒灯':spec?.name||({pendant:'吊灯',downlight:'筒灯',tracklight:'轨道灯'}[f.type]),min=7*k;
 html+=`<g class="furn top-symbol" data-fid="${f.id}" transform="translate(${f.cx} ${f.cy})"><g transform="rotate(${f.rot})">${furnSVG(f.type,f.w,f.d,f.color,f)}</g><circle r="${Math.max(min,Math.min(f.w,f.d)*.2)}" fill="transparent" stroke="#9c7852" stroke-width="1" vector-effect="non-scaling-stroke"/><text y="${Math.max(f.d/2,8*k)+12*k}" text-anchor="middle" font-size="${10*k}" fill="#544a3e" stroke="#fffdf8" stroke-width="${3*k}" paint-order="stroke" pointer-events="none">${label}</text><title>${esc(f.name)} · ${f.w}×${f.d} mm · 离地 ${f.elevation} mm</title></g>`;
 });layer.innerHTML=html;
 // Place ceiling labels around their symbol, keeping room names and labels apart.
 const rect=e=>{const b=e.getBoundingClientRect();return {left:b.left-2,right:b.right+2,top:b.top-2,bottom:b.bottom+2};},used=[];
 const overlaps=(a,b)=>a.left<b.right&&a.right>b.left&&a.top<b.bottom&&a.bottom>b.top;
 if(ui.layers.labels)$('#gLabels').querySelectorAll('text').forEach(el=>{if(getComputedStyle(el).display!=='none')used.push(rect(el));});
 const bounds=svg.getBoundingClientRect();
 for(const el of layer.querySelectorAll('.top-symbol text')){
  const f=getF(el.parentElement.dataset.fid),halfX=Math.max(f.w/2,8*k),halfY=Math.max(f.d/2,8*k);
  const points=[[0,halfY+12*k,'middle'],[0,-halfY-8*k,'middle'],[halfX+8*k,3*k,'start'],[-halfX-8*k,3*k,'end'],[0,halfY+26*k,'middle'],[0,-halfY-22*k,'middle']];
  let placed=false;
  for(const [x,y,anchor]of points){el.setAttribute('x',x);el.setAttribute('y',y);el.setAttribute('text-anchor',anchor);const r=rect(el);if(r.left<bounds.left+4||r.right>bounds.right-4||r.top<bounds.top+4||r.bottom>bounds.bottom-4||used.some(b=>overlaps(r,b)))continue;used.push(r);placed=true;break;}
  if(!placed)el.style.display='none'; // Full name stays available on the symbol's hover title.
 }
}
const renRender=renderAll;renderAll=function(){renRender();renderTop();};
const renSel=renderSel;renderSel=function(){if(ui.sel?.kind==='furn'&&(is3D()?!topView&&constructionDetail(getF(ui.sel.id)):!planItemVisible(getF(ui.sel.id))))ui.sel=null;renSel();renderTop();};
function isRenovation(f){return !!RENOVATION_MAP[f.type]||TOP_TYPES.has(f.type)||['wallcab','fridgecab','endpanel','hood','acwall'].includes(f.type);}
const renOverview=overviewPanel;
overviewPanel=function(){const n=state.furniture.filter(isRenovation).length;return renOverview().replace('<small>家具</small><span class="big">'+state.furniture.length+'</span> 件','<small>家具</small><span class="big">'+(state.furniture.length-n)+'</span> 件</div><div><small>装修构件</small><span class="big">'+n+'</span> 件');};
const renRoomPanel=roomPanel;
roomPanel=function(r){const html=renRoomPanel(r),all=state.furniture.filter(f=>!f.assemblyOwner&&!UNNECESSARY_DISPLAY_TYPES.has(f.type)&&inPolygon([f.cx,f.cy],r.poly)),items=all.filter(f=>!isRenovation(f)),parts=all.filter(isRenovation),table=fs=>'<table>'+fs.map(f=>'<tr class="click" data-fid="'+f.id+'"><td>'+esc(f.name)+'</td><td class="r muted">'+f.w+'×'+f.d+'</td></tr>').join('')+'</table>';
 return html.replace(/<section><h3>(?:家具|房间内家具)[\s\S]*?<\/section>/,'<section><h3>家具 <small>'+items.length+' 件</small></h3>'+table(items)+'<details class="renovation-list"><summary>装修构件 · '+parts.length+' 件</summary>'+table(parts)+'</details></section>');};
const renPanel=furnPanel;
furnPanel=function(f){let html=renPanel(f);if(RENOVATION_MAP[f.type]||TOP_TYPES.has(f.type))html+=`<section><h3>安装</h3><p class="muted">${mountedLabel[f.mount]||'独立构件'} · ${f.mount==='ceiling'?'随完成顶面自动调整离地':'离地与长宽高均可编辑'}</p></section>`;if(['curtainrail','curtain'].includes(f.type))html+=`<section><label><input id=renFollowCeiling type=checkbox ${f.followCeiling?'checked':''}> 随完成顶面调整</label></section>`;if(LIT_TYPES.has(f.type))html+=`<section><h3>照明</h3><label><input id="renLightOn" type="checkbox" ${f.lightOn!==false?'checked':''}> 启用</label><div class="form"><label>强度<input id="renLightIntensity" type="number" min="0" max="8" step=".5" value="${f.lightIntensity??3}"></label><label>色温 K<input id="renLightTemp" type="number" min="2200" max="6500" step="100" value="${f.lightTemperature||3000}"></label></div></section>`;return html;};
const renBind=bindFurnPanel;bindFurnPanel=function(f){renBind(f);if(f.mount==='ceiling'){$('#fE').disabled=true;$('#fE').title='贴顶构件自动随完成顶面调整';}
 if($('#renFollowCeiling'))$('#renFollowCeiling').onchange=e=>mutate(()=>getF(f.id).followCeiling=e.target.checked);if(f.followCeiling){if(f.type==='curtain')$('#fH').disabled=true;else $('#fE').disabled=true;}
 for(const [id,key]of [['renLightOn','lightOn'],['renLightIntensity','lightIntensity'],['renLightTemp','lightTemperature']]){const el=document.getElementById(id);if(el)el.onchange=e=>mutate(()=>getF(f.id)[key]=key==='lightOn'?e.target.checked:Number(e.target.value));}
};
function rebuildFixtureLights(){
 if(!inited)return;lampG.clear();
 for(const f of state.furniture.filter(f=>LIT_TYPES.has(f.type))){const t=f.lightTemperature||3000,col=f.type==='downlight'?'#ffffff':t<3500?'#ffe1b8':t<5000?'#fff1db':'#edf3ff';const range=Math.max(2.5,Math.min(7,(Math.max(f.w,f.d)/1000)*2+3));const light=f.type==='downlight'?new THREE.SpotLight(col,0,range,Math.PI*.36,.8,2):new THREE.PointLight(col,0,range,2);light.position.set(wx(f.cx),M(f.elevation||0)-.012,wz(f.cy));if(light.isSpotLight){light.target.position.set(wx(f.cx),0,wz(f.cy));lampG.add(light.target);}light.userData.fixtureId=f.id;light.userData.nominalIntensity=f.lightIntensity??3;light.userData.enabled=f.lightOn!==false;lampG.add(light);}
 applyLight();
}
const renLight=applyLight;applyLight=function(){renLight();lampG.children.forEach(o=>{if(o.isLight)o.intensity=opt.night&&o.userData.enabled?o.userData.nominalIntensity:0;});furnG.traverse(o=>{if(!o.isMesh)return;for(const m of Array.isArray(o.material)?o.material:[o.material])if(m.emissive?.getHex()){let parent=o;while(parent&&!parent.userData.fid)parent=parent.parent;const f=parent&&getF(parent.userData.fid);m.emissiveIntensity=f&&LIT_TYPES.has(f.type)&&f.lightOn===false?0:(m.userData.recessedLuminousFace?(opt.night?2.2:.65):(opt.night?1.2:.12));}});};
function applyTop3D(){if(!inited)return;
 const shown=topView||constructionExporting,solid=opt.mode==='walk'||constructionExporting;
 archUp.traverse(o=>{if(o.userData.ceilingId||o.userData.baseCeiling){o.visible=shown;if(o.material){o.material.transparent=!solid;o.material.opacity=solid?1:.16;o.material.depthWrite=solid;o.material.side=THREE.DoubleSide;o.material.needsUpdate=true;}}});
 for(const g of furnG.children){const f=getF(g.userData.fid);g.visible=!constructionDetail(f)||shown;}
 updateSel();
}
const renArch=buildArch;buildArch=function(){renArch();rebuildFixtureLights();applyTop3D();};
const renFurn=buildFurn;buildFurn=function(){renFurn();rebuildFixtureLights();applyTop3D();};
const renMode=setMode;setMode=function(m){renMode(m);applyTop3D();};
const renQuick=syncQuickActions;syncQuickActions=function(){renQuick();document.querySelectorAll('[data-top-view]').forEach(b=>{b.classList.toggle('on',topView);b.setAttribute('aria-pressed',String(topView));b.disabled=switching;});};
function setTopView(v){topView=!!v;if(!topView&&ui.sel?.kind==='furn'&&constructionDetail(getF(ui.sel.id)))select(null);renderTop();applyTop3D();syncQuickActions();}
for(const el of document.querySelectorAll('[data-top-view]'))el.onclick=()=>setTopView(!topView);
const renAudit=dimensionAudit;dimensionAudit=function(){const a=renAudit();a.version=12;
 for(const row of a.rows){const f=getF(row.id);if(!RENOVATION_MAP[f.type]&&!['acwall','waterheater'].includes(f.type))continue;row.exactHeightCheck=true;row.match=Math.abs(row.meshHeightMm-row.bodyHeightMm)<2;row.mount=f.mount;
  if(f.type==='cove'){const g=furnG.children.find(g=>g.userData.fid===f.id),bb=g?new THREE.Box3().setFromObject(g):null;row.ceilingExceeded=!bb||bb.max.y>M(DEFAULT.height)+.002;row.installationHeightMatch=!!bb&&Math.abs(bb.min.y*1000-(finishedCeiling(f)-18))<2;row.match=row.match&&row.installationHeightMatch;row.definition='灯槽主体藏于吊顶内部，下沿低于完成顶面18mm';}
  if(['acwall','waterheater'].includes(f.type)){const g=furnG.children.find(g=>g.userData.fid===f.id),bb=g?new THREE.Box3().setFromObject(g):null;row.bottomMm=bb?Math.round(bb.min.y*10000)/10:null;row.installationHeightMatch=bb!==null&&Math.abs(bb.min.y*1000-row.elevationMm)<2;row.match=row.match&&row.installationHeightMatch;row.mountGeometryRevision=f.mountGeometryRevision;}
 }
 a.errors=a.rows.filter(r=>!r.match||r.ceilingExceeded);return a;};
const renCapture=captureActualBundle;captureActualBundle=async function(){try{constructionExporting=true;const b=await renCapture();b.scene.illumination=lampG.children.filter(o=>o.isLight).map(o=>({fixtureId:o.userData.fixtureId,type:o.type,colorLinear:o.color.toArray(),position:o.position.toArray(),intensity:o.userData.nominalIntensity,enabled:o.userData.enabled,distance:o.distance,decay:o.decay,...(o.isSpotLight?{target:o.target.position.toArray(),angle:o.angle,penumbra:o.penumbra}: {})}));b.renovationRevision=12;b.presentationProfile=structuredClone(PRESENTATION_PROFILE);b.limitations.push('新增灯位、窗帘及电气附件是概念安装位置；未作为施工定位或隐蔽系统设计确认。');return b;}finally{constructionExporting=false;applyTop3D();}};
Object.assign(window.homeStudio,{validate:fixState,dimensionAudit,captureActualBundle,setTopView,getTopView:()=>topView,getRenovationSpecs:()=>structuredClone(RENOVATION_SPECS),getFixtureLights:()=>lampG.children.filter(o=>o.isLight).map(o=>({id:o.userData.fixtureId,position:o.position.toArray(),intensity:o.intensity})),setLighting:(mode)=>setLightingMode(mode),setCameraMode:setMode,deleteSelected:()=>deleteSel(),duplicateSelected:()=>duplicateSel(),addCatalogItem:(type,x,y)=>{const it=LIB.flatMap(g=>g.items).find(i=>i[0]===type);if(!it)throw Error('未知组件');addItem(it,x,y);}});

// Furniture labels are a display overlay; geometry, installation and stacking stay untouched.
const furnitureLabelNames={bed:'双人床',sofa:'沙发',sofabed:'沙发床',armchair:'休闲椅',cornersofa:'转角沙发',chair:'椅子',officechair:'办公椅',nightstand:'床头柜',wardrobe:'衣柜',bookshelf:'书柜',dresser:'梳妆台',desk:'书桌',table:'餐桌',roundtable:'茶几',coffee:'茶几',coffeetable:'茶几',sidetable:'边几',tvstand:'电视柜',tv:'电视',counter:'地柜',ksink:'水槽',sink:'水槽',vanity:'洗手台',basin:'洗手台',stove:'灶台',hob:'灶台',fridge:'冰箱',shower:'淋浴区',toilet:'马桶',rug:'地毯',plant:'绿植',floorlamp:'落地灯',hood:'油烟机',wallcab:'吊柜',fridgecab:'上柜',baycushion:'飘窗垫',washer:'洗衣机',dryer:'烘干机',dishwasher:'洗碗机',acwall:'空调',aircon:'空调'};
const labelCanvas=document.createElement('canvas'),labelMeasure=labelCanvas.getContext('2d');
function furnitureLabelName(f){return nm(furnitureLabelNames[f.originalType||f.type]||furnitureLabelNames[f.type]||RENOVATION_MAP[f.type]?.name||f.name);}
function renderFurnitureLabels(){
 const layer=$('#gFurnitureLabels');if(!layer)return;layer.replaceChildren();if(planDrawingMode==='structure'||planDrawingMode==='furniture'&&!ui.layers.furn)return;
 const scale=view.s,k=1/scale,sr=svg.getBoundingClientRect(),used=[];
 const obstacle=el=>{const b=el.getBoundingClientRect();if(!b.width||!b.height)return;used.push({x0:view.x0+(b.left-sr.left)*k-2*k,y0:view.y0+(b.top-sr.top)*k-2*k,x1:view.x0+(b.right-sr.left)*k+2*k,y1:view.y0+(b.bottom-sr.top)*k+2*k});};
 if(ui.layers.labels)$('#gLabels').querySelectorAll('text').forEach(obstacle);if(is3D()?topView:planDrawingMode==='hard')$('#gTop').querySelectorAll('text').forEach(obstacle);$('#gSel').querySelectorAll('text').forEach(obstacle);
 const overlaps=(a,b)=>a.x0<b.x1&&a.x1>b.x0&&a.y0<b.y1&&a.y1>b.y0;
 const visible=state.furniture.filter(f=>!f.assemblyOwner&&f.type!=='laundrycab'&&!f.planPoint&&!['laundrypower','waterinlet','drainoutlet'].includes(f.type)&&planItemVisible(f)&&!TOP_TYPES.has(f.type)),order=new Map(state.furniture.map((f,i)=>[f.id,i]));
 const inside=(f,x,y,pad=0)=>{const a=f.rot*Math.PI/180,dx=x-f.cx,dy=y-f.cy;return Math.abs(dx*Math.cos(a)+dy*Math.sin(a))<=f.w/2+pad&&Math.abs(-dx*Math.sin(a)+dy*Math.cos(a))<=f.d/2+pad;};
 const sorted=visible.slice().sort((a,b)=>(b.id===ui.sel?.id)-(a.id===ui.sel?.id)||b.w*b.d-a.w*a.d);
 let html='';
 for(const f of sorted){
  // Tiny installation symbols use their full hover name instead of illegible micro-text.
  if(Math.min(f.w,f.d)*scale<13||Math.max(f.w,f.d)*scale<23)continue;
  const pairedBase=['wallcab','fridgecab','hood'].includes(f.type)&&visible.some(base=>({wallcab:'counter',fridgecab:'fridge',hood:'stove'}[f.type]===base.type)&&inside(base,f.cx,f.cy,50));if(pairedBase)continue;
  const name=f.type==='counter'&&visible.some(upper=>upper.type==='wallcab'&&inside(f,upper.cx,upper.cy,50))?nm('橱柜'):furnitureLabelName(f),large=Math.min(f.w,f.d)*scale>45,font=large?11:10,theta=f.rot*Math.PI/180,c=Math.cos(theta),s=Math.sin(theta);
  const wrapped=f.type==='nightstand'&&LANG!=='en'?['床头','柜']:null;
  const versions=[{lines:[name],font,angle:0}];if(wrapped)versions.unshift({lines:wrapped,font:9.5,angle:0,pitch:.95});
  if(Math.max(f.w,f.d)>Math.min(f.w,f.d)*1.7){let angle=f.rot+(f.d>f.w?90:0);angle=((angle+90)%180+180)%180-90;versions.push({lines:[name],font,angle});}
  const anchors=f.type==='rug'?[[0,.38],[.32,.32],[-.32,.32],[.32,-.32],[-.32,-.32],[0,-.38]]:f.type==='bed'?[[0,.12],[0,.24],[0,0],[.18,.15],[-.18,.15]]:f.type==='desk'?[[0,.18],[.25,.15],[-.25,.15],[0,0]]:[[0,0],[0,.18],[0,-.18],[.22,0],[-.22,0],[.2,.2],[-.2,-.2]];
  let placed=null;
  for(const version of versions){labelMeasure.font=`500 ${version.font}px -apple-system, "PingFang SC", sans-serif`;const metrics=version.lines.map(t=>labelMeasure.measureText(t)),width=Math.max(...metrics.map(m=>m.width))+3,height=Math.max(version.font*1.4,...metrics.map(m=>(m.fontBoundingBoxAscent||0)+(m.fontBoundingBoxDescent||0)))+(version.lines.length-1)*version.font*(version.pitch||1.1)+2,angle=version.angle*Math.PI/180,ac=Math.cos(angle),as=Math.sin(angle);
   for(const [u,v]of anchors){const lx=f.w*u,ly=f.d*v,x=f.cx+lx*c-ly*s,y=f.cy+lx*s+ly*c,corners=[[-width/2,-height/2],[width/2,-height/2],[width/2,height/2],[-width/2,height/2]].map(([p,q])=>[x+(p*ac-q*as)*k,y+(p*as+q*ac)*k]),box={x0:Math.min(...corners.map(p=>p[0])),y0:Math.min(...corners.map(p=>p[1])),x1:Math.max(...corners.map(p=>p[0])),y1:Math.max(...corners.map(p=>p[1]))};
    if(!corners.every(([x,y])=>inside(f,x,y,2*k))||used.some(b=>overlaps(box,b)))continue;
    if(visible.some(other=>other.id!==f.id&&order.get(other.id)>order.get(f.id)&&(other.elevation||0)<1000&&!['rug','plant','floorlamp'].includes(other.type)&&inside(other,x,y,-1*k)))continue;
    placed={...version,x,y,box};break;
   }if(placed)break;
  }
  if(!placed)continue;used.push(placed.box);
  html+=`<g class="furniture-label" data-label-for="${f.id}" data-font-px="${placed.font}" transform="translate(${placed.x} ${placed.y}) rotate(${placed.angle})" opacity="1" pointer-events="none"><text text-anchor="middle" dominant-baseline="central" font-size="${placed.font*k}" font-weight="500" fill="#34302b" stroke="#fffdf8" stroke-width="${2*k}" stroke-linejoin="round" paint-order="stroke">${placed.lines.map((line,i)=>`<tspan x="0" y="${(i-(placed.lines.length-1)/2)*placed.font*(placed.pitch||1.1)*k}">${esc(line)}</tspan>`).join('')}</text></g>`;
 }
 layer.innerHTML=html;
}
const labelRenderTop=renderTop;renderTop=function(){labelRenderTop();renderFurnitureLabels();};
window.select=select;
// Recessed lighting: thin trim below finish, housing inside the dropped ceiling.
const RECESSED_LIGHT_REVISION='perimeter-recessed-20261005.2';
const recessedAdd=addItem;
addItem=function(it,x,y){
 if(it[0]!=='downlight')return recessedAdd(it,x,y);
 const f=F(it[0],it[1],Math.round(x/10)*10,Math.round(y/10)*10,it[2],it[3],0,styleFurnitureColor(currentStyle(),it[0],it[4]));f.h=DIMENSIONS[it[0]].h;
 const occupied=state.furniture.some(g=>{if(!['cove','curtainbox'].includes(g.type))return false;const dx=f.cx-g.cx,dy=f.cy-g.cy,a=g.rot*Math.PI/180;return Math.abs(dx*Math.cos(a)+dy*Math.sin(a))<(g.w+f.w)/2&&Math.abs(-dx*Math.sin(a)+dy*Math.cos(a))<(g.d+f.d)/2;});
 if(occupied||DEFAULT.height-finishedCeiling(f)<f.h){toast('请将筒灯放入降顶区域，并避开灯槽及帘盒');return;}
 Object.assign(f,{recessedRevision:RECESSED_LIGHT_REVISION,recessedCeiling:true,mount:'ceiling',elevation:finishedCeiling(f)-1,lightTemperature:5000,lightOn:true,lightIntensity:2});
 f.catalogKey=LIB.flatMap((g,ci)=>g.items.flatMap((v,ii)=>v===it?[ci+':'+ii]:[]))[0];
 ui.sel={kind:'furn',id:f.id};return mutate(()=>state.furniture.push(f));
};
const recessedBuildFurniture=buildFurniture;
buildFurniture=function(f){if(f.type!=='downlight'||!f.recessedCeiling)return recessedBuildFurniture(f);
 const g=new THREE.Group(),w=M(f.w),d=M(f.d),h=M(f.h),trim=mat('#c1b49c',{roughness:.32,metalness:.65}),dark=mat('#48443d',{roughness:.8}),glow=mat('#ffffff',{emissive:'#ffffff',emissiveIntensity:opt.night?2.2:.65,roughness:.4});
 const ring=new THREE.Mesh(new THREE.RingGeometry(w*.40,w*.50,48),trim);ring.geometry.rotateX(Math.PI/2);ring.material.side=THREE.DoubleSide;ring.name='recessed-trim-flush';g.add(ring);
 const shell=new THREE.Mesh(new THREE.CylinderGeometry(w*.395,w*.395,h-.002,48,1,true),dark);shell.position.y=(h+.002)/2;shell.name='concealed-downlight-housing';g.add(shell);
 const reflector=new THREE.Mesh(new THREE.CylinderGeometry(w*.34,w*.39,.004,48,1,true),trim);reflector.position.y=.003;reflector.name='recessed-reflector';g.add(reflector);
 // Visible luminous lens is 0.4mm below the finished surface, with trim lower by 0.6mm.
 // Deep housing remains in the ceiling; the lens must not sit behind the plasterboard.
 const face=new THREE.Mesh(new THREE.CircleGeometry(w*.34,48),glow);face.geometry.rotateX(Math.PI/2);face.position.y=.0006;face.material.side=THREE.DoubleSide;face.name='recessed-luminous-face';face.material.userData.recessedLuminousFace=true;g.add(face);
 g.scale.z=d/w;g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-(f.rot||0)*Math.PI/180;g.userData={fid:f.id,caseHeight:f.h,recessedCeiling:true};return g;
};
const recessedCeilingShape=ceilingShape;
ceilingShape=function(c){const shape=recessedCeilingShape(c),r=ROOMS.find(r=>r.id===c.roomId);for(const f of state.furniture){if(!f.recessedCeiling||!inPolygon([f.cx,f.cy],ceilingFootprint(c)))continue;
 if(c.mode==='perimeter'&&inPolygon([f.cx,f.cy],insetPoly(ceilingFootprint(c),c.band)))continue;
 const hole=new THREE.Path();hole.absellipse(wx(f.cx),wz(f.cy),M(f.w)*.40,M(f.d)*.40,0,Math.PI*2,true,(f.rot||0)*Math.PI/180);shape.holes.push(hole);
 }return shape;
};
const recessedAudit=dimensionAudit;
dimensionAudit=function(){const a=recessedAudit();for(const row of a.rows){const f=getF(row.id);if(!f?.recessedCeiling)continue;
 const finish=finishedCeiling(f),g=furnG.children.find(g=>g.userData.fid===f.id),box=g?new THREE.Box3().setFromObject(g):null;
 row.recessed=true;row.mount='ceiling-recessed';row.ceilingExceeded=box?box.max.y>M(DEFAULT.height)+.002:true;row.flushOffsetMm=box?Math.round((box.min.y*1000-finish)*10)/10:null;
 row.installationHeightMatch=box!==null&&Math.abs(row.flushOffsetMm+1)<.1&&box.max.y<=M(DEFAULT.height)+.002;
 const origin=new THREE.Vector3(wx(f.cx),M(finish)-.5,wz(f.cy)),ray=new THREE.Raycaster(origin,new THREE.Vector3(0,1,0),0,.6);const hits=ray.intersectObjects(scene.children,true).filter(h=>{let o=h.object;while(o){if(!o.visible)return false;o=o.parent;}return true;});row.luminousFaceVisible=hits[0]?.object.name==='recessed-luminous-face';row.occluder=row.luminousFaceVisible?null:hits[0]?.object.name||null;
 row.match=row.match&&row.installationHeightMatch&&row.luminousFaceVisible;row.definition='嵌入灯体高度；薄边框低于完成顶面1mm，灯体藏于吊顶内';
 }a.errors=a.rows.filter(r=>!r.match||r.ceilingExceeded);return a;};
Object.assign(window.homeStudio,{validate:fixState,dimensionAudit,recessedLightRevision:RECESSED_LIGHT_REVISION});

// Guard every add path, while leaving existing instances editable and loadable.
const curatedAddItem=addItem;
addItem=function(it,x,y){if(REMOVED_CATALOG_TYPES.has(it[0])){toast('该构件已从组件库移除');return false;}return curatedAddItem(it,x,y);};
Object.assign(window.homeStudio,{getCatalog:()=>structuredClone(availableCatalog()),getRemovedCatalogTypes:()=>[...REMOVED_CATALOG_TYPES]});

// V12 component completion: architectural door presets and owned assemblies.
const ASSEMBLY_REVISION='owned-components-20261005.1';
const DOOR_COMPONENTS={slidingdoor:{label:'推拉门',kind:'sliding',width:1600},doubledoor:{label:'对开门',kind:'door',model:'double',width:1400}};
let pendingDoorComponent=null;
function openingKey(w,o,i){return o.id||w.id+':'+i;}
const DOOR_STYLE_OPTIONS=[['single','普通门'],['double','对开门'],['sliding','推拉门'],['hidden','隐藏门']];
function effectiveDoorOpening(s,w,o,i){const style=s.doorStyles?.[openingKey(w,o,i)];return style&&o.kind!=='window'?{...o,...style}:o;}
const styleSelectedOpening=selectedOpening;selectedOpening=function(sel=ui.sel){const hit=styleSelectedOpening(sel);return hit?{...hit,o:effectiveDoorOpening(state,hit.w,hit.o,hit.index)}:null;};
function doorStateKey(w,o,i){return i===0?w.id:w.id+':'+(o.id||i);}

function armDoorComponent(type){pendingDoorComponent=type;const arm=()=>{setTool('door');pendingDoorComponent=type;syncModeHint();};if(is3D())setView('2d').then(arm);else arm();}
const completedHint=syncModeHint;syncModeHint=function(){completedHint();if(ui.tool==='door'&&pendingDoorComponent){$('#modehint').textContent='点击普通墙或已有可编辑门洞放置'+DOOR_COMPONENTS[pendingDoorComponent].label;$('#modehint').classList.add('show');}};
const completedTool=setTool;setTool=function(t){pendingDoorComponent=null;return completedTool(t);};
function placeDoorComponent(type,p){
 if(previewMode||is3D()&&opt.mode==='walk')return false;
 const preset=DOOR_COMPONENTS[type],hit=nearestWall(p);if(!hit){armDoorComponent(type);toast('请选择普通墙或可编辑门洞');return false;}const {w,at,l}=hit;
 if(w.bearing){toast('承重墙及原有洞口已锁定');return false;}
 const existing=w.opens.find(o=>o.kind!=='window'&&at>=o.at-30&&at<=o.at+o.width+30);
 let opening,index;
 const ok=mutate(()=>{
  if(existing){opening=existing;Object.assign(opening,{kind:preset.kind,doorModel:preset.model||'sliding',label:preset.label,height:opening.height||2100,swing:opening.swing||1,angle:opening.angle||90,leaves:2,slideOpen:0,slideDirection:1});}
  else{const ranges=[];let start=0;for(const o of [...w.opens].sort((a,b)=>a.at-b.at)){ranges.push([start,o.at]);start=o.at+o.width;}ranges.push([start,l]);const range=ranges.find(([a,b])=>at>=a&&at<=b);if(!range||range[1]-range[0]<preset.width+40)throw Error('这一段墙没有足够位置，请调整门宽或选择另一段墙');opening={id:uid(),kind:preset.kind,doorModel:preset.model||'sliding',label:preset.label,at:Math.max(range[0]+20,Math.min(range[1]-preset.width-20,Math.round((at-preset.width/2)/10)*10)),width:preset.width,height:2100,swing:1,hingeEnd:'start',angle:90,leaves:2,slideOpen:0,slideDirection:1};w.opens.push(opening);}
  clearOpeningDoorPose(w.id);index=w.opens.indexOf(opening);
 });
 if(ok){setTool('select');select(openingSelection(w,index));}return ok;
}
const completedOpeningAdd=addOpeningAt;addOpeningAt=function(p,kind){return kind==='door'&&pendingDoorComponent?placeDoorComponent(pendingDoorComponent,p):completedOpeningAdd(p,kind);};
const completedSymbol=furnSVG;furnSVG=function(t,w,d,c,f={}){
 const stroke='stroke="#666158" stroke-width="1.2" vector-effect="non-scaling-stroke"';
 if(t==='boiler')return `<rect x="${-w/2}" y="${-d/2}" width="${w}" height="${d}" rx="30" fill="#f2f1ed" ${stroke}/><rect x="${-w*.28}" y="${d*.12}" width="${w*.56}" height="${d*.2}" rx="10" fill="#53625f" ${stroke}/><circle cx="${w*.32}" cy="${d*.24}" r="${w*.035}" fill="#b4a086"/>`;
 if(t==='slidingdoor')return `<rect x="${-w/2}" y="${-d/2}" width="${w*.55}" height="${d}" fill="#e6eff1" ${stroke}/><rect x="${-w*.05}" y="${-d/2}" width="${w*.55}" height="${d}" fill="#e6eff1" ${stroke}/><path d="M${-w*.1} ${-d*.1}v${d*.2}M${w*.1} ${-d*.1}v${d*.2}" ${stroke}/>`;
 if(t==='doubledoor')return `<rect x="${-w/2}" y="${-d/2}" width="${w}" height="${d}" fill="${c}" ${stroke}/><path d="M0 ${-d/2}v${d}M${-w*.08} ${-d*.06}v${d*.12}M${w*.08} ${-d*.06}v${d*.12}" ${stroke}/>`;
 return completedSymbol(t,w,d,c,f);
};
function mountBoilerAt(f,p){let best=null;for(const w of state.walls){if(w.demolished)continue;const {u,n,len}=wallAxes(w),along=(p.x-w.a[0])*u[0]+(p.y-w.a[1])*u[1],sign=(p.x-w.a[0])*n[0]+(p.y-w.a[1])*n[1]>=0?1:-1;
 for(const [a,b]of intervals(w)){if(b-a<f.w+40)continue;const at=Math.max(a+f.w/2+20,Math.min(b-f.w/2-20,along)),cx=w.a[0]+u[0]*at+n[0]*sign*(w.t/2+f.d/2),cy=w.a[1]+u[1]*at+n[1]*sign*(w.t/2+f.d/2),dist=Math.hypot(cx-p.x,cy-p.y);if(!best||dist<best.dist)best={cx,cy,rot:norm(Math.atan2(u[1],u[0])*180/Math.PI+(sign<0?180:0)),dist,wallId:w.id};}}
 if(best)Object.assign(f,{cx:Math.round(best.cx),cy:Math.round(best.cy),rot:best.rot,wallId:best.wallId});return f;}
const completedAdd=addItem;addItem=function(it,x,y){if(DOOR_COMPONENTS[it[0]]){toast('请选择门洞，在右侧切换门型');return false;}if(it[0]!=='boiler')return completedAdd(it,x,y);
 const f=F('boiler','壁挂炉',Math.round(x/10)*10,Math.round(y/10)*10,it[2],it[3],0,currentStyle().palette.cabinet||'#f1eee8');Object.assign(f,{h:720,elevation:1300,mount:'wall',catalogKey:LIB.flatMap((g,ci)=>g.items.flatMap((v,ii)=>v===it?[ci+':'+ii]:[]))[0]});mountBoilerAt(f,{x,y});ui.sel={kind:'furn',id:f.id};return mutate(()=>state.furniture.push(f));
};
const completedModel=buildFurniture;buildFurniture=function(f){
 if(f.type!=='boiler'){const g=completedModel(f);if(f.assemblyOwner){g.userData.assemblyOwner=f.assemblyOwner;g.traverse(o=>{if(o.isMesh)o.userData.assemblyOwner=f.assemblyOwner;});}return g;}
 const g=new THREE.Group(),w=M(f.w),d=M(f.d),h=M(f.h),shell=surfaceMaterial(f.color,'lacquer'),dark=mat('#53625f',{roughness:.5}),steel=metal();
 g.add(box(w,h*.82,d,shell,0,h*.18),box(w*.7,h*.14,.014,dark,0,h*.26,d/2+.006));
 for(const a of [-.28,-.14,0,.14,.28])g.add(cyl(Math.min(.014,w*.025),Math.min(.014,w*.025),h*.18,steel,w*a,0,0));
 [-.24,.24].forEach(x=>g.add(cyl(w*.035,w*.035,.014,steel,w*x,h*.35,d/2+.02)));
 g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-f.rot*Math.PI/180;g.userData={fid:f.id,caseHeight:f.h,mount:'wall'};return g;
};
function slidePanelPositions(rect,o={}){const [x0,y0,x1,y1]=rect,v=y1-y0>x1-x0,L=v?y1-y0:x1-x0,n=o.leaves===3?3:2,pw=L/n+Math.min(30,L*.02),open=Math.max(0,Math.min(1,o.slideOpen||0)),dir=o.slideDirection===-1?-1:1;return Array.from({length:n},(_,i)=>{const closed=-L/2+L*(i+.5)/n,target=dir*(L/2-pw/2);return{cx:(x0+x1)/2+(v?(i-(n-1)/2)*35:closed+(target-closed)*open),cy:(y0+y1)/2+(v?closed+(target-closed)*open:(i-(n-1)/2)*35),w:v?30:pw,d:v?pw:30,pw,v};});}
function renderSlidingPlan(slide){const hit=selectedOpening(slide.opening),o=hit?.o||{},stroke='stroke="#4f7394" stroke-width="1" vector-effect="non-scaling-stroke"';return slidePanelPositions(slide.rect,o).map(p=>`<rect x="${p.cx-p.w/2}" y="${p.cy-p.d/2}" width="${p.w}" height="${p.d}" fill="#eaf1f3" ${stroke}/>`).join('');}
function buildSliding3D(slide,top){const o=selectedOpening(slide.opening)?.o||{},g=new THREE.Group(),h=Math.min(M(o.height||2100),top);g.userData={opening:slide.opening,productionOpeningKind:'sliding'};
 for(const p of slidePanelPositions(slide.rect,o)){const leaf=new THREE.Group(),w=M(p.pw),glass=box(w,h,.018,glassMat,0,0,0);leaf.add(glass);[0,h-.04].forEach(y=>leaf.add(box(w,.04,.035,frameMat,0,y)));[-1,1].forEach(s=>leaf.add(box(.035,h,.035,frameMat,s*(w/2-.0175))));leaf.position.set(wx(p.cx),0,wz(p.cy));leaf.rotation.y=p.v?-Math.PI/2:0;leaf.userData.opening=slide.opening;leaf.userData.slidingLeaf=true;g.add(leaf);}return g;}
const completedGeometry=syncGeometry;syncGeometry=function(){completedGeometry();const doorsBefore=[...DOORS];DOORS.length=0;for(const d of doorsBefore){const hit=selectedOpening(d.opening);d.height=hit?.o.height||2100;if(hit?.o.doorModel==='hidden'){const {w,o}=hit,p=doorPose(w,o);d.hiddenLeaf=true;d.h=p.nominalHinge.map((v,i)=>v+p.inward[i]*(w.t/2-20)+p.closed[i]*25);}if(hit?.o.doorModel!=='double'){DOORS.push(d);continue;}const {w,o}=hit,ratio=o.leafRatio??.5;for(const [side,start,width]of [['start',o.at,o.width*ratio],['end',o.at+o.width*ratio,o.width*(1-ratio)]]){const p=doorPose(w,{...o,at:start,width,hingeEnd:side});DOORS.push({...d,h:p.hinge,c:p.closed,o:p.leaf,len:width-25,secondLeaf:side==='end',doubleLeaf:true});}}};
const completedOpeningPanel=openingPanel;openingPanel=function(hit){const {w,o}=hit,locked=w.bearing;let html=completedOpeningPanel(hit);if(o.kind==='window')return html+`<section><h3>收口</h3><label><input type="checkbox" data-opening-finish="trim" ${o.finishOptions?.trim!==false?'checked':''} ${locked?'disabled':''}> 窗套</label></section>`;
 const mode=o.kind==='sliding'?'sliding':o.doorModel==='double'?'double':o.doorModel==='hidden'?'hidden':'single';
 const choices=`<section class="door-style-section"><h3>门型</h3><div class="door-style-options" role="group" aria-label="门型选择">${DOOR_STYLE_OPTIONS.map(([k,n])=>`<button type="button" class="btn door-style-choice" data-door-style="${k}" aria-pressed="${mode===k}">${n}${mode===k?'<span aria-hidden="true">✓</span>':''}</button>`).join('')}</div></section>`;
 const controls=`<label>门高 / mm<input type="number" id="openingHeight" value="${o.height||2100}" min="1800" max="2500" ${locked?'disabled':''}></label>`;
 html=choices+html.replace('<div class="form">','<div class="form">'+controls).replace(' · 锁定',' · 尺寸锁定');
 if(mode==='double')html=html.replace(/<label>门轴[\s\S]*?<\/label>/,'')+`<section><label>左扇占比<input id="openingRatio" type="number" min="30" max="70" value="${Math.round((o.leafRatio??.5)*100)}" > %</label></section>`;
 if(mode==='sliding')html+=`<section><div class="form"><label>门扇<select id="openingLeaves"><option value="2" ${o.leaves!==3?'selected':''}>双扇</option><option value="3" ${o.leaves===3?'selected':''}>三扇</option></select></label><label>滑动方向<select id="openingSlideDirection"><option value="1" ${o.slideDirection!==-1?'selected':''}>终点侧</option><option value="-1" ${o.slideDirection===-1?'selected':''}>起点侧</option></select></label><label class="full">开启程度<input id="openingSlideOpen" type="range" min="0" max="100" value="${Math.round((o.slideOpen||0)*100)}"></label></div></section>`;
 if(mode==='hidden')return html+`<section><p class="scene-mode-note">与墙面同色，无外露门套。</p><button type="button" class="btn" id="hiddenDoorToggle">${state.doors[doorStateKey(w,o,hit.index)]===false?'开门':'关门'}</button></section>`;
 return html+`<section><h3>收口</h3>${[['trim','门套'],['threshold','门槛石'],['transition','过渡条']].map(([k,n])=>`<label style="display:block"><input type="checkbox" data-opening-finish="${k}" ${o.finishOptions?.[k]!==false&&(k!=='transition'||o.finishOptions?.[k])?'checked':''} ${locked?'disabled':''}> ${n}</label>`).join('')}</section>`;
};
function updateOpeningDecoration(hit,fn,style=null){return mutate(()=>{const doorKey=doorStateKey(hit.w,hit.o,hit.index),open=state.doors[doorKey];const raw=hit.w.opens[hit.index];if(hit.w.bearing){state.doorStyles=state.doorStyles||{};const key=openingKey(hit.w,raw,hit.index),next={kind:hit.o.kind,doorModel:hit.o.kind==='sliding'?'sliding':hit.o.doorModel||'single',...Object.fromEntries(['label','leaves','slideOpen','slideDirection','leafRatio','swing','hingeEnd','angle','finishOptions'].filter(k=>hit.o[k]!==undefined).map(k=>[k,hit.o[k]])),...(state.doorStyles[key]||{})};fn(next);state.doorStyles[key]=next;}else fn(raw);clearOpeningDoorPose(hit.w.id);if(style==='hidden')state.doors[doorKey]=false;else if(!style&&open!==undefined)state.doors[doorKey]=open;});}
function changeOpeningDoorStyle(mode,hit=selectedOpening()){
 if(!hit||hit.o.kind==='window'||!DOOR_STYLE_OPTIONS.some(([k])=>k===mode)||previewMode||switching||is3D()&&opt.mode==='walk')return false;
 if(mode===(hit.o.kind==='sliding'?'sliding':hit.o.doorModel||'single'))return true;
 return updateOpeningDecoration(hit,o=>{o.kind=mode==='sliding'?'sliding':'door';o.doorModel=mode;o.label=Object.fromEntries(DOOR_STYLE_OPTIONS)[mode];o.leaves=o.leaves||2;if(mode==='double')o.leafRatio=o.leafRatio||.5;o.swing=o.swing||hit.o.swing||1;o.hingeEnd=o.hingeEnd||hit.o.hingeEnd||'start';o.angle=o.angle||hit.o.angle||90;},mode);
}
const completedOpeningBind=bindOpeningPanel;bindOpeningPanel=function(hit){completedOpeningBind(hit);
 const update=(fn,style=null)=>updateOpeningDecoration(hit,fn,style);
 document.querySelectorAll('[data-door-style]').forEach(b=>b.onclick=()=>changeOpeningDoorStyle(b.dataset.doorStyle,hit));
 for(const [id,key,number]of [['openingHinge','hingeEnd',false],['openingSwing','swing',true],['openingAngle','angle',true]]){const el=$('#'+id);if(el){el.disabled=false;el.onchange=e=>update(o=>o[key]=number?Number(e.target.value):e.target.value);}}
 for(const [id,key,div]of [['openingHeight','height',1],['openingRatio','leafRatio',100],['openingLeaves','leaves',1],['openingSlideDirection','slideDirection',1],['openingSlideOpen','slideOpen',100]])$('#'+id)?.addEventListener('change',e=>update(o=>o[key]=Number(e.target.value)/div));
 document.querySelectorAll('[data-opening-finish]').forEach(el=>el.onchange=()=>update(o=>{o.finishOptions={...o.finishOptions,[el.dataset.openingFinish]:el.checked};}));
 $('#hiddenDoorToggle')?.addEventListener('click',()=>mutate(()=>{const key=doorStateKey(hit.w,hit.o,hit.index);state.doors[key]=state.doors[key]===false;}));
};

// Derived accessories are owned by a furniture object, opening or room.
const MERGED_TYPES=new Set(['endpanel','fridgecab','cabinetlight','backsplash','curtainrail','doortrim','windowtrim','threshold','transition','skirting']);
function syncOwnedAssemblies(s){
 const first=s.assemblyRevision!==ASSEMBLY_REVISION,existing=s.furniture,base=existing.filter(f=>!f.assemblyOwner);
 const nearest=(f,types)=>base.filter(p=>types.includes(p.type)).sort((a,b)=>Math.hypot(a.cx-f.cx,a.cy-f.cy)-Math.hypot(b.cx-f.cx,b.cy-f.cy))[0];
 if(first){for(const f of base){if(!MERGED_TYPES.has(f.type))continue;
  const owner=nearest(f,f.type==='fridgecab'||f.type==='endpanel'?['fridge']:f.type==='cabinetlight'?['wallcab']:f.type==='backsplash'?['counter']:f.type==='curtainrail'?['curtain','rollerblind']:[]);
  if(owner&&Math.hypot(owner.cx-f.cx,owner.cy-f.cy)<2500){owner.assemblyOptions={...owner.assemblyOptions};if(f.type==='fridgecab'||f.type==='endpanel'){owner.assemblyOptions.enclosure=true;if(f.type==='fridgecab')owner.assemblyOptions.upperGap=Math.max(50,f.elevation-(owner.elevation||0)-(owner.h||1800));}if(f.type==='cabinetlight')owner.assemblyOptions.workLight=true;if(f.type==='backsplash')owner.assemblyOptions.backsplash=true;if(f.type==='curtainrail')owner.assemblyOptions.rail=true;}
 }}
 // One-time replacement of legacy generated trim pieces; custom unattached accessories remain.
 const roots=base.filter(f=>!MERGED_TYPES.has(f.type));
 const parts=[],add=(owner,role,type,props)=>{const spec=RENOVATION_MAP[type];const color=props.color||spec&&getStyle(s.style).palette[spec.role]||getStyle(s.style).palette.cabinet;parts.push({id:'A12:'+owner.kind+':'+(owner.id||owner.openingId)+':'+role,type,name:props.name||({endpanel:'柜侧板',fridgecab:'冰箱上柜'}[type])||spec?.name,w:100,d:30,h:80,elevation:0,cx:0,cy:0,rot:0,color,mount:spec?.mount||'floor',assemblyOwner:owner,assemblyRole:role,source:'随主体自动生成',...props});};
 const local=(p,x,y)=>{const a=p.rot*Math.PI/180;return{cx:p.cx+x*Math.cos(a)-y*Math.sin(a),cy:p.cy+x*Math.sin(a)+y*Math.cos(a),rot:p.rot};};
 for(const p of roots){
  const options=p.assemblyOptions||{},owner={kind:'furn',id:p.id},ceil=finishedCeiling(p,s);
  if(p.type==='fridge'&&options.enclosure){const t=20,gap=Number.isFinite(options.upperGap)?options.upperGap:150,bottom=(p.elevation||0)+(p.h||1800)+gap;if(bottom>=ceil-50)throw Error('冰箱上柜没有足够空间，请减小机身高度或上方间距');
   for(const sign of [-1,1])add(owner,'side'+sign,'endpanel',{...local(p,sign*(p.w/2+t/2),0),w:t,d:p.d,h:ceil,elevation:0,color:getStyle(s.style).palette.cabinet});
   if(bottom<ceil-50)add(owner,'upper','fridgecab',{...local(p,0,0),w:p.w,d:p.d,h:ceil-bottom,elevation:bottom,color:getStyle(s.style).palette.cabinet});
  }
  if(['wardrobe','bookshelf','counter','wallcab','cabinet','ovencol'].includes(p.type)&&options.sidePanels){for(const sign of [-1,1])add(owner,'side'+sign,'endpanel',{...local(p,sign*(p.w/2+10),0),w:20,d:p.d,h:p.h||850,elevation:p.elevation||0,color:p.color});}
  if(p.type==='wallcab'&&options.workLight){add(owner,'light','cabinetlight',{...local(p,0,p.d*.35),w:Math.max(50,p.w-60),d:30,h:20,elevation:Math.max(0,(p.elevation||1800)-20),lightOn:true,lightIntensity:2,lightTemperature:3000});}
  if(p.type==='counter'&&options.backsplash)add(owner,'backsplash','backsplash',{...local(p,0,-p.d/2+15),w:p.w,d:30,h:80,elevation:(p.elevation||0)+(p.h||900),color:getStyle(s.style).palette.stone});
  if(['curtain','rollerblind'].includes(p.type)&&options.rail!==false)add(owner,'rail','curtainrail',{...local(p,0,0),w:p.w,d:60,h:35,elevation:Math.min(ceil-35,(p.elevation||0)+p.h)});
 }
 for(const w of s.walls){if(w.demolished)continue;const {len:l,u,n}=wallAxes(w),rot=Math.atan2(u[1],u[0])*180/Math.PI;
  w.opens.forEach((raw,i)=>{const o=effectiveDoorOpening(s,w,raw,i);const key=openingKey(w,o,i),owner={kind:'opening',wallId:w.id,openingId:key,index:i},cx=w.a[0]+u[0]*(o.at+o.width/2),cy=w.a[1]+u[1]*(o.at+o.width/2),opts=o.finishOptions||{};
   if(o.kind==='window'){if(opts.trim!==false){
    const original=CASE.initialState.walls.find(v=>v.id===w.id)?.opens[i],baselineTrim=CASE.initialState.furniture.find(f=>f.type==='windowtrim'&&f.assemblyOwner?.wallId===w.id&&f.assemblyOwner?.index===i);
    const sameOpening=original&&['kind','at','width','height','sillHeight'].every(k=>original[k]===raw[k]);
    const preserve=CASE.presentation?.preserveImportedOpeningTrim&&sameOpening&&baselineTrim;
    add(owner,'trim','windowtrim',{cx,cy,rot,openingId:w.id,w:o.width+70,d:w.t+30,h:preserve?baselineTrim.h:(o.height||1350)+80,elevation:preserve?baselineTrim.elevation:Math.max(0,(o.sillHeight??850)-40)});
   }}
   else{if(o.doorModel==='hidden')return;if(opts.trim!==false)add(owner,'trim','doortrim',{cx,cy,rot,openingId:i===0?w.id:w.id+':'+(o.id||i),w:o.width+70,d:w.t+40,h:(o.height||2100)+50});if(opts.threshold!==false)add(owner,'threshold','threshold',{cx,cy,rot,openingId:i===0?w.id:w.id+':'+(o.id||i),w:o.width,d:w.t,h:15});if(opts.transition)add(owner,'transition','transition',{cx,cy,rot,w:o.width,d:30,h:15});}
  });
  for(const sign of [-1,1]){
   let spans=intervals(w);
   // Fixed joinery meets the finished wall; trim must not occupy its contact face.
   for(const f of roots.filter(f=>f.builtIn&&f.fixedToWalls&&f.attachedWallIds?.includes(w.id))){
    const side=(f.cx-w.a[0])*n[0]+(f.cy-w.a[1])*n[1];if(side*sign<=0)continue;
    const projection=([-1,1].flatMap(x=>[-1,1].map(y=>(f.cx+x*f.w/2-w.a[0])*u[0]+(f.cy+y*f.d/2-w.a[1])*u[1])));
    const start=Math.min(...projection),end=Math.max(...projection);
    spans=spans.flatMap(([a,b])=>end<=a||start>=b?[[a,b]]:[[a,Math.min(b,start)],[Math.max(a,end),b]].filter(([x,y])=>y-x>0));
   }
   for(const [a,b]of spans){if(b-a<90)continue;const cx=w.a[0]+u[0]*(a+b)/2+n[0]*sign*(w.t/2+16),cy=w.a[1]+u[1]*(a+b)/2+n[1]*sign*(w.t/2+16),room=ROOMS.find(r=>inPolygon([cx,cy],r.poly));if(room&&s.rooms[room.id].skirting!==false)add({kind:'room',id:room.id},w.id+':'+a+':'+sign,'skirting',{cx,cy,rot,w:b-a-30,d:30,h:80,wallId:w.id,roomId:room.id});}
  }
 }
 s.furniture=[...roots,...parts];s.assemblyRevision=ASSEMBLY_REVISION;return s;
}
const assembledAnchor=syncCeilingAnchors;syncCeilingAnchors=function(s){assembledAnchor(s);return syncOwnedAssemblies(s);};
const assembledDefault=defaultState,assembledFix=fixState;defaultState=()=>syncCeilingAnchors(assembledDefault());fixState=s=>assembledFix(syncCeilingAnchors(structuredClone(s)));state=fixState(state);
const assembledRenderFurn=renderFurn;renderFurn=function(){syncCeilingAnchors(state);assembledRenderFurn();for(const el of $('#gFurn').children)if(getF(el.dataset.fid)?.assemblyOwner)el.style.pointerEvents='none';};
const assembledGeometry=syncGeometry;syncGeometry=function(){syncCeilingAnchors(state);return assembledGeometry();};
const assembledSelect=select;select=function(sel,opts){if(sel?.kind==='furn'){const owner=getF(sel.id)?.assemblyOwner;if(owner){if(owner.kind==='opening'){const w=state.walls.find(w=>w.id===owner.wallId),i=w?.opens.findIndex((o,i)=>openingKey(w,o,i)===owner.openingId);sel=i>=0?openingSelection(w,i):null;}else sel=owner;}}return assembledSelect(sel,opts);};
const assembledPanel=furnPanel;furnPanel=function(f){let html=assembledPanel(f),options=f.assemblyOptions||{},fields=[];
 if(f.type==='fridge')fields.push(['enclosure','侧板与到顶上柜']);if(['wardrobe','bookshelf','counter','wallcab','cabinet','ovencol'].includes(f.type))fields.push(['sidePanels','外侧封板']);if(f.type==='wallcab')fields.push(['workLight','柜底灯']);if(f.type==='counter')fields.push(['backsplash','挡水条']);if(['curtain','rollerblind'].includes(f.type))fields.push(['rail','窗帘轨道']);
 if(fields.length)html+=`<section><h3>组合</h3>${fields.map(([k,n])=>`<label style="display:block;margin-bottom:6px"><input type="checkbox" data-assembly-option="${k}" ${(k==='rail'?options[k]!==false:options[k])?'checked':''}> ${n}</label>`).join('')}${f.type==='fridge'&&options.enclosure?`<label>上柜与机身间距 / mm<input id="assemblyUpperGap" type="number" min="50" max="800" value="${options.upperGap??150}"></label>`:''}</section>`;
 if(f.type==='boiler')html+=`<section><h3>安装</h3><p class="scene-mode-note">壁挂式；宽深高及离地可编辑，尺寸按所选产品设置。</p></section>`;return html;};
const assembledBind=bindFurnPanel;bindFurnPanel=function(f){assembledBind(f);document.querySelectorAll('[data-assembly-option]').forEach(el=>el.onchange=()=>mutate(()=>{const g=getF(f.id);g.assemblyOptions={...g.assemblyOptions,[el.dataset.assemblyOption]:el.checked};}));$('#assemblyUpperGap')?.addEventListener('change',e=>mutate(()=>{const n=Number(e.target.value);if(!Number.isFinite(n)||n<50||n>800)throw Error('间距须在 50–800 mm 之间');getF(f.id).assemblyOptions.upperGap=n;}));};
const assembledRoomPanel=roomPanel,assembledBindRoom=bindRoomPanel;roomPanel=function(r){return assembledRoomPanel(r)+`<section><label><input id="roomSkirting" type="checkbox" ${state.rooms[r.id].skirting!==false?'checked':''}> 踢脚线</label></section>`;};bindRoomPanel=function(){assembledBindRoom();const id=ui.sel.id;$('#roomSkirting').onchange=e=>mutate(()=>state.rooms[id].skirting=e.target.checked);};
const assembledDuplicate=duplicateSel;duplicateSel=function(){const f=ui.sel?.kind==='furn'?getF(ui.sel.id):null;if(!f?.assemblyOptions)return assembledDuplicate();const n=structuredClone(f);n.id=uid();n.cx+=200;n.cy+=200;ui.sel={kind:'furn',id:n.id};return mutate(()=>state.furniture.push(n));};
function validateDoorStyles(s){if(s.doorStyles===undefined)return;if(!s.doorStyles||Array.isArray(s.doorStyles)||typeof s.doorStyles!=='object')throw Error('门型数据无效');
 for(const [key,o]of Object.entries(s.doorStyles)){let aperture;for(const w of s.walls||[])w.opens.forEach((raw,i)=>{if(openingKey(w,raw,i)===key&&raw.kind!=='window')aperture=raw;});if(!aperture||!o||typeof o!=='object'||Object.keys(o).some(k=>!['kind','doorModel','label','leaves','slideOpen','slideDirection','leafRatio','swing','hingeEnd','angle','finishOptions'].includes(k)))throw Error('门型配置必须对应已有门洞');
 if(!['single','double','sliding','hidden'].includes(o.doorModel)||o.kind!==(o.doorModel==='sliding'?'sliding':'door'))throw Error('门型配置无效');
 if(o.doorModel==='double'&&(aperture.width<600||!Number.isFinite(o.leafRatio??.5)||(o.leafRatio??.5)<.3||(o.leafRatio??.5)>.7))throw Error('对开门门扇比例无效');
 if(o.kind==='sliding'&&(![2,3].includes(o.leaves||2)||aperture.width<(o.leaves||2)*300||!Number.isFinite(o.slideOpen??0)||(o.slideOpen??0)<0||(o.slideOpen??0)>1||![1,-1].includes(o.slideDirection??1)))throw Error('推拉门配置无效');
 if(![1,-1].includes(o.swing||1)||!['start','end',undefined].includes(o.hingeEnd)||!Number.isFinite(o.angle??90)||(o.angle??90)<5||(o.angle??90)>100)throw Error('门轴和开启方向无效');
 }}
const doorStyleFix=fixState;fixState=function(input){validateDoorStyles(input);return doorStyleFix(input);};state=fixState(state);
Object.assign(window.homeStudio,{validate:fixState,select,deleteSelected:()=>deleteSel(),getAssemblies:()=>structuredClone(state.furniture.filter(f=>f.assemblyOwner)),placeDoorComponent,armDoorComponent,assemblyRevision:ASSEMBLY_REVISION});

// Door choices remain visible beside the selected opening even with properties collapsed.
const doorShortcutFab=renderFab;
renderFab=function(){
 doorShortcutFab();
 const fab=$('#fab'),hit=selectedOpening(),show=!!hit&&hit.o.kind!=='window'&&!previewMode&&(!is3D()||opt.mode!=='walk');
 fab.classList.toggle('door-style-fab',show);
 if(!show)return;
 const mode=hit.o.kind==='sliding'?'sliding':hit.o.doorModel||'single';
 fab.innerHTML=`<div class="door-style-options" role="group" aria-label="门型选择">${DOOR_STYLE_OPTIONS.map(([k,n])=>`<button type="button" class="btn door-style-choice" data-door-quick="${k}" aria-pressed="${mode===k}">${n}${mode===k?'<span aria-hidden="true">✓</span>':''}</button>`).join('')}</div>${deletionAllowed()?'<div class="door-shortcut-actions"><button type="button" class="btn danger" data-context="delete">删除</button></div>':''}`;
 fab.setAttribute('aria-label','门型与操作');
 fab.querySelectorAll('[data-door-quick]').forEach(b=>b.onclick=()=>changeOpeningDoorStyle(b.dataset.doorQuick));
 fab.querySelector('[data-context="delete"]')?.addEventListener('click',deleteSel);
 positionObjectMenu();
};

// Three mutually exclusive 2D drawings use the same editable plan data.
const PLAN_DRAWING_KEY=STORE+':drawing-mode';
let planDrawingMode=(()=>{try{const v=localStorage.getItem(PLAN_DRAWING_KEY);return ['structure','furniture','hard'].includes(v)?v:'furniture';}catch{return 'furniture';}})();
function hardPlanItem(f){if(f?.planPoint||['laundrycab','laundrypower','waterinlet','drainoutlet'].includes(f?.type))return true;return !!f&&!UNNECESSARY_DISPLAY_TYPES.has(f.type)&&!['curtain','rollerblind','tablelamp','fridgecab','endpanel'].includes(f.type)&&(constructionDetail(f)||['hood','boiler','waterheater'].includes(f.type));}
function planItemVisible(f){if(f?.laundryOwner&&(f.planPoint||['laundrypower','waterinlet','drainoutlet'].includes(f.type)))return false;if(f?.planPoint||['laundrypower','waterinlet','drainoutlet'].includes(f?.type))return planDrawingMode==='hard';if(!f||UNNECESSARY_DISPLAY_TYPES.has(f.type))return false;return planDrawingMode==='structure'?false:planDrawingMode==='hard'?hardPlanItem(f):(!constructionDetail(f)||['curtain','rollerblind','tablelamp'].includes(f.type))&&!!ui.layers.furn;}
function applyPlanDrawingLayers(){
 document.body.dataset.drawingMode=planDrawingMode;
 const group=$('#gFurn');group.setAttribute('display',planDrawingMode==='hard'||planDrawingMode==='furniture'&&ui.layers.furn?'inline':'none');group.style.opacity='';
 for(const el of group.children){const f=getF(el.dataset.fid),shown=planItemVisible(f)&&!(planDrawingMode==='hard'&&TOP_TYPES.has(f?.type));el.style.display=shown?'':'none';el.style.opacity='';}
 for(const el of $('#gRooms').querySelectorAll('[data-floor-connection]')){const c=FLOOR_CONNECTIONS.find(c=>c.id===el.dataset.floorConnection);el.setAttribute('fill',planDrawingMode==='furniture'?`url(#m-${connectionMat(c)})`:planDrawingMode==='hard'?(finishPalette().ceiling||'#faf8f3'):'#faf8f3');}
 for(const el of $('#gRooms').querySelectorAll('.room')){const r=el.dataset.room;el.setAttribute('fill',planDrawingMode==='furniture'?`url(#m-${state.rooms[r].mat})`:planDrawingMode==='hard'?(finishPalette().ceiling||'#faf8f3'):'#faf8f3');}
 $('#gLabels').style.opacity='';
 for(const el of $('#gLabels').querySelectorAll('text'))el.style.display=planDrawingMode==='hard'&&el.textContent.includes('m²')?'none':'';
 // Furniture and hard-finish drawings both show the complete door swing symbol.
 for(const el of $('#gOpen').querySelectorAll('path[stroke-dasharray]'))el.style.display='';
}
function syncPlanDrawingUI(){
 document.querySelectorAll('[data-plan-drawing]').forEach(b=>{const on=b.dataset.planDrawing===planDrawingMode;b.classList.toggle('on',on);b.setAttribute('aria-pressed',String(on));b.disabled=switching;});
}
function setPlanDrawingMode(mode){
 if(!['structure','furniture','hard'].includes(mode)||switching)return;
 planDrawingMode=mode;try{localStorage.setItem(PLAN_DRAWING_KEY,mode);}catch{}
 if(!is3D()&&ui.sel?.kind==='furn'&&!planItemVisible(getF(ui.sel.id)))select(null);
 renderAll();syncPlanDrawingUI();
}
const drawingQuickSync=syncQuickActions;syncQuickActions=function(){drawingQuickSync();syncPlanDrawingUI();};
const drawingRooms=renderRooms;renderRooms=function(){drawingRooms();applyPlanDrawingLayers();};
const drawingLabels=renderLabels;renderLabels=function(){drawingLabels();applyPlanDrawingLayers();};
const drawingSelection=select;select=function(sel,opts){if(!is3D()&&sel?.kind==='furn'&&!planItemVisible(getF(sel.id)))sel=null;return drawingSelection(sel,opts);};
// Adding an object always reveals the drawing where that object can be edited.
const drawingAdd=addItem;addItem=function(it,x,y){if(!is3D()&&!REMOVED_CATALOG_TYPES.has(it[0])){const mode=hardPlanItem({type:it[0]})?'hard':'furniture';if(mode!==planDrawingMode)setPlanDrawingMode(mode);}return drawingAdd(it,x,y);};
const drawingTopToggle=setTopView;setTopView=function(v){if(!is3D())return setPlanDrawingMode(v?'hard':'furniture');return drawingTopToggle(v);};
document.querySelectorAll('[data-plan-drawing]').forEach(b=>b.onclick=()=>setPlanDrawingMode(b.dataset.planDrawing));
Object.assign(window.homeStudio,{select,setPlanDrawingMode,getPlanDrawingMode:()=>planDrawingMode,setTopView,getTopView:()=>is3D()?topView:planDrawingMode==='hard'});

// Confirmed layout: living perimeter and small circulation ceiling zones.
Object.assign(window.homeStudio,{validate:fixState,finishedCeiling:(id)=>finishedCeiling(getF(id)),getCeilingZones:()=>structuredClone(state.ceilings)});

// Balcony laundry zone: equipment/cabinet in layout, utilities in hard plan only.
const LAUNDRY_POINT_TYPES=new Set(['laundrypower','waterinlet','drainoutlet']);
const laundryFix=fixState;fixState=function(input){for(const f of input.furniture||[])if(f.type==='laundrycab'&&(f.w<800||f.d<680||f.h<920))throw Error('洗衣机柜至少800×680×920 mm');return laundryFix(input);};state=fixState(state);
furnitureLabelNames.laundrycab='洗衣机柜';
const laundrySymbol=furnSVG;
furnSVG=function(t,w,d,c,f={}){
 const S='stroke="#666158" stroke-width="1.1" vector-effect="non-scaling-stroke"';
 if(t==='laundrycab'){
  const k=typeof view==='undefined'?16:1/view.s,label=f.id?`<g data-laundry-label transform="rotate(${-f.rot})"><text text-anchor="middle" y="${-4*k}" font-size="${10*k}" fill="#49443c" stroke="#fffdf8" stroke-width="${2.5*k}" paint-order="stroke" pointer-events="none">洗衣机</text><text text-anchor="middle" y="${8*k}" font-size="${10*k}" fill="#49443c" stroke="#fffdf8" stroke-width="${2.5*k}" paint-order="stroke" pointer-events="none">柜</text></g>`:'';
  if(f.id&&planDrawingMode==='hard')return `<rect x="${-w/2}" y="${-d/2}" width="${w}" height="${d}" fill="none" stroke="#9b9387" stroke-width="1" stroke-dasharray="4 3" vector-effect="non-scaling-stroke"/>${label}`;
  const left=-w/2+18,center=left+330,divider=left+660;
  return `<rect x="${-w/2}" y="${-d/2}" width="${w}" height="${d}" rx="16" fill="${c}" ${S}/><rect x="${center-300}" y="${-d/2+60}" width="600" height="600" rx="20" fill="#edf0ed" ${S}/><path d="M${divider} ${-d/2+18}V${d/2-18}" ${S}/><rect x="${-w/2}" y="${d/2-20}" width="${w}" height="20" fill="#d5cbbd" ${S}/><ellipse cx="${center}" cy="${d/2-80}" rx="120" ry="45" fill="#c7d6d8" ${S}/><g transform="translate(${center} 0)">${label}</g>`;
 }
 if(LAUNDRY_POINT_TYPES.has(t)){
  if(f.laundryOwner)return '';
  if(!f.id)return `<circle r="14" fill="#fffdf8" stroke="${c}" stroke-width="2"/><path d="M-7 0H7M0 -7V7" stroke="${c}" stroke-width="2"/>`;
  const k=typeof view==='undefined'?16:1/view.s,r=Math.max(45,5*k),[lx,ly]=f.labelOffset||[-220,-100],label=t==='laundrypower'?'插座':t==='waterinlet'?'冷水':'排水',color=t==='laundrypower'?'#a77745':t==='waterinlet'?'#4b88ac':'#687b80';
  return `<path data-point-leader d="M0 0L${lx+6*k} ${ly}" stroke="${color}" stroke-width=".8" fill="none" vector-effect="non-scaling-stroke" opacity=".65" pointer-events="none"/><circle data-utility-point r="${r}" fill="#fffdf8" stroke="${color}" stroke-width="1.5" vector-effect="non-scaling-stroke"/><path d="${t==='laundrypower'?`M${-r*.35} ${-r*.35}v${r*.7}M${r*.35} ${-r*.35}v${r*.7}`:t==='waterinlet'?`M${-r*.45} 0H${r*.45}M0 ${-r*.45}V${r*.45}`:`M${-r*.4} ${-r*.4}L${r*.4} ${r*.4}M${r*.4} ${-r*.4}L${-r*.4} ${r*.4}` }" stroke="${color}" stroke-width="1" vector-effect="non-scaling-stroke" pointer-events="none"/><text data-utility-label x="${lx}" y="${ly}" text-anchor="end" dominant-baseline="middle" font-size="${10*k}" fill="${color}" stroke="#fffdf8" stroke-width="${3*k}" paint-order="stroke" pointer-events="none">${f.pointCode||''} ${label} · H${f.elevation||0}</text>`;
 }
 return laundrySymbol(t,w,d,c,f);
};
const laundryModel=buildFurniture;
buildFurniture=function(f){
 if(f.type!=='laundrycab'&&!LAUNDRY_POINT_TYPES.has(f.type))return laundryModel(f);
 const g=new THREE.Group();
 if(LAUNDRY_POINT_TYPES.has(f.type))g.add(box(M(f.w),M(f.h),M(f.d),mat(f.color)));
 else{
  const w=M(f.w),d=M(f.d),h=M(f.h),t=.018,left=-w/2+t,divider=left+.66,body=surfaceMaterial(f.color,'lacquer'),stone=surfaceMaterial(finishPalette().stone,'stone'),edge=metal();
  [-1,1].forEach(side=>g.add(box(t,h-.02,d-.02,body,side*(w/2-t/2),0)));
  g.add(box(w,.02,d,stone,0,h-.02),box(t,h-.02,d-.04,body,divider,0));
  const storage=w/2-t-divider-t/2;if(storage>0){const center=divider+t/2+storage/2;g.add(box(storage,h*.10,d-.04,body,center,0),box(storage,h-.15,.018,body,center,.12,d/2-.018),box(storage*.6,.009,.016,edge,center,h-.14,d/2));}
  const washer=laundryModel({...f,type:'washer',name:'内置洗衣机',w:600,d:600,h:850,elevation:0,rot:0,color:'#e6e8e4'});washer.position.set(left+.33,0,-d/2+.36);washer.rotation.set(0,0,0);washer.userData.embeddedWasher=true;g.add(washer);
  g.userData.washerSizeMm=[600,600,850];g.userData.clearanceMm={bayWidth:660,side:30,rear:60,top:f.h-20-850};
 }
 g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-f.rot*Math.PI/180;Object.assign(g.userData,{fid:f.id,caseHeight:f.h,laundryCabinet:f.type==='laundrycab',utilityPoint:LAUNDRY_POINT_TYPES.has(f.type)});return g;
};
const laundryVisibility=applyTop3D;applyTop3D=function(){laundryVisibility();for(const g of furnG.children){const f=getF(g.userData.fid);if(f?.planPoint||LAUNDRY_POINT_TYPES.has(f?.type))g.visible=false;}};
const laundryPanel=furnPanel;furnPanel=function(f){return laundryPanel(f)+(f.type==='laundrycab'?'<section><h3>柜内设备</h3><p class="scene-mode-note">洗衣机 600×600×850 mm<br>机身两侧各30 mm，背后60 mm；正面外露、底部落地，顶部台面包覆。</p></section>':LAUNDRY_POINT_TYPES.has(f.type)?'<section><h3>洗衣区点位</h3><p class="scene-mode-note">'+esc(f.pointCode||'')+' · 安装高度 '+f.elevation+' mm<br>位于阳台南侧实墙，属于建议定位；线条为标注引线。</p></section>':'');};
const laundryDelete=deleteSel;deleteSel=function(){const f=ui.sel?.kind==='furn'?getF(ui.sel.id):null;if(f?.type!=='laundrycab')return laundryDelete();return mutate(()=>{state.furniture=state.furniture.filter(g=>g.id!==f.id&&g.laundryOwner!==f.id);ui.sel=null;});};
Object.assign(window.homeStudio,{validate:fixState,deleteSelected:deleteSel});

function syncAssemblyModels(){syncCeilingAnchors(state);for(const g of furnG.children){const f=getF(g.userData.fid);if(f?.assemblyOwner){g.position.set(wx(f.cx),M(f.elevation||0),wz(f.cy));g.rotation.y=-f.rot*Math.PI/180;}}}
const curatedConstruction2D=applyConstruction2D;applyConstruction2D=function(){curatedConstruction2D();for(const el of $('#gFurn').children){const f=getF(el.dataset.fid);if(UNNECESSARY_DISPLAY_TYPES.has(f?.type)){el.style.display='none';el.style.pointerEvents='none';}}};
const curatedTop3D=applyTop3D;applyTop3D=function(){curatedTop3D();for(const g of furnG.children){const f=getF(g.userData.fid);if(UNNECESSARY_DISPLAY_TYPES.has(f?.type))g.visible=false;else if(f?.assemblyOwner)g.visible=f.type!=='curtainrail'||topView||constructionExporting;}};
window.select=select;

applyStaticLang();syncFullscreen();buildDefs();buildLib();renderOpenings();renderDims();$('#tip').textContent=TIPS()['2d'];fitView();renderAll();initWorkbench();


// Presentation and controls do not alter the confirmed scheme.
const SCENE_EXPERIENCE_REVISION='immersive-controls-compact-labels-20261006';
opt.labels=true;opt.lamps=true;opt.lookSensitivity=1;
let walkCtl=null,walkFallback=false,walkLockPending=false,walkLockFailure=null,walkLockUnavailable=false,walkLockDiagnostic=null,walkLockAttempt=0,walkOrbitPose=null,walkOrbitCut=H;
let walkUITimer=null;const walkVelocity=new THREE.Vector3();let ceilingFill=null;
function roomAtCamera(){return ROOMS.find(r=>inPolygon([camera.position.x*1000+OX,camera.position.z*1000+OY],r.poly));}
function revealWalkControls(){
 document.body.classList.remove('walk-ui-idle');clearTimeout(walkUITimer);
 if(active&&opt.mode==='walk'&&(touchWalk||walkCtl?.isLocked))walkUITimer=setTimeout(()=>{if(!$('#walkSettings').open&&!$('#walkHelp').open&&!$('#walkToolbar').contains(document.activeElement))document.body.classList.add('walk-ui-idle');},2800);
}
function syncWalkExperience(){
 const walking=inited&&active&&opt.mode==='walk',locked=!!walkCtl?.isLocked,paused=walking&&!touchWalk&&!locked;
 document.body.classList.toggle('pointer-locked',locked);document.body.classList.toggle('walk-paused',paused);
 $('#walkToolbar').hidden=!walking;
 if(!walking){clearTimeout(walkUITimer);document.body.classList.remove('walk-ui-idle');$('#walkSettings').open=false;$('#walkHelp').open=false;}
 else if(paused){clearTimeout(walkUITimer);document.body.classList.remove('walk-ui-idle');}
 if(inited){$('#cross').style.display=walking&&(locked||touchWalk)?'block':'none';$('#joy').style.display=walking&&!locked?'block':'none';$('#walkExit').style.display='none';}
 const notice=$('#walkNotice');notice.hidden=!walking||(!paused&&!walkFallback);notice.textContent=paused?'已暂停 · 空格或点击场景继续':walkFallback?(walkLockUnavailable?'当前浏览器未允许鼠标锁定 · 可拖动转头': '鼠标锁定未成功 · 点击场景后可重试，或拖动转头'):'';
 $('#walkLock').hidden=COARSE||walkLockUnavailable||(inited&&!renderer.domElement.requestPointerLock);$('#walkLock').disabled=walkLockPending||locked;$('#walkLock').setAttribute('aria-pressed',String(locked));
 $('#walkNight').textContent=opt.night?'切换日景':'切换夜景';$('#walkNight').setAttribute('aria-pressed',String(!!opt.night));
 if(walking){const text=locked?'WASD / 方向键移动 · 鼠标转头 · E 开关门 · Esc 暂停':paused?'已暂停 · 空格 / 点击场景继续 · 摇杆可直接走动':(COARSE?'摇杆移动 · 拖动转头 · 轻点画面显示工具':'摇杆 / WASD / 方向键移动 · 拖动转头 · E 开关门 · Esc 暂停');$('#hint3d').textContent=text;$('#tip').textContent=text;$('#tip').title=text;}
 const heading=$('aside.lib .pane-heading b');if(heading)heading.textContent='家具';
}
function resumeDragWalk(){
 if(!active||opt.mode!=='walk')return;
 touchWalk=true;walkVelocity.set(0,0,0);Object.keys(keys).forEach(k=>keys[k]=false);syncHint3d();revealWalkControls();
}
function lockFailed(error,attempt=walkLockAttempt){
 if(attempt!==walkLockAttempt||walkCtl?.isLocked)return;
 const failure=recordPointerLockFailure(walkLockDiagnostic,error);
 walkLockDiagnostic=failure.diagnostic;walkLockFailure=failure.reason;walkLockUnavailable=failure.unavailable;
 walkLockPending=false;walkFallback=true;$('#walkLock').blur();resumeDragWalk();syncWalkExperience();
}
function requestWalkLock(){
 if(!inited||!active||opt.mode!=='walk'||walkLockPending||walkCtl?.isLocked||COARSE||walkLockUnavailable)return;
 const attempt=++walkLockAttempt;
 walkLockDiagnostic={attempt,requestedAt:new Date().toISOString(),context:pointerLockContext(renderer.domElement,document,navigator,window),error:null};
 if(!renderer.domElement.requestPointerLock){lockFailed({name:'NotSupportedError',message:'当前环境未提供 requestPointerLock API。'},attempt);return;}
 walkLockPending=true;walkLockFailure=null;walkFallback=false;
 // Request synchronously inside the user's click, preserving transient activation.
 try{const pending=walkCtl.lock();if(pending?.catch)pending.catch(error=>lockFailed(error,attempt));}catch(error){lockFailed(error,attempt);}
 syncWalkExperience();
}
const experienceInit=init;
init=function(){const ready=inited;experienceInit();if(ready)return;
 walkCtl={get isLocked(){return document.pointerLockElement===renderer.domElement;},lock:()=>renderer.domElement.requestPointerLock(),unlock:()=>{if(document.pointerLockElement===renderer.domElement)document.exitPointerLock();}};
 document.addEventListener('pointerlockchange',()=>{walkLockPending=false;touchWalk=false;walkVelocity.set(0,0,0);joy.x=joy.y=0;joy.id=null;$('#joy i').style.transform='';Object.keys(keys).forEach(k=>keys[k]=false);if(walkCtl.isLocked){walkFallback=false;walkLockUnavailable=false;walkLockFailure=null;if(walkLockDiagnostic)walkLockDiagnostic={...walkLockDiagnostic,error:null,lockedAt:new Date().toISOString()};if(!active||opt.mode!=='walk')walkCtl.unlock();else{revealWalkControls();$('#walkLock').blur();}}syncWalkExperience();});
 document.addEventListener('pointerlockerror',()=>{const attempt=walkLockAttempt;if(!walkLockPending&&!walkFallback)return;setTimeout(()=>lockFailed(null,attempt),0);});
 document.addEventListener('mousemove',e=>{if(!active||opt.mode!=='walk'||!walkCtl.isLocked)return;eul.setFromQuaternion(camera.quaternion);eul.y-=e.movementX*.0015*opt.lookSensitivity;eul.x=THREE.MathUtils.clamp(eul.x-e.movementY*.0015*opt.lookSensitivity,-1.15,1.15);camera.quaternion.setFromEuler(eul);});
 renderer.domElement.addEventListener('pointermove',e=>{if(opt.mode==='walk'&&!walkCtl.isLocked&&!e.buttons)revealWalkControls();});
 syncWalkExperience();
};
const experienceStop=stopTouchWalk;stopTouchWalk=function(){walkCtl?.unlock();walkVelocity.set(0,0,0);experienceStop();syncWalkExperience();};
startTouchWalk=function(){if(walkCtl?.isLocked)return;resumeDragWalk();};
const experienceWorkbench=syncWorkbench;syncWorkbench=function(){experienceWorkbench();syncWalkExperience();};
const experienceHint=syncHint3d;syncHint3d=function(){experienceHint();syncWalkExperience();};
const experienceMode=setMode;
setMode=function(mode){
 if(anim)return;const before=opt.mode;if(mode===before){if(mode==='walk')startTouchWalk();return;}
 if(mode==='walk'){walkOrbitPose=curPose();walkOrbitCut=opt.cut;walkFallback=false;closeMenus();closeDrawers();}
 if(mode==='orbit')walkCtl?.unlock();
 experienceMode(mode);walkVelocity.set(0,0,0);
 camera.fov=mode==='walk'?65:FOV;camera.updateProjectionMatrix();
 if(mode==='walk'){camera.position.y=(CASE.walkStart?.eyeMm||1600)/1000;applyTop3D();if(opt.mode==='walk')startTouchWalk();}
 else if(before==='walk'){opt.cut=walkOrbitCut;syncCutBtns();sync();applyTop3D();if(walkOrbitPose)flyTo(walkOrbitPose,650);}
 syncQuickActions();syncWalkExperience();
};
const experienceExit=exit;exit=async function(){stopTouchWalk();camera.fov=FOV;camera.updateProjectionMatrix();await experienceExit();syncWalkExperience();};window.View3D.exit=exit;
stepWalk=function(dt){
 if(!touchWalk&&!walkCtl?.isLocked)return;
 const fwd=new THREE.Vector3();camera.getWorldDirection(fwd);fwd.y=0;fwd.normalize();const right=new THREE.Vector3(-fwd.z,0,fwd.x),mv=new THREE.Vector3();
 if(keys.KeyW||keys.ArrowUp)mv.add(fwd);if(keys.KeyS||keys.ArrowDown)mv.sub(fwd);if(keys.KeyD||keys.ArrowRight)mv.add(right);if(keys.KeyA||keys.ArrowLeft)mv.sub(right);if(touchWalk)mv.addScaledVector(fwd,-joy.y).addScaledVector(right,joy.x);
 const mag=Math.min(1,mv.length()),speed=keys.ShiftLeft||keys.ShiftRight?1.8:.95;if(mag>.03)mv.normalize().multiplyScalar(speed*mag);else mv.set(0,0,0);
 walkVelocity.lerp(mv,1-Math.exp(-dt*10));const p=camera.position,dx=walkVelocity.x*dt,dz=walkVelocity.z*dt;
 if(!blocked(p.x+dx,p.z))p.x+=dx;else walkVelocity.x=0;if(!blocked(p.x,p.z+dz))p.z+=dz;else walkVelocity.z=0;
};
const experienceTop=applyTop3D;applyTop3D=function(){
 const selectedTop=topView;if(opt.mode==='walk')topView=true;try{experienceTop();}finally{topView=selectedTop;}
 for(const g of furnG.children){const f=getF(g.userData.fid);if(f&&LIT_TYPES.has(f.type)&&!UNNECESSARY_DISPLAY_TYPES.has(f.type))g.visible=opt.furn&&(f.mount!=='ceiling'||opt.mode==='walk'||opt.cut>=H);}
};
const experienceLight=applyLight;applyLight=function(){
 experienceLight();const profile=lightingProfile(opt.night);sun.intensity=opt.night?profile.sun:(1.4+Math.sin(Math.PI*(opt.hour-6)/12)*1.6)*profile.sunScale;hemi.intensity=profile.hemisphere;hemi.color.set('#f5f6fa');hemi.groundColor.set('#f1f2f3');sun.color.set('#fffdf9');renderer.toneMappingExposure=profile.exposure;
 if(!ceilingFill){ceilingFill=new THREE.AmbientLight('#ffffff',.45);ceilingFill.name='interior-ceiling-fill';scene.add(ceilingFill);}ceilingFill.intensity=profile.ambient;
 wallMat.roughness=.96;capMat.color.set('#111111');
 lampG.children.forEach(light=>{if(light.isLight)light.intensity=opt.lamps&&light.userData.enabled?light.userData.nominalIntensity:0;});
 furnG.traverse(o=>{if(!o.isMesh)return;const parent=(()=>{let p=o;while(p&&!p.userData.fid)p=p.parent;return p;})();const f=parent&&getF(parent.userData.fid);
  for(const m of Array.isArray(o.material)?o.material:[o.material]){if(f&&LIT_TYPES.has(f.type)&&m.emissive?.getHex())m.emissiveIntensity=opt.lamps&&f.lightOn!==false?(m.userData.recessedLuminousFace?(opt.night?2.2:1.0):(opt.night?1.2:1.0)):0;
   const role=m.userData.finishRole;if(role==='upholstery'||role==='textile'){m.roughness=.86;m.envMapIntensity=.16;}else if(role==='cabinet'){m.roughness=.44;m.clearcoat=.15;m.envMapIntensity=.30;}else if(role==='stone'){m.roughness=.34;m.envMapIntensity=.38;}
  }
 });
};
const experienceRebuildLights=rebuildFixtureLights;rebuildFixtureLights=function(){experienceRebuildLights();
 // Limit spot shadow maps; fixtures remain independent fill lights.
 for(const light of lampG.children){if(!light.isSpotLight)continue;light.castShadow=(CASE.render?.shadowFixtureIds||lampG.children.filter(o=>o.isSpotLight).slice(0,3).map(o=>o.userData.fixtureId)).includes(light.userData.fixtureId);if(light.castShadow){light.shadow.mapSize.set(512,512);light.shadow.camera.near=.05;light.shadow.camera.far=light.distance;light.shadow.bias=-.00015;light.shadow.normalBias=.012;}}
};
const experienceBuildFurn=buildFurn;buildFurn=function(){experienceBuildFurn();
 // Cached materials must not let one fixture's switch change a different fixture's lens.
 for(const g of furnG.children){if(!LIT_TYPES.has(getF(g.userData.fid)?.type))continue;const owned=new Map();g.traverse(o=>{if(!o.isMesh)return;const own=m=>{if(!m.emissive?.getHex())return m;if(!owned.has(m)){const clone=m.clone();clone.userData.ownedFurnitureDetail=true;owned.set(m,clone);}return owned.get(m);};o.material=Array.isArray(o.material)?o.material.map(own):own(o.material);});}
 applyTop3D();applyLight();};
const experienceBuildLabels=buildLabels;buildLabels=function(){experienceBuildLabels();for(const [i,label]of labelG.children.entries()){const r=ROOMS.filter(r=>r.at)[i],point=chooseSceneLabelPoint(r,state.furniture,inPolygon);label.position.set(wx(point[0]),opt.cut+.15,wz(point[1]));label.userData.roomId=r.id;label.element.dataset.roomId=r.id;label.element.innerHTML=`<span>${esc(nm(state.rooms[r.id].name))}</span><small>${area(r.poly).toFixed(1)} m²</small>`;label.element.setAttribute('aria-label',`${state.rooms[r.id].name}，${area(r.poly).toFixed(2)} 平方米`);}};
function declutterSceneLabels(){
 const enabled=active&&opt.mode==='orbit'&&opt.labels&&!anim,used=[];camera.updateMatrixWorld();
 const project=p=>{const v=new THREE.Vector3(wx(p[0]),opt.cut+.15,wz(p[1])).project(camera);return{x:(v.x+1)*SW()/2,y:(1-v.y)*SH()/2};};
 const entries=labelG.children.map(label=>{const r=ROOMS.find(r=>r.id===label.userData.roomId),points=r.poly.map(project),extent=Math.min(Math.max(...points.map(p=>p.x))-Math.min(...points.map(p=>p.x)),Math.max(...points.map(p=>p.y))-Math.min(...points.map(p=>p.y)));return{label,extent};}).sort((a,b)=>b.extent-a.extent);
 for(const {label,extent}of entries){label.element.classList.toggle('name-only',extent<100);let visible=enabled&&extent>32;const point=label.position.clone().project(camera),x=(point.x+1)*SW()/2,y=(1-point.y)*SH()/2,w=label.element.offsetWidth||80,h=label.element.offsetHeight||24;
  const rect={x:x-w/2,y:y-h/2,w:w+6,h:h+4};if(point.z< -1||point.z>1||rect.x<4||rect.y<4||rect.x+w>SW()-4||rect.y+h>SH()-4)visible=false;
  if(visible&&used.some(r=>rect.x<r.x+r.w&&rect.x+rect.w>r.x&&rect.y<r.y+r.h&&rect.y+rect.h>r.y))visible=false;
  label.visible=visible;if(visible)used.push(rect);
 }
}
const experienceSelection=updateSel;updateSel=function(){experienceSelection();declutterSceneLabels();};
function roomViewingTarget(r){
 const types=['bed','sofa','sofabed','vanity','counter','laundrycab','desk','toilet'],items=state.furniture.filter(f=>types.includes(f.type)&&inPolygon([f.cx,f.cy],r.poly));
 items.sort((a,b)=>types.indexOf(a.type)-types.indexOf(b.type)||b.w*b.d-a.w*a.d);const f=items[0];return {point:f?[f.cx,f.cy]:r.at,front:f?[-Math.sin(f.rot*Math.PI/180),Math.cos(f.rot*Math.PI/180)]:[0,1]};
}
function findWalkLanding(r){
 const target=roomViewingTarget(r),focus=target.point,candidates=[r.at],xs=r.poly.map(p=>p[0]),ys=r.poly.map(p=>p[1]),desired=Math.min(2400,Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys))*.48);
 for(let y=Math.min(...ys)+280;y<Math.max(...ys)-200;y+=250)for(let x=Math.min(...xs)+280;x<Math.max(...xs)-200;x+=250)candidates.push([x,y]);
 const score=p=>{const dx=p[0]-focus[0],dy=p[1]-focus[1],distance=Math.hypot(dx,dy);let occluded=0;for(let t=.1;t<.95;t+=.1){const x=wx(p[0]+(focus[0]-p[0])*t),z=wz(p[1]+(focus[1]-p[1])*t);if(colliders.some(([x0,z0,x1,z1])=>x>x0&&x<x1&&z>z0&&z<z1)){occluded=8;break;}}return Math.abs(distance-desired)/1000+(1-(dx*target.front[0]+dy*target.front[1])/Math.max(1,distance))*.9+occluded;};
 return candidates.filter(p=>inPolygon(p,r.poly)&&!blocked(wx(p[0]),wz(p[1]),.22)).sort((a,b)=>score(a)-score(b))[0];
}
const experienceQuick=syncQuickActions;syncQuickActions=function(){experienceQuick();for(const el of document.querySelectorAll('[data-quick-toggle="labels"]')){el.classList.toggle('on',opt.labels);el.setAttribute('aria-pressed',String(opt.labels));}syncWalkExperience();};
const experienceRoomFly=flyToRoom;flyToRoom=function(id){const r=ROOMS.find(r=>r.id===id);if(!r)return;const xs=r.poly.map(p=>p[0]),ys=r.poly.map(p=>p[1]),width=M(Math.max(...xs)-Math.min(...xs)),depth=M(Math.max(...ys)-Math.min(...ys)),dist=Math.max(depth,width/Math.max(.6,SW()/SH()))/(2*Math.tan(FOV*Math.PI/360));const t=new THREE.Vector3(wx(r.at[0]),.35,wz(r.at[1]));flyTo(pose(t,new THREE.Vector3(t.x+dist*.38,dist+3.4,t.z+dist*.65)),750);};
$('#walkSensitivity').oninput=e=>opt.lookSensitivity=Number(e.target.value);
$('#sceneWhole').onclick=()=>flyTo(isoWhole(),650);$('#sceneTop').onclick=()=>flyTo(topWhole(),750);
$('#walkReturn').onclick=()=>setMode('orbit');$('#walkNight').onclick=()=>{setLightingMode(opt.night?'day':'night');$('#walkNight').blur();revealWalkControls();};
$('#walkFullscreen').onclick=()=>$('#fullscreen').click();$('#walkLock').onclick=requestWalkLock;
$('#walkToolbar').addEventListener('pointerenter',()=>{clearTimeout(walkUITimer);document.body.classList.remove('walk-ui-idle');});
$('#walkToolbar').addEventListener('pointerleave',revealWalkControls);
for(const id of ['walkSettings','walkHelp'])$('#'+id).addEventListener('toggle',()=>{if($('#'+id).open){clearTimeout(walkUITimer);document.body.classList.remove('walk-ui-idle');}else revealWalkControls();});
Object.assign(window.homeStudio,{setCameraMode:setMode,setLighting:setLightingMode,sceneExperienceRevision:SCENE_EXPERIENCE_REVISION,roomAtCamera:()=>roomAtCamera()?.id||null,walkStatus:()=>({locked:!!walkCtl?.isLocked,fallback:walkFallback,paused:!touchWalk&&!walkCtl?.isLocked,pending:walkLockPending,reason:walkLockFailure,unavailable:walkLockUnavailable,diagnostic:walkLockDiagnostic?JSON.parse(JSON.stringify(walkLockDiagnostic)):null})});
syncQuickActions();syncWalkExperience();


/* Fixed spatial illumination: never depend on camera/room/view direction.
   All fixture records contribute to permanent groups; only explicit switches
   or scheme/light changes rebuild the cached contributions. */
const performanceLighting=createLightingRuntime({SpotLight:THREE.SpotLight,PointLight:THREE.PointLight,Color:THREE.Color,CASE,ROOMS,getF,inPolygon,opt,getRuntime:()=>({lampG,scene,renderer,camera,ceilingFill,hemi,anim,fly}),pixelRatio:()=>devicePixelRatio});
function updatePerformanceLighting(dt){performanceLighting.update(dt);}
window.homeStudio.performanceStatus=()=>performanceLighting.status();

window.homeStudio.ready=true;

function currentAreaStatus(){return roomAreaStatus(DEFAULT.walls,state.walls);}
function syncAreaStatus(){
 const status=currentAreaStatus(),el=document.getElementById('areaStatusNotice');
 el.hidden=status.status==='source-partitions';el.textContent=status.message;
 document.body.classList.toggle('area-pending',!el.hidden);
 for(const label of labelG?.children||[]){label.element.title=status.message;label.element.classList.toggle('area-reference',!el.hidden);}
}
const areaRenderAll=renderAll;renderAll=function(){areaRenderAll();syncAreaStatus();};
const areaLabelBuild=buildLabels;buildLabels=function(){areaLabelBuild();syncAreaStatus();};
const areaRoomPanel=roomPanel;roomPanel=function(r){const status=currentAreaStatus();return(status.message?'<section class="area-status-warning">'+esc(status.message)+'</section>':'')+areaRoomPanel(r);};
Object.assign(window.homeStudio,{toggleWall,areaStatus:currentAreaStatus,workbenchRevision:WORKBENCH_VERSION,serializeScheme:()=>JSON.stringify(state),importScheme:raw=>{const parsed=decodeScheme(raw,fixState);return mutate(()=>{state=parsed;ui.sel=null;});}});
syncAreaStatus();

// Rendering-only optimization: no scheme geometry, dimensions or colors change.
const optimizedBuildArch=buildArch;buildArch=function(){optimizedBuildArch();sceneRevision++;};
const optimizedBuildFurn=buildFurn;buildFurn=function(){optimizedBuildFurn();renderMetrics.savedDrawCalls=0;renderMetrics.batches=0;
 if(CASE.render?.batchFurniture!==false)for(const g of furnG.children){const f=getF(g.userData.fid);if(!f||LIT_TYPES.has(f.type)||f.assemblyOwner||['curtain','rollerblind','shower'].includes(f.type))continue;const result=batchFurniture(g);renderMetrics.savedDrawCalls+=result.savedDrawCalls;renderMetrics.batches+=result.batches;}
 for(const owner of furnG.children)for(const decor of owner.children.filter(g=>g.userData.tabletopDecor)){const result=batchFurniture(decor);renderMetrics.savedDrawCalls+=result.savedDrawCalls;renderMetrics.batches+=result.batches;}
 sceneRevision++;
};
const optimizedTop=applyTop3D;applyTop3D=function(){optimizedTop();sceneRevision++;};
const optimizedLight=applyLight;applyLight=function(){optimizedLight();sceneRevision++;};
Object.assign(window.homeStudio,{renderStatus:()=>({...renderMetrics,mode:'on-change'}),setShadowPreview:enabled=>{performanceLighting.setShadows(enabled);sceneRevision++;}});

// Presentation cut: architecture is lowered, furniture retains full dimensions.
// Light objects remain active: clipping only removes rendered surfaces.
const sectionPlane=new THREE.Plane(new THREE.Vector3(0,-1,0),H);
let sectionRebuilds=0;
const sectionMaterialSource=new WeakMap();
function sectionEligible(mesh,root){
 if(root===archUp)return true;
 let p=mesh;while(p&&p!==root&&!p.userData.fid)p=p.parent;
 return ['doortrim','windowtrim'].includes(getF(p?.userData.fid)?.type);
}
function rebuildSectionCaps(root,architectural){
 for(const child of root.children.slice())if(child.userData.sectionCaps){clearGroup(child);root.remove(child);}
 if(opt.cut>=H)return;
 const caps=new THREE.Group();caps.userData.sectionCaps=true;caps.name='Unified-section-caps';
 root.updateWorldMatrix(true,true);const inverse=new THREE.Matrix4().copy(root.matrixWorld).invert(),meshes=[];
 root.traverse(o=>{if(o.isMesh&&!o.userData.wallSurface&&!o.userData.baseCeiling&&!o.userData.walkOnly&&o.visible&&sectionEligible(o,root))meshes.push(o);});
 const materials=new Map();
 for(const mesh of meshes){
  const matrix=new THREE.Matrix4().multiplyMatrices(inverse,mesh.matrixWorld),geo=mesh.geometry,pos=geo.attributes.position;if(!pos)continue;
  const point=new THREE.Vector3(),points=[];let low=Infinity,high=-Infinity;
  for(let i=0;i<pos.count;i++){point.fromBufferAttribute(pos,i).applyMatrix4(matrix);points.push(point.toArray());low=Math.min(low,point.y);high=Math.max(high,point.y);}
  if(low>=opt.cut-1e-5||high<=opt.cut+1e-5)continue;
  const idx=geo.index,triangles=[];for(let i=0;i<(idx?idx.count:pos.count);i+=3)triangles.push([points[idx?idx.getX(i):i],points[idx?idx.getX(i+1):i+1],points[idx?idx.getX(i+2):i+2]]);
  const regions=contourRegions(horizontalContours(triangles,opt.cut));if(!regions.length)continue;
  const shapes=regions.map(r=>{const shape=new THREE.Shape(r.outer.map(p=>new THREE.Vector2(p[0],-p[1])));shape.holes=r.holes.map(h=>new THREE.Path(h.map(p=>new THREE.Vector2(p[0],-p[1]))));return shape;});
  let material=capMat;
  if(!architectural){const source=Array.isArray(mesh.material)?mesh.material[0]:mesh.material,key=source?.color?.getHexString()||'756d61';if(!materials.has(key)){const color=new THREE.Color('#'+key).multiplyScalar(.8),m=new THREE.MeshBasicMaterial({color,side:THREE.DoubleSide});m.userData.sectionOwned=true;materials.set(key,m);}material=materials.get(key);}
  const surface=new THREE.Mesh(new THREE.ShapeGeometry(shapes),material);surface.geometry.rotateX(-Math.PI/2);surface.position.y=opt.cut-.00005;surface.userData.sectionCap=true;surface.userData.sourceMesh=mesh.uuid;let owner=mesh;while(owner&&owner!==root){for(const tag of ['fid','opening','assemblyOwner'])if(owner.userData[tag]&&!surface.userData[tag])surface.userData[tag]=owner.userData[tag];owner=owner.parent;}caps.add(surface);
 }
 root.add(caps);sectionRebuilds++;
}
function updateSectionPlane(){
 if(!renderer)return;sectionPlane.constant=opt.cut+.0005;renderer.clippingPlanes=[];renderer.localClippingEnabled=true;
 for(const root of [archUp,furnG]){const cloned=new Map(),disposed=new Set();root.traverse(mesh=>{
  if(!mesh.isMesh||mesh.userData.sectionCap)return;
  const single=!Array.isArray(mesh.material),sources=(single?[mesh.material]:mesh.material).map(m=>{const source=sectionMaterialSource.get(m);if(source){disposed.add(m);return source;}return m;});
  const clip=opt.cut<H&&sectionEligible(mesh,root);
  const materials=sources.map(source=>{if(!clip)return source;if(!cloned.has(source)){const material=source.clone();material.clippingPlanes=[sectionPlane];material.clipShadows=true;material.userData.sectionOwned=true;sectionMaterialSource.set(material,source);cloned.set(source,material);}return cloned.get(source);});
  mesh.material=single?materials[0]:materials;
 });disposed.forEach(m=>m.dispose());}
 sceneRevision++;
}
const sectionArchBuild=buildArch;buildArch=function(){sectionArchBuild();rebuildSectionCaps(archUp,true);updateSectionPlane();};
const sectionFurnitureBuild=buildFurn;buildFurn=function(){sectionFurnitureBuild();rebuildSectionCaps(furnG,false);updateSectionPlane();};
const sectionSync=sync;sync=function(force){const previous=sync.sectionCut;sectionSync(force);if(inited&&previous!==opt.cut){sync.sectionCut=opt.cut;rebuildSectionCaps(furnG,false);updateSectionPlane();}};
const sectionClear=clearGroup;clearGroup=function(root){const owned=new Set();root.traverse(o=>{for(const m of Array.isArray(o.material)?o.material:[o.material])if(m?.userData.sectionOwned)owned.add(m);});sectionClear(root);owned.forEach(m=>m.dispose());};
Object.assign(window.homeStudio,{
 setSectionHeight:mm=>{if(!inited||opt.mode==='walk')return false;const h=Number(mm)/1000;if(!Number.isFinite(h)||h<.3||h>H)throw Error('Invalid section height');opt.cut=h;syncCutBtns();sync();renderPanel();return true;},
 sectionStatus:()=>({active:opt.cut<H,heightMm:opt.cut*1000,scope:'architecture-only',planeCount:opt.cut<H?1:0,capCount:[archUp,furnG].reduce((n,g)=>n+(g?.children.find(o=>o.userData.sectionCaps)?.children.length||0),0),rebuilds:sectionRebuilds})
});
