"""Shared production rules. Case values and historical acceptance are never migrated silently."""
import json, math
from pathlib import Path

RULESET = 'homeowner-tour-rules/2'
PROFILE = Path(__file__).resolve().parents[2]/'assets/h5/tour/homeowner-profile.json'
def profile(): return json.loads(PROFILE.read_text(encoding='utf-8'))['defaults'].copy()
def fingerprint():
    import hashlib
    root=Path(__file__).parent;names=json.loads((root/'tour_rules_sources.json').read_text(encoding='utf-8'))
    data=''.join(name+':'+hashlib.sha256((root/name).read_bytes()).hexdigest()+'\n' for name in names)
    return hashlib.sha256(data.encode()).hexdigest()
def exception(config, code, chapter=None, subject=None):
    return any(x.get('code')==code and str(x.get('reason','')).strip()
               and (chapter is None or x.get('chapter')==chapter)
               and (subject is None or x.get('subjectId')==subject)
               for x in config.get('ruleExceptions',[]))

def inspect(tour, config):
    from tour_workflow import markers
    issues=[]; fs=tour['frames']; fps=tour['fps']; m=markers(tour)
    def fail(code, **kw): issues.append({'code':code, **kw})
    if config.get('tourContract',{}).get('rulesetVersion')!=RULESET: fail('outdated_tour_ruleset')
    expected={**profile(),**config.get('cameraProfile',{})}
    for key in ('eyeMm','horizontalFovDegrees','shiftY'):
        default=profile()[key]
        if expected[key]!=default and not exception(config,'camera_profile_override'):
            fail('unexplained_camera_profile_override',field=key)
        bad=[i for i,f in enumerate(fs) if key not in f or not isinstance(f[key],(int,float)) or not math.isfinite(f[key]) or abs(f[key]-expected[key])>1e-6]
        if bad: fail('camera_profile_frame_mismatch',field=key,frames=bad[:8])
    for ch in config['chapters']:
        if ch.get('phase')!='observe': continue
        if not ch.get('subjects') and not ch.get('orderedViewTargets'): fail('missing_view_targets',chapter=ch['name'])
        if ch.get('tourRole') not in ('public','primary','secondary','service','return_public','return'): fail('missing_or_invalid_tour_role',chapter=ch['name'])
        if ch.get('observationRegionId',ch.get('roomId'))!=ch.get('roomId') and not str(ch.get('adjacentViewReason','')).strip(): fail('unexplained_adjacent_room_view',chapter=ch['name'])
        if set(ch.get('coveredRoomIds',[]))-{ch.get('roomId')} and not str(ch.get('adjacentViewReason','')).strip():fail('unexplained_adjacent_room_view',chapter=ch['name'])
    policy=config.get('roomBudgetPolicy')
    if not policy: fail('missing_room_visit_budgets')
    else:
        covered={r for row in policy.get('rooms',[]) for r in row.get('roomIds',[])}
        for room in {c.get('roomId') for c in config['chapters'] if c.get('phase')=='observe'}-covered: fail('missing_room_visit_budget',roomId=room)
    point=config.get('observationPointPolicy',{})
    for key,limit in [('maximumSecondsPerPoint',3),('maximumStillSeconds',.5)]:
        if point.get(key,limit)>limit and not exception(config,'observation_limit_override'): fail('unexplained_observation_limit_override',field=key)
    from camera_gaze import PROFILE as P
    for key, value in config.get('motionReviewLimits',{}).items():
        if value>json.loads(P.read_text(encoding='utf-8'))['reviewLimits'].get(key,value) and not exception(config,'motion_limit_override'):fail('unexplained_motion_limit_override',field=key)
    choreography={'maximumTransitYawDegrees':180,'maximumObservationReversals':1,'maximumTransitFraction':.55}
    for key,limit in choreography.items():
        if config.get('choreographyPolicy',{}).get(key,limit)>limit and not exception(config,'choreography_limit_override'):fail('unexplained_choreography_limit_override',field=key)
    locks=config.get('timingLocks',{})
    if set(locks)-{'totalFrames','totalSeconds','fps','viewingFrames'}:fail('unknown_timing_lock_field')
    if 'totalSeconds' in locks and abs(tour['seconds']-locks['totalSeconds'])>1e-8:fail('locked_total_duration_changed')
    if 'totalFrames' in locks and len(fs)!=locks['totalFrames']:fail('locked_total_duration_changed')
    if 'fps' in locks and fps!=locks['fps']:fail('locked_fps_changed')
    by_name={c['name']:c for c in config['chapters']}
    for name,count in locks.get('viewingFrames',{}).items():
        ch=by_name.get(name)
        if not ch or ch.get('from') not in m or ch.get('to') not in m or m[ch['to']]-m[ch['from']]!=count:fail('locked_viewing_duration_changed',chapter=name)
    if config.get('tourContract',{}).get('subjectRepeatExceptionReason'):fail('unscoped_repeat_exception')
    if config.get('cameraEvidenceOverrideReason'):fail('unscoped_camera_evidence_override')
    return {'rulesetVersion':RULESET,'issues':issues,'profile':expected}

