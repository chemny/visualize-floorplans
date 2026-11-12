import unittest,tempfile,json,copy
from pathlib import Path
from blender_draft import validate
from unittest.mock import patch
from blender_test_fixtures import unit_route_refs
from tour_stage_gate import bound
class ReviewGate(unittest.TestCase):
 def setUp(self):
  gate=patch('route_rehearsal.require_route',return_value={});gate.start();self.addCleanup(gate.stop)
 def test_full_review_requires_bound_evidence_and_never_becomes_draft_authorization(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   def write(name,value):
    q=p/name;q.write_text(json.dumps(value));return bound(q)
   (p/'scene.blend').write_bytes(b'synthetic-scene');(p/'still.png').write_bytes(b'synthetic-still');(p/'sample.mp4').write_bytes(b'synthetic-sample')
   model={'width':9130,'depth':17160};tour={'schemeSha256':'s','fps':24,'seconds':6,'frames':[{'pointMm':[0,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0}]*144}
   refs={'scene':bound(p/'scene.blend'),'tour':write('tour.json',tour),'bundle':write('bundle.json',{'schemeSha256':'s','model':model}),'staticApproval':write('static.json',{'status':'user_confirmed','evidence':'synthetic static','scene':bound(p/'scene.blend'),'image':bound(p/'still.png')}),'roomPresentation':write('profile.json',{'schema':'blender-room-presentation/1'})}
   refs.update(unit_route_refs(p,refs['bundle']))
   sample={'schema':'homeowner-blender-draft-result/1','sources':{k:refs[k] for k in ('scene','tour')},'video':bound(p/'sample.mp4'),'capture':{'cameraFromExactSourceFrames':True,'nearSurfaceWarnings':[]},'temporalDiagnostic':{'suspectedGlobalFlickerFrames':[]}}
   evidence=[{'kind':k,'result':write(k+'.json',sample)} for k in ('doorway','bathroom','window_move')]
   calibration=write('calibration.json',{'status':'engineer_checked','roomPresentation':refs['roomPresentation'],'route':refs['tour'],'frames':[{'image':bound(p/'still.png')}]})
   auth={'scope':'blender_review_film','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'synthetic full review only','startFrame':0,'endFrameExclusive':144,'anchorFrame':30,**refs,'dynamicValidation':evidence,'calibrationReview':calibration}
   job={'schema':'homeowner-blender-review-job/1',**refs,'model':model,'startFrame':0,'endFrameExclusive':144,'anchorFrame':30,'width':1280,'samples':16,'captureWorkers':2,'dynamicValidation':evidence,'calibrationReview':calibration}
   def bind_auth(j,a):j['authorization']=write('auth.json',a)
   bind_auth(job,auth);validate(job,p,review=True)
   with self.assertRaises(ValueError):validate(job,p)
   for field,value in [('startFrame',1),('endFrameExclusive',143),('captureWorkers',3),('captureWorkers',True)]:
    j=copy.deepcopy(job);j[field]=value
    with self.assertRaises(ValueError):validate(j,p,review=True)
   # Empty, partial AND disjoint sets must be rejected, even if authorized identically.
   for kinds in ([],['doorway'],['unrelated'],['doorway','bathroom','unrelated']):
    j=copy.deepcopy(job);a=copy.deepcopy(auth);a['dynamicValidation']=j['dynamicValidation']=[{'kind':k,'result':evidence[0]['result']} for k in kinds];bind_auth(j,a)
    with self.assertRaises(ValueError):validate(j,p,review=True)
   a=copy.deepcopy(auth);a['scope']='blender_dynamic_draft';j=copy.deepcopy(job);bind_auth(j,a)
   with self.assertRaises(ValueError):validate(j,p,review=True)
   j=copy.deepcopy(job);bind_auth(j,auth);(p/'window_move.json').write_text('{}')
   with self.assertRaises(ValueError):validate(j,p,review=True)
   write('window_move.json',sample);bind_auth(j,auth)
   # The worker spells paths in its own style; the same file written another way is still the same evidence.
   respelled=lambda r:{**r,'path':str(Path(r['path']).parent/'.'/Path(r['path']).name)}
   cal=write('calibration-respelled.json',{'status':'engineer_checked','roomPresentation':respelled(refs['roomPresentation']),'route':respelled(refs['tour']),'frames':[{'image':bound(p/'still.png')}]})
   j2=copy.deepcopy(job);a2=copy.deepcopy(auth);j2['calibrationReview']=a2['calibrationReview']=cal;bind_auth(j2,a2);validate(j2,p,review=True)
   (p/'profile.json').write_text('{"schema":"changed"}')
   with self.assertRaises(ValueError):validate(j,p,review=True)
if __name__=='__main__':unittest.main()
