"""Four-stage approval chain: route -> camera rehearsal -> video -> narration.
Reads and checks bound records. Never creates, repairs or infers an approval.
"""
import json,math
from pathlib import Path
from tour_stage_gate import bound,resolve,read,require_video
from tour_spatial_plan import require_approval,conformance

def path_of(value,base):
 """Accept a bound record or a plain path; plain paths are bound at read time."""
 if isinstance(value,dict):return resolve(value,base)
 if not value:raise ValueError('Missing stage reference')
 p=Path(value);return (p if p.is_absolute() else Path(base)/p).resolve()

def require_camera_entry(job,base='.'):
 """Every camera/time planning entry consumes a real route approval first."""
 if not job.get('spatialPlan') or not job.get('spatialReview'):raise ValueError('Camera planning requires an approved spatial route: run h5.py plan-route, show route.html and record the user confirmation first')
 plan=path_of(job['spatialPlan'],base);review=path_of(job['spatialReview'],base)
 value=require_approval(review,plan,path_of(job['bundle'],base) if job.get('bundle') else None)
 return {'plan':plan,'review':review,'value':value}

def require_rehearsal_chain(manifest,base,tour_path):
 """Capture entries re-verify the route approval the rehearsal was built from."""
 refs=manifest.get('references',{})
 if not refs.get('spatialPlan') or not refs.get('spatialReview'):raise ValueError('Rehearsal has no approved spatial route; confirm the route, then regenerate the camera rehearsal')
 plan=resolve(refs['spatialPlan'],base);review=resolve(refs['spatialReview'],base)
 value=require_approval(review,plan,resolve(refs['bundle'],base))
 if value['schemeSha256']!=manifest.get('schemeSha256'):raise ValueError('Spatial route scheme differs from rehearsal')
 report=conformance(value,read(tour_path))
 if report['issues']:raise ValueError('Camera left the approved route; return to route confirmation: '+', '.join(i['code'] for i in report['issues']))
 return value

def pass_through_stations(brief,plan):
    """Route stations the brief does not stop to observe; report them so none is dropped unseen."""
    seen={r['name'] for r in brief.get('rooms',[])}
    return [s['name'] for s in plan['stations'] if s['name'] not in seen]


def check_brief_alignment(brief,plan):
    """The camera brief must follow the approved route; catch drift before a long search."""
    issues=[];stations=plan['stations'];names=[x['name'] for x in stations]
    rooms={r.get('observationId',r.get('roomId')):r for r in brief.get('rooms',[])}
    order=brief.get('fixedOrder')
    if not order:return [{'code':'brief_order_not_fixed','message':'Set fixedOrder to the approved route order'}]
    unknown=[i for i in order if i not in rooms]
    if unknown:return [{'code':'brief_unknown_observation','ids':unknown}]
    mine=[rooms[i]['name'] for i in order]
    # A route station the brief does not observe is a pass-through; observed ones keep route order.
    cursor=0;ordered=True
    for name in mine:
        if name not in names[cursor:]:ordered=False;break
        cursor=names.index(name,cursor)+1
    if not ordered:issues.append({'code':'brief_order_differs_from_route','approved':names,'brief':mine})
    if brief.get('entranceOpeningId')!=plan['entrance']['openingId']:issues.append({'code':'brief_entrance_differs_from_route','approved':plan['entrance']['openingId'],'brief':brief.get('entranceOpeningId')})
    start=plan['entrance']['startPointMm'];given=brief.get('startPoint')
    if not given or math.dist(given,start)>1:issues.append({'code':'brief_start_differs_from_route','approved':start,'brief':given})
    tolerance=plan['cameraEnvelope']['stationToleranceMm'];by_name={x['name']:x for x in stations}
    for i in order:
        r=rooms[i];station=by_name.get(r['name'])
        points=r.get('candidatePoints') or []
        if station and (not points or min(math.dist(p,station['pointMm']) for p in points)>tolerance):
            issues.append({'code':'brief_station_far_from_route','name':r['name'],'approved':station['pointMm'],'brief':points[:1]})
    return issues


def evaluate(job,base='.'):
 """Report each stage from actual bytes. An upstream problem blocks downstream stages."""
 base=Path(base);stages={};bundle=None
 def later(reason):
  return {'status':'blocked_by_upstream','reason':reason}
 def fail(error):
  return {'status':'stale_or_invalid','reason':str(error)}
 try:
  bundle=path_of(job['bundle'],base) if job.get('bundle') else None
  plan=path_of(job['spatialPlan'],base) if job.get('spatialPlan') else None
 except (ValueError,OSError) as error:plan=None;stages['route']=fail(error)
 approved=None
 if 'route' not in stages:
  if plan is None:stages['route']={'status':'not_prepared'}
  else:
   value=read(plan)
   if bundle is not None and value.get('bundle',{}).get('sha256')!=bound(bundle)['sha256']:stages['route']=fail('Current bundle differs from the route plan')
   elif not job.get('spatialReview'):stages['route']={'status':'pending_user_confirmation' if value.get('status')=='pending_user_confirmation' else 'needs_revision'}
   else:
    try:approved=require_approval(path_of(job['spatialReview'],base),plan,bundle);stages['route']={'status':'approved'}
    except (ValueError,OSError) as error:stages['route']=fail(error)
 camera_ok=False
 if approved is None:stages['preview']=later('Route is not approved')
 elif not job.get('routeReview'):stages['preview']={'status':'pending_user_confirmation' if job.get('rehearsal') else 'not_prepared'}
 else:
  try:
   from route_rehearsal import require_route
   runtime=path_of(job['runtime'],base);tour=path_of(job['tour'],base);require_route(path_of(job['routeReview'],base),tour,runtime);stages['preview']={'status':'approved'};camera_ok=True
  except (ValueError,OSError,KeyError) as error:stages['preview']=fail(error)
 video_ok=False
 if not camera_ok:stages['video']=later('Camera rehearsal is not approved')
 elif not job.get('video'):stages['video']={'status':'not_generated'}
 elif not job.get('videoReview'):stages['video']={'status':'pending_user_confirmation'}
 else:
  try:require_video(path_of(job['videoReview'],base),path_of(job['video'],base),path_of(job['tour'],base));stages['video']={'status':'approved'};video_ok=True
  except (ValueError,OSError) as error:stages['video']=fail(error)
 if not video_ok:stages['narrated']=later('Video is not approved')
 elif not job.get('narrated'):stages['narrated']={'status':'not_generated'}
 else:stages['narrated']={'status':'pending_user_confirmation'}
 return {'schema':'homeowner-tour-stage-state/1','stages':stages,'approvalGranted':False,'order':['route','preview','video','narrated']}

def main():
 import argparse
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--job',required=True);a.add_argument('--out',required=True);v=a.parse_args();out=Path(v.out)
 if out.exists():raise ValueError('Use a new stage state path')
 state=evaluate(read(v.job),Path(v.job).resolve().parent);out.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(state['stages'],ensure_ascii=False))
if __name__=='__main__':main()
