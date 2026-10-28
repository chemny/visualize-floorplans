import contextlib,io,json,subprocess,sys,tempfile,unittest,urllib.request
from unittest.mock import MagicMock
from pathlib import Path
from unittest.mock import patch
import workbench_browser_suite as suite

class BrowserSuiteTest(unittest.TestCase):
 def case(self):return {'initialState':{'furniture':[],'walls':[]},'model':{'rooms':[{'id':'renamed'}]}}
 def test_registry_and_scope(self):
  self.assertIn('copy',suite.selected_checks('core'));self.assertIn('bathtub-resize',suite.selected_checks('full'))
  with self.assertRaises(ValueError):suite.selected_checks('wrong')
  self.assertFalse(suite.prerequisite(self.case(),'copy')[0]);self.assertFalse(suite.prerequisite(self.case(),'bathtub')[0])
 def test_skips_and_blockers_are_not_pass(self):
  self.assertEqual(suite.suite_status([{'status':'not_applicable'}]),'not_applicable');self.assertEqual(suite.suite_status([{'status':'blocked'}]),'blocked');self.assertEqual(suite.suite_status([{'status':'pass'},{'status':'fail'}]),'fail')
 def test_subtest_cannot_pass_without_actual_artifact_evidence(self):
  with tempfile.TemporaryDirectory() as tmp:
   def fake(command,**kw):Path(command[-1]).write_text('{"status":"passed"}');return subprocess.CompletedProcess(command,0,'','')
   self.assertEqual(suite.run_one('lighting','http://127.0.0.1/',Path(tmp),{},'node',1,run=fake)['status'],'fail')
 def test_receipts_must_match_this_run_html_and_case(self):
  with tempfile.TemporaryDirectory() as tmp:
   out=Path(tmp);manifest={k:str(i)*64 for i,k in enumerate(['htmlSha256','engineSha256','templateSha256','caseSha256'],1)}
   for f in ['before','after']:(out/(f+'.build.json')).write_text(json.dumps(manifest))
   def binding(receipts):return {'status':'passed','pages':[{'status':'passed','artifacts':receipts}]}
   current={**manifest,'url':'http://127.0.0.1:1234/after.html?view=3d'}
   self.assertTrue(suite.verify_binding(binding([current]),'lighting','http://127.0.0.1:1234/',out))
   for change in [{'url':'http://127.0.0.1:1234/other.html'},{'caseSha256':'e'*64},{'htmlSha256':'f'*64}]:
    with self.assertRaises(ValueError):suite.verify_binding(binding([{**current,**change}]),'lighting','http://127.0.0.1:1234/',out)
   with self.assertRaises(ValueError):suite.verify_binding(binding([current]),'copy','http://127.0.0.1:1234/',out)
   self.assertTrue(suite.verify_binding(binding([current,{**manifest,'url':'http://127.0.0.1:1234/before.html'}]),'copy','http://127.0.0.1:1234/',out))
 def test_timeout_is_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   def fake(*a,**k):raise subprocess.TimeoutExpired('node',1)
   self.assertEqual(suite.run_one('lighting','http://127.0.0.1/',Path(tmp),{},'node',1,run=fake)['status'],'fail')
 def test_interruption_cleans_owned_browser_processes(self):
  process=MagicMock();process.communicate.side_effect=[KeyboardInterrupt(),('','')]
  with patch.object(suite.subprocess,'Popen',return_value=process),patch.object(suite,'stop_test_process') as stop:
   with self.assertRaises(KeyboardInterrupt):suite.run_process(['node'],timeout=1,capture_output=True,text=True)
   stop.assert_called_once_with(process)
 def test_missing_runtime_explicitly_blocks(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'case.json';p.write_text(json.dumps(self.case()));out=root/'out'
   with contextlib.redirect_stdout(io.StringIO()):rc=suite.main(['--case',str(p),'--out',str(out),'--node',str(root/'missing'),'--checks','lighting'])
   report=json.loads((out/'result.json').read_text());self.assertEqual(rc,2);self.assertEqual(report['status'],'blocked');self.assertTrue(report['caseUnchanged']);self.assertFalse(report['installsPerformed'])
 def test_temporary_loopback_server_is_closed_and_case_unchanged(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);p=root/'case.json';p.write_text(json.dumps(self.case()));original=p.read_bytes();out=root/'out'
   def build(command,**kw):Path(command[command.index('--out')+1]).write_text('test-only');return subprocess.CompletedProcess(command,0,'','')
   def check(name,url,*a):self.assertEqual(urllib.request.urlopen(url+'after.html').read(),b'test-only');return {'name':name,'status':'pass'}
   with patch.object(suite.subprocess,'run',side_effect=build),patch.object(suite,'run_one',side_effect=check),contextlib.redirect_stdout(io.StringIO()):rc=suite.main(['--case',str(p),'--out',str(out),'--node',sys.executable,'--browser',sys.executable,'--playwright-module',sys.executable,'--checks','lighting'])
   report=json.loads((out/'result.json').read_text());self.assertEqual(rc,0);self.assertEqual(p.read_bytes(),original);self.assertTrue(report['serverStopped'])
   with self.assertRaises(Exception):urllib.request.urlopen(f"http://127.0.0.1:{report['serverPort']}/after.html",timeout=.5)

if __name__=='__main__':unittest.main()
