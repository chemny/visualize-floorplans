"""Single numeric contract for tour generation, revision, rehearsal and capture.
Case policies supply budgets/coverage/geometry. Numeric success never approves visuals.
"""
import argparse,copy,json,math
from pathlib import Path
from tour_workflow import markers,metrics,sha,chapter_limits

SCHEMA='homeowner-tour-contract/1'

def from_brief(brief):
    coverage=brief.get('coveragePolicy')
    if coverage is None:raise ValueError('Explicit case coveragePolicy required; no shared coverage percentage')
    if coverage.get('enabled'):
        value=coverage.get('minimumPercent')
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0<value<=100:
            raise ValueError('Explicit case coverage minimumPercent in (0,100] required')
    from tour_rules import RULESET
    return {'schema':SCHEMA,'rulesetVersion':RULESET,'tourMode':brief.get('tourMode','full_tour'),
            'entranceOpeningId':brief.get('entranceOpeningId'),
            'bodyRadiusMm':brief.get('bodyRadiusMm',180),
            'orderOverrideReason':brief.get('orderOverrideReason',''),
            'singleEpisodeExceptionReason':brief.get('singleEpisodeExceptionReason',''),
            'subjectRepeatExceptionReason':brief.get('subjectRepeatExceptionReason',''),
            'diagnosticOnly':not coverage.get('enabled',False)}

def preserve_viewing_floors(tour,config):
    """Carry original per-window time floors through repeated local revisions."""
    m=markers(tour);floors=copy.deepcopy(config.get('viewingDurationFloors',{}))
    for ch in config['chapters']:
        if ch['phase']=='observe':floors[ch['name']]=max(floors.get(ch['name'],0),(m[ch['to']]-m[ch['from']])/tour['fps'])
    return floors

