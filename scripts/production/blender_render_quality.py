"""Explicit, bound animation sampling/diagnostic settings; no scene/material edits."""
import math

def validate(profile,samples):
 if profile.get('schema')!='blender-render-quality/1':raise ValueError('Unsupported Blender quality profile')
 allowed={'schema','adaptiveSampling','minimumSamples','noiseThreshold','retainDiagnosticPasses','causticsReflective','causticsRefractive','denoiser','denoisingInputPasses','useDenoising','motionBlur','persistentData','pngCompression','seed'}
 if set(profile)-allowed:raise ValueError('Unknown Blender quality option')
 for key in ('adaptiveSampling','retainDiagnosticPasses','causticsReflective','causticsRefractive','useDenoising','motionBlur','persistentData'):
  if key in profile and type(profile[key])!=bool:raise ValueError('Invalid '+key)
 minimum=profile.get('minimumSamples',0);threshold=profile.get('noiseThreshold',.015)
 if type(minimum)!=int or not 0<=minimum<=samples:raise ValueError('Invalid minimumSamples')
 if type(threshold) not in (int,float) or not math.isfinite(threshold) or not .001<=threshold<=.1:raise ValueError('Invalid noiseThreshold')
 if profile.get('denoiser','OPENIMAGEDENOISE') not in ('OPENIMAGEDENOISE','OPTIX'):raise ValueError('Invalid denoiser')
 if profile.get('denoisingInputPasses','RGB_ALBEDO_NORMAL') not in ('RGB','RGB_ALBEDO','RGB_ALBEDO_NORMAL'):raise ValueError('Invalid denoising passes')
 if profile.get('motionBlur',False):raise ValueError('Exact-pose capture has no animated shutter trajectory; motion blur requires a separate verified animation method')
 if 'pngCompression' in profile and (type(profile['pngCompression']) is not int or not 0<=profile['pngCompression']<=100):raise ValueError('Invalid pngCompression')
 if type(profile.get('seed',42)) is not int or not 0<=profile.get('seed',42)<2**31:raise ValueError('Invalid seed')
 return profile

def apply(scene,profile,samples):
 import bpy
 validate(profile,samples)
 # Speed options that leave the rendered picture unchanged: keep scene data between frames, and write lossless PNG with less compression work.
 if 'persistentData' in profile:scene.render.use_persistent_data=profile['persistentData']
 if 'pngCompression' in profile:scene.render.image_settings.compression=profile['pngCompression']
 scene.render.use_motion_blur=False;scene.cycles.seed=profile.get('seed',42);scene.cycles.use_animated_seed=False
 scene.cycles.use_denoising=profile.get('useDenoising',True);scene.cycles.denoiser=profile.get('denoiser','OPENIMAGEDENOISE');scene.cycles.denoising_input_passes=profile.get('denoisingInputPasses','RGB_ALBEDO_NORMAL')
 scene.cycles.use_adaptive_sampling=profile.get('adaptiveSampling',True);scene.cycles.adaptive_min_samples=profile.get('minimumSamples',0);scene.cycles.adaptive_threshold=profile.get('noiseThreshold',.015)
 for key in ('causticsReflective','causticsRefractive'):
  if key in profile:setattr(scene.cycles,'caustics_reflective' if key=='causticsReflective' else 'caustics_refractive',profile[key])
 raw_node=None
 if profile.get('retainDiagnosticPasses'):
  if getattr(scene,'compositing_node_group',None):raise ValueError('Existing compositor requires explicit diagnostic integration')
  for layer in scene.view_layers:
   layer.cycles.denoising_store_passes=True;layer.use_pass_normal=True;layer.use_pass_vector=False
   for key in ('diffuse_direct','diffuse_indirect','glossy_direct','glossy_indirect','transmission_direct','transmission_indirect'):setattr(layer,'use_pass_'+key,True)
   layer.update_render_passes()
  group=bpy.data.node_groups.new('Bound-render-quality-diagnostics','CompositorNodeTree');scene.compositing_node_group=group
  group.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
  layer=group.nodes.new('CompositorNodeRLayers');output=group.nodes.new('NodeGroupOutput');group.links.new(layer.outputs['Image'],output.inputs['Image'])
  if not layer.outputs.get('Noisy Image'):raise ValueError('Missing raw Cycles image pass')
  raw_node=group.nodes.new('CompositorNodeOutputFile');raw_node.format.file_format='OPEN_EXR_MULTILAYER';raw_node.format.color_depth='16';raw_node.save_as_render=False;raw_node.file_output_items.new('RGBA','raw');group.links.new(layer.outputs['Noisy Image'],raw_node.inputs[0])
  diagnostic=group.nodes.new('CompositorNodeOutputFile');diagnostic['diagnosticPassOutput']=True;diagnostic.format.file_format='OPEN_EXR_MULTILAYER';diagnostic.format.color_depth='16';diagnostic.save_as_render=False
  for name in ['Image','Noisy Image','Denoising Albedo','Denoising Normal','Normal','Diffuse Direct','Diffuse Indirect','Glossy Direct','Glossy Indirect','Transmission Direct','Transmission Indirect']:
   if not layer.outputs.get(name):raise ValueError('Missing diagnostic pass '+name)
   diagnostic.file_output_items.new('RGBA',name);group.links.new(layer.outputs[name],diagnostic.inputs[name])
 return raw_node

def diagnostic_path(raw_node,out,local):
 from pathlib import Path
 if raw_node is None:return
 p=Path(out)/'raw-linear';p.mkdir(exist_ok=True);raw_node.directory=str(p);raw_node.file_name=f'frame-{local:06d}'
 for node in raw_node.id_data.nodes:
  if node.get('diagnosticPassOutput'):
   q=Path(out)/'diagnostic-exr';q.mkdir(exist_ok=True);node.directory=str(q);node.file_name=f'frame-{local:06d}'

def save_passes(scene,out,local):
 import bpy
 from pathlib import Path
 diagnostic=list((Path(out)/'diagnostic-exr').glob(f'frame-{local:06d}*.exr'))
 if len(diagnostic)!=1:raise ValueError('Expected one multi-pass EXR')
 raw_files=list((Path(out)/'raw-linear').glob(f'frame-{local:06d}*.exr'))
 if len(raw_files)!=1:raise ValueError('Expected one raw linear image')
 raw=bpy.data.images.load(str(raw_files[0]),check_existing=False)
 target=Path(out)/'raw-frames';target.mkdir(exist_ok=True)
 try:raw.save_render(str(target/f'frame-{local:06d}.png'),scene=scene)
 finally:bpy.data.images.remove(raw)
 return diagnostic[0]
