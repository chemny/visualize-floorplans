"""Scoped room light/background overrides inside Blender; never change furniture/materials."""
import math

def apply(scene,profile):
 import bpy
 from mathutils import Vector
 if profile.get('schema')!='blender-room-presentation/1':raise ValueError('Unsupported room presentation')
 changes=[];exterior_materials={}
 for name in profile.get("disableExterior",[]):
  o=scene.objects.get(name)
  if not o or o.type!="MESH" or o.get("sourceObjectId") or o.get("schemeSha256"):raise ValueError("Only unbound exterior presentation meshes can be disabled")
  o.hide_render=True;changes.append({"disabledExterior":name})
 for spec in profile.get('fixtureLights',[]):
  o=scene.objects.get(spec['name'])
  if not o or o.type!='LIGHT' or o.data.type!='POINT':raise ValueError('Existing point fixture required')
  energy=spec['energy'];color=spec.get('color',list(o.data.color));radius=spec.get('radius',o.data.shadow_soft_size)
  if not math.isfinite(energy) or not 0<energy<=200 or len(color)!=3 or any(not math.isfinite(x) or not 0<=x<=1 for x in color) or not 0<=radius<=1:raise ValueError('Invalid local light settings')
  changes.append({'name':o.name,'beforeEnergy':o.data.energy,'afterEnergy':energy});o.data.energy=energy;o.data.color=color;o.data.shadow_soft_size=radius
 for spec in profile.get('exteriorCards',[]):
  if scene.objects.get(spec['name']):raise ValueError('Exterior card name already exists')
  coords=spec.get('uv',[(0,0),(1,0),(1,1),(0,1)])
  if len(coords)!=4 or any(len(v)!=2 or not all(math.isfinite(x) for x in v) for v in coords):raise ValueError('Invalid exterior UV coordinates')
  if any(not 0<=u<=1 for u,v in coords) and spec.get('horizontalWrap')!='mirror':raise ValueError('Exterior horizontal UV range needs explicit wrapping')
  if any(not 0<=v<=1 for u,v in coords) and not spec.get('verticalEdgeFade',0)>0:raise ValueError('Exterior vertical UV range needs edge treatment')
  material=bpy.data.materials.get(spec['material'])
  if not material:raise ValueError('Existing exterior material required')
  wrap=spec.get('horizontalWrap')
  if wrap:
   if wrap!='mirror' or not material.node_tree:raise ValueError('Unsupported exterior horizontal wrap')
   fade=spec.get('verticalEdgeFade',0)
   if not isinstance(fade,(int,float)) or not math.isfinite(fade) or not 0<=fade<=1:raise ValueError('Invalid exterior edge fade')
   key=(material.name,wrap,fade)
   if key not in exterior_materials:
    original=material;material=original.copy();material.name=original.name+'-presentation-mirror';material['presentationRole']='exterior'
    nodes=material.node_tree.nodes;links=material.node_tree.links;uv=nodes.new('ShaderNodeTexCoord');separate=nodes.new('ShaderNodeSeparateXYZ');mirror=nodes.new('ShaderNodeMath');mirror.operation='PINGPONG';mirror.inputs[1].default_value=1;combine=nodes.new('ShaderNodeCombineXYZ');links.new(uv.outputs['UV'],separate.inputs[0]);links.new(separate.outputs['X'],mirror.inputs[0]);links.new(mirror.outputs[0],combine.inputs['X']);links.new(separate.outputs['Y'],combine.inputs['Y'])
    textures=[n for n in nodes if n.type=='TEX_IMAGE']
    if not textures:raise ValueError('Exterior wrap requires image texture')
    for texture in textures:
     if texture.inputs['Vector'].is_linked:raise ValueError('Exterior texture already has explicit mapping')
     texture.extension='EXTEND';links.new(combine.outputs[0],texture.inputs['Vector'])
     if fade:
      image=texture.image
      if not image or len(image.pixels)<4:raise ValueError('Decoded exterior image required')
      targets=[l.to_socket for l in texture.outputs['Color'].links]
      def edge_color(y):
       width,height=image.size;values=[image.pixels[(min(height-1,int(height*y))*width+min(width-1,int(width*x)))*4+j] for x in [.125,.375,.625,.875] for j in range(3)]
       rgb=[sum(values[j::3])/4 for j in range(3)]
       if image.colorspace_settings.name=='sRGB':rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
       return (*rgb,1)
      below=nodes.new('ShaderNodeMath');below.operation='MULTIPLY';below.inputs[1].default_value=-1/fade;below.use_clamp=True;links.new(separate.outputs['Y'],below.inputs[0])
      above=nodes.new('ShaderNodeMath');above.operation='SUBTRACT';above.inputs[1].default_value=1;links.new(separate.outputs['Y'],above.inputs[0]);factor=nodes.new('ShaderNodeMath');factor.operation='MULTIPLY';factor.inputs[1].default_value=1/fade;factor.use_clamp=True;links.new(above.outputs[0],factor.inputs[0])
      ground=nodes.new('ShaderNodeMixRGB');ground.inputs[2].default_value=edge_color(.005);links.new(below.outputs[0],ground.inputs[0]);links.new(texture.outputs['Color'],ground.inputs[1]);sky=nodes.new('ShaderNodeMixRGB');sky.inputs[2].default_value=edge_color(.99);links.new(factor.outputs[0],sky.inputs[0]);links.new(ground.outputs[0],sky.inputs[1])
      for target in targets:links.new(sky.outputs[0],target)
    exterior_materials[key]=material
   else:material=exterior_materials[key]
  vertices=spec['vertices']
  if len(vertices)!=4 or any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in vertices):raise ValueError('Invalid background vertices')
  mesh=bpy.data.meshes.new(spec['name']);mesh.from_pydata(vertices,[],[(0,1,2,3)]);mesh.update();obj=bpy.data.objects.new(spec['name'],mesh);scene.collection.objects.link(obj);obj['presentationRole']='exterior';mesh.materials.append(material)
  uv=mesh.uv_layers.new(name='ExteriorUV')
  for loop,xy in zip(uv.data,coords):loop.uv=xy
  obj.visible_shadow=False;obj.visible_diffuse=False;obj.visible_camera=spec.get('cameraVisible',True);obj.visible_transmission=spec.get('transmissionVisible',True);obj.visible_glossy=spec.get('glossyVisible',True)
  changes.append({'exterior':obj.name})
 return changes

