#!/usr/bin/env python3
"""Case-local timing, motion report, local edits and unapproved preview review template."""
import argparse,json
from pathlib import Path
from tour_workflow import retime,refine,metrics,intent_check,sha,scene_review_sha
from camera_gaze import PROFILE

def main():
 ap=argparse.ArgumentParser();ap.add_argument('command',choices=['retime','refine','check','review-template']);ap.add_argument('--tour',required=True);ap.add_argument('--config');ap.add_argument('--runtime');ap.add_argument('--output',required=True);a=ap.parse_args();p=Path(a.output)
 if p.exists():raise ValueError('Fresh output required')
 t=json.loads(Path(a.tour).read_text());c=json.loads(Path(a.config).read_text()) if a.config else {};profile=json.loads(PROFILE.read_text())
 if a.command=='retime':o=retime(t,c,{**profile['reviewLimits'],**c.get('motionReviewLimits',{})});o['chapterReview']=intent_check(o,c)
 elif a.command=='refine':o=refine(t,c['windows']);o['localRefinement']['baselineTourSha256']=sha(a.tour)
 elif a.command=='check':o={'tourSha256':sha(a.tour),'motion':metrics(t),'chapterReview':intent_check(t,c),'humanAcceptance':'pending'}
 else:
  if not a.runtime:raise ValueError('--runtime required')
  o={'schema':'homeowner-preview-review/1','status':'pending','reviewedBy':'','tourSha256':sha(a.tour),'schemeSha256':t['schemeSha256'],'sceneReviewSha256':scene_review_sha(a.runtime),'geometrySha256':sha(Path(a.runtime)/'geometry.bin'),'checks':{k:False for k in ['turnSamplesViewed','wholePreviewViewed','subjectsReadable','paceComfortable','noBlankCaptureEdges']},'artifacts':{k:{'path':'','sha256':''} for k in ['turnSamples','wholePreview','subjectAudit','meshAudit']},'limitations':'Populate only after actual dynamic viewing; this template grants no approval. Resolution-only changes do not invalidate scene identity; renderer changes require a fresh review.'}
  o['rendererSha256']=sha(Path(a.runtime)/'renderer.html');o['sceneArtifact']={'path':str((Path(a.runtime)/'scene.json').resolve()),'sha256':sha(Path(a.runtime)/'scene.json')}
 p.write_text(json.dumps(o,ensure_ascii=False,indent=2));print(a.command,p)
 if a.command=='check' and o['chapterReview']['failures']:return 2
 return 0
if __name__=='__main__':raise SystemExit(main())
