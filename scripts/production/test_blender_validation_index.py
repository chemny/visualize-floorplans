import json,tempfile,unittest
from pathlib import Path
from blender_draft_review import validation_index
from tour_stage_gate import bound
class ValidationIndex(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.p=Path(self.temp.name)
  for name in ('scene.blend','tour.json'):(self.p/name).write_bytes(b'synthetic '+name.encode())
  self.rows=[]
  for name in ('first','second'):
   out=self.p/name;out.mkdir();(out/'draft.mp4').write_bytes(b'synthetic video '+name.encode());result={'sources':{'scene':bound(self.p/'scene.blend'),'tour':bound(self.p/'tour.json')},'video':bound(out/'draft.mp4'),'probe':{'seconds':2,'width':768,'height':432}};(out/'draft-result.json').write_text(json.dumps(result));self.rows.append({'out':str(out),'title':'<'+name+'>'})
 def test_shared_shell_no_auto_approval(self):
  validation_index(self.p,self.rows);text=(self.p/'index.html').read_text();self.assertEqual(text.count('<video '),2);self.assertEqual(text.count('<nav class="steps">'),1);self.assertIn('&lt;first&gt;',text);self.assertFalse(json.loads((self.p/'validation-index.json').read_text())['approvalGranted'])
 def test_tampered_clip_rejected(self):
  (self.p/'second/draft.mp4').write_bytes(b'changed')
  with self.assertRaises(ValueError):validation_index(self.p,self.rows)
  self.assertFalse((self.p/'index.html').exists())
 def test_mixed_scene_rejected(self):
  q=self.p/'other.blend';q.write_bytes(b'other scene');result=json.loads((self.p/'second/draft-result.json').read_text());result['sources']['scene']=bound(q);(self.p/'second/draft-result.json').write_text(json.dumps(result))
  with self.assertRaises(ValueError):validation_index(self.p,self.rows)
  self.assertFalse((self.p/'index.html').exists())
if __name__=='__main__':unittest.main()
