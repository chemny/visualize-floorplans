// Dimensions are editable concept defaults, not universal product maxima.
export const DIMENSIONS={
 fridge:{label:'冰箱',h:1800,min:1200,max:2200,meaning:'机身高度',note:'常见设计范围 1500–2000；超出初值范围请以具体产品资料确认。'},
 shower:{label:'淋浴房',h:2000,min:1800,max:2400,meaning:'玻璃围挡高度',note:'龙头、花洒最高点单独计入外包络。'},
 washer:{label:'洗衣机',h:850,min:700,max:1100},dryer:{label:'烘干机',h:850,min:700,max:1100},dishwasher:{label:'洗碗机',h:850,min:450,max:1000},
 bed:{label:'床',h:1080,min:450,max:1600,meaning:'床头最高点'},sofa:{label:'沙发',h:850,min:600,max:1200,meaning:'靠背最高点'},
 dresser:{label:'梳妆台',h:750,min:650,max:900,meaning:'桌面高度；桌面镜单独计入外包络'},
 counter:{label:'地柜',h:900,min:750,max:1000},table:{label:'餐桌',h:750,min:680,max:850},desk:{label:'书桌',h:750,min:650,max:900},
 wallcab:{label:'吊柜',h:750,elevation:1800,min:300,max:1200,meaning:'柜体高度'},hood:{label:'油烟机',h:500,elevation:1575,min:250,max:1000,meaning:'完整机身高度',note:'灶面至烟机底部初值 650 mm，实际依所选灶具及烟机安装说明。'},
 fridgecab:{label:'冰箱上柜',h:600,elevation:2150,min:200,max:1000},endpanel:{label:'柜侧板',h:2750,min:300,max:2750},
 pendant:{label:'吊灯',h:500,elevation:2250,min:80,max:800},downlight:{label:'筒灯',h:40,elevation:2710,min:15,max:150},tracklight:{label:'轨道灯',h:120,elevation:2600,min:40,max:350},
 wardrobe:{label:'衣柜',h:2750,min:1500,max:2750},bookshelf:{label:'书柜',h:2750,min:1000,max:2750}
};
export const NEW_COMPONENTS=[
 ['wallcab','厨房吊柜',900,320,'#ece5db'],['hood','油烟机',750,480,'#9eaaa7'],
 ['fridgecab','冰箱上柜',600,650,'#ece5db'],['endpanel','柜侧板',50,650,'#ece5db'],
 ['pendant','餐厅吊灯',700,260,'#a8957b'],['downlight','嵌入筒灯',100,100,'#ece5db'],['tracklight','轨道灯',1200,90,'#5b5e58']
];
export const WALL_FINISHES={paint:{label:'乳胶漆',role:'wall',kind:'plaster'},wallpaper:{label:'织纹壁纸',role:'wall',kind:'fabric'},wood:{label:'木饰面',role:'wood',kind:'wood'},tile:{label:'瓷砖',role:'tile',kind:'tile'}};
export function validateDimensions(f,height=2750){
 const s=DIMENSIONS[f.type],h=f.fitToCeiling?height:(Number(f.h)||s?.h||850),e=Number(f.elevation)||0;
 if(!Number.isFinite(h)||!Number.isFinite(e)||h<=0||e<0||h+e>height+.1)throw Error(f.name+'：高度与离地之和不得超过层高 '+height+' mm');
 if(f.fitToCeiling&&!['wardrobe','bookshelf','endpanel'].includes(f.type))throw Error(f.name+'：该组件不能设置为到顶柜');
 const maximum=['wardrobe','bookshelf','endpanel'].includes(f.type)?height:s?.max;
 if(s&&!f.assemblyOwner&&(h<s.min||h>maximum))throw Error(f.name+'：高度应在 '+s.min+'–'+s.max+' mm 的设计范围内；特殊产品需确认尺寸');
 return {h,e};
}
