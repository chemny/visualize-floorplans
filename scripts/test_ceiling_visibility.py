"""Execute the production visibility functions with scene doubles; no visual claim."""
import pathlib, shutil, subprocess, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class CeilingVisibility(unittest.TestCase):
 def test_modes_and_fixture_light_independence(self):
  node=shutil.which('node')
  if not node:self.skipTest('Node required for runtime function test')
  source=(ROOT/'assets/h5/source/app.js').read_text()
  base=source[source.index('function applyTop3D(){'):source.index('const renArch=buildArch;')]
  wrapper=source[source.index('const experienceTop=applyTop3D;'):source.index('const experienceLight=applyLight;')]
  script="""
const assert=require('node:assert/strict');
const inited=true,THREE={DoubleSide:2},H=2.75;
let topView=false,constructionExporting=false;
const opt={mode:'orbit',cut:H,furn:true},TOP_TYPES=new Set(['ceilinground','pendant','downlight']),LIT_TYPES=new Set(['ceilinground','pendant','downlight','tablelamp','walllamp']),UNNECESSARY_DISPLAY_TYPES=new Set(['hiddenlamp']);
const items=[{id:'a',type:'ceilinground',mount:'ceiling'},{id:'b',type:'pendant'},{id:'c',type:'customlamp',mount:'ceiling'},{id:'d',type:'tablelamp',mount:'surface'},{id:'e',type:'walllamp',mount:'wall'}];
LIT_TYPES.add('customlamp');
const getF=id=>items.find(f=>f.id===id),constructionDetail=f=>TOP_TYPES.has(f.type)||f.mount==='ceiling';
const ceilings=[{userData:{baseCeiling:true},material:{}},{userData:{ceilingId:'x'},material:{}}];
const archUp={traverse:fn=>ceilings.forEach(fn)},furnG={children:items.map(f=>({userData:{fid:f.id}}))};
const lights=[{visible:true,intensity:3.5},{visible:true,intensity:5}],lightSnapshot=JSON.stringify(lights);
function updateSel(){}
"""+base+wrapper+"""
function check(top,mode,exporting,expected){topView=top;opt.mode=mode;constructionExporting=exporting;applyTop3D();assert.equal(topView,top);for(const c of ceilings)assert.equal(c.visible,expected);for(const g of furnG.children.slice(0,3))assert.equal(g.visible,expected);for(const g of furnG.children.slice(3))assert.equal(g.visible,true);assert.equal(JSON.stringify(lights),lightSnapshot);}
check(false,'orbit',false,false);check(true,'orbit',false,true);
check(false,'walk',false,true);check(false,'orbit',false,false);
check(false,'orbit',true,true);check(false,'orbit',false,false);
opt.furn=false;topView=true;applyTop3D();for(const g of furnG.children)assert.equal(g.visible,false);
console.log('visibility checks passed');
"""
  result=subprocess.run([node,'-e',script],capture_output=True,text=True)
  self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()
