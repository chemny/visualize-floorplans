"""Feature-scoped diagnostics. Detect only; never installs or changes services."""
import importlib,json,re,shutil,subprocess,sys
from pathlib import Path

def module(name):
 try:return importlib.import_module(name)
 except ImportError as e:
  hint='Use the selected Python environment to install opencv-python-headless after user authorization.' if name=='cv2' else 'Configure the required module in the selected Python environment.'
  raise ValueError('Missing optional dependency '+name+'. '+hint+' No installation performed.') from e

def program(value,kind):
 exe=shutil.which(str(value)) if value else shutil.which(kind)
 if not exe and value and Path(value).is_file():exe=str(Path(value).resolve())
 if not exe:raise ValueError('Existing '+kind+' unavailable; configure its executable path. No installation performed.')
 return exe

def blender(value):
 exe=program(value,'blender');r=subprocess.run([exe,'--version'],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=20)
 m=re.search(r'Blender (\d+)\.(\d+)',r.stdout+r.stderr)
 if r.returncode or not m or not (5,2)<=tuple(map(int,m.groups()))<(6,0):raise ValueError('This Blender importer requires Blender5.2.x-compatible APIs (tested5.2); configure an existing supported executable, do not auto-install.')
 return exe

def inspect(feature,settings=None):
 settings=settings or {};checks=[]
 def need(name,fn):
  try:checks.append({'name':name,'status':'pass','value':fn()})
  except (ValueError,OSError,subprocess.SubprocessError) as e:checks.append({'name':name,'status':'missing_or_incompatible','message':str(e)})
 if feature not in ('basic','video','blender','remote','quality','delivery'):raise ValueError('Unknown runtime feature')
 if feature in ('video','blender','delivery'):
  for k in ('ffmpeg','ffprobe'):need(k,lambda k=k:program(settings.get(k),k))
 if feature=='blender':need('blender',lambda:blender(settings.get('blender')))
 if feature in ('video','delivery'):
  need('node',lambda:program(settings.get('node'),'node'));need('browser',lambda:program(settings.get('browser'),'chrome'))
  def playwright():
   f=settings.get('playwright_module')
   if not f or not Path(f).is_file():raise ValueError('Pass an existing --playwright-module; no automatic download.')
   return str(Path(f).resolve())
  need('playwright',playwright)
 if feature=='remote':
  for k in ('ssh','scp'):need(k,lambda k=k:program(None,k))
 if feature=='quality':need('opencv',lambda:str(getattr(module('cv2'),'__version__','available')))
 return {'feature':feature,'status':'pass' if all(c['status']=='pass' for c in checks) else 'blocked','checks':checks,'installsPerformed':False,'scope':'Local tools only; remote executables and GPU are rechecked by the worker, no network probing.'}
