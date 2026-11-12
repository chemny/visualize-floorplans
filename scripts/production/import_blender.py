"""Static, same-source H5 mesh import. Blender --background --python ... -- --help.
Animation stays disabled until reviewed route/capture gates are implemented.
"""
import argparse,base64,json,math,sys,hashlib,time,array
from pathlib import Path
import bpy
from mathutils import Vector,Matrix
sys.path.insert(0,str(Path(__file__).resolve().parent))
from blender_lighting_profile import validate as validate_lighting,fixture_power

def args():
 p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--runtime',help='Optional prepared geometry.bin + scene.json of the same model/state/scheme');p.add_argument('--route');p.add_argument('--frame',type=int);p.add_argument('--out',required=True);p.add_argument('--animation',action='store_true');p.add_argument('--stills',action='store_true');p.add_argument('--views');p.add_argument('--resolution',type=int,default=1280);p.add_argument('--engine',choices=['eevee','cycles'],default='eevee');p.add_argument('--samples',type=int,default=96);p.add_argument('--render-profile',help='Explicit case lighting/material presentation JSON');p.add_argument('--review-only',action='store_true',help='Static review only; preserve unconfirmed source status');return p.parse_args(sys.argv[sys.argv.index('--')+1:])

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def convert(v):return (v[0],-v[2],v[1])
def texture_uv(uv,t):
 x,y=uv;cx,cy=t.get('center',[0,0]);sx,sy=t.get('repeat',[1,1]);ox,oy=t.get('offset',[0,0]);r=t.get('rotation',0);c,s=math.cos(r),math.sin(r)
 u=sx*(c*(x-cx)+s*(y-cy))+cx+ox;v=sy*(-s*(x-cx)+c*(y-cy))+cy+oy
 return (u,v if t.get('flipY',True) else 1-v)

def load_scene(a):
 b=json.loads(Path(a.bundle).read_text());assert b.get('schema')=='floor-visualization-production/1.0'
 confirmed=all(v['status']=='confirmed' for v in b['confirmations'].values())
 if not confirmed and not a.review_only:raise ValueError('Unconfirmed source requires explicit --review-only for static review; statuses are never changed')
 if a.runtime:
  p=Path(a.runtime);d=json.loads((p/'scene.json').read_text());raw=(p/'geometry.bin').read_bytes()
  for k in ['schemeSha256','model','state']:
   if d[k]!=b[k]:raise ValueError('Prepared runtime differs from bundle '+k)
  for m in d['meshes']:
   for key in ['positions','normals','uv','indices']:
    desc=m.get(key)
    if desc:
     vals=array.array('I' if key=='indices' else 'f');vals.frombytes(raw[desc['offset']:desc['offset']+desc['count']*4]);m[key]=vals.tolist()
  provenance={'runtimeGeometrySha256':hashlib.sha256(raw).hexdigest(),'runtimeSceneSha256':hashlib.sha256((p/'scene.json').read_bytes()).hexdigest()}
 else:d=b['scene'];provenance={}
 return b,d,provenance

def mapping_nodes(nodes,links,t):
 uv=nodes.new('ShaderNodeTexCoord');sub=nodes.new('ShaderNodeVectorMath');sub.operation='SUBTRACT';cx,cy=t.get('center',[0,0]);sub.inputs[1].default_value=(cx,cy,0);links.new(uv.outputs['UV'],sub.inputs[0]);rot=nodes.new('ShaderNodeVectorRotate');rot.rotation_type='AXIS_ANGLE';rot.inputs['Axis'].default_value=(0,0,1);rot.inputs['Angle'].default_value=-t.get('rotation',0);links.new(sub.outputs['Vector'],rot.inputs['Vector']);scale=nodes.new('ShaderNodeVectorMath');scale.operation='MULTIPLY';scale.inputs[1].default_value=(*t.get('repeat',[1,1]),1);links.new(rot.outputs['Vector'],scale.inputs[0]);add=nodes.new('ShaderNodeVectorMath');add.operation='ADD';ox,oy=t.get('offset',[0,0]);add.inputs[1].default_value=(cx+ox,cy+oy,0);links.new(scale.outputs['Vector'],add.inputs[0]);last=add.outputs['Vector']
 if not t.get('flipY',True):
  mul=nodes.new('ShaderNodeVectorMath');mul.operation='MULTIPLY_ADD';mul.inputs[1].default_value=(1,-1,1);mul.inputs[2].default_value=(0,1,0);links.new(last,mul.inputs[0]);last=mul.outputs['Vector']
 # Respect per-axis wrapping; image REPEAT handles the default case.
 if t.get('wrapS',1000)!=1000 or t.get('wrapT',1000)!=1000:
  sep=nodes.new('ShaderNodeSeparateXYZ');links.new(last,sep.inputs[0]);join=nodes.new('ShaderNodeCombineXYZ')
  for axis,wrap in enumerate([t.get('wrapS',1000),t.get('wrapT',1000)]):
   output=sep.outputs[axis]
   if wrap==1001:
    low=nodes.new('ShaderNodeMath');low.operation='MAXIMUM';low.inputs[1].default_value=.000001;links.new(output,low.inputs[0]);high=nodes.new('ShaderNodeMath');high.operation='MINIMUM';high.inputs[1].default_value=.999999;links.new(low.outputs[0],high.inputs[0]);output=high.outputs[0]
   elif wrap==1002:
    mirror=nodes.new('ShaderNodeMath');mirror.operation='PINGPONG';mirror.inputs[1].default_value=1;links.new(output,mirror.inputs[0]);output=mirror.outputs[0]
   links.new(output,join.inputs[axis])
  last=join.outputs[0]
 return last

