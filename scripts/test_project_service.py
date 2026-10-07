import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error
import urllib.request
from project_service import Store, Conflict, make_server


class ProjectServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.seed={'caseId':'test','furniture':[{'id':'sofa'}],'walls':[{'id':'w1'}],'rooms':{'living':{}},'doors':{}}
        self.store=Store(self.root,self.seed,'layout')

    def test_save_read_restart_and_backup(self):
        edited=copy.deepcopy(self.seed);edited['furniture'][0]['cx']=123
        saved=self.store.save(edited,1)
        self.assertEqual(saved['revision'],2)
        self.assertEqual(Store(self.root,self.seed,'layout').current()['scheme'],edited)
        self.assertEqual(json.loads(self.store.backup.read_text())['scheme'],self.seed)

    def test_two_tabs_conflict(self):
        edited=copy.deepcopy(self.seed);edited['doors']['d1']={'swing':-1}
        self.store.save(edited,1)
        with self.assertRaises(Conflict):self.store.save(self.seed,1)
        self.assertEqual(self.store.current()['scheme'],edited)

    def test_confirmation_bound_to_exact_version(self):
        v=self.store.current();confirmed=self.store.confirm(v['revision'],v['schemeHash'])
        self.assertEqual(confirmed['confirmation']['stage'],'layout')
        edited=copy.deepcopy(self.seed);edited['style']='champagne_pearl'
        self.assertIsNone(self.store.save(edited,1)['confirmation'])
        with self.assertRaises(Conflict):self.store.confirm(1,v['schemeHash'])

    def test_no_change_save_preserves_confirmation(self):
        v=self.store.current();self.store.confirm(1,v['schemeHash'])
        self.assertIsNotNone(self.store.save(self.seed,1)['confirmation'])

    def test_invalid_and_foreign_scheme_rejected(self):
        for key,value in [('caseId','other'),('furniture',[{'id':'x'},{'id':'x'}]),('walls',None)]:
            edited={**self.seed,key:value}
            with self.assertRaises(ValueError):self.store.save(edited,1)
        self.assertEqual(self.store.current()['revision'],1)

    def test_write_failure_keeps_last_valid_file(self):
        edited={**self.seed,'style':'new'}
        import project_service
        replace=project_service.os.replace
        def fail_current(src,dst):
            if dst==self.store.path:raise OSError('disk error')
            return replace(src,dst)
        with patch('project_service.os.replace',side_effect=fail_current):
            with self.assertRaises(OSError):self.store.save(edited,1)
        self.assertEqual(self.store.current()['scheme'],self.seed)

    def test_corrupt_file_not_reset_to_defaults(self):
        self.store.path.write_text('{broken')
        with self.assertRaises(ValueError):Store(self.root,self.seed,'layout')
        self.assertEqual(self.store.path.read_text(),'{broken')

    def test_http_auth_host_origin_and_roundtrip(self):
        page=self.root/'page.html'
        page.write_text('<html><head></head><script id="caseData">{"caseId":"test"}</script><script id="projectSeed" type="application/json">null</script><!-- project-service-client/1 --></html>')
        server=make_server(self.store,page);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        base=f'http://127.0.0.1:{server.server_port}'
        html=urllib.request.urlopen(base+'/workbench').read().decode()
        config=json.loads(html.split('window.PROJECT_IO=')[1].split(';</script>')[0])
        self.assertIn('"caseId": "test"',html)
        payload=json.dumps({'scheme':{**self.seed,'style':'new'},'expectedRevision':1}).encode()
        def post(extra):
            return urllib.request.urlopen(urllib.request.Request(base+'/api/save',data=payload,headers={'Content-Type':'application/json',**extra}))
        for headers in ({},{'X-Project-Token':config['token'],'Origin':'https://evil.example'},{'X-Project-Token':config['token'],'Host':'evil.example'}):
            with self.assertRaises(urllib.error.HTTPError) as caught:post(headers)
            self.assertEqual(caught.exception.code,403)
        result=json.load(post({'X-Project-Token':config['token'],'Origin':base}))
        self.assertEqual(result['revision'],2)
        with self.assertRaises(urllib.error.HTTPError) as caught:post({'X-Project-Token':config['token']})
        self.assertEqual(caught.exception.code,409)


if __name__=='__main__':unittest.main()
