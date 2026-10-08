import contextlib,io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import h5

class RunIntegration(unittest.TestCase):
 def test_config_run_applies_shared_camera_and_retime_before_audit(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);bundle=p/'bundle.json';bundle.write_text(json.dumps({'schemeSha256':'case'}));config=p/'config.json';config.write_text(json.dumps({'cameraKeys':[{'atStop':'entry','targetMm':[3000,100,1400]},{'atStop':'exit','targetMm':[3000,100,1400]}],'chapters':[{'name':'view','from':'entry','to':'exit','phase':'observe','subjects':['cabinet'],'minimumSeconds':2}]}))
   source={'schemeSha256':'case','fps':24,'seconds':1,'frames':[{'frame':i,'pointMm':[i*100,0],'eyeMm':1600,'yawRadians':0,'pitchRadians':0} for i in range(24)],'visits':[{'name':'entry','frame':0},{'name':'exit','frame':23}]}
   def planner(cmd,**kwargs):Path(cmd[cmd.index('--output')+1]).write_text(json.dumps(source))
   def prepare(*args,**kwargs):Path(args[1]).mkdir();(Path(args[1])/'scene.json').write_text(json.dumps({'renderSettings':{'size':[1280,720]}}))
   called=[]
   def browser(command,args):
    called.append(command);o=json.loads(Path(args.tour).read_text());self.assertIn('timingMethod',o);self.assertEqual(o['cameraMethod']['method'],'subject-key-curves-v1');self.assertFalse(o['chapterReview']['failures']);Path(args.out).mkdir()
    if command=='audit':(Path(args.out)/'audit.json').write_text(json.dumps({'subjectStatus':'not_checked'}))
   argv=['h5.py','run','--bundle',str(bundle),'--config',str(config),'--out',str(p/'run'),'--preview']
   with patch.object(sys,'argv',argv),patch.object(h5,'validate_bundle'),patch.object(h5,'prepare',side_effect=prepare),patch.object(h5.subprocess,'run',side_effect=planner),patch.object(h5,'node_call',side_effect=browser),patch.object(h5,'handoff'),contextlib.redirect_stdout(io.StringIO()):h5.main()
   self.assertEqual(called,['audit','capture'])
 def test_hd_diagnostic_cannot_skip_review(self):
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);(p/'scene.json').write_text(json.dumps({'renderSettings':{'size':[1920,1080]}}))
   with self.assertRaises(ValueError):h5.require_capture_review(SimpleNamespace(full=True,tour='tour.json',runtime=p,preview=True,preview_review=None))
if __name__=='__main__':unittest.main()