def make_materials(data,out):
 images={};folder=out/'textures';folder.mkdir(exist_ok=True)
 def image_for(tid,is_data):
  key=(tid,is_data)
  if key not in images:
   t=data['textures'][tid];file=folder/(str(tid)+'.png');file.write_bytes(base64.b64decode(t['dataUrl'].split(',',1)[1]));im=bpy.data.images.load(str(file),check_existing=False);im.colorspace_settings.name='Non-Color' if is_data or t.get('colorSpace')!='srgb' else 'sRGB';im.pack();images[key]=im
  return images[key]
 materials={}
 for m in data['materials']:
  mat=bpy.data.materials.new('H5-'+str(m['id'])+'-'+str(m.get('role') or 'surface'));mat.use_nodes=True;mat['sourceMaterialId']=m['id'];nodes=mat.node_tree.nodes;links=mat.node_tree.links;p=nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*m['colorLinear'],1);p.inputs['Roughness'].default_value=m['roughness'];p.inputs['Metallic'].default_value=m['metalness'];p.inputs['Alpha'].default_value=m['opacity'] if m['transparent'] else 1
  if m['transparent']:mat.surface_render_method='DITHERED';mat.use_transparency_overlap=False
  if any(m.get('emissiveLinear',[0,0,0])):p.inputs['Emission Color'].default_value=(*m['emissiveLinear'],1);p.inputs['Emission Strength'].default_value=m['emissiveIntensity']
  for prop,is_bump in [('map',False),('bumpMap',True)]:
   tid=m.get(prop)
   if tid is None:continue
   tex=nodes.new('ShaderNodeTexImage');tex.name='source-'+prop;tex.image=image_for(tid,is_bump);tex.extension='REPEAT';links.new(mapping_nodes(nodes,links,data['textures'][tid]),tex.inputs['Vector']);tex['sourceTextureId']=tid
   if is_bump:
    bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=1;bump.inputs['Distance'].default_value=abs(m.get('bumpScale',0));bump.invert=m.get('bumpScale',0)<0;links.new(tex.outputs['Color'],bump.inputs['Height']);links.new(bump.outputs['Normal'],p.inputs['Normal'])
   else:
    mix=nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1;mix.inputs[2].default_value=(*m['colorLinear'],1);links.new(tex.outputs['Color'],mix.inputs[1]);links.new(mix.outputs[0],p.inputs['Base Color'])
  materials[m['id']]=mat
 return materials

