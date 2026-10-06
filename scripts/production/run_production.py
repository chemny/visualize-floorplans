"""Portable local branch: confirmed actual meshes -> H5 (default) / Blender -> FFmpeg.
Existing executables only; no installs, publishing or remote API calls.
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path

def main():
 if '--engine' not in sys.argv or sys.argv[sys.argv.index('--engine')+1]=='h5':
  args=sys.argv[1:]
  if '--engine' in args:
   i=args.index('--engine');del args[i:i+2]
  subprocess.run([sys.executable,str(Path(__file__).with_name('h5.py')),'run',*args],check=True)
  return
 ap=argparse.ArgumentParser();ap.add_argument('--engine',choices=['blender']);ap.add_argument('--bundle',required=True);ap.add_argument('--config',required=True);ap.add_argument('--views');ap.add_argument('--out',required=True);ap.add_argument('--blender');ap.add_argument('--ffmpeg');ap.add_argument('--ffprobe');ap.add_argument('--animation',action='store_true');ap.add_argument('--resolution',type=int,default=640);a=ap.parse_args()
 out=Path(a.out).resolve()
 if out.exists() and any(out.iterdir()):raise SystemExit('Output directory must be empty; use a new revision directory.')
 bpath=Path(a.bundle).resolve();bundle=json.loads(bpath.read_text(encoding='utf-8'))
 if bundle.get('schema')!='floor-visualization-production/1.0':raise SystemExit('Unsupported bundle schema')
 if set(bundle.get('confirmations',{}))!={'structure','layout','style'} or any(v['status']!='confirmed' for v in bundle['confirmations'].values()):raise SystemExit('Confirm current structure/layout/style before production')
 if 'costSettings' in bundle['state']:raise SystemExit('Production bundle must exclude pricing')
 blender=a.blender or shutil.which('blender')
 if not blender and sys.platform=='darwin' and Path('/Applications/Blender.app/Contents/MacOS/Blender').exists():blender='/Applications/Blender.app/Contents/MacOS/Blender'
 if not blender:raise SystemExit('Existing Blender executable unavailable; pass --blender')
 ffmpeg=a.ffmpeg or shutil.which('ffmpeg');ffprobe=a.ffprobe or shutil.which('ffprobe')
 if a.animation and (not ffmpeg or not ffprobe):raise SystemExit('Existing FFmpeg and ffprobe are required for animation')
 out.mkdir(parents=True,exist_ok=True);shutil.copy2(bpath,out/'production-bundle.json');shutil.copy2(a.config,out/'tour-config.json');scripts=Path(__file__).parent;commands=[]
 def run(command):
  commands.append(command);subprocess.run(command,check=True)
 run([sys.executable,str(scripts/'plan_route.py'),'--bundle',str(out/'production-bundle.json'),'--config',str(out/'tour-config.json'),'--output',str(out/'tour.json')])
 cmd=[blender,'--background','--python',str(scripts/'import_blender.py'),'--','--bundle',str(out/'production-bundle.json'),'--route',str(out/'tour.json'),'--out',str(out/'renders'),'--stills','--resolution',str(a.resolution)]
 if a.views:shutil.copy2(a.views,out/'interior-views.json');cmd+=['--views',str(out/'interior-views.json')]
 if a.animation:cmd+=['--animation']
 run(cmd);video=None
 if a.animation:
  tour=json.loads((out/'tour.json').read_text(encoding='utf-8'));video=out/'continuous-preflight.mp4';run([ffmpeg,'-hide_banner','-loglevel','error','-framerate',str(tour['fps']),'-i',str(out/'renders/frames/frame-%04d.png'),'-c:v','libx264','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(video)])
  probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames,duration','-of','json',str(video)]));s=probe['streams'][0]
  assert int(s['nb_read_frames'])==len(tour['frames']);assert abs(float(s['duration'])-tour['seconds'])<.1;(out/'video-probe.json').write_text(json.dumps(probe,indent=2), encoding='utf-8')
 (out/'run.json').write_text(json.dumps({'schemeSha256':bundle['schemeSha256'],'commands':commands,'localBranch':'completed','video':str(video) if video else None,'finalGenerativeVideo':'not requested by this CLI; separate reviewed Seedance branch','humanAcceptance':'pending for newly generated renders/video'},ensure_ascii=False,indent=2), encoding='utf-8');print('LOCAL_PRODUCTION_PASS',out)
if __name__=='__main__':main()
