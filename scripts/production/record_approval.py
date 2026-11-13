"""Write the stage-one route approval from the user's own words. Never invents either.

The caller passes the user's real name and verbatim statement; agents, fixtures and empty
evidence are refused. The record is bound to the plan, bundle and displayed page hashes.
"""
import datetime,json
from pathlib import Path
from tour_stage_gate import bound,resolve,read
from tour_spatial_plan import APPROVAL_SCHEMA,CHECKS,NON_SIGNERS,require_approval

def record_route(pending,out,confirmed_by,evidence):
    pending=Path(pending).resolve();out=Path(out).resolve()
    if out.exists():raise ValueError('Use a new approval path; existing records are preserved')
    name=str(confirmed_by or '').strip();words=str(evidence or '').strip()
    if not name or any(w in name.lower() for w in NON_SIGNERS):raise ValueError('confirmedBy must be the actual user, not an agent or fixture')
    if len(words)<2:raise ValueError("evidence must be the user's own words confirming the displayed route")
    record=read(pending)
    if record.get('schema')!=APPROVAL_SCHEMA or record.get('status')!='pending':raise ValueError('Expected an untouched pending spatial approval')
    base=pending.parent
    for key in ('plan','bundle','presentedPage'):resolve(record.get(key),base)
    record.update(status='approved',approvalSource='explicit_user_confirmation',confirmedBy=name,evidence=words,
                  checks={k:True for k in CHECKS},recordedAt=datetime.datetime.now().astimezone().isoformat(timespec='seconds'))
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    try:require_approval(out,resolve(record['plan'],base))
    except ValueError:
        out.unlink();raise
    return record


def _signer(confirmed_by,evidence):
    name=str(confirmed_by or '').strip();words=str(evidence or '').strip()
    if not name or any(w in name.lower() for w in NON_SIGNERS):raise ValueError('confirmedBy must be the actual user, not an agent or fixture')
    if len(words)<2:raise ValueError("evidence must be the user's own words about what they were shown")
    return name,words

def record_camera(pending,out,confirmed_by,evidence):
    """Camera rehearsal confirmation (homeowner-route-approval/1): only for a rehearsal that passed its own checks."""
    pending=Path(pending).resolve();out=Path(out).resolve()
    if out.exists():raise ValueError('Use a new approval path; existing records are preserved')
    name,words=_signer(confirmed_by,evidence);record=read(pending)
    if record.get('schema')!='homeowner-route-approval/1' or record.get('status')!='pending':raise ValueError('Expected an untouched pending camera approval')
    manifest_path=resolve(record.get('rehearsal'),pending.parent);manifest=read(manifest_path)
    if manifest.get('status')!='pending_user_review':raise ValueError('The rehearsal still needs revision ('+str(manifest.get('status'))+'); it is not something the user can confirm yet')
    animation=manifest['references']['animation'];shown=resolve(animation,manifest_path.parent)
    record.update(status='approved',approvalSource='explicit_user_confirmation',confirmedBy=name,evidence=words,presentedAnimationSha256=bound(shown)['sha256'],
                  checks={k:True for k in ('animationViewed','pathAndFacingApproved','durationAndRhythmApproved')},recordedAt=datetime.datetime.now().astimezone().isoformat(timespec='seconds'))
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');return record

def record_video(pending,out,confirmed_by,evidence):
    """Exact-video confirmation (homeowner-video-approval/1); checked by the same gate narration uses."""
    from tour_stage_gate import CHECKS,require_video
    pending=Path(pending).resolve();out=Path(out).resolve()
    if out.exists():raise ValueError('Use a new approval path; existing records are preserved')
    name,words=_signer(confirmed_by,evidence);record=read(pending)
    if record.get('schema')!='homeowner-video-approval/1' or record.get('status')!='pending' or record.get('purpose')=='sample':raise ValueError('Expected an untouched pending video approval for a real video')
    video=resolve(record.get('video'),pending.parent);tour=resolve(record.get('tour'),pending.parent)
    record.update(status='approved',approvalSource='explicit_user_confirmation',confirmedBy=name,evidence=words,checks={k:True for k in CHECKS},recordedAt=datetime.datetime.now().astimezone().isoformat(timespec='seconds'))
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
    try:require_video(out,video,tour)
    except ValueError:
        out.unlink();raise
    return record

NARRATED_SCHEMA='homeowner-narrated-approval/1'
NARRATED_CHECKS=('filmHeardInFull','voiceAndScriptApproved','subtitlesApproved','timingMatchesPicture')

def record_narrated(report,out,confirmed_by,evidence):
    """Narrated-film confirmation (stage 4): binds the exact composed film, captions and the video approval it came from."""
    from tour_stage_gate import require_video
    report=Path(report).resolve();out=Path(out).resolve()
    if out.exists():raise ValueError('Use a new approval path; existing records are preserved')
    name,words=_signer(confirmed_by,evidence);rec=read(report)
    if rec.get('status')!='pending_narrated_review' or rec.get('approvalGranted'):raise ValueError('Expected an untouched composition report awaiting narrated review')
    film=resolve(rec.get('output'),report.parent);captions=resolve(rec.get('captions'),report.parent)
    video=resolve(rec.get('video'),report.parent);tour=resolve(rec.get('tour'),report.parent);review=resolve(rec.get('videoReview'),report.parent)
    require_video(review,video,tour)
    record={'schema':NARRATED_SCHEMA,'status':'approved','approvalSource':'explicit_user_confirmation','confirmedBy':name,'evidence':words,
            'film':bound(film),'captions':bound(captions),'compositionReport':bound(report),'videoReview':bound(review),'video':bound(video),'tour':bound(tour),
            'checks':{k:True for k in NARRATED_CHECKS},'recordedAt':datetime.datetime.now().astimezone().isoformat(timespec='seconds')}
    out.write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8');return record

def require_narrated(approval,film):
    """True only if the approval is valid and still bound to exactly this film file."""
    approval=Path(approval);rec=read(approval)
    if rec.get('schema')!=NARRATED_SCHEMA or rec.get('status')!='approved' or not all(rec.get('checks',{}).get(k) for k in NARRATED_CHECKS):raise ValueError('Not a valid narrated-film approval')
    if resolve(rec.get('film'),approval.parent)!=Path(film).resolve():raise ValueError('Approval is for a different film')
    resolve(rec.get('captions'),approval.parent);resolve(rec.get('compositionReport'),approval.parent);return rec
