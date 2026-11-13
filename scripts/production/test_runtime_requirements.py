import unittest
from unittest.mock import patch
from types import SimpleNamespace
from runtime_requirements import inspect,blender,module
class RuntimeChecks(unittest.TestCase):
 def test_basic_does_not_probe_optional_tools(self):
  with patch('runtime_requirements.program',side_effect=AssertionError('optional')):self.assertEqual(inspect('basic')['status'],'pass')
 def test_missing_quality_dependency_is_actionable(self):
  with patch('runtime_requirements.importlib.import_module',side_effect=ImportError('missing')):
   r=inspect('quality');self.assertEqual(r['status'],'blocked');self.assertIn('opencv-python-headless',r['checks'][0]['message'])
 def test_blender_versions_checked_without_rendering(self):
  with patch('runtime_requirements.program',return_value='blender'),patch('runtime_requirements.subprocess.run',return_value=SimpleNamespace(stdout='Blender5.2',stderr='',returncode=0)):
   with self.assertRaises(ValueError):blender('blender')
  for version,okay in [('4.5',False),('5.2.1',True),('6.0',False)]:
   with patch('runtime_requirements.program',return_value='blender'),patch('runtime_requirements.subprocess.run',return_value=SimpleNamespace(stdout='Blender '+version,stderr='',returncode=0)):
    if okay:self.assertEqual(blender('blender'),'blender')
    else:
     with self.assertRaises(ValueError):blender('blender')
if __name__=='__main__':unittest.main()
