"""Explicitly authorized, exact-route full review film. Never grants delivery/narration approval."""
import json
from tour_stage_gate import resolve

def require_evidence(job,authorization,base,refs):
 rows=job.get('dynamicValidation',[])
 if not {'doorway','bathroom','window_move'}.issubset({r.get('kind') for r in rows}):raise ValueError('Door, bath and moving-window validation required')
 if rows!=authorization.get('dynamicValidation'):raise ValueError('Validation evidence differs from authorization')
 for row in rows:
  p=resolve(row.get('result'),base);r=json.loads(p.read_text())
  if r.get('schema')!='homeowner-blender-draft-result/1':raise ValueError('Expected actual dynamic draft result')
  for key in ('scene','tour'):
   if resolve(r['sources'][key],p.parent)!=refs[key]:raise ValueError('Dynamic sample belongs to other source')
  resolve(r['video'],p.parent)
  capture=r.get('capture',{});temporal=r.get('temporalDiagnostic',{})
  if capture.get('cameraFromExactSourceFrames') is not True or capture.get('nearSurfaceWarnings')!=[] or temporal.get('suspectedGlobalFlickerFrames')!=[]:raise ValueError('Unresolved dynamic diagnostic findings')
 calibration=job.get('calibrationReview')
 if calibration!=authorization.get('calibrationReview'):raise ValueError('Calibration evidence differs from authorization')
 p=resolve(calibration,base);r=json.loads(p.read_text())
 # Compare by resolved file, not by the record text: the worker normalizes paths to its own style (backslashes on Windows).
 if r.get('status')!='engineer_checked' or not r.get('roomPresentation') or resolve(r['roomPresentation'],p.parent)!=refs.get('roomPresentation') or not r.get('frames'):raise ValueError('Current lighting calibration required')
 for row in r['frames']:resolve(row['image'],p.parent)
 if not r.get('route') or resolve(r['route'],p.parent)!=refs['tour']:raise ValueError('Calibration route mismatch')
 # These are production inputs and engineering checks, never fictional user acceptance.
 return True

def run(job,base,out,blender,ffmpeg):
 from blender_draft import run as capture
 return capture(job,base,out,blender,ffmpeg,review=True)
