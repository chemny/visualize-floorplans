"""Version-bound layout reasoning, furniture groups and revision intent gate.

Numeric relations are computed from the scheme. Qualitative observations remain
human review, with hash-bound evidence; this tool never certifies taste or consent.
"""
import argparse, hashlib, json, math
from pathlib import Path
from design_contract import digest
from layout_access_checks import footprint, overlap
from layout_use_review import extensions
from layout_candidate_review import compare_candidates


def require(ok, message):
    if not ok: raise ValueError(message)


def artifact(ref, base):
    require(isinstance(ref, dict) and bool(ref.get('path')), 'Evidence artifact required')
    p = Path(base) / ref['path']
    require(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest() == ref.get('sha256'), 'Evidence missing or changed: '+str(p))
    return p


def observation(value, base):
    require(isinstance(value, dict) and value.get('status') == 'observed_clear', 'Reasoning/operation is unresolved')
    require(isinstance(value.get('observation'), str) and bool(value['observation'].strip()), 'Concrete review observation required')
    require(bool(value.get('evidence')), 'Review evidence required')
    for ref in value['evidence']: artifact(ref, base)


def relation(rule, objects):
    """Explicit case targets, never shared dimensional defaults."""
    kind = rule['kind']; ids = rule.get('ids', [])
    require(ids and len(ids)==len(set(ids)) and all(i in objects for i in ids), 'Relation references missing/duplicate objects')
    fs = [objects[i] for i in ids]
    if kind == 'count':
        require(len(fs) == rule['expected'], 'Object count differs from intent')
    elif kind == 'uniform_depth':
        require(max(f['d'] for f in fs)-min(f['d'] for f in fs) <= rule['toleranceMm'], 'Depth is not uniform')
    elif kind == 'aligned':
        field = {'x':'cx','y':'cy'}[rule['axis']]
        require(max(f[field] for f in fs)-min(f[field] for f in fs) <= rule['toleranceMm'], 'Furniture group axis misaligned')
    elif kind == 'pose':
        require(len(fs)==1 and bool(rule['values']), 'Pose needs one object and explicit fields')
        for k,v in rule['values'].items(): require(fs[0].get(k)==v, 'Requested field differs: '+k)
    elif kind == 'gap':
        require(len(fs)==2, 'Gap needs two objects')
        a,b=map(footprint,fs);axis={'x':0,'y':1}[rule['axis']]
        gap=max(b[axis]-a[axis+2],a[axis]-b[axis+2])
        require(rule['minimumMm'] <= gap <= rule['maximumMm'], 'Furniture edge gap outside declared targets')
    elif kind == 'operating_zone':
        r=rule['rect'];require(len(r)==4 and all(math.isfinite(x) for x in r) and r[2]>r[0] and r[3]>r[1], 'Invalid operating zone')
        require(not any(overlap(r,footprint(f)) for f in fs if f.get('elevation',0)<rule['heightLimitMm']), 'Operating zone blocked')
    else: raise ValueError('Unsupported layout relation: '+str(kind))


def review(case, record, base):
    require(record.get('schema')=='layout-review/1', 'Unsupported layout review schema')
    state=case.get('initialState',case.get('state',case));objects={f['id']:f for f in state['furniture'] if not f.get('assemblyOwner')}
    require(record.get('stateSha256')==digest(state), 'Layout review is stale')
    expected={r['id'] for r in case['model']['rooms']};rooms=record['rooms']
    require(len(rooms)==len(expected) and {r['id'] for r in rooms}==expected, 'Every real room needs a function/reasonableness review')
    for r in rooms:
        require(bool(r.get('purpose')) and isinstance(r.get('requirements'),list), 'Room purpose and independent function requirements required')
        observation(r['reasonableness'],base)
        require(r['requirements'] or bool(r.get('noEquipmentReason')), 'Empty inventory needs a reason')
        for q in r['requirements']:
            matches=[f for f in objects.values() if f.get('roomId')==r['id'] and f['type'] in q['types']]
            require(type(q['minimum']) is int and q['minimum']>=0 and len(matches)>=q['minimum'], 'Required room function/equipment missing: '+r['id'])
            if 'maximum' in q: require(len(matches)<=q['maximum'], 'Unrequested/surplus equipment: '+r['id'])
    groups=record['groups'];require(len({g['id'] for g in groups})==len(groups), 'Duplicate furniture group')
    for g in groups:
        require(g['members'] and all(i in objects for i in g['members']), 'Furniture group has missing members')
        require(all(objects[i].get('roomId')==g['roomId'] for i in g['members']), 'Furniture group room mismatch')
        observation(g['composition'],base)
        require(bool(g['useStates']), 'Group operating states required')
        for u in g['useStates']:
            require(bool(u.get('name')), 'Operating state name required');observation(u,base)
        require(bool(g['relations']), 'Explicit group relationships required')
        for rule in g['relations']: relation(rule,objects)
    furnished={f.get('roomId') for f in objects.values() if f['type']!='ceilinground' and not f.get('planPoint')}
    require(furnished <= {g['roomId'] for g in groups}, 'Furnished room missing group review')
    revision=record.get('revision')
    if revision:
        artifact(revision['intentEvidence'],base)
        old=json.loads(artifact(revision['baseline'],base).read_text())
        old=old.get('scheme',old.get('initialState',old.get('state',old)))
        before={f['id']:f for f in old['furniture'] if not f.get('assemblyOwner')}
        changed={i for i in set(before)|set(objects) if before.get(i)!=objects.get(i)}
        require(changed <= set(revision['allowedChangedIds']), 'Unrequested furniture changed')
        require(old['walls']==state['walls'] and old.get('doorStyles',{})==state.get('doorStyles',{}), 'Structural/opening changes need separate review')
        require(bool(revision['requirements']), 'Revision needs explicit semantic acceptance requirements')
        for q in revision['requirements']:
            if q['kind']=='inventory':
                matches=[f for f in objects.values() if f.get('roomId')==q['roomId'] and f['type'] in q['types']]
                require(len(matches)==q['expected'], 'Intent inventory count mismatch')
                for field in ('d','w','h'):
                    if field in q: require(all(f[field]==q[field] for f in matches), 'Intent dimensions differ: '+field)
            elif q['kind']=='absent': require(not (set(q['ids']) & set(objects)), 'Removed object still present')
            else: relation(q,objects)
    extra=extensions(state,record,groups,base,artifact,observation,relation)
    extra['candidateComparisonCheck']=compare_candidates(state,record,base,artifact)
    if 'candidateComparisonCheck' in record.get('requiredChecks',[]):
        require(extra['candidateComparisonCheck']['status']!='not_provided','Required candidate comparison missing')
    return {'status':'pass','rooms':len(rooms),'groups':len(groups),'revisionChecked':bool(revision),**extra,'scope':'Version/evidence and declared geometric/semantic checks only; qualitative observations are reviewer supplied. Not user acceptance, automatic image understanding or construction certification.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--case',required=True,type=Path);p.add_argument('--review',required=True,type=Path);a=p.parse_args()
    try: print(json.dumps(review(json.loads(a.case.read_text()),json.loads(a.review.read_text()),a.review.resolve().parent),ensure_ascii=False));return 0
    except (ValueError,KeyError,TypeError,OSError) as e:print(json.dumps({'status':'fail','error':str(e)},ensure_ascii=False));return 1
if __name__=='__main__':raise SystemExit(main())