def coverage(scene,profile,tour,model):
 """Project actual window bounds through every specified source viewpoint onto its background."""
 from mathutils import Vector
 results=[]
 if profile.get('enclosure'):
  spec=profile['enclosure'];lo=spec['min'];hi=spec['max'];names=spec['faces']
  if len(lo)!=3 or len(hi)!=3 or any(not math.isfinite(x) for x in lo+hi) or any(a>=z for a,z in zip(lo,hi)) or len(set(names))!=6:raise ValueError('Invalid exterior enclosure')
  faces=set()
  for name in names:
   obj=scene.objects.get(name)
   if not obj or obj.get('presentationRole')!='exterior' or len(obj.data.vertices)!=4 or not obj.visible_camera or not obj.visible_transmission:raise ValueError('Incomplete exterior enclosure')
   points=[obj.matrix_world@v.co for v in obj.data.vertices];matched=False
   for axis in range(3):
    for side,target in enumerate((lo[axis],hi[axis])):
     if all(abs(p[axis]-target)<1e-4 for p in points):
      other=[j for j in range(3) if j!=axis];expected={(lo[other[0]],lo[other[1]]),(lo[other[0]],hi[other[1]]),(hi[other[0]],lo[other[1]]),(hi[other[0]],hi[other[1]])}
      if all(any(abs(p[other[0]]-u)<1e-4 and abs(p[other[1]]-v)<1e-4 for p in points) for u,v in expected):faces.add((axis,side));matched=True
   if not matched:raise ValueError('Exterior face leaves a coverage gap')
  if len(faces)!=6:raise ValueError('Exterior enclosure is not closed')
  for f in tour['frames']:
   c=((f['pointMm'][0]-model['width']/2)/1000,-(f['pointMm'][1]-model['depth']/2)/1000,f['eyeMm']/1000)
   if not all(a<x<z for a,x,z in zip(lo,c,hi)):raise ValueError('Source camera outside exterior enclosure')
  for obj in scene.objects:
   if obj.type=='MESH' and obj.get('schemeSha256'):
    for v in obj.bound_box:
     p=obj.matrix_world@Vector(v)
     if not all(a<x<z for a,x,z in zip(lo,p,hi)):raise ValueError('Source geometry outside exterior enclosure')
  results.append({'representation':'closed fixed distant concept enclosure','frames':len(tour['frames']),'fullCoverage':True,'faces':sorted(names),'notSurveyedOutdoorGeometry':True})
 for spec in profile.get('exteriorCards',[]):
  if not spec.get('windowMesh'):continue
  window=scene.objects.get(spec['windowMesh']);card=scene.objects.get(spec['name'])
  if not window or not card:raise ValueError('Missing bound window/background')
  a,z=spec['coverageFrames']
  if not 0<=a<z<=len(tour['frames']):raise ValueError('Invalid coverage interval')
  corners=[card.matrix_world@v.co for v in card.data.vertices];origin=corners[0];u=corners[1]-origin;v=corners[3]-origin;n=u.cross(v).normalized();uu=u.dot(u);vv=v.dot(v);uv=u.dot(v);det=uu*vv-uv*uv
  if det<=1e-10:raise ValueError('Degenerate background')
  misses=[];samples=0
  for i in range(a,z):
   f=tour['frames'][i];c=Vector(((f['pointMm'][0]-model['width']/2)/1000,-(f['pointMm'][1]-model['depth']/2)/1000,f['eyeMm']/1000))
   for q in window.bound_box:
    w=window.matrix_world@Vector(q);ray=w-c;denom=n.dot(ray);samples+=1
    if abs(denom)<1e-10:misses.append(i);continue
    t=n.dot(origin-c)/denom;p=c+ray*t-origin;x=(p.dot(u)*vv-p.dot(v)*uv)/det;y=(p.dot(v)*uu-p.dot(u)*uv)/det
    if t<=1 or not (-1e-5<=x<=1+1e-5 and -1e-5<=y<=1+1e-5):misses.append(i)
  results.append({'card':card.name,'window':window.name,'sourceFrames':[a,z],'samples':samples,'missedFrames':sorted(set(misses)),'fullCoverage':not misses})
 return results
