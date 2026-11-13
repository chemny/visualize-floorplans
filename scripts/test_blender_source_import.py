"""Blender-only API check; ordinary unittest discovery never imports bpy."""
def main():
 """Blender --background --factory-startup --python scripts/test_blender_source_import.py"""
 import sys,importlib.util,math,base64,tempfile,json
 from pathlib import Path
 import bpy
 from mathutils import Matrix
 path=Path(__file__).parent/'production/import_blender.py';spec=importlib.util.spec_from_file_location('source_import',path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
 t={'repeat':[2,3],'center':[.5,.5],'offset':[.1,.2],'rotation':math.pi/2,'flipY':True}
 a=m.texture_uv((.7,.2),t);assert abs(a[0])<1e-6 and abs(a[1]-.1)<1e-6,a
 t['flipY']=False;assert abs(m.texture_uv((.7,.2),t)[1]-.9)<1e-6
 mat=bpy.data.materials.new('test');source={'name':'test-sliding-leaf','kind':'furniture','objectId':'door','visible':True,'openingKind':'sliding','positions':[0,0,0,1,0,0,1,1,0,0,1,0],'normals':[0,0,1]*4,'uv':[0,0,1,0,1,1,0,1],'indices':[0,1,2,0,2,3],'groups':[{'start':0,'count':3,'materialIndex':5},{'start':3,'count':3,'materialIndex':4}],'materials':[0],'matrix':[1,0,0,0,0,2,0,0,0,0,1,0,1,2,3,1]}
 bundle={'schemeSha256':'fixture','state':{'furniture':[{'id':'door','type':'wardrobe'}]}}
 objects,rows=m.import_meshes({'meshes':[source]},bundle,{0:mat},bpy.context.scene);o=objects[0];assert not o.hide_render;assert all(p.material_index==0 for p in o.data.polygons);assert len(o.data.uv_layers.active.data)==6;assert tuple(o.data.uv_layers.active.data[3].uv)==(0,0);assert tuple(o.data.uv_layers.active.data[5].uv)==(0,1);assert rows[0]['customNormalVertices']==4;bpy.context.view_layer.update();assert all(n.vector.dot(m.Vector((0,-1,0)))>.999 for n in o.data.corner_normals);assert tuple(o.data.vertices[2].co)==(2,-3,4)
 # Non-uniform + reflection transform preserves outward normals and winding.
 source['matrix'][0]=-1;objects,_=m.import_meshes({'meshes':[source]},bundle,{0:mat},bpy.context.scene);assert list(objects[0].data.polygons[0].vertices)==[2,1,0]
 camdata=bpy.data.cameras.new('test-camera');cam=bpy.data.objects.new('test-camera',camdata);bpy.context.scene.collection.objects.link(cam);cam.rotation_mode='QUATERNION';bpy.context.scene.render.resolution_x=1280;bpy.context.scene.render.resolution_y=720
 f={'pointMm':[6500,11000],'eyeMm':1600,'yawRadians':1.4,'pitchRadians':-.12,'horizontalFovDegrees':84,'shiftY':.15};audit=m.set_camera(bpy.context.scene,cam,f,{'width':9130,'depth':17160});assert audit['projectionNdcMaxError']<1e-5;assert abs(camdata.shift_y+.15/(2*1280/720))<1e-6
 # Exercise actual nodes: channel-specific image colour spaces and UV transform controls.
 with tempfile.TemporaryDirectory() as tmp:
  image=bpy.data.images.new('one-pixel',width=1,height=1);image.pixels=[.5,.5,.5,1];image.filepath_raw=str(Path(tmp)/'pixel.png');image.file_format='PNG';image.save();uri='data:image/png;base64,'+base64.b64encode(Path(image.filepath_raw).read_bytes()).decode()
  d={'textures':[{'id':0,'dataUrl':uri,'colorSpace':'srgb',**t}],'materials':[{'id':0,'colorLinear':[.8,.7,.6],'roughness':.8,'metalness':0,'opacity':1,'transparent':False,'emissiveLinear':[0,0,0],'emissiveIntensity':0,'map':0,'bumpMap':0,'bumpScale':.001}]}
  materials=m.make_materials(d,Path(tmp));nodes=materials[0].node_tree.nodes;assert nodes['source-map'].image.colorspace_settings.name=='sRGB';assert nodes['source-bumpMap'].image.colorspace_settings.name=='Non-Color';assert nodes['source-map'].image!=nodes['source-bumpMap'].image;assert any(n.bl_idname=='ShaderNodeVectorRotate' and abs(n.inputs['Angle'].default_value+math.pi/2)<1e-6 for n in nodes)
 print('BLENDER_SOURCE_TEST_PASS',json.dumps({'singleMaterialIgnoresFaceGroups':True,'indexedUVLoops':6,'customNormals':True,'nonUniformTransform':True,'mirroredWinding':True,'doorVisibility':True,'cameraShiftAndFov':True,'imageColorSpaces':True,'textureTransforms':True}))

if __name__=='__main__':main()
