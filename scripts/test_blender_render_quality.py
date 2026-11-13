"""Blender-only API check; ordinary unittest discovery never imports bpy."""
def main():
 """Existing Blender API integration; no render, scene export or user source changes."""
 import sys
 from pathlib import Path
 sys.path.insert(0,str(Path(__file__).resolve().parent/'production'))
 import bpy
 from blender_render_quality import apply,diagnostic_path
 s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=64
 profile={'schema':'blender-render-quality/1','adaptiveSampling':False,'minimumSamples':0,'noiseThreshold':.005,'retainDiagnosticPasses':True}
 source=[(o.name,list(o.matrix_world[0])) for o in s.objects];node=apply(s,profile,64)
 assert not s.cycles.use_adaptive_sampling and s.cycles.samples==64
 assert source==[(o.name,list(o.matrix_world[0])) for o in s.objects]
 outputs=[n for n in s.compositing_node_group.nodes if n.type=='OUTPUT_FILE'];assert len(outputs)==2
 for n in outputs:
  for item in n.file_output_items:assert n.inputs[item.name].is_linked
 assert [n for n in outputs if n.get('diagnosticPassOutput')][0].inputs['Glossy Direct'].is_linked
 assert [n for n in outputs if n.get('diagnosticPassOutput')][0].inputs['Denoising Normal'].is_linked
 try:apply(s,profile,64);raise AssertionError('Existing compositor overwritten')
 except ValueError:pass
 print('BLENDER_QUALITY_AND_NAMED_PASS_LINK_TEST_PASS')

if __name__=='__main__':main()
