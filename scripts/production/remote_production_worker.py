"""Durable worker launched with an existing remote Python. All output remains pending review."""
import argparse,json,os,sys,time,traceback,hashlib
from pathlib import Path
from remote_production import write
from tour_stage_gate import sha,bound

def verify(root):
 manifest=json.loads((root/'manifest.json').read_text())
 for row in manifest['files']:
  p=Path(row['path'])
  if p.is_absolute() or '..' in p.parts or ':' in row['path']:raise ValueError('Invalid input manifest path')
  if sha(root/p)!=row['sha256']:raise ValueError('Frozen input/producer changed: '+row['path'])
 return manifest
def run(root):
 root=Path(root).resolve();phase='preflight';started=time.monotonic()
 def state(stage,**v):write(root/'state.json',{'schema':'homeowner-remote-state/1','stage':stage,'workerPid':os.getpid(),'updatedAt':time.time(),**v})
 try:
  state(phase);verify(root);request=json.loads((root/'request.json').read_text());job=json.loads((root/request['job']).read_text());e=request['endpoint']
  os.environ['PYTHONUTF8']='1'
  os.environ['PATH']=str(Path(e['ffmpeg']).parent)+os.pathsep+str(Path(e['ffprobe']).parent)+os.pathsep+os.environ.get('PATH','')
  phase='rendering' if request['kind']=='blender' else 'upscaling';state(phase)
  if request['kind']=='blender':
   from blender_draft import run as capture
   def progress(name):
    nonlocal phase
    phase=name;state(name)
   report=capture(job,root,root/'output',e['blender'],e['ffmpeg'],review=job['schema']=='homeowner-blender-review-job/1',on_phase=progress)
   video=Path(report['video']['path']);reports=[p for p in (root/'output').glob('*.json') if p.name!='job.json']
  else:
   from video_upscale import execute
   report=execute(job,root,root/'output',e['ffmpeg'],e['ffprobe'],comfy=e.get('comfyUrl'))
   video=Path(report['video']['path']);reports=list((root/'output').glob('*.json'))
  phase='verifying_outputs';state(phase);verify(root)
  artifacts=[video,*reports,*[Path(row['video']['path']) for row in report.get('variants',[])]]
  # Small representative source images only. All rendered frame sequences stay remote.
  frame_dir=root/'output/frames'
  if frame_dir.is_dir():
   files=sorted(frame_dir.glob('frame-*.png'))
   for i in sorted({0,len(files)//2,len(files)-1}):
    if i>=0:artifacts.append(files[i])
  result={'schema':'homeowner-remote-result/1','manifestSha256':sha(root/'manifest.json'),'kind':request['kind'],'renderAndEncodingRemote':True,'videoPath':video.relative_to(root).as_posix(),'artifacts':[{'path':p.relative_to(root).as_posix(),'sha256':sha(p)} for p in dict.fromkeys(artifacts)],'seconds':time.monotonic()-started,'visualReview':'pending','narrationAuthorized':False}
  write(root/'result.json',result);state('ready_for_review',videoPath=result['videoPath'],seconds=result['seconds'])
 except Exception as e:
  state('failed',failedStage=phase,error=str(e),framesPreserved=True);traceback.print_exc();raise
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',required=True);a=p.parse_args();run(a.root)
