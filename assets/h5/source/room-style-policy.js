// Neutral service-room finishes are a default; explicit fixed finishes stay fixed.
export const NEUTRAL_WET_PALETTE=Object.freeze({wall:'#f6f5f1',ceiling:'#fbfaf7',tile:'#e7e7e1',grout:'#c9cac4',kitchen:'#f3f2ed',cabinet:'#f3f2ed',wood:'#e7e3d9',stone:'#f1f0e9',metal:'#a3a6a3',frame:'#5d6166',ceramic:'#f7f7f2'});
export function roomVisualRole(room={}){
 const semantic=room.function||room.usage||room.role;
 if(semantic)return ['kitchen','bathroom','bath','toilet'].includes(semantic)?'wet':['closet','dressing'].includes(semantic)?'closet':'dry';
 const text=[room.id,room.name].join(' ').toLowerCase();return /kitchen|bath|toilet|厨房|卫生间|公卫|套卫|主卫/.test(text)?'wet':/closet|衣帽/.test(text)?'closet':'dry';
}
export function roomFurnitureStyle(f,style,rooms){
 const room=rooms.find(r=>r.id===f.roomId);if(roomVisualRole(room)!=='wet')return style;
 return {...style,id:'neutral_service',furnitureWoodFinish:'lacquer',palette:{...style.palette,...NEUTRAL_WET_PALETTE}};
}