def inspect(bundle,tour,config):
    contract=config.get('tourContract')
    if not contract:return {'schema':'homeowner-tour-contract-report/1','status':'legacy_not_contracted','issues':[{'code':'missing_tour_contract'}],
                            'actual3DVisibility':'pending','dynamicComfort':'pending','humanAcceptance':'pending'}
    if contract.get('schema')!=SCHEMA:raise ValueError('Unsupported tour contract')
    from plan_route import Planner,inside
    from tour_observation_points import inspect as points
    from tour_choreography import inspect as choreography
    from tour_coverage import inspect as coverage
    from tour_room_budgets import inspect as budgets
    from camera_gaze import PROFILE
    issues=[];checks={};fs=tour['frames'];fps=tour['fps'];m=markers(tour)
    def issue(code,**details):issues.append({'code':code,**details})
    if not fs or not isinstance(fps,(int,float)) or not math.isfinite(fps) or fps<=0:raise ValueError('Invalid final frame timeline')
    from tour_rules import inspect as rules_inspect,trajectory,RULESET,exception,fingerprint
    checks['executionRules']=rules_inspect(tour,config);issues.extend(checks['executionRules']['issues'])
    checks['trajectory']=trajectory(tour,config);issues.extend(checks['trajectory']['issues'])
    from tour_forward_motion import inspect as forward_motion
    checks['forwardMotion']=forward_motion(tour,config);issues.extend(checks['forwardMotion']['issues'])
    from tour_stop_smoothness import inspect as stop_smoothness
    checks['stopSmoothness']=stop_smoothness(tour,config);issues.extend(checks['stopSmoothness']['issues'])
    from tour_small_room_depth import inspect as small_room_depth
    checks['smallRoomDepth']=small_room_depth(bundle,tour,config);issues.extend(checks['smallRoomDepth']['issues'])
    from tour_forward_motion import verify_policy
    checks['smallRoomBackOut']=verify_policy(bundle,config);issues.extend(checks['smallRoomBackOut']['issues'])
    from tour_core_targets import inspect as core_targets
    checks['coreTargets']=core_targets(bundle,config);issues.extend(checks['coreTargets']['issues'])
    if tour.get('schemeSha256')!=bundle.get('schemeSha256'):issue('scheme_mismatch')
    if abs(tour['seconds']-len(fs)/fps)>1e-7:issue('duration_frame_mismatch')
    maximum=config.get('maximumSeconds')
    if isinstance(maximum,bool) or not isinstance(maximum,(int,float)) or not math.isfinite(maximum) or maximum<=0:issue('missing_case_duration_limit')
    elif tour['seconds']>maximum+1e-7:issue('total_over_budget',seconds=tour['seconds'],maximumSeconds=maximum)
    radius=contract.get('bodyRadiusMm')
    if isinstance(radius,bool) or not isinstance(radius,(int,float)) or not math.isfinite(radius) or radius<=0:raise ValueError('Positive contract body radius required')
    access=[]
    if contract.get('tourMode')=='full_tour':
        from design_homeowner_tour import entry_apron
        try:
            access,_=entry_apron(bundle,{'entranceOpeningId':contract.get('entranceOpeningId'),'startPoint':fs[0]['pointMm'],'bodyRadiusMm':radius})
            if math.dist(fs[0]['pointMm'],fs[-1]['pointMm'])>1:issue('full_tour_does_not_return_to_entrance')
        except ValueError as e:issue('unsupported_entrance',message=str(e))
    planner=Planner(bundle,{'accessPolygons':access,'bodyRadiusMm':radius,'gridMm':50})
    hits=[i for i,f in enumerate(fs) if planner.blocked(f['pointMm'])]
    chords=[i for i,(a,b) in enumerate(zip(fs,fs[1:])) if not planner.line_free(a['pointMm'],b['pointMm'])]
    checks['geometry']={'collisionFrames':hits,'collisionChords':chords}
    if hits or chords:issue('body_path_collision')
    limits=json.loads(PROFILE.read_text())['reviewLimits'];measured=metrics(tour)
    # Limits are inherited from the existing profile/config; no retiming or relaxation here.
    limits={**limits,**config.get('motionReviewLimits',{})}
    checks['motion']={'actual':measured,'limits':limits}
    for key,value in limits.items():
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('Invalid motion limit')
        if measured.get(key,0)>value+1e-6:issue('motion_limit',metric=key)
    checks['chapterMotion']=[]
    chapters=config['chapters'];ranges=[];last_end=0;last_episode=None;closed=set();room_episodes={};last_role=-1;previous_view_room=None;subject_history={};observation_index=0
    priorities={'public':0,'primary':1,'secondary':2,'service':3,'return_public':1.5,'return':4}
    room_polys={r['id']:r['poly'] for r in bundle['model']['rooms']}
    floors=config.get('viewingDurationFloors',{});found_floor_names=set()
    single=config.get('roomViewingPolicy',{}).get('singleEpisode',True)
    if not single and not str(contract.get('singleEpisodeExceptionReason','')).strip():issue('unjustified_multi_episode_exception')
    for ix,ch in enumerate(chapters):
        a,z=m.get(ch.get('from')),m.get(ch.get('to'))
        if not isinstance(a,int) or not isinstance(z,int) or not 0<=a<z<len(fs) or a!=last_end:
            issue('invalid_chapter_partition',chapter=ch.get('name'));continue
        last_end=z;ranges.append((a,z));duration=(z-a)/fps
        local=chapter_limits(limits,ch);actual=metrics({'frames':fs[a:z+1],'fps':fps})
        checks['chapterMotion'].append({'chapter':ch['name'],'phase':ch['phase'],'actual':actual,'limits':local})
        for key,value in local.items():
            if actual.get(key,0)>value+1e-6:issue('chapter_motion_limit',chapter=ch['name'],metric=key,actual=actual[key],maximum=value)
        if ch.get('phase')=='observe':
            room=ch.get('roomId');episode=ch.get('episodeId',room)
            for subject in set(ch.get('subjects',[])+ch.get('orderedViewTargets',[])):
                previous=subject_history.get(subject)
                continuation=previous and previous['index']==observation_index-1 and previous['episode']==episode and (previous['moving'] or ch.get('movingView'))
                if previous and not continuation and not exception(config,'repeat_subject',ch['name'],subject):issue('duplicate_subject_introduction',subjectId=subject,chapter=ch['name'])
                subject_history[subject]={'index':observation_index,'episode':episode,'moving':ch.get('movingView',False)}
            observation_index+=1
            if room not in room_polys or not str(ch.get('viewPurpose','')).strip():issue('missing_room_view_intent',chapter=ch['name'])
            if single:
                if room in room_episodes and (room_episodes[room]!=episode or previous_view_room!=room):issue('split_room_view',roomId=room)
                room_episodes[room]=episode
                previous_view_room=room
                if episode!=last_episode:
                    if episode in closed:issue('noncontiguous_viewing_episode',episodeId=episode)
                    if last_episode is not None:closed.add(last_episode)
                    last_episode=episode
            if ch['name'] in floors:
                found_floor_names.add(ch['name'])
                if duration+.5/tour['fps']+1e-8<floors[ch['name']]:issue('viewing_time_compressed',chapter=ch['name'])  # time is whole frames: half a frame is rounding, not compression
            sweep=ch.get('singleSweepDegrees')
            if sweep is None:issue('missing_sweep_direction',chapter=ch['name'])
            else:
                sign=1 if sweep>0 else -1 if sweep<0 else 0
                changes=[math.degrees(b['yawRadians']-a['yawRadians']) for a,b in zip(fs[a:z],fs[a+1:z+1])]
                reverse=sum(max(0,-sign*v) for v in changes) if sign else sum(map(abs,changes))
                if reverse>1:issue('observation_sweep_reversal',chapter=ch['name'],oppositeDegrees=reverse)
            if ch.get('movingView'):
                # A moving link is not a free way to rename extra stationary furniture stops.
                neighbours=[q for q in chapters[max(0,ix-1):ix+2] if q is not ch and q.get('phase')=='observe' and not q.get('movingView')]
                connected=any(q.get('roomId')==room and q.get('episodeId',room)==episode for q in neighbours)
                distance=sum(math.dist(f['pointMm'],g['pointMm']) for f,g in zip(fs[a:z],fs[a+1:z+1]))
                if not connected or distance<100:issue('invalid_moving_view_continuation',chapter=ch['name'])
            elif contract.get('requireInsideObservation',True) and room in room_polys:
                region=ch.get('observationRegionId',room)
                if region not in room_polys:issue('unknown_observation_region',chapter=ch['name']);region=room
                # Quantized chapter boundaries may touch a threshold for one frame.
                if any(not inside(f['pointMm'],room_polys[region]) for f in fs[a+1:z]):issue('observation_outside_room',chapter=ch['name'])
            role=ch.get('tourRole')
            if role in priorities:
                rank=priorities[role]
                if rank<last_role and not str(contract.get('orderOverrideReason','')).strip():issue('unjustified_presentation_order',chapter=ch['name'])
                last_role=rank
        elif ch.get('phase')!='transit':issue('unknown_chapter_phase',chapter=ch['name'])
    if last_end!=len(fs)-1:issue('incomplete_timeline')
    for name in set(floors)-found_floor_names:issue('missing_preserved_viewing_window',chapter=name)
    checks['observationPoints']=points(tour,config)
    if checks['observationPoints']['status']=='not_configured':issue('missing_observation_point_policy')
    issues.extend(checks['observationPoints']['issues'])
    run=longest=0
    for a,b in zip(fs,fs[1:]):
        still=math.dist(a['pointMm'],b['pointMm'])<.1 and abs(a['yawRadians']-b['yawRadians'])<1e-5 and abs(a.get('pitchRadians',0)-b.get('pitchRadians',0))<1e-5
        run=run+1 if still else 0;longest=max(longest,run)
    checks['longestSimultaneousStillSeconds']=longest/fps
    if longest/fps>config.get('observationPointPolicy',{}).get('maximumStillSeconds',.5)+1/fps:issue('stationary_camera_hold_on_timeline')
    checks['choreography']=choreography(tour,config);issues.extend(checks['choreography']['issues'])
    cp=config.get('coveragePolicy',{})
    if cp.get('enabled') and 'minimumPercent' in cp:
        checks['coverage']=coverage(bundle,tour,planner,cp['minimumPercent'],config=config)
        if checks['coverage'].get('mode')!='reference':
            for row in checks['coverage']['rooms']:
                if not row['meetsProxyMinimum']:issue('room_coverage_below_case_minimum',roomId=row['roomId'])
    else:issue('coverage_not_configured_for_capture')
    if config.get('roomBudgetPolicy'):
        checks['roomBudgets']=budgets(bundle,tour,config,config['roomBudgetPolicy']);issues.extend(checks['roomBudgets']['issues'])
    from tour_camera_evidence import inspect as camera_evidence
    checks['cameraEvidence']=camera_evidence(bundle,tour,config,planner)
    issues.extend(checks['cameraEvidence']['issues'])
    if contract.get('diagnosticOnly'):issue('diagnostic_only_contract')
    return {'schema':'homeowner-tour-contract-report/1','rulesetVersion':RULESET,'ruleFingerprint':fingerprint(),'status':'needs_revision' if issues else 'numeric_pass_visual_pending',
            'issues':issues,'checks':checks,'actual3DVisibility':'pending','dynamicComfort':'pending','humanAcceptance':'pending',
            'limitations':['Coverage is a horizontal wall/door proxy, not actual 3D surface visibility',
                           'Necessary return paths are allowed; no claim of globally shortest route',
                           'Numeric checks do not prove subject readability or dynamic comfort']}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('bundle','tour','config','out'):ap.add_argument('--'+key,required=True)
    a=ap.parse_args();paths={k:getattr(a,k) for k in ('bundle','tour','config')};values={k:json.loads(Path(v).read_text()) for k,v in paths.items()}
    report=inspect(values['bundle'],values['tour'],values['config']);report['inputs']={k:{'path':str(Path(v).resolve()),'sha256':sha(v)} for k,v in paths.items()}
    out=Path(a.out)
    if out.exists():raise ValueError('Fresh audit output required')
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps({'status':report['status'],'issues':report['issues']},ensure_ascii=False))
    return 0 if report['status']=='numeric_pass_visual_pending' else 2
if __name__=='__main__':raise SystemExit(main())