def import_meshes(data,bundle,materials,scene):
 hidden_types=set(data.get('presentationProfile',bundle.get('presentationProfile',{})).get('hiddenTypes',[]));hidden={f['id'] for f in bundle['state']['furniture'] if f['type'] in hidden_types or f.get('planPoint') or f.get('laundryOwner')}
 imported=[];rows=[];axes=Matrix(((1,0,0),(0,0,-1),(0,1,0)))
 for index,m in enumerate(data['meshes']):
  matrix=Matrix([m['matrix'][i::4] for i in range(4)]);pos=m['positions'];vertices=[convert(matrix@Vector(pos[i:i+3])) for i in range(0,len(pos),3)];ids=m['indices'] if m['indices'] is not None else list(range(len(vertices)));faces=[ids[i:i+3] for i in range(0,len(ids),3)];
  if matrix.to_3x3().determinant()<0:faces=[list(reversed(f)) for f in faces]
  mesh=bpy.data.meshes.new(m['name']);mesh.from_pydata(vertices,[],faces);mesh.update();obj=bpy.data.objects.new(m['name'],mesh);scene.collection.objects.link(obj);obj['sourceMeshIndex']=index;obj['sourceKind']=m['kind'];obj['sourceObjectId']=m['objectId'] or '';obj['schemeSha256']=bundle['schemeSha256'];obj.hide_render=not m['visible'] or m['objectId'] in hidden or m['name'].startswith('shower-drain');imported.append(obj)
  for mid in m['materials']:mesh.materials.append(materials[mid])
  if len(m['materials'])>1:
   for g in m['groups']:
    if g['materialIndex']>=len(m['materials']):raise ValueError('Invalid multi-material group '+m['name'])
    for poly in mesh.polygons[g['start']//3:(g['start']+g['count'])//3]:poly.material_index=g['materialIndex']
  # Three.js ignores geometry face groups when a mesh uses a single material.
  uv_error=0
  if m.get('uv'):
   layer=mesh.uv_layers.new(name='source-UV')
   for loop in mesh.loops:
    original=m['uv'][loop.vertex_index*2:loop.vertex_index*2+2];layer.data[loop.index].uv=original;uv_error=max(uv_error,max(abs(layer.data[loop.index].uv[k]-original[k]) for k in range(2)))
  normal_count=0
  if m.get('normals'):
   nmat=axes@matrix.to_3x3().inverted().transposed();normal=[(nmat@Vector(m['normals'][i:i+3])).normalized() for i in range(0,len(m['normals']),3)]
   for poly in mesh.polygons:poly.use_smooth=True
   mesh.normals_split_custom_set_from_vertices(normal);normal_count=len(normal)
  max_error=max((Vector(v.co)-Vector(vertices[i])).length for i,v in enumerate(mesh.vertices)) if vertices else 0
  rows.append({'index':index,'name':m['name'],'objectId':m['objectId'],'vertices':len(vertices),'triangles':len(faces),'uvLoops':len(mesh.uv_layers.active.data) if mesh.uv_layers else 0,'uvMaxError':uv_error,'customNormalVertices':normal_count,'worldPositionMaxErrorM':max_error,'hidden':obj.hide_render,'openingKind':m.get('openingKind')})
 return imported,rows

def set_camera(scene,cam,f,model):
 aspect=scene.render.resolution_x/scene.render.resolution_y;camera=cam.data;camera.type='PERSP';camera.sensor_fit='HORIZONTAL';camera.sensor_width=36;camera.lens=36/(2*math.tan(math.radians(f.get('horizontalFovDegrees',70))/2));camera.shift_x=0;camera.shift_y=-f.get('shiftY',0)/(2*aspect);camera.clip_start=.04;camera.clip_end=50
 x=(f['pointMm'][0]-model['width']/2)/1000;z=(f['pointMm'][1]-model['depth']/2)/1000;cam.location=convert((x,f['eyeMm']/1000,z));yaw=f['yawRadians'];pitch=f['pitchRadians'];direction=Vector(convert((math.cos(yaw)*math.cos(pitch),math.sin(pitch),math.sin(yaw)*math.cos(pitch))));cam.rotation_quaternion=direction.to_track_quat('-Z','Y');bpy.context.view_layer.update()
 # Check actual Blender projection against the source perspective at five ray offsets.
 proj=cam.calc_matrix_camera(bpy.context.evaluated_depsgraph_get(),x=scene.render.resolution_x,y=scene.render.resolution_y);expected_shift=f.get('shiftY',0);errors=[]
 for x,y in [(0,0),(.4,0),(-.4,.3),(0,-.3),(.2,.4)]:
  v=proj@Vector((x,y,-2,1));actual=(v.x/v.w,v.y/v.w);tan=math.tan(math.radians(f.get('horizontalFovDegrees',70))/2);expected=(x/(2*tan),y/(2*tan/aspect)+expected_shift);errors.append(max(abs(a-b) for a,b in zip(actual,expected)))
 if max(errors)>1e-5:raise ValueError('Camera projection does not match source: '+str(errors))
 return {'sourceFrame':f,'horizontalFovDegrees':math.degrees(camera.angle_x),'shiftY':camera.shift_y,'projectionNdcMaxError':max(errors),'location':list(cam.location),'quaternion':list(cam.rotation_quaternion)}

def configure_lighting(scene,data,profile):
 validate_lighting(profile)
 world=bpy.data.worlds.new('RenderWorld');scene.world=world;world.use_nodes=True;bg=world.node_tree.nodes['Background'];bg.inputs['Color'].default_value=(*profile.get('worldColor',[.72,.78,.88]),1);bg.inputs['Strength'].default_value=profile.get('worldStrength',.35)
 if 'cameraBackgroundStrength' in profile:
  nodes=world.node_tree.nodes;links=world.node_tree.links;visible=nodes.new('ShaderNodeBackground');visible.inputs['Color'].default_value=(*profile.get('cameraBackgroundColor',profile.get('worldColor',[.72,.78,.88])),1);visible.inputs['Strength'].default_value=profile['cameraBackgroundStrength'];path=nodes.new('ShaderNodeLightPath');mask=nodes.new('ShaderNodeMath');mask.operation='MAXIMUM';links.new(path.outputs['Is Camera Ray'],mask.inputs[0]);links.new(path.outputs['Is Transmission Ray'],mask.inputs[1]);mix=nodes.new('ShaderNodeMixShader');links.new(mask.outputs[0],mix.inputs[0]);links.new(bg.outputs[0],mix.inputs[1]);links.new(visible.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],nodes.get('World Output').inputs['Surface'])
 lights=[]
 if profile.get('fixtureWattsPerIntensity'):
  kinds={f['id']:f.get('type') for f in data.get('state',{}).get('furniture',[])}  # the case profile decides which fixture types are main or auxiliary
  for l in data.get('illumination',[]):
   if not l['enabled']:continue
   cone=profile.get('spotFixturesAsCones') and l.get('type')=='SpotLight' and l.get('target')
   light=bpy.data.lights.new('Source-fixture-'+l['fixtureId'],'SPOT' if cone else 'POINT');light.energy=fixture_power(profile,l['fixtureId'],kinds.get(l['fixtureId']),l['intensity']);light.color=l['colorLinear'];light.shadow_soft_size=.16;obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=convert(l['position'])
   if cone:
    # A recessed downlight throws a cone at its target; as a point light it would also light the ceiling around it.
    light.spot_size=min(math.pi,2*l.get('angle',.5));light.spot_blend=min(1,max(0,l.get('penumbra',.3)));obj.rotation_euler=(Vector(convert(l['target']))-obj.location).to_track_quat('-Z','Y').to_euler()
  if profile.get('excludeFixtureHousingShadows'):
   ids={l['fixtureId'] for l in data.get('illumination',[])}
   for obj in scene.objects:
    if obj.get('sourceObjectId') in ids:obj.visible_shadow=False
 for spec in profile.get('lights',[]):
  light=bpy.data.lights.new(spec['name'],spec['type']);light.energy=spec['energy'];light.color=spec.get('color',[1,1,1]);obj=bpy.data.objects.new(light.name,light);scene.collection.objects.link(obj);obj.location=convert(spec['positionThree']);target=Vector(convert(spec['targetThree']));obj.rotation_euler=(target-obj.location).to_track_quat('-Z','Y').to_euler();obj.visible_camera=not spec.get('hideFromCamera',False);obj.visible_glossy=not spec.get('hideFromGlossy',False);obj.visible_transmission=not spec.get('hideFromCamera',False)
  if spec['type']=='AREA':light.shape='RECTANGLE';light.size=spec['width'];light.size_y=spec['height']
  elif spec['type']=='SUN':light.angle=math.radians(spec.get('angleDegrees',5))
  lights.append(spec)
 return lights

