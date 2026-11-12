import unittest
from blender_lighting_profile import validate,watts_per_intensity,fixture_power,power_table,brightness_report

BASE={'worldStrength':.4,'fixtureWattsPerIntensity':12}

class LightingProfile(unittest.TestCase):
 def test_unknown_keys_and_bad_numbers_are_refused(self):
  for bad in ({'wattsEverywhere':5},{'worldStrength':-1},{'worldColor':[1,1]},{'worldColor':[1,2,0]},{'fixtureWattsPerIntensity':True},{'fixtureWattsPerIntensity':1e9}):
   with self.assertRaises(ValueError,msg=str(bad)):validate({**BASE,**bad})
 def test_per_type_and_per_fixture_power_need_a_global_default(self):
  with self.assertRaises(ValueError):validate({'fixtureWattsByType':{'downlight':4}})
  validate({**BASE,'fixtureWattsByType':{'downlight':4},'fixtureWattsById':{'X':2},'cameraBackgroundColor':[.9,.9,.85],'cameraBackgroundStrength':1})
 def test_spot_cone_option_must_be_boolean(self):
  validate({**BASE,'spotFixturesAsCones':True})
  with self.assertRaises(ValueError):validate({**BASE,'spotFixturesAsCones':1})
 def test_id_beats_type_beats_global(self):
  p={**BASE,'fixtureWattsByType':{'downlight':4,'pendant':14},'fixtureWattsById':{'D1':2.4}}
  self.assertEqual(watts_per_intensity(p,'D1','downlight'),2.4)
  self.assertEqual(watts_per_intensity(p,'D2','downlight'),4)
  self.assertEqual(watts_per_intensity(p,'P1','pendant'),14)
  self.assertEqual(watts_per_intensity(p,'S1','spot'),12)
  self.assertAlmostEqual(fixture_power(p,'D1','downlight',3),7.2)
 def test_power_table_skips_disabled_fixtures(self):
  rows=power_table({**BASE,'fixtureWattsByType':{'downlight':4}},[{'fixtureId':'a','intensity':3,'enabled':True},{'fixtureId':'b','intensity':3,'enabled':False}],{'a':'downlight','b':'downlight'})
  self.assertEqual([(r['fixtureId'],r['watts']) for r in rows],[('a',12)])
 def test_brightness_band(self):
  self.assertEqual(brightness_report([170,180])['status'],'too_bright')
  self.assertEqual(brightness_report([100,120])['status'],'too_dark')
  self.assertEqual(brightness_report([150,155])['status'],'in_band')
