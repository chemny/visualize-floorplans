"""Hash-bound revision review and engineering closeout; never creates a video.

The engineering stage and human acceptance are separate. A green audit can make
a candidate ready for review, but does not certify visual comfort or acceptance.
Scopes use inclusive frame intervals; unspecified frame fields stay frozen.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
from pathlib import Path

from tour_playback import ASSETS, prepare_renderer
from tour_pages import theme


def artifact_sha256(value):
    """Stable semantic identity for an in-memory tour/config/playback record."""
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def _load(value):
    if isinstance(value, (str, Path)):
        return json.loads(Path(value).read_text())
    return value


def _hashes(value, loaded):
    hashes = {artifact_sha256(loaded)}
    if isinstance(value, (str, Path)):
        hashes.add(hashlib.sha256(Path(value).read_bytes()).hexdigest())
    # Public production artifacts use this serialization; preserve semantic
    # binding when their loaded dictionaries are passed instead of file paths.
    hashes.add(hashlib.sha256(json.dumps(loaded, ensure_ascii=False, indent=2).encode()).hexdigest())
    hashes.add(hashlib.sha256((json.dumps(loaded, ensure_ascii=False, indent=2)+'\n').encode()).hexdigest())
    return hashes


def _result(status, **evidence):
    return {'status': status, **evidence}


def _failed(node):
    if isinstance(node, dict):
        if node.get('status') in {'fail', 'failed', 'blocked', 'error', 'rejected', 'needs_revision'}:
            return True
        for key in ('issues', 'collisionFrames', 'collisionChords', 'missingTargets'):
            if node.get(key):
                return True
        return any(_failed(v) for k, v in node.items()
                   if k not in {'actualPlayback', 'humanAcceptance', 'dynamicComfort'})
    return isinstance(node, list) and any(_failed(v) for v in node)


def _audit(node, source):
    if not isinstance(node, dict) or not node:
        return _result('not_evaluated', source=source)
    if _failed(node):
        return _result('failed', source=source, issues=node.get('issues', []))
    status = node.get('status')
    if status in {'pending', 'not_evaluated', 'not_performed', 'skipped', 'unavailable'}:
        return _result('not_evaluated', source=source)
    if status is None and 'issues' not in node:
        return _result('not_evaluated', source=source)
    if status is not None and status not in {'pass', 'numeric_pass_visual_pending', 'no_numeric_flags', 'within_numeric_limits'}:
        return _result('action_required', source=source, reportedStatus=status)
    return _result('pass', source=source)


def _combine(nodes):
    statuses = [n['status'] for n in nodes]
    for status in ('failed', 'action_required', 'not_evaluated'):
        if status in statuses:
            return _result(status, evidence=nodes)
    return _result('pass', evidence=nodes)


def _ranges(indices):
    out = []
    for index in indices:
        if out and out[-1][1]+1 == index:
            out[-1][1] = index
        else:
            out.append([index, index])
    return out


def _windows(tour, config):
    visits = {v['name']: v['frame'] for v in tour.get('visits', [])}
    out = []
    for chapter in config.get('chapters', []):
        if chapter.get('phase') != 'observe':
            continue
        start, end = visits.get(chapter.get('from')), visits.get(chapter.get('to'))
        if start is None or end is None or not 0 <= start <= end < len(tour.get('frames', [])):
            raise ValueError('Observation chapter has no valid frame window: '+chapter.get('name', ''))
        out.append({'name': chapter.get('name'), 'from': chapter.get('from'),
                    'to': chapter.get('to'), 'frames': [start, end]})
    return out


def closeout_assessment(baseline_tour, candidate_tour, config, contract_report,
                        mesh_report, scope=None, actual_playback=None):
    """Assess a new plan or an explicitly bounded revision without granting acceptance.

    scope.allowedChanges maps frame fields (e.g. yawRadians/pointMm) to closed
    frame ranges. preserveViewingWindows=True freezes complete observation
    frames including boundaries. A missing scope permits ordinary replanning.
    Playback evidence needs performed=True, result=pass|failed, method,
    reviewedSeconds, candidateTourSha256 and candidateConfigSha256. It records
    an assistant review only; user acceptance is never inferred.
    """
    source_tour, source_config = candidate_tour, config
    before, after, config = map(_load, (baseline_tour, candidate_tour, config))
    contract, mesh = _load(contract_report), _load(mesh_report)
    th, ch = _hashes(source_tour, after), _hashes(source_config, config)
    checks = {}
    frames = after.get('frames', [])
    fps, seconds = after.get('fps'), after.get('seconds')
    valid = (isinstance(fps, (int, float)) and math.isfinite(fps) and fps > 0
             and isinstance(seconds, (int, float)) and math.isfinite(seconds)
             and bool(frames) and abs(seconds-len(frames)/fps) < 1e-7
             and all(f.get('frame') == i for i, f in enumerate(frames)))
    checks['frameTiming'] = _result('pass' if valid else 'failed', frames=len(frames), fps=fps, seconds=seconds)
    maximum = config.get('maximumSeconds')
    checks['timeBound'] = _result('not_evaluated' if maximum is None else
                                 'pass' if valid and seconds <= maximum+1e-7 else 'failed',
                                 maximumSeconds=maximum, seconds=seconds)
    if scope is not None:
        time_same = all(before.get(k) == after.get(k) for k in ('fps', 'seconds')) and len(before.get('frames', [])) == len(frames)
        checks['timePreserved'] = _result('pass' if time_same else 'failed')
        changes, illegal = [], []
        allowed = scope.get('allowedChanges', {})
        for i in range(max(len(before.get('frames', [])), len(frames))):
            a = before.get('frames', [])[i] if i < len(before.get('frames', [])) else {}
            b = frames[i] if i < len(frames) else {}
            fields = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
            if fields:
                changes.append(i)
            for key in fields:
                ranges = allowed.get(key, [])
                if not any(len(r) == 2 and r[0] <= i <= r[1] for r in ranges):
                    illegal.append({'frame': i, 'field': key})
        top_changes = [k for k in ('visits', 'schemeSha256', 'sourceSchemeSha256', 'cameraProfile')
                       if before.get(k) != after.get(k)]
        checks['scopeFreeze'] = _result('failed' if illegal or top_changes else 'pass',
                                       changedFrameRanges=_ranges(changes), illegalChanges=illegal,
                                       changedFrozenMetadata=top_changes)
        base_config = _load(scope.get('baselineConfig', config))
        checks['configPreserved'] = (_result('pass' if base_config == config else 'failed')
                                     if 'baselineConfig' in scope else
                                     _result('not_evaluated', reason='baseline_config_missing'))
        if scope.get('preserveViewingWindows'):
            try:
                a_windows, b_windows = _windows(before, base_config), _windows(after, config)
                altered = [w['name'] for w in a_windows if before['frames'][w['frames'][0]:w['frames'][1]+1]
                           != frames[w['frames'][0]:w['frames'][1]+1]]
                checks['viewingWindows'] = _result('pass' if a_windows == b_windows and not altered else 'failed',
                                                    count=len(a_windows), altered=altered, boundariesIncluded=True)
            except (ValueError, KeyError, TypeError) as exc:
                checks['viewingWindows'] = _result('failed', reason=str(exc))
    else:
        for key in ('timePreserved', 'scopeFreeze', 'configPreserved', 'viewingWindows'):
            checks[key] = _result('not_evaluated', required=False, reason='ordinary_replanning')
    checks['layoutPreserved'] = _result('pass' if before.get('schemeSha256') and before.get('schemeSha256') == after.get('schemeSha256') else 'failed')
    checks['numericAudit'] = _audit(contract, 'contract')
    checks['meshAudit'] = _audit(mesh, 'actual_mesh')
    for name, report in (('numericBinding', contract), ('meshBinding', mesh)):
        mismatch = bool(isinstance(report, dict) and
                        ((report.get('tourSha256') and report['tourSha256'] not in th) or
                         (report.get('configSha256') and report['configSha256'] not in ch)))
        checks[name] = _result('failed' if mismatch else 'pass',
                              binding='explicit' if report and report.get('tourSha256') else 'supplied_report')
    cc = contract.get('checks', {}) if isinstance(contract, dict) else {}
    checklist = {
        'layoutReadable': _combine([_audit(cc.get('coreTargets'), 'contract.coreTargets'), _audit(mesh.get('coreTargets') if mesh else None, 'mesh.coreTargets')]),
        'orderedScan': _combine([_audit(cc.get('choreography'), 'contract.choreography'), _audit(cc.get('cameraEvidence'), 'contract.cameraEvidence')]),
        'naturalNavigation': _combine([_audit(cc.get('trajectory'), 'contract.trajectory'), _audit(cc.get('forwardMotion'), 'contract.forwardMotion')]),
        'noSustainedObstruction': _audit(mesh.get('screenQuality') if mesh else None, 'mesh.screenQuality'),
        'timeBound': checks['timeBound'],
    }
    required = [v for v in checks.values() if v.get('required', True)] + list(checklist.values())
    states = [v['status'] for v in required]
    engineering = ('failed' if 'failed' in states else 'action_required' if any(s != 'pass' for s in states) else 'pass')
    playback = _load(actual_playback) or {}
    bound = (playback.get('candidateTourSha256') in th and playback.get('candidateConfigSha256') in ch)
    review_times = playback.get('reviewedSeconds', [])
    valid_times = (isinstance(review_times, list) and bool(review_times) and valid and
                   all(isinstance(t, (int, float)) and math.isfinite(t) and 0 <= t < seconds for t in review_times))
    recorded = (bound and playback.get('performed') is True and bool(playback.get('method'))
                and valid_times and playback.get('result') in {'pass', 'failed'})
    playback_check = _result(playback['result'] if recorded else 'not_evaluated',
                             hashBound=bound, source='assistant_playback',
                             coverage=playback.get('coverage', 'targeted') if recorded else None)
    if recorded:
        playback_check['reviewedSeconds'] = playback['reviewedSeconds']
    return {'schema': 'homeowner-tour-closeout/1', 'engineeringStatus': engineering,
            'reviewStatus': 'ready_for_review' if engineering == 'pass' and playback_check['status'] != 'failed' else 'action_required',
            'candidateTourSha256': artifact_sha256(after), 'candidateConfigSha256': artifact_sha256(config),
            'checks': checks, 'closeoutChecklist': checklist, 'actualPlayback': playback_check,
            'humanAcceptance': _result('not_evaluated', accepted=False),
            'stageConclusion': 'playback_requires_action' if playback_check['status'] == 'failed' else
                               'engineering_ready_for_review' if engineering == 'pass' else 'engineering_requires_action',
            'videoGenerated': False,
            'limitations': ['Engineering audits do not certify visual comfort or user acceptance.',
                            'Exterior or other known failures receive no automatic exemption.']}


_HTML = '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>路线修改对照</title><style>__THEME__
.shell{max-width:1500px;margin:0 auto;padding:24px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:16px}.viewer{aspect-ratio:16/9;background:#eae6de;border:1px solid #ded5c8;border-radius:12px;overflow:hidden}iframe{width:100%;height:100%;border:0}.bar{display:flex;gap:12px;align-items:center;margin:18px 0}button{border:1px solid #cdbca7;border-radius:8px;padding:9px 16px;background:#fffaf2;color:#775234;cursor:pointer}button:disabled{opacity:.45}input{flex:1;min-width:60px;accent-color:#987047}h2{font-size:16px}.badge{font-size:13px;color:#7c6955}.points{display:flex;flex-wrap:wrap;gap:8px}.clock{white-space:nowrap;font-size:13px}@media(max-width:750px){.pair{grid-template-columns:1fr}.shell{padding:16px}.bar{gap:8px}button{padding:8px}}</style><main class="shell"><h1>路线修改对照</h1><p class="badge" id="status">正在加载…</p><div class="pair"><section><h2>调整前</h2><div class="viewer"><iframe id="before" src="runtime/renderer.html" title="调整前"></iframe></div></section><section><h2>调整后</h2><div class="viewer"><iframe id="after" src="runtime/renderer.html" title="调整后"></iframe></div></section></div><div class="bar"><button id="play" disabled>播放</button><button id="reset" disabled>重播</button><input id="seek" aria-label="对照进度" type="range" min="0" max="1" step="any" value="0"><span class="clock" id="clock">0.0 秒</span></div><div class="points" id="points"></div><p class="badge">两个画面使用同一时间轴。尚未生成视频。</p></main><script type="module" src="revision-review.js"></script></html>'''

_JS = '''import{samplePose}from './rehearsal-player.js';
const $=id=>document.getElementById(id),m=await fetch('comparison-manifest.json',{cache:'no-store'}).then(r=>r.json());
const tours=await Promise.all(['baseline','candidate'].map(k=>fetch(m[k].tour,{cache:'no-store'}).then(r=>r.json())));
let at=0,playing=false,last=null,ready=false,busy=false;const duration=m.sharedDurationSeconds;
$('seek').max=duration;function paint(){if(!ready||busy)return;busy=true;try{['before','after'].forEach((id,i)=>$(id).contentWindow.renderInteractiveFrame(samplePose(tours[i],at)));$('seek').value=at;$('clock').textContent=at.toFixed(1)+' / '+duration.toFixed(1)+' 秒';}finally{busy=false}}
function pause(){playing=false;last=null;$('play').textContent='播放'}function seek(v){pause();at=Math.max(0,Math.min(duration,v));paint()}
$('play').onclick=()=>{if(!ready)return;if(playing)pause();else{if(at>=duration)at=0;playing=true;last=null;$('play').textContent='暂停'}};$('reset').onclick=()=>seek(0);$('seek').oninput=()=>seek(Number($('seek').value));
for(const seconds of m.reviewSeconds){const b=document.createElement('button');b.textContent=seconds.toFixed(1)+' 秒';b.onclick=()=>seek(seconds);$('points').append(b)}
const timer=setInterval(()=>{if(['before','after'].every(id=>$(id).contentWindow.rendererReady)){clearInterval(timer);ready=true;$('play').disabled=false;$('reset').disabled=false;const status=m.engineeringStatus;$('status').textContent=status==='pass'?'检查完成 · 待审阅':status==='failed'?'检查发现问题 · 待调整':'待审阅';paint()}},100);
function tick(t){if(playing){if(last!==null)at=Math.min(duration,at+Math.max(0,t-last)/1000);last=t;paint();if(at>=duration)pause()}requestAnimationFrame(tick)}requestAnimationFrame(tick);document.addEventListener('visibilitychange',()=>{if(document.hidden)pause()});window.revisionReview={seek,getTime:()=>at,getTours:()=>tours,manifest:m};
'''


def build_revision_review(out, baseline_tour_path, candidate_tour_path,
                          baseline_config_path, candidate_config_path, runtime,
                          baseline_report=None, candidate_report=None, limits=None):
    """Create a portable, synchronous before/after HTML review on a shared scene.

    Optional candidate_report is {contract, mesh, scope, actualPlayback}; limits
    may provide reviewSeconds and maximumSeconds. Existing output is rejected.
    Both versions must reference the same frozen scheme and have valid timing.
    """
    out, runtime = Path(out), Path(runtime)
    if out.exists():
        raise ValueError('Fresh revision review output required')
    before, after = map(_load, (baseline_tour_path, candidate_tour_path))
    bc, cc = map(_load, (baseline_config_path, candidate_config_path))
    if not before.get('schemeSha256') or before.get('schemeSha256') != after.get('schemeSha256'):
        raise ValueError('Both revisions must use the same frozen scene')
    limits = limits or {}
    for tour in (before, after):
        if not tour.get('frames') or tour.get('fps', 0) <= 0 or abs(tour['seconds']-len(tour['frames'])/tour['fps']) > 1e-7:
            raise ValueError('Invalid comparison timeline')
    if limits.get('maximumSeconds') is not None and after['seconds'] > limits['maximumSeconds']+1e-7:
        raise ValueError('Candidate exceeds the declared time budget')
    scene = json.loads((runtime/'scene.json').read_text())
    if scene.get('schemeSha256') and scene['schemeSha256'] != after['schemeSha256']:
        raise ValueError('Comparison runtime does not match the frozen scheme')
    report = _load(candidate_report) or {}
    if report:
        report = {**report}
        for key in ('contract', 'mesh', 'scope', 'actualPlayback'):
            if key in report:
                report[key] = _load(report[key])
        if isinstance(report.get('scope'), dict) and 'baselineConfig' in report['scope']:
            report['scope'] = {**report['scope'], 'baselineConfig': _load(report['scope']['baselineConfig'])}
    assessment = None
    if 'contract' in report or 'mesh' in report:
        scope = report.get('scope')
        if scope is not None:
            scope = {**scope, 'baselineConfig': bc}
        assessment = closeout_assessment(baseline_tour_path, candidate_tour_path, candidate_config_path,
                                         report.get('contract'), report.get('mesh'), scope,
                                         report.get('actualPlayback'))
    end = min((len(before['frames'])-1)/before['fps'], (len(after['frames'])-1)/after['fps'])
    review_seconds = sorted(set(float(x) for x in limits.get('reviewSeconds', []) if 0 <= float(x) <= end))
    manifest = {'schema': 'homeowner-tour-revision-review/1', 'baseline': {}, 'candidate': {},
                'sharedRuntime': 'runtime', 'sharedDurationSeconds': end,
                'reviewSeconds': review_seconds, 'sameAbsoluteTime': True,
                'engineeringStatus': assessment['engineeringStatus'] if assessment else 'not_evaluated',
                'humanAcceptance': 'not_evaluated', 'videoGenerated': False}
    required_sources = ('renderer.html', 'scene.json', 'geometry.bin', 'three.module.js', 'three.core.js', 'THREE-LICENSE.txt')
    for name in required_sources:
        if not (runtime/name).is_file():
            raise ValueError('Missing comparison runtime source: '+name)
    renderer = prepare_renderer((runtime/'renderer.html').read_text())
    renderer = renderer.replace('</style>', 'html,body{height:100%;background:#eae6de}body{display:flex;align-items:center;justify-content:center}canvas{width:100%!important;height:auto!important;max-height:100%;object-fit:contain}</style>', 1)
    out.mkdir(parents=True)
    target = out/'runtime'
    target.mkdir()
    for name in ('scene.json', 'geometry.bin', 'three.module.js', 'three.core.js', 'THREE-LICENSE.txt'):
        shutil.copy2(runtime/name, target/name)
    (target/'renderer.html').write_text(renderer)
    manifest['runtimeHashes'] = {n: hashlib.sha256((target/n).read_bytes()).hexdigest()
                                 for n in ('scene.json', 'geometry.bin')}
    for key, tour, config in (('baseline', before, bc), ('candidate', after, cc)):
        tour_name, config_name = key+'-tour.json', key+'-config.json'
        (out/tour_name).write_text(json.dumps(tour, ensure_ascii=False, indent=2))
        (out/config_name).write_text(json.dumps(config, ensure_ascii=False, indent=2))
        manifest[key] = {'tour': tour_name, 'config': config_name, 'tourSha256': artifact_sha256(tour),
                         'configSha256': artifact_sha256(config), 'seconds': tour['seconds']}
    for key, item in (('baseline', baseline_report), ('candidate', report or None)):
        if item is not None:
            name = key+'-report.json'
            (out/name).write_text(json.dumps(_load(item), ensure_ascii=False, indent=2))
            manifest[key]['report'] = name
    if assessment:
        (out/'closeout-assessment.json').write_text(json.dumps(assessment, ensure_ascii=False, indent=2))
        manifest['assessment'] = 'closeout-assessment.json'
    shutil.copy2(ASSETS/'rehearsal-player.js', out/'rehearsal-player.js')
    (out/'index.html').write_text(_HTML.replace('__THEME__', theme()))
    (out/'revision-review.js').write_text(_JS)
    (out/'comparison-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest
