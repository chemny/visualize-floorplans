import * as THREE from 'three';
import {paintFrenchPanels} from './french-panel-pattern.js';
import {wallDecorProfile} from './wall-decoration-style.js';
// Procedural local graphics: no image downloads or independent new wall objects.
export function paintWallDecor(g,size,pattern){
 const u=size/512;g.save();g.scale(u,u);g.fillStyle='#ffffff';g.fillRect(0,0,512,512);
 const frame=(x,y,w,h,color='#c8c1b6',width=2)=>{g.strokeStyle=color;g.lineWidth=width;g.strokeRect(x,y,w,h);};
 if(pattern==='french_panel'){paintFrenchPanels(g,512);}
 else if(pattern==='classic_frame'){frame(34,42,444,302,'#bba77e',4);frame(42,50,428,286,'#ded4c3',2);frame(34,382,444,88,'#bba77e',3);g.fillStyle='#cbbd9f';g.fillRect(0,359,512,4);}
 else if(pattern==='oak_slat'){for(let x=0;x<512;x+=32){g.fillStyle='#c4b9a7';g.fillRect(x,0,3,512);g.fillStyle='#ede8de';g.fillRect(x+3,0,2,512);}}
 else if(pattern==='walnut_panel'){g.fillStyle='#d2c9bd';g.fillRect(0,0,512,512);g.fillStyle='#ffffff';g.fillRect(0,0,512,334);g.fillStyle='#b6aa97';g.fillRect(0,334,512,3);for(let x=0;x<512;x+=128){g.fillStyle='#b5a793';g.fillRect(x,338,2,174);}}
 else if(pattern==='chinese_frame'){frame(58,48,396,414,'#9d9181',3);frame(67,58,378,395,'#e4ded2');g.fillStyle='#c4b6a1';g.fillRect(0,480,512,3);}
 else if(pattern==='champagne_frame'){frame(64,60,384,390,'#c7b999',2);frame(70,66,372,378,'#f4f1e9',1);}
 else if(pattern==='italian_panel'){g.fillStyle='#ddd6ca';g.fillRect(0,0,512,512);for(let x=0;x<512;x+=256){g.fillStyle='#b9afa1';g.fillRect(x,0,2,512);}g.strokeStyle='#b6aa9924';for(let k=0;k<4;k++){g.beginPath();g.moveTo(k*150,0);g.bezierCurveTo(k*150+30,180,k*150-15,300,k*150+65,512);g.stroke();}}
 else if(pattern==='artdeco_frame'){g.fillStyle='#f4f1e8';g.fillRect(0,0,512,512);frame(48,40,416,432,'#a99057',3);g.strokeStyle='#ad955d';g.lineWidth=2;g.beginPath();g.moveTo(80,450);g.lineTo(80,142);g.lineTo(256,64);g.lineTo(432,142);g.lineTo(432,450);g.stroke();}
 g.restore();
}
const artCache=new Map();
export function artworkTexture(styleId){
 if(artCache.has(styleId))return artCache.get(styleId);const c=document.createElement('canvas');c.width=c.height=512;const g=c.getContext('2d'),art=wallDecorProfile(styleId).art;
 const rect=(x,y,w,h,color)=>{g.fillStyle=color;g.fillRect(x,y,w,h);},circle=(x,y,r,color)=>{g.fillStyle=color;g.beginPath();g.arc(x,y,r,0,Math.PI*2);g.fill();};
 rect(0,0,512,512,'#f5f0e4');
 if(art==='minimal'){rect(82,90,124,278,'#343935');rect(245,188,174,194,'#c8c4bb');g.strokeStyle='#76766c';g.lineWidth=5;g.beginPath();g.moveTo(52,424);g.lineTo(433,76);g.stroke();}
 else if(art==='botanical'){g.strokeStyle='#7b8972';g.lineWidth=5;for(let k=0;k<3;k++){const x=140+k*110;g.beginPath();g.moveTo(x,450);g.quadraticCurveTo(x-60,250,x+25,60);g.stroke();for(let i=0;i<5;i++){g.fillStyle=i%2?'#a9b29a':'#788c73';g.beginPath();g.ellipse(x+(i%2?20:-25),110+i*62,38,13,i%2?-.5:.5,0,Math.PI*2);g.fill();}}}
 else if(art==='retro'){rect(75,170,158,260,'#b98c52');circle(154,170,79,'#b98c52');rect(282,86,145,283,'#aa654a');circle(354,369,72,'#aa654a');circle(268,220,62,'#d7bb80');}
 else if(art==='ink'){for(let k=0;k<3;k++){g.fillStyle=['#b5bcb2','#8f9e94','#53675f'][k];g.beginPath();g.moveTo(0,420-k*62);for(let x=0;x<=512;x+=35)g.lineTo(x,260-k*55+Math.sin(x*.018+k)*55);g.lineTo(512,512);g.lineTo(0,512);g.fill();}rect(412,65,30,45,'#a6503e');}
 else if(art==='pearl'){circle(240,230,150,'#ded0b6');circle(275,210,120,'#f4eee0');g.strokeStyle='#b39c6d';g.lineWidth=5;g.strokeRect(80,72,350,370);}
 else if(art==='landscape'){rect(0,0,512,305,'#d4d9ce');circle(365,112,58,'#e9ddbb');for(let k=0;k<3;k++){g.fillStyle=['#a7af8b','#829578','#536c59'][k];g.beginPath();g.moveTo(0,310+k*40);g.quadraticCurveTo(220,180+k*75,512,320+k*42);g.lineTo(512,512);g.lineTo(0,512);g.fill();}}
 else if(art==='floral'){rect(220,292,92,158,'#b6ad99');g.strokeStyle='#889477';g.lineWidth=5;for(let i=0;i<7;i++){const x=125+i*43,y=104+(i%3)*48;g.beginPath();g.moveTo(265,330);g.lineTo(x,y);g.stroke();for(let k=0;k<5;k++)circle(x+Math.cos(k*1.26)*18,y+Math.sin(k*1.26)*18,18,['#ddd0b8','#e8dfcd','#bcc4af'][i%3]);circle(x,y,9,'#b7a076');}}
 else if(art==='deco'){rect(0,0,512,512,'#203c50');g.strokeStyle='#c2a05b';g.lineWidth=5;for(let k=0;k<11;k++){g.beginPath();g.moveTo(256,430);g.lineTo(40+k*44,65);g.stroke();}circle(256,345,115,'#c5aa70');rect(0,430,512,82,'#152f40');}
 else{rect(65,100,183,295,'#ae9980');rect(244,180,188,235,'#cdbda3');circle(318,150,75,'#e4d8c4');}
 const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.userData.shared=true;artCache.set(styleId,t);return t;
}

const panelCache=new Map();export function wallPanelTexture(styleId){if(panelCache.has(styleId))return panelCache.get(styleId);const c=document.createElement('canvas');c.width=c.height=512;paintWallDecor(c.getContext('2d'),512,wallDecorProfile(styleId).pattern);const t=new THREE.CanvasTexture(c);t.colorSpace=THREE.SRGBColorSpace;t.userData.shared=true;panelCache.set(styleId,t);return t;}