def trajectory(tour, config):
    from tour_workflow import markers
    fs=tour['frames'];fps=tour['fps'];issues=[]
    policy={'maximumPlanarAccelerationMps2':3.,'maximumMovingHeadingStepDegrees':12.,**config.get('trajectoryPolicy',{})}
    for key,value in policy.items():
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('Positive trajectory limit required')
        defaults={'maximumPlanarAccelerationMps2':3.,'maximumMovingHeadingStepDegrees':12.}
        if value>defaults[key] and not exception(config,'trajectory_limit_override'):issues.append({'code':'unexplained_trajectory_limit_override','field':key})
    # A one-vertex concession must never turn into a chapter/global motion limit.
    # Anchor it to semantic chapter markers so unrelated earlier retiming cannot
    # silently move the concession to another kitchen/doorway/path vertex.
    scoped={};marks=markers(tour)
    chapters=config.get('chapters',[])
    for value in config.get('ruleExceptions',[]):
        if value.get('code')!='path_tangent_step_override':continue
        name=value.get('chapter');offset=value.get('offsetFrame');limit=value.get('maximumDegrees')
        matching=[ch for ch in chapters if ch.get('name')==name]
        if (not isinstance(name,str) or not name.strip() or len(matching)!=1
                or not isinstance(value.get('reason'),str) or not value['reason'].strip()
                or isinstance(offset,bool) or not isinstance(offset,int)
                or isinstance(limit,bool) or not isinstance(limit,(int,float))
                or not math.isfinite(limit) or not policy['maximumMovingHeadingStepDegrees']<limit<=180):
            raise ValueError('Path tangent exception requires one exact chapter, offsetFrame, higher maximumDegrees and reason')
        chapter=matching[0];start,end=marks.get(chapter.get('from')),marks.get(chapter.get('to'))
        if (isinstance(start,bool) or not isinstance(start,int)
                or isinstance(end,bool) or not isinstance(end,int)
                or not 0<=start<end<len(fs) or not 0<=offset<end-start
                or not 1<=start+offset<len(fs)-1):
            raise ValueError('Path tangent exception offsetFrame is outside its chapter or an interior path vertex')
        frame=start+offset
        if frame in scoped:raise ValueError('Duplicate path tangent exception vertex')
        scoped[frame]={'code':value['code'],'chapter':name,'offsetFrame':offset,
                       'frame':frame,'maximumDegrees':limit,'reason':value['reason'].strip()}
    velocities=[[(b['pointMm'][k]-a['pointMm'][k])*fps/1000 for k in (0,1)] for a,b in zip(fs,fs[1:])]
    acc=[math.dist(a,b)*fps for a,b in zip(velocities,velocities[1:])]
    angles=[]
    for i,(a,b) in enumerate(zip(velocities,velocities[1:])):
        if min(math.hypot(*a),math.hypot(*b))>.05:
            ang=math.degrees(math.acos(max(-1,min(1,sum(x*y for x,y in zip(a,b))/(math.hypot(*a)*math.hypot(*b))))))
            angles.append((ang,i+1))
    peak=max(acc,default=0);turn,at=max(angles,default=(0,None))
    if peak>policy['maximumPlanarAccelerationMps2']+1e-6:issues.append({'code':'path_acceleration_spike','frame':acc.index(peak)+1,'actual':peak})
    concessions=[]
    for actual,frame in angles:
        concession=scoped.get(frame);limit=concession['maximumDegrees'] if concession else policy['maximumMovingHeadingStepDegrees']
        if actual>limit+1e-6:issues.append({'code':'path_tangent_discontinuity','frame':frame,'actual':actual,'maximumDegrees':limit})
        if concession:
            concessions.append({**concession,'actualDegrees':actual,
                                'defaultMaximumDegrees':policy['maximumMovingHeadingStepDegrees'],
                                'needed':actual>policy['maximumMovingHeadingStepDegrees']+1e-6,
                                'withinScopedLimit':actual<=limit+1e-6})
    # Keep unused allowances visible instead of silently accepting a stale scope.
    measured_frames={frame for _,frame in angles}
    for frame,concession in scoped.items():
        if frame not in measured_frames:concessions.append({**concession,'actualDegrees':None,
            'defaultMaximumDegrees':policy['maximumMovingHeadingStepDegrees'],'needed':False,
            'withinScopedLimit':True,'note':'Vertex is below the moving-speed threshold; allowance was not applied'})
    return {'issues':issues,'policy':policy,'scopedExceptions':concessions,'maximumPlanarAccelerationMps2':peak,'maximumMovingHeadingStepDegrees':turn,'basis':'Final-frame velocity vectors, including chapter seams. Numeric safety does not certify visual comfort.'}

