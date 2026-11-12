"""Whole front half of the chain for one case, no hand edits: route, brief, camera draft.

Writes a scorecard. It checks that the chain runs and how the numbers move; it never grants
approval, uses no stand-in approval and renders nothing.
"""
import argparse,json,time
from pathlib import Path
from tour_stage_gate import read

SCHEMA='homeowner-validation-scorecard/1'
PROTECTED=('excessive_transit_turn','transit_turn_beyond_path','abrupt_stop','small_room_too_deep','sustained_backward_walking','body_path_collision')

def validate(entry,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);card={'schema':SCHEMA,'id':entry['id'],'stages':{},'metrics':{},'failure':None,'approvalGranted':False,'videoGenerated':False}
    def stage(name,fn):
        started=time.monotonic()
        try:value=fn();card['stages'][name]={'status':'ok','seconds':round(time.monotonic()-started,1)};return value
        except (ValueError,KeyError,OSError,TimeoutError) as error:
            card['stages'][name]={'status':'failed','seconds':round(time.monotonic()-started,1),'error':str(error)[:300]};card['failure']=name;return None
    from tour_spatial_plan import run as run_route
    job={'schema':'homeowner-spatial-job/1','bundle':entry['bundle']}
    if entry.get('entranceOpeningId'):job.update(entranceOpeningId=entry['entranceOpeningId'],entranceSource=entry.get('entranceSource','manifest entry'))
    else:job['caseFile']=entry['caseFile']
    if entry.get('planImage'):job['planImage']=entry['planImage'];job['planBounds']=entry.get('planBounds')
    plan=stage('route',lambda:run_route(job,out,out/'route'))
    if plan is None:return card
    card['metrics'].update(routeStatus=plan['status'],routeDistanceM=round(plan['distanceM'],2),stationNames=[s['name'] for s in plan['stations']],autoFilled=plan['autoFilled'],excludedRooms=[r.get('name') or r.get('roomId') for r in plan['excludedRooms']])
    from brief_from_route import build as build_brief
    options={'maximumSeconds':entry.get('maximumSeconds'),'coverageMinimumPercent':entry.get('coverageMinimumPercent'),'coverageOff':entry.get('coverageOff',False),'cameraOptions':entry.get('cameraOptions','tuned')}
    built=stage('brief',lambda:build_brief(out/'route'/'spatial-plan.json',options))
    if built is None:return card
    brief,notes=built;(out/'brief.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8');(out/'brief-assumptions.json').write_text(json.dumps(notes,ensure_ascii=False,indent=2),encoding='utf-8')
    card['metrics'].update(observed=len(brief['rooms']),passThrough=[x['station'] for x in notes['passThrough']]+notes['routePassThrough'])
    if entry.get('optimizeStations') and entry.get('runtime'):
        from optimize_stations import optimize
        optimized=stage('stations',lambda:optimize(out/'brief.json',out/'route'/'spatial-plan.json',entry['runtime'],out/'stations',progress=lambda *a:None))
        if optimized is None:return card
        brief=optimized[0];(out/'brief-optimized.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2),encoding='utf-8');brief_path=out/'brief-optimized.json'
    else:brief_path=out/'brief.json'
    from tour_draft import draft
    result=stage('draft',lambda:draft(entry['bundle'],brief_path,out/'draft',entry.get('runtime') if entry.get('meshAudit') else None))
    if result is None:return card
    summary,diag,report=result
    card['metrics'].update(totalSeconds=round(summary['totalSeconds'],1),transitFraction=round(summary['transitFraction'],2),maxTransitTurnDegrees=summary['maxTransitTurnDegrees'],contractIssues=summary['contractIssues'],meshIssues=summary['meshIssues'],
                           protectedIssues=sorted(c for c in summary['contractIssues'] if c in PROTECTED))
    return card

def compare(card,baseline,turn_slack=15):
    """Regressions against recorded numbers. Better numbers are fine; worse ones are named."""
    problems=[]
    if card['failure']:problems.append({'code':'stage_failed','stage':card['failure'],'error':card['stages'][card['failure']].get('error')})
    m,b=card['metrics'],baseline or {}
    if not b or card['failure']:return problems
    new=sorted(set(m.get('protectedIssues',[]))-set(b.get('protectedIssues',[])))
    if new:problems.append({'code':'new_protected_issue','issues':new})
    if m.get('maxTransitTurnDegrees',0)>b.get('maxTransitTurnDegrees',0)+turn_slack:problems.append({'code':'turning_worse','was':b.get('maxTransitTurnDegrees'),'now':m.get('maxTransitTurnDegrees')})
    if m.get('stationNames')!=b.get('stationNames'):problems.append({'code':'route_stations_changed','was':b.get('stationNames'),'now':m.get('stationNames')})
    if m.get('routeDistanceM',0)>b.get('routeDistanceM',1e9)*1.1:problems.append({'code':'route_longer','was':b.get('routeDistanceM'),'now':m.get('routeDistanceM')})
    return problems

def unusable(entry):
    """Why a case cannot be run here, or None. A different bundle than the one the baseline came from is not run."""
    missing=[k for k in ('bundle','caseFile','runtime') if entry.get(k) and not Path(entry[k]).exists()]
    if missing:return 'inputs missing on this machine: '+', '.join(missing)
    if not entry.get('caseFile') and not entry.get('entranceOpeningId'):return 'needs caseFile or entranceOpeningId'
    expected=entry.get('schemeSha256')
    if expected and read(entry['bundle']).get('schemeSha256')!=expected:return 'bundle scheme differs from the one recorded for this case (older or restored file)'
    return None

def run_corpus(manifest_path,out,only=None):
    manifest=read(manifest_path);out=Path(out);rows=[]
    for entry in manifest['cases']:
        if only and entry['id'] not in only:continue
        reason=unusable(entry)
        if reason:rows.append({'id':entry['id'],'status':'skipped','reason':reason});continue
        card=validate(entry,out/entry['id']);problems=compare(card,entry.get('baseline'))
        (out/entry['id']/'scorecard.json').write_text(json.dumps({**card,'regressions':problems},ensure_ascii=False,indent=2),encoding='utf-8')
        rows.append({'id':entry['id'],'status':'regressed' if problems else 'ok','failure':card['failure'],'problems':problems,'metrics':card['metrics']})
    (out/'corpus-summary.json').write_text(json.dumps({'schema':SCHEMA,'rows':rows,'approvalGranted':False},ensure_ascii=False,indent=2),encoding='utf-8');return rows

def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--manifest',required=True);a.add_argument('--out',required=True);a.add_argument('--only',action='append')
    v=a.parse_args()
    if Path(v.out).exists():raise ValueError('Use a new output directory')
    rows=run_corpus(v.manifest,v.out,set(v.only) if v.only else None)
    for r in rows:print(r['id'],r['status'],r.get('failure') or '',[p['code'] for p in r.get('problems',[])])
    raise SystemExit(1 if any(r['status']=='regressed' for r in rows) else 0)
if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError) as e:raise SystemExit(str(e))
