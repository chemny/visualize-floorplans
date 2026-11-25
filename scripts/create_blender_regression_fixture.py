"""Blender --background --factory-startup --python THIS -- --out NEW_TEST_DIR.
Creates an independent synthetic test scene, never a real user's approval or layout.
"""
import bpy,sys,argparse,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'production'))
from import_blender import set_camera
from tour_stage_gate import bound
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--backend',choices=['CPU','OPTIX','CUDA','METAL'],default='CPU');p.add_argument('--graphics-backend',choices=['vulkan','metal','opengl']);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);out=Path(a.out)
if out.exists():raise ValueError('Use a fresh synthetic fixture directory')
out.mkdir(parents=True);bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.device='CPU';s.cycles.samples=1;s.render.resolution_x=320;s.render.resolution_y=180;s.render.resolution_percentage=100;s.render.image_settings.file_format='PNG'
bpy.ops.mesh.primitive_cube_add(size=.8,location=(1.5,.5,.5));bpy.context.object['schemeSha256']='synthetic-remote-regression'
bpy.ops.mesh.primitive_plane_add(size=8);bpy.context.object['schemeSha256']='synthetic-remote-regression'
bpy.ops.object.light_add(type='AREA',location=(1,.5,3));bpy.context.object.data.energy=300;bpy.context.object.data.shape='DISK';bpy.context.object.data.size=3
bpy.ops.object.camera_add();cam=bpy.context.object;cam.rotation_mode='QUATERNION';s.camera=cam
frames=[{'pointMm':[500+i*30,500],'eyeMm':1300,'yawRadians':0,'pitchRadians':0,'horizontalFovDegrees':76,'shiftY':0} for i in range(4)]
model={'width':2000,'depth':2000};set_camera(s,cam,frames[0],model);s.render.filepath=str(out/'still.png');bpy.ops.render.render(write_still=True);bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))
def save(name,value):
 f=out/name;f.write_text(json.dumps(value,ensure_ascii=False,indent=2));return bound(f)
from blender_test_fixtures import approved_route
refs=approved_route(out,'synthetic-remote-regression');refs['scene']=bound(out/'scene.blend')
refs['staticApproval']=save('static.json',{'status':'user_confirmed','evidence':'SYNTHETIC REGRESSION FIXTURE ONLY. Not a user design acceptance.','scene':refs['scene'],'image':bound(out/'still.png')})
refs['executionProfile']=save('execution.json',{'schema':'blender-execution-profile/1','backend':a.backend,'allowCpuFallback':False,'graphicsBackend':a.graphics_backend,'requirePackedImages':True})
refs['qualityProfile']=save('quality.json',{'schema':'blender-render-quality/1','adaptiveSampling':False,'denoiser':'OPENIMAGEDENOISE','denoisingInputPasses':'RGB_ALBEDO_NORMAL','motionBlur':False,'seed':42})
refs['authorization']=save('authorization.json',{'scope':'blender_dynamic_draft','status':'approved','approvalSource':'explicit_user_confirmation','evidence':'SYNTHETIC REGRESSION FIXTURE ONLY, permitted by requested engine self-check. Not a user design acceptance.','startFrame':1,'endFrameExclusive':3,'anchorFrame':0,**refs})
save('capture-job.json',{'schema':'homeowner-blender-draft-job/1',**refs,'model':model,'startFrame':1,'endFrameExclusive':3,'anchorFrame':0,'width':320,'samples':8})
print('SYNTHETIC_REMOTE_FIXTURE_CREATED')