def review_state(numeric, mesh, visual='pending'):
    passed=numeric=='numeric_pass_visual_pending' and mesh=='pass'
    return {'numericStatus':numeric,'meshVisibility':mesh,'visualReview':visual,
            'readyForVisualReview':passed and visual!='needs_revision',
            'reviewable':passed and visual!='needs_revision',
            'productionReady':False,'humanAcceptance':'pending','videoGenerated':False}

def require_visual_evidence(manifest, tour_path):
    """Bound, current screen evidence and a real playback review precede any capture."""
    import hashlib
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    refs=manifest['references'];config_path=refs['config']['path']
    report=json.loads(Path(refs['contractReport']['path']).read_text(encoding='utf-8'))
    if report.get('ruleFingerprint')!=fingerprint():raise ValueError('Tour rule engine changed; re-audit and reconfirm')
    for key in ('screenAudit','visualReview'):
        if key not in refs:raise ValueError('Missing '+key+'; regenerate rehearsal and perform visual review')
        if sha(refs[key]['path'])!=refs[key]['sha256']:raise ValueError('Changed '+key+'; rebind and reconfirm rehearsal')
        value=json.loads(Path(refs[key]['path']).read_text(encoding='utf-8'))
        if value.get('tourSha256')!=sha(tour_path) or value.get('configSha256')!=sha(config_path) or value.get('geometrySha256')!=manifest['geometrySha256']:raise ValueError('Stale '+key)
        if value.get('ruleFingerprint')!=fingerprint():raise ValueError('Stale rule engine evidence: '+key)
        if key=='screenAudit':
            from tour_core_targets import readability
            core=readability(json.loads(Path(refs['bundle']['path']).read_text()),json.loads(Path(config_path).read_text()),value.get('chapters',[]),value.get('policy',{}),json.loads(Path(tour_path).read_text())['fps'])
            if core['issues']:raise ValueError('Actual core facility audit incomplete: '+str(core['issues']))
            if value.get('rulesetVersion')!=RULESET or value.get('ruleFingerprint')!=fingerprint() or value.get('status')!='pass' or value.get('screenQuality',{}).get('status')!='pass':raise ValueError('Screen composition/occlusion requires revision')
        elif value.get('result')!='pass' or value.get('observationMode')!='continuous_playback' or not str(value.get('reviewedBy','')).strip() or not str(value.get('evidence','')).strip() or any(value.get('checks',{}).get(k) is not True for k in ('transitionsNatural','noRepeatedIntroduction','noSustainedObstruction','noUncomfortableTurns')):raise ValueError('Actual continuous playback review is pending or failed')
