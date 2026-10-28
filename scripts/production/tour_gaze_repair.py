"""Local fixed-time gaze revision; no path edits, timing edits or media capture.

``revise(tour, config, patches)`` treats patch keys as soft angle targets and
freezes every unpatched axis/frame. Final motion limits and declared observation
sweep directions are hard constraints. A nonconverged candidate raises ValueError.
"""
import copy,json,math
from camera_gaze import PROFILE
from tour_camera_evidence import DEFAULTS
from tour_connection_motion import project_gaze_numpy
from tour_workflow import markers,metrics,edge_limits

_AXES={'yawRadians':'yawDegrees','pitchRadians':'pitchDegrees'}

def revise(tour,config,patches,maximum_iterations=24000,projection_tolerance=1e-7,deadline=None):
    frames=tour['frames'];n=len(frames);fps=tour['fps'];marks=markers(tour);chapters=config['chapters']
    if not frames or not isinstance(patches,list) or not patches:raise ValueError('Frames and at least one gaze patch required')
    names={}
    for index,ch in enumerate(chapters):
        name=ch['name']
        if name in names:raise ValueError('Chapter names must be unique for gaze patching')
        names[name]=index
    targets={axis:[math.degrees(f[axis]) for f in frames] for axis in _AXES}
    masks={axis:[False]*n for axis in _AXES};ranges=[]
    for patch in patches:
        first=names.get(patch.get('chapter'));last=names.get(patch.get('endChapter',patch.get('chapter')))
        if first is None or last is None or first>last:raise ValueError('Invalid gaze patch chapter range')
        selected=chapters[first:last+1]
        if any(a['to']!=z['from'] for a,z in zip(selected,selected[1:])):raise ValueError('Gaze patch must span contiguous chapters')
        a,z=marks[selected[0]['from']],marks[selected[-1]['to']]
        if not isinstance(a,int) or not isinstance(z,int) or not 0<=a<z<n:raise ValueError('Invalid gaze patch frame range')
        start_offset=patch.get('startOffsetFrame',0);end_offset=patch.get('endOffsetFrame',z-a)
        if (isinstance(start_offset,bool) or isinstance(end_offset,bool)
                or not isinstance(start_offset,int) or not isinstance(end_offset,int)
                or not 0<=start_offset<end_offset<=z-a):
            raise ValueError('Gaze patch offsets must select a nonempty subrange of its chapters')
        a,z=a+start_offset,a+end_offset
        axes=patch.get('axes');keys=patch.get('keys',[])
        if not isinstance(axes,list) or not axes or len(axes)!=len(set(axes)) or any(axis not in _AXES for axis in axes):raise ValueError('Gaze patch axes must explicitly name yawRadians/pitchRadians')
        if len(keys)<2:raise ValueError('Gaze patch needs at least its first and final keys')
        offsets=[key.get('offsetFrame') for key in keys]
        if any(not isinstance(v,int) for v in offsets) or offsets[0]!=0 or offsets[-1]!=z-a or any(u>=v for u,v in zip(offsets,offsets[1:])):raise ValueError('Patch keys must be ordered, include offset 0 and final offset, and remain in range')
        for axis in axes:
            if any(masks[axis][i] for i in range(a,z+1)):raise ValueError('Overlapping gaze patches for the same axis must be combined')
            field=_AXES[axis];values=[]
            for key,offset in zip(keys,offsets):
                value=key.get(field)
                if not isinstance(value,(int,float)) or not math.isfinite(value):raise ValueError('Finite patch key angle required: '+field)
                if axis=='yawRadians':value+=360*round((math.degrees(frames[a+offset][axis])-value)/360)
                values.append(value)
            for left,right,one,two in zip(offsets,offsets[1:],values,values[1:]):
                for offset in range(left,right+1):
                    u=(offset-left)/(right-left);targets[axis][a+offset]=one*(1-u)+two*u;masks[axis][a+offset]=True
        ranges.append({'chapter':patch['chapter'],'endChapter':patch.get('endChapter',patch['chapter']),'startFrame':a,'endFrame':z,'axes':axes[:]})
    profile=json.loads(PROFILE.read_text());limits={**profile['reviewLimits'],**config.get('motionReviewLimits',{})};evidence_policy={**DEFAULTS,**config.get('cameraEvidencePolicy',{})}
    signs={}
    for ch in chapters:
        if ch.get('phase')!='observe' or 'singleSweepDegrees' not in ch:continue
        sweep=ch['singleSweepDegrees'];sign=1 if sweep>0 else -1 if sweep<0 else 0
        for i in range(marks[ch['from']],marks[ch['to']]):
            if i in signs and signs[i]!=sign:raise ValueError('Conflicting observation sweep directions')
            signs[i]=sign
    out=copy.deepcopy(tour);axis_evidence={}
    for axis,mask in masks.items():
        if not any(mask):continue
        yaw=axis=='yawRadians';speed_key='maxYawDegreesPerSecond' if yaw else 'maxPitchDegreesPerSecond';accel_key='maximumYawAccelerationDegreesPerSecondSquared' if yaw else 'maximumPitchAccelerationDegreesPerSecondSquared'
        # Frozen, already-valid frames can lie on the configured ceilings.
        # Tightening the global feasible set would reject those immutable
        # frames even though the local edit respects the original limits.
        speed=[v/fps for v in edge_limits(tour,config,speed_key,limits)];accel=evidence_policy[accel_key]/fps**2
        fixed={i:math.degrees(frames[i][axis]) for i in range(n) if not mask[i]}
        projected=project_gaze_numpy(targets[axis],fps,speed,accel,signs if yaw else {},maximum_iterations=maximum_iterations,fixed_values=fixed,tolerance=projection_tolerance,deadline=deadline)
        for i,value in enumerate(projected):
            if mask[i]:out['frames'][i][axis]=math.radians(value)
        # Unpatched values stay the original floats, not degree/radian roundtrips.
        values=[math.degrees(f[axis]) for f in out['frames']]
        axis_evidence[axis]={'patchedFrames':sum(mask),'unchangedOutsidePatch':all(out['frames'][i][axis]==frames[i][axis] for i in range(n) if not mask[i]),'maximumChangeDegrees':max(abs(v-math.degrees(f[axis])) for v,f in zip(values,frames)),'maximumDegreesPerSecond':max((abs(v-u)*fps for u,v in zip(values,values[1:])),default=0),'maximumAccelerationDegreesPerSecondSquared':max((abs(w-2*v+u)*fps**2 for u,v,w in zip(values,values[1:],values[2:])),default=0)}
    out['audit']=metrics(out);out['humanAcceptance']='pending';out['previewOnly']=True
    for key in ('subjectAudit','qualityReview','roomTimeline','roomJumpTimes'):out.pop(key,None)
    evidence={'schema':'homeowner-local-gaze-revision/1','patches':ranges,'axes':axis_evidence,'positionsPreserved':all(a['pointMm']==b['pointMm'] for a,b in zip(frames,out['frames'])),'frameCountPreserved':len(out['frames'])==n,'visitsPreserved':out.get('visits')==tour.get('visits') and out.get('stopFrames')==tour.get('stopFrames'),'timingPreserved':out.get('seconds')==tour.get('seconds') and out['fps']==fps,'meshCoverageAndComposition':'must_reaudit','actualPlayback':'not_performed','humanAcceptance':'pending'}
    return out,evidence