def apply_profile(materials,data,profile):
 for key,patch in profile.get('materials',{}).items():
  mat=materials[int(key)];p=mat.node_tree.nodes.get('Principled BSDF')
  for name,value in patch.get('inputs',{}).items():p.inputs[name].default_value=value
  if patch.get('thinGlass'):
   # Material treatment only: retain every original window pane and frame.
   nodes=mat.node_tree.nodes;links=mat.node_tree.links;out=nodes.get('Material Output');glass=nodes.new('ShaderNodeBsdfGlass');glass.inputs['Color'].default_value=(.98,.99,1,1);glass.inputs['Roughness'].default_value=.035;glass.inputs['IOR'].default_value=1.45;transparent=nodes.new('ShaderNodeBsdfTransparent');mix=nodes.new('ShaderNodeMixShader');mix.inputs[0].default_value=.15;links.new(transparent.outputs[0],mix.inputs[1]);links.new(glass.outputs[0],mix.inputs[2]);links.new(mix.outputs[0],out.inputs['Surface'])

def run(a):
 if a.animation:raise ValueError('Blender animation disabled: reviewed route/preview capture gates not integrated')
 begin=time.monotonic();out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True);bundle,data,provenance=load_scene(a);profile=json.loads(Path(a.render_profile).read_text()) if a.render_profile else {};route=json.loads(Path(a.route).read_text()) if a.route else None
 if route and route['schemeSha256']!=bundle['schemeSha256']:raise ValueError('Route belongs to another scheme')
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);scene=bpy.context.scene;scene.render.engine='CYCLES' if a.engine=='cycles' else 'BLENDER_EEVEE';scene.render.resolution_x=a.resolution;scene.render.resolution_y=round(a.resolution*9/16);scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGB';scene.render.fps=route['fps'] if route else 24;scene.view_settings.view_transform='AgX';scene.view_settings.look='AgX - Medium High Contrast';scene.view_settings.exposure=profile.get('exposure',0)
 device='CPU'
 if a.engine=='cycles':
  prefs=bpy.context.preferences.addons['cycles'].preferences
  try:
   prefs.compute_device_type='METAL';prefs.get_devices()
   for d in prefs.devices:d.use=d.type=='METAL'
   if any(d.type=='METAL' for d in prefs.devices):scene.cycles.device='GPU';device='METAL'
  except Exception:pass
  scene.cycles.samples=a.samples;scene.cycles.use_denoising=True;scene.cycles.adaptive_threshold=.025;scene.cycles.max_bounces=8;scene.cycles.diffuse_bounces=4;scene.cycles.glossy_bounces=4;scene.cycles.transmission_bounces=6
 materials=make_materials(data,out);imported,rows=import_meshes(data,bundle,materials,scene);apply_profile(materials,data,profile);lights=configure_lighting(scene,data,profile)
 camera=bpy.data.cameras.new('SameSourceCamera');cam=bpy.data.objects.new(camera.name,camera);scene.collection.objects.link(cam);scene.camera=cam;cam.rotation_mode='QUATERNION'
 f=route['frames'][a.frame if a.frame is not None else 0] if route else None;camera_audit=set_camera(scene,cam,f,bundle['model']) if f else None
 audit={'schema':'blender-static-source-audit/2','schemeSha256':bundle['schemeSha256'],'confirmations':bundle['confirmations'],'reviewOnly':a.review_only,'renderAccepted':False,'animationEnabled':False,'meshCount':len(imported),'meshRows':rows,'camera':camera_audit,'sourceLayoutSha256':digest(bundle['state']),'sourceGeometryProvenance':provenance,'lightingProfile':profile,'sourceDoorVisibilityPreserved':all(obj.hide_render==(not bool(m['visible'])) for obj,m in zip(imported,data['meshes']) if m.get('openingKind')=='sliding'),'maxUvError':max(r['uvMaxError'] for r in rows),'maxPositionErrorM':max(r['worldPositionMaxErrorM'] for r in rows),'engine':scene.render.engine,'device':device,'samples':a.samples,'loadSeconds':time.monotonic()-begin}
 assert audit['maxUvError']<1e-5 and audit['maxPositionErrorM']<1e-5
 (out/'blender-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));bpy.ops.wm.save_as_mainfile(filepath=str(out/'03-同源场景.blend'))
 if a.stills:
  if f:
   scene.render.filepath=str(out/'living-cycles.png');started=time.monotonic();bpy.ops.render.render(write_still=True);audit['renderSeconds']=time.monotonic()-started
  elif a.views:
   for view in json.loads(Path(a.views).read_text()):
    at=view['point'];target=view['target'];f={'pointMm':at,'eyeMm':view.get('eyeMm',1600),'yawRadians':math.atan2(target[1]-at[1],target[0]-at[0]),'pitchRadians':math.atan2(view.get('targetHeightMm',1250)-view.get('eyeMm',1600),math.dist(at,target)),'horizontalFovDegrees':view.get('horizontalFovDegrees',76),'shiftY':view.get('shiftY',0)};set_camera(scene,cam,f,bundle['model']);scene.render.filepath=str(out/(view['name']+'.png'));bpy.ops.render.render(write_still=True)
  else:raise ValueError('Static render needs --route/--frame or --views')
 (out/'blender-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2));print('PRODUCTION_IMPORT_PASS',json.dumps({k:audit[k] for k in ['meshCount','maxUvError','maxPositionErrorM','engine','device']}))
if __name__=='__main__':run(args())
