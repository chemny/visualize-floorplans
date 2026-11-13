"""Blender-only API check; ordinary unittest discovery never imports bpy."""
def main():
 """Run with existing Blender --background --factory-startup --python-exit-code 1."""
 import sys,json
 from pathlib import Path
 sys.path.insert(0,str(Path(__file__).resolve().parent/'production'))
 import bpy
 from blender_room_presentation import apply,coverage
 bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);s=bpy.context.scene
 bpy.ops.mesh.primitive_cube_add();cube=bpy.context.object;before=[tuple(v.co) for v in cube.data.vertices];mat=bpy.data.materials.new('Exterior-test');mat.use_nodes=True;cube.data.materials.append(mat);nodes=[(n.name,n.type) for n in mat.node_tree.nodes]
 data=bpy.data.lights.new('local','POINT');data.energy=6;o=bpy.data.objects.new('local',data);s.collection.objects.link(o);location=tuple(o.location)
 p={'schema':'blender-room-presentation/1','fixtureLights':[{'name':'local','energy':30,'color':[1,.98,.95],'radius':.25}],'exteriorCards':[{'name':'far-test','material':mat.name,'vertices':[[0,10,0],[2,10,0],[2,10,2],[0,10,2]],'cameraVisible':False,'transmissionVisible':False,'glossyVisible':True}]};changes=apply(s,p)
 assert data.energy==30 and tuple(o.location)==location;assert [tuple(v.co) for v in cube.data.vertices]==before;assert [(n.name,n.type) for n in mat.node_tree.nodes]==nodes
 card=s.objects['far-test'];assert card['presentationRole']=='exterior';assert not card.visible_camera and not card.visible_transmission and card.visible_glossy and not card.visible_diffuse and not card.visible_shadow
 try:apply(s,p);raise AssertionError('Duplicate exterior accepted')
 except ValueError:pass
 try:apply(s,{'schema':p['schema'],'fixtureLights':[{'name':cube.name,'energy':30}]});raise AssertionError('Furniture accepted as light')
 except ValueError:pass
 mesh=bpy.data.meshes.new('window');mesh.from_pydata([(-1,2,0),(1,2,0),(1,2,2),(-1,2,2)],[],[(0,1,2,3)]);mesh.update();window=bpy.data.objects.new('window',mesh);s.collection.objects.link(window)
 spec={**p['exteriorCards'][0],'windowMesh':'window','coverageFrames':[0,2]};tour={'frames':[{'pointMm':[0,0],'eyeMm':1000},{'pointMm':[200,0],'eyeMm':1000}]};model={'width':0,'depth':0}
 assert not coverage(s,{'exteriorCards':[spec]},tour,model)[0]['fullCoverage']
 for vertex,point in zip(card.data.vertices,[(-6,10,-5),(6,10,-5),(6,10,7),(-6,10,7)]):vertex.co=point
 card.data.update();assert coverage(s,{'exteriorCards':[spec]},tour,model)[0]['fullCoverage']
 print('BLENDER_ROOM_PRESENTATION_TEST_PASS')
 # Closed backgrounds must cover the complete source path; duplicate/missing faces fail.
 faces=[('south',[[-10,-10,-10],[10,-10,-10],[10,-10,10],[-10,-10,10]]),('north',[[10,10,-10],[-10,10,-10],[-10,10,10],[10,10,10]]),('west',[[-10,10,-10],[-10,-10,-10],[-10,-10,10],[-10,10,10]]),('east',[[10,-10,-10],[10,10,-10],[10,10,10],[10,-10,10]]),('sky',[[-10,-10,10],[10,-10,10],[10,10,10],[-10,10,10]]),('ground',[[-10,10,-10],[10,10,-10],[10,-10,-10],[-10,-10,-10]])]
 closed={'schema':p['schema'],'exteriorCards':[{'name':'box-'+name,'material':mat.name,'vertices':v} for name,v in faces],'enclosure':{'min':[-10,-10,-10],'max':[10,10,10],'faces':['box-'+name for name,_ in faces]}}
 apply(s,closed);assert coverage(s,closed,tour,model)[0]['fullCoverage']
 for broken in ({'frames':[{'pointMm':[11000,0],'eyeMm':1000}]},):
  try:coverage(s,closed,broken,model);raise AssertionError('Camera outside box accepted')
  except ValueError:pass
 s.objects['box-sky'].visible_camera=False
 try:coverage(s,closed,tour,model);raise AssertionError('Invisible background face accepted')
 except ValueError:pass
 s.objects['box-sky'].visible_camera=True
 s.objects['box-east'].data.vertices[0].co.x=9
 try:coverage(s,closed,tour,model);raise AssertionError('Open enclosure accepted')
 except ValueError:pass
 print('BLENDER_CLOSED_ENVIRONMENT_TEST_PASS')
 # Horizontal out-of-range UVs must mirror in an exterior-only material copy.
 source=bpy.data.materials.new('Source-exterior');source.use_nodes=True;texture=source.node_tree.nodes.new('ShaderNodeTexImage');texture.image=bpy.data.images.new('synthetic-outdoor',width=2,height=2)
 original_nodes=len(source.node_tree.nodes)
 apply(s,{'schema':p['schema'],'exteriorCards':[{'name':'wrapped-exterior','material':source.name,'horizontalWrap':'mirror','vertices':[[-20,-20,0],[20,-20,0],[20,-20,5],[-20,-20,5]],'uv':[[-2,0],[3,0],[3,1],[-2,1]]}]})
 copy=s.objects['wrapped-exterior'].data.materials[0];assert copy!=source and len(source.node_tree.nodes)==original_nodes
 assert any(n.type=='MATH' and n.operation=='PINGPONG' for n in copy.node_tree.nodes)
 assert next(n for n in copy.node_tree.nodes if n.type=='TEX_IMAGE').inputs['Vector'].is_linked
 print('BLENDER_EXTERIOR_MAPPING_TEST_PASS')
 apply(s,{'schema':p['schema'],'exteriorCards':[{'name':'faded-exterior','material':source.name,'horizontalWrap':'mirror','verticalEdgeFade':.02,'vertices':[[-20,-20,0],[20,-20,0],[20,-20,5],[-20,-20,5]],'uv':[[-2,-1],[3,-1],[3,2],[-2,2]]}]})
 fade=s.objects['faded-exterior'].data.materials[0];assert sum(n.type=='MIX_RGB' for n in fade.node_tree.nodes)==2
 assert len(source.node_tree.nodes)==original_nodes
 print('BLENDER_EXTERIOR_EDGE_FADE_TEST_PASS')
 for coords in ([[-2,0],[3,0],[3,1],[-2,1]],[[0,-1],[1,-1],[1,2],[0,2]]):
  try:
   apply(s,{'schema':p['schema'],'exteriorCards':[{'name':'unprotected-edge','material':source.name,'vertices':[[-20,-20,0],[20,-20,0],[20,-20,5],[-20,-20,5]],'uv':coords}]});raise AssertionError('Unprotected out-of-range UV accepted')
  except ValueError:pass
 print('BLENDER_UV_EDGE_GUARD_TEST_PASS')

if __name__=='__main__':main()
