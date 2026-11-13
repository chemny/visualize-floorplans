import copy,json,tempfile,unittest
from pathlib import Path
from case_upgrade import inspect,require_media,digest
from test_floor_boundaries import fixture

class CaseUpgradeTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.p=Path(self.tmp.name)
  self.c=fixture();self.c.update(caseId='original');self.c['initialState'].update(caseId='original',style='wood_cream');self.c['initialState']['furniture'][0]['type']='table'
  self.source=self.write('source.json',self.c);self.current=self.write('case.json',self.c)
 def write(self,name,data):
  p=self.p/name;p.write_text(json.dumps(data),encoding='utf-8');return p
 def test_review_does_not_grant_acceptance(self):
  before=self.current.read_bytes();r=inspect(self.current,self.source)
  self.assertEqual(r['status'],'needs_review');self.assertEqual(r['humanAcceptance'].split(';')[0],'pending');self.assertEqual(before,self.current.read_bytes())
 def test_room_assignment_is_metadata_not_furniture_motion(self):
  c=copy.deepcopy(self.c);c['initialState']['furniture'][0]['roomId']='r';self.write('case.json',c)
  self.assertTrue(inspect(self.current,self.source)['frozenSource']['furniture'])
 def test_explicit_legacy_color_can_be_locked_without_changing_selection(self):
  self.c['initialState']['furniture'][0]['color']='#eeeedd';self.c['presentation']={'finishOverrides':{'furnitureColors':{'fixed':'#eeeedd'}}};self.write('source.json',self.c)
  c=copy.deepcopy(self.c);c['initialState']['furniture'][0]['colorStyleMode']='fixed';self.write('case.json',c)
  self.assertTrue(inspect(self.current,self.source)['frozenSource']['furniture'])
  c['initialState']['furniture'][0]['color']='#000000';self.write('case.json',c)
  self.assertFalse(inspect(self.current,self.source)['frozenSource']['furniture'])
 def test_furniture_and_architecture_changes_are_reported(self):
  c=copy.deepcopy(self.c);c['initialState']['furniture'][0]['cx']+=1;c['initialState']['walls'][0]['t']=110;self.write('case.json',c)
  r=inspect(self.current,self.source);self.assertEqual(r['status'],'blocked');self.assertFalse(r['frozenSource']['furniture']);self.assertFalse(r['frozenSource']['wallsAndOpenings'])
 def test_changed_build_is_not_accepted(self):
  b=self.write('demo.build.json',{'caseId':'original','caseSha256':digest(self.current),'htmlSha256':'wrong'})
  (self.p/'demo.html').write_text('actual')
  self.assertIn('Build receipt differs from actual case or HTML',inspect(self.current,self.source,b)['blockers'])
 def manifest(self):
  f=self.p/'drawing.svg';f.write_text('<svg/>');return {'schema':'case-media-manifest/1','caseId':'original','caseSha256':digest(self.current),'schemeSha256':'s'*64,'items':[{'id':'plan','kind':'drawing','status':'current','caseId':'original','caseSha256':digest(self.current),'artifact':{'path':'drawing.svg','sha256':digest(f)}}]}
 def test_same_case_media(self):
  m=self.manifest();self.assertEqual(require_media(m,self.p,'original',digest(self.current),'s'*64)[0]['status'],'current')
 def test_mixed_case_and_changed_artifact_are_rejected(self):
  m=self.manifest();m['items'][0]['caseId']='other'
  with self.assertRaisesRegex(ValueError,'Mixed case'):require_media(m,self.p,'original',digest(self.current),'s'*64)
  m=self.manifest();(self.p/'drawing.svg').write_text('changed')
  with self.assertRaisesRegex(ValueError,'missing or changed'):require_media(m,self.p,'original',digest(self.current),'s'*64)
 def test_historical_reference_needs_explicit_boundary(self):
  m=self.manifest();m['items'][0]['status']='historical'
  with self.assertRaisesRegex(ValueError,'Historical'):require_media(m,self.p,'original',digest(self.current),'s'*64)
  m['items'][0].update(sourceCaseSha256='old',representationNote='Concept reference from an older revision')
  self.assertEqual(require_media(m,self.p,'original',digest(self.current),'s'*64)[0]['status'],'historical')
 def test_video_needs_current_scheme_and_route(self):
  m=self.manifest();m['items'][0].update(kind='video',schemeSha256='wrong')
  with self.assertRaisesRegex(ValueError,'current exported scheme'):require_media(m,self.p,'original',digest(self.current),'s'*64)
  m['items'][0]['schemeSha256']='s'*64
  with self.assertRaisesRegex(ValueError,'route binding'):require_media(m,self.p,'original',digest(self.current),'s'*64)
 def test_pending_video_has_no_fake_artifact(self):
  m=self.manifest();m['items'][0]['status']='pending'
  with self.assertRaisesRegex(ValueError,'Pending media'):require_media(m,self.p,'original',digest(self.current),'s'*64)
if __name__=='__main__':unittest.main()
