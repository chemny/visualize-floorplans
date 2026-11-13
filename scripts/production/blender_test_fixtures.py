"""Independent synthetic fixtures, never approval for an actual house."""
import json
from pathlib import Path
from tour_stage_gate import bound

def unit_route_refs(p,bundle):
 """Unit-layer inputs; scope tests explicitly mock the independently tested route gate."""
 p=Path(p);b=json.loads(Path(bundle['path']).read_text());b.setdefault('state',{});Path(bundle['path']).write_text(json.dumps(b));bundle.update(bound(bundle['path']))
 scene=p/'route-scene.json';scene.write_text(json.dumps({k:b[k] for k in ('schemeSha256','model','state')}));geometry=p/'route-geometry.bin';geometry.write_bytes(b'synthetic gate geometry');r=p/'route-review.json';r.write_text(json.dumps({'syntheticUnitLayer':True}))
 return {'routeReview':bound(r),'routeScene':bound(scene),'routeGeometry':bound(geometry)}

def approved_route(p,scheme='synthetic-route'):
 """Public route gate with a small synthetic plan and labelled synthetic evidence."""
 from route_rehearsal import build,CHECKS
 from tour_rules import RULESET,fingerprint
 p=Path(p);p.mkdir(parents=True,exist_ok=True)
 def save(name,value):
  f=p/name;f.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8');return bound(f)
 frames=[{'pointMm':[500+i*30,500],'eyeMm':1600,'yawRadians':0,'pitchRadians':0,'shiftY':0,'horizontalFovDegrees':76} for i in range(8)]
 tour={'schemeSha256':scheme,'fps':2,'seconds':4,'frames':frames,'visits':[{'name':'start','frame':0},{'name':'view','frame':3},{'name':'end','frame':7}]}
 bundle={'schemeSha256':scheme,'model':{'width':2000,'depth':2000,'rooms':[{'id':'living','poly':[[0,0],[2000,0],[2000,2000],[0,2000]]}]},'state':{'walls':[],'furniture':[{'id':'sofa','type':'tv','cx':1700,'cy':500,'w':100,'d':20}]}}
 config={'chapters':[{'name':'连接','from':'start','to':'view','phase':'transit'},{'name':'客厅','from':'view','to':'end','phase':'observe','subjects':['sofa'],'roomId':'living','episodeId':'living','viewPurpose':'Synthetic room arrangement','singleSweepDegrees':0,'tourRole':'public'}],'tourContract':{'schema':'homeowner-tour-contract/1','tourMode':'indoor_segment','bodyRadiusMm':100,'rulesetVersion':RULESET},'maximumSeconds':5,'coveragePolicy':{'enabled':True,'minimumPercent':1},'roomViewingPolicy':{'singleEpisode':True},'observationPointPolicy':{'defaultPointsPerRoom':1,'maximumPointsPerRoom':2,'maximumSecondsPerPoint':3,'maximumStillSeconds':.5},'roomBudgetPolicy':{'maximumTotalSeconds':5,'rooms':[{'name':'Living','roomIds':['living'],'maximumSeconds':5}]}}
 tr=save('tour.json',tour);br=save('bundle.json',bundle);save('config.json',config);scene=save('scene.json',{**bundle,'renderSettings':{'size':[320,180]}});(p/'geometry.bin').write_bytes(b'synthetic geometry')
 plan=p/'plan.png'
 if not plan.exists():
  if (p/'still.png').exists():plan.write_bytes((p/'still.png').read_bytes())
  else:
   from PIL import Image
   Image.new('RGB',(200,200),'ivory').save(plan)
 m=build(p/'tour.json',p/'config.json',p/'bundle.json',plan,[0,0,2000,2000],p/'rehearsal',5,p)
 common={'tourSha256':tr['sha256'],'configSha256':bound(p/'config.json')['sha256'],'geometrySha256':bound(p/'geometry.bin')['sha256'],'ruleFingerprint':fingerprint()}
 for k,v in {'screenAudit':{**common,'rulesetVersion':RULESET,'status':'pass','screenQuality':{'status':'pass'}},'visualReview':{**common,'result':'pass','observationMode':'continuous_playback','reviewedBy':'synthetic fixture','evidence':'SYNTHETIC GATE TEST ONLY; not actual house visual acceptance','checks':{k:True for k in ['transitionsNatural','noRepeatedIntroduction','noSustainedObstruction','noUncomfortableTurns']}}}.items():m['references'][k]=save(k+'.json',v)
 mr=save('rehearsal/rehearsal.json',m)
 review=save('route-approved.json',{'schema':'homeowner-route-approval/1','status':'approved','approvalSource':'explicit_user_confirmation','confirmedBy':'synthetic fixture','evidence':'SYNTHETIC GATE TEST ONLY; not real user approval','rehearsal':mr,'presentedAnimationSha256':m['references']['animation']['sha256'],'checks':{k:True for k in CHECKS}})
 return {'tour':tr,'bundle':br,'routeScene':scene,'routeGeometry':bound(p/'geometry.bin'),'routeReview':review}
