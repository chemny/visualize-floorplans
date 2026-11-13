"""Explicit render-device policy. Importable outside Blender for preflight/tests."""
import os

def validate(profile):
 if profile.get('schema')!='blender-execution-profile/1':raise ValueError('Unsupported execution profile')
 if set(profile)-{'schema','backend','allowCpuFallback','graphicsBackend','cpuThreads','requirePackedImages'}:raise ValueError('Unknown execution option')
 if profile.get('backend') not in ('AUTO','CPU','METAL','OPTIX','CUDA'):raise ValueError('Invalid Cycles backend')
 if type(profile.get('allowCpuFallback',False)) is not bool:raise ValueError('Invalid CPU fallback policy')
 if type(profile.get('requirePackedImages',False)) is not bool:raise ValueError('Invalid texture portability policy')
 if profile.get('graphicsBackend') not in (None,'vulkan','metal','opengl'):raise ValueError('Invalid Blender graphics backend')
 if 'cpuThreads' in profile and (type(profile['cpuThreads']) is not int or not 1<=profile['cpuThreads']<=256):raise ValueError('Invalid CPU threads')
 return profile

def select(scene,prefs,profile):
 validate(profile);requested=profile['backend'];failures=[]
 if requested=='CPU':
  scene.cycles.device='CPU';actual='CPU'
 else:
  actual=None
  for backend in (['OPTIX','METAL','CUDA'] if requested=='AUTO' else [requested]):
   try:
    prefs.compute_device_type=backend;prefs.get_devices()
    if not any(d.type==backend for d in prefs.devices):raise RuntimeError('No '+backend+' device')
    for d in prefs.devices:d.use=d.type==backend
    scene.cycles.device='GPU';actual=backend;break
   except (TypeError,ValueError,RuntimeError) as e:failures.append(backend+': '+str(e))
  if actual is None:
   if not profile.get('allowCpuFallback',False):raise ValueError('Requested GPU unavailable; CPU fallback forbidden: '+'; '.join(failures))
   scene.cycles.device='CPU';actual='CPU-fallback'
 if profile.get('cpuThreads'):
  scene.render.threads_mode='FIXED';scene.render.threads=profile['cpuThreads']
 return {'requested':requested,'actual':actual,'cpuFallbackAllowed':profile.get('allowCpuFallback',False),'devices':[{'name':d.name,'type':d.type} for d in prefs.devices if d.use] if actual not in ('CPU','CPU-fallback') else [],'selectionFailures':failures}

def arguments(profile):
 validate(profile)
 return ['--gpu-backend',profile['graphicsBackend']] if profile.get('graphicsBackend') else []

LEGACY_PROFILE={'schema':'blender-execution-profile/1','backend':'AUTO','allowCpuFallback':True}
