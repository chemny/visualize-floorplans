// Room-owned outline trim can contain real short corner returns. Ordinary
// user furniture retains its existing lower bounds; never enlarge the geometry.
export function validateFurniturePlanSize(f){
 const minimum=(f.type==='skirting'&&f.assemblyOwner?.kind==='room') ? .5 : (f.type==='endpanel' ? 15 : 50);
 if(!['w','d','cx','cy','rot'].every(k=>Number.isFinite(f[k]))||f.w<minimum||f.d<30||f.w>15000||f.d>15000||Math.abs(f.cx)>50000||Math.abs(f.cy)>50000)throw Error('尺寸超出范围：'+f.id);
 return f;
}
