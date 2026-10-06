"""Run with Blender --background --python import_blender.py -- --bundle ... --route ... --out ...
Imports actual H5 vertices/materials. Does not rebuild approximate furniture.
"""
import argparse, base64, json, math, sys, hashlib
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

def args():
 ap=argparse.ArgumentParser();ap.add_argument('--bundle',required=True);ap.add_argument('--route');ap.add_argument('--out',required=True);ap.add_argument('--animation',action='store_true');ap.add_argument('--stills',action='store_true');ap.add_argument('--views');ap.add_argument('--resolution',type=int,default=640);return ap.parse_args(sys.argv[sys.argv.index('--')+1:])

def run(a):
 out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);bundle=json.loads(Path(a.bundle).read_text(encoding='utf-8'));assert bundle.get('schema')=='floor-visualization-production/1.0','Unsupported production schema';assert all(v['status']=='confirmed' for v in bundle['confirmations'].values()),'Unconfirmed scheme';data=bundle['scene'];route=json.loads(Path(a.route).read_text(encoding='utf-8')) if a.route else None
 if route and route['schemeSha256']!=bundle['schemeSha256']:raise ValueError('Route belongs to another scheme')
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 scene=bpy.context.scene;scene.render.engine='BLENDER_EEVEE';scene.render.resolution_x=a.resolution;scene.render.resolution_y=round(a.resolution*9/16);scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.fps=route['fps'] if route else 24;scene.render.film_transparent=False
 scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=0
 try:scene.eevee.taa_render_samples=16
 except AttributeError:pass
 scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.65,.72,.8,1);scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.3
 texdir=out/'textures';texdir.mkdir(exist_ok=True);images={}
 for t in data['textures']:
  p=texdir/(str(t['id'])+'.png');p.write_bytes(base64.b64decode(t['dataUrl'].split(',',1)[1]));images[t['id']]=bpy.data.images.load(str(p));images[t['id']].pack()
 material_cache={};materials={}
 for m in data['materials']:
  key=json.dumps({k:v for k,v in m.items() if k!='id'},sort_keys=True)
  if key in material_cache:materials[m['id']]=material_cache[key];continue
  mat=bpy.data.materials.new('H5-'+str(m['id'])+'-'+str(m.get('role') or 'surface'));mat.use_nodes=True;p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*m['colorLinear'],1);p.inputs['Roughness'].default_value=m['roughness'];p.inputs['Metallic'].default_value=m['metalness']
  if m['transparent']:
   p.inputs['Alpha'].default_value=m['opacity'];p.inputs['Transmission Weight'].default_value=.5 if m['opacity']<.5 else 0
   mat.surface_render_method='DITHERED';mat.use_transparency_overlap=False
  if m['emissiveIntensity']:
   p.inputs['Emission Color'].default_value=(*m['emissiveLinear'],1);p.inputs['Emission Strength'].default_value=m['emissiveIntensity']
  for prop,is_bump in [('map',False),('bumpMap',True)]:
   tid=m[prop]
   if tid is None:continue
   t=data['textures'][tid];nodes=mat.node_tree.nodes;links=mat.node_tree.links;uv=nodes.new('ShaderNodeTexCoord');mapping=nodes.new('ShaderNodeMapping');mapping.inputs['Scale'].default_value=(*t['repeat'],1);links.new(uv.outputs['UV'],mapping.inputs['Vector']);img=nodes.new('ShaderNodeTexImage');img.image=images[tid];links.new(mapping.outputs['Vector'],img.inputs['Vector'])
   if is_bump:
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.28;bump.inputs['Distance'].default_value=m['bumpScale'];links.new(img.outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
   else:
    mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*m['colorLinear'],1);links.new(img.outputs['Color'],mix.inputs[1]);links.new(mix.outputs[0],p.inputs['Base Color'])
  material_cache[key]=mat;materials[m['id']]=mat
 imported=[];ceilings=[];bounds={}
 for index,m in enumerate(data['meshes']):
  matrix=Matrix([m['matrix'][i::4] for i in range(4)]);positions=m['positions'];vertices=[]
  for i in range(0,len(positions),3):
   v=matrix@Vector(positions[i:i+3]);vertices.append((v.x,-v.z,v.y))
  ids=m['indices'] or list(range(len(vertices)));faces=[ids[i:i+3] for i in range(0,len(ids),3)]
  mesh=bpy.data.meshes.new(m['name']);mesh.from_pydata(vertices,[],faces);mesh.update();obj=bpy.data.objects.new(m['name'],mesh);scene.collection.objects.link(obj);obj['sourceMeshIndex']=index;obj['sourceKind']=m['kind'];obj['sourceObjectId']=m['objectId'] or '';obj['schemeSha256']=bundle['schemeSha256'];obj.hide_render=not m['visible'];imported.append(obj)
  for mid in m['materials']:mesh.materials.append(materials[mid])
  for g in m['groups']:
   for poly in mesh.polygons[g['start']//3:(g['start']+g['count'])//3]:poly.material_index=g['materialIndex']
  for poly in mesh.polygons:poly.use_smooth=m['kind']=='furniture'
  lo=[min(v[i] for v in vertices) for i in (0,1,2)];hi=[max(v[i] for v in vertices) for i in (0,1,2)]
  if m['kind']=='architecture' and abs(lo[2]-bundle['model']['height']/1000)<.005 and hi[2]-lo[2]<.01:ceilings.append(obj)
  if m['objectId'] and m['kind']=='furniture':
   fid=m['objectId'];old=bounds.get(fid,{'min':lo[:],'max':hi[:]});bounds[fid]={'min':[min(lo[i],old['min'][i]) for i in (0,1,2)],'max':[max(hi[i],old['max'][i]) for i in (0,1,2)]}
 # Room ceiling area lights: documented render lighting, separate from scheme geometry.
 origin=bundle['coordinates']['origin']
 def point(p,z):return ((p[0]-origin[0])/1000,-(p[1]-origin[1])/1000,z)
 for r in bundle['model']['rooms']:
  xy=r['at'];light=bpy.data.lights.new('Room-'+r['id'],'AREA');poly=r['poly'];area=abs(sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(poly,poly[1:]+poly[:1])))/2e6;light.energy=max(75,min(240,area*8));light.color=(1,.91,.79);light.shape='DISK';light.size=1.6;obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=point(xy,2.64)
 sun=bpy.data.lights.new('Daylight','SUN');sun.energy=1.6;sun.angle=math.radians(12);obj=bpy.data.objects.new('Daylight',sun);scene.collection.objects.link(obj);obj.rotation_euler=(math.radians(24),math.radians(-35),math.radians(-20))
 camera=bpy.data.cameras.new('WalkCamera');cam=bpy.data.objects.new('WalkCamera',camera);scene.collection.objects.link(cam);scene.camera=cam;camera.lens=23;camera.clip_start=.06;camera.clip_end=100;cam.rotation_mode='QUATERNION'
 def aim(location,target):cam.location=location;cam.rotation_quaternion=(Vector(target)-Vector(location)).to_track_quat('-Z','Y')
 # Current H5 balcony sliders are shown closed. Move their leaves for walking access,
 # keeping opening position/width unchanged; record the presentation-only change.
 sliders=[obj for obj,m in zip(imported,data['meshes']) if m.get('openingKind')=='sliding']
 for obj in sliders:obj.hide_render=True
 scene['schemeSha256']=bundle['schemeSha256'];scene['routePresentation']='Sliding panels hidden only during tour for open access; wall/window openings unchanged.'
 if route:
  scene.frame_start=1;scene.frame_end=len(route['frames'])
  for f in route['frames']:
   cam.location=point(f['pointMm'],f['eyeMm']/1000);yaw=f['yawRadians'];pitch=f['pitchRadians'];direction=Vector((math.cos(yaw)*math.cos(pitch),-math.sin(yaw)*math.cos(pitch),math.sin(pitch)));cam.rotation_quaternion=direction.to_track_quat('-Z','Y');cam.keyframe_insert(data_path='location',frame=f['frame']);cam.keyframe_insert(data_path='rotation_quaternion',frame=f['frame'])
  # Dense samples with linear interpolation prevent Bezier ease-in/ease-out pauses.
  try:
   for layer in cam.animation_data.action.layers:
    for strip in layer.strips:
     for bag in strip.channelbags:
      for curve in bag.fcurves:
       for key in curve.keyframe_points:key.interpolation='LINEAR'
  except AttributeError:pass
  scene.frame_set(1)
 bpy.ops.wm.save_as_mainfile(filepath=str(out/'03-同源场景.blend'))
 expected={f['id'] for f in bundle['state']['furniture']};audit={'schemeSha256':bundle['schemeSha256'],'meshCount':len(imported),'furnitureIds':sorted(bounds),'missingFurniture':sorted(expected-set(bounds)),'heightM':bundle['model']['height']/1000,'bounds':bounds,'coordinateConversion':'(Three.X,-Three.Z,Three.Y)','ceilingMeshes':len(ceilings),'slidingPanelsOpenedForTour':len(sliders),'lighting':'Blender daylight plus room area lights; Three.js pixels are not asserted identical','renderAccepted':False}
 assert not audit['missingFurniture'];assert all(b['max'][2]<=2.751 for b in bounds.values()),'Furniture exceeds ceiling'
 (out/'blender-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2), encoding='utf-8')
 if a.stills:
  # Hide ceilings only for bird's eye. Stills retain original sliding panels.
  cam.animation_data_clear()
  for obj in sliders:obj.hide_render=False
  for obj in ceilings:obj.hide_render=True
  camera.type='ORTHO';camera.ortho_scale=19;aim((11,-15,18),(0,0,0));scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.filepath=str(out/'04-鸟瞰.png');bpy.ops.render.render(write_still=True)
  for obj in ceilings:obj.hide_render=False
  camera.type='PERSP';camera.lens=24;scene.render.resolution_x=1200;scene.render.resolution_y=675
  views=json.loads(Path(a.views).read_text(encoding='utf-8')) if a.views else [];
  for view in views:
   name,p,target=view['name'],view['point'],view['target']
   aim(point(p,1.6),point(target,1.25));scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True)
 if a.animation:
  # Reload saved camera action after still renders to keep the same frame path.
  bpy.ops.wm.open_mainfile(filepath=str(out/'03-同源场景.blend'));scene=bpy.context.scene;scene.render.resolution_x=a.resolution;scene.render.resolution_y=round(a.resolution*9/16);frames=out/'frames';frames.mkdir(exist_ok=True);scene.render.filepath=str(frames/'frame-');bpy.ops.render.render(animation=True)
 print('PRODUCTION_IMPORT_PASS',json.dumps({'meshes':len(imported),'furniture':len(bounds),'out':str(out)}))
if __name__=='__main__':run(args())
