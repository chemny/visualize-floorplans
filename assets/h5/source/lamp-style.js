// Style defaults are product choices, not lighting or construction standards.
export const LAMP_SHAPES=Object.freeze({flat:{name:'薄边平面灯',drop:45},dome:{name:'弧面吸顶灯',drop:112},crystal:{name:'欧式水晶灯',drop:325},crystal_classic:{name:'古典水晶灯',drop:520}});
export const LAMP_STYLE_MAP=Object.freeze({modern_minimal:'flat',wood_cream:'dome',midcentury_modern:'dome',modern_chinese:'dome',champagne_pearl:'dome',european_luxury:'crystal_classic',contemporary_french:'crystal',italian_luxury:'dome',paris_art_deco:'crystal',milan_greige:'flat'});
export const styleLampEligible=f=>['ceilinground','ceilingsquare'].includes(f?.type);
export function roomLampRole(room={},name=''){
 const value=[name,room.name,room.function,room.role,room.type].filter(x=>typeof x==='string').join(' ').toLowerCase();
 if(/厨房|厨|卫|浴|阳台|过道|走廊|衣帽|玄关|kitchen|bath|toilet|balcony|corridor|hall|closet|entry/.test(value))return 'utility';
 if(/客厅|餐厅|客餐|卧|儿童|书房|客书|living|dining|bed|study|office|child/.test(value))return 'decorative';
 return 'utility';
}
export function ensureLampStyle(f,{style,role='utility',ceiling=2800}={}){
 if(!styleLampEligible(f))return f;
 if(f.lampStyleMode!==undefined&&!['follow','fixed'].includes(f.lampStyleMode))throw Error('灯具联动设置无效');
 if(f.lampShape!==undefined&&!LAMP_SHAPES[f.lampShape])throw Error('灯具款式无效');
 f.lampStyleMode??='follow';
 if(f.lampStyleMode==='fixed'&&!f.lampShape)throw Error('请选择固定灯具款式');
 let shape=f.lampStyleMode==='fixed'?f.lampShape:(role==='decorative'?LAMP_STYLE_MAP[style]||'flat':'flat');
 // Low rooms retain a flush fitting automatically; explicit unsafe choices fail.
 if(ceiling-LAMP_SHAPES[shape].drop<2100){
  if(f.lampStyleMode==='fixed')throw Error('灯具下沿过低，请选吸顶款式');
  shape='flat';
 }
 if(ceiling-LAMP_SHAPES[shape].drop<2100)throw Error('层高不足，需核对灯具安装高度');
 f.lampLightOffset??=Number(f.h)||100;
 if(!Number.isFinite(f.lampLightOffset)||f.lampLightOffset<0||f.lampLightOffset>1000)throw Error('灯具光源位置无效');
 f.lampShape=shape;f.lampShapeRevision=1;f.h=LAMP_SHAPES[shape].drop;f.mount='ceiling';f.elevation=ceiling-f.h;
 return f;
}
export function lampPlanSymbol(shape,w,d,color){
 const stroke='stroke="#756d62" stroke-width="1" vector-effect="non-scaling-stroke"';
 if(['crystal','crystal_classic'].includes(shape))return `<ellipse rx="${w*.44}" ry="${d*.44}" fill="none" ${stroke}/>`+Array.from({length:6},(_,i)=>{const a=i*Math.PI/3;return `<path d="M0 0L${Math.cos(a)*w*.43} ${Math.sin(a)*d*.43}" ${stroke}/><ellipse cx="${Math.cos(a)*w*.43}" cy="${Math.sin(a)*d*.43}" rx="${w*.06}" ry="${d*.06}" fill="${color}" ${stroke}/>`;}).join('');
 return `<ellipse rx="${w/2}" ry="${d/2}" fill="${color}" ${stroke}/><ellipse rx="${w*.46}" ry="${d*.46}" fill="#fffdf7" ${stroke}/>`;
}
