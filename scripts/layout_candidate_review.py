"""Evidence-bound candidate comparison, not automatic design optimisation.

Six qualitative dimensions reuse case evidence. Hard failures cannot be offset
by appearance or storage gains. Older reviews report missing comparison honestly.
"""
import json
from design_contract import digest

DIMENSIONS = ('function', 'space_use', 'convenience', 'safety_comfort', 'maintenance', 'visual_coherence')
HARD_CHECKS = ('required_functions', 'safe_operation', 'required_access')


def require(ok, text):
    if not ok: raise ValueError(text)


def state_from(value):
    return value.get('scheme', value.get('initialState', value.get('state', value)))


def compare_candidates(state, record, base, artifact):
    block = record.get('candidateComparison')
    if block is None: return {'status': 'not_provided'}
    require(block['contextStateSha256'] == digest(state), 'Candidate comparison context is stale')
    require(block.get('mode') in ('design_comparison','retrospective_validation'), 'Declare design comparison or retrospective validation')
    artifact(block['intentEvidence'], base)
    require(bool(block.get('scope')), 'Candidate comparison needs an explicit scope')
    candidates = block['candidates']; require(len(candidates) >= 2, 'At least two actual candidate states required')
    ids=set(); hashes=set(); states={}; summaries={}
    for c in candidates:
        require(c.get('id') and c['id'] not in ids, 'Candidate ID missing or duplicate'); ids.add(c['id'])
        candidate = state_from(json.loads(artifact(c['snapshot'], base).read_text(encoding='utf-8')))
        require(c['stateSha256'] == digest(candidate), 'Candidate snapshot/hash mismatch')
        require(c['stateSha256'] not in hashes, 'Duplicate layouts are not alternatives'); hashes.add(c['stateSha256']); states[c['id']]=candidate
        require(set(c['hardChecks']) == set(HARD_CHECKS), 'Functional, safety and access hard checks required')
        for name, check in c['hardChecks'].items():
            require(check['status'] in ('pass','fail','unverified') and bool(check.get('finding')), 'Hard check needs a finding and status')
            require(check.get('evidence'), 'Hard check evidence required')
            for ref in check['evidence']: artifact(ref,base)
        require(set(c['dimensions']) == set(DIMENSIONS), 'All six layout dimensions required')
        for name, finding in c['dimensions'].items():
            require(finding.get('status') in ('assessed','unverified','not_applicable'), 'Unknown dimension status')
            require(bool(finding.get('benefit')) and bool(finding.get('limitation')), 'Dimension needs benefits and limitations, not only collision pass')
            require(finding.get('evidence'), 'Dimension evidence required')
            for ref in finding['evidence']: artifact(ref, base)
        summaries[c['id']]={name:v['status'] for name,v in c['hardChecks'].items()}
    eligible={cid for cid, checks in summaries.items() if all(v=='pass' for v in checks.values())}
    if block['mode']=='design_comparison':
        require(len(eligible)>=2, 'Design comparison needs at least two viable alternatives')
    selection=block['selection']; chosen=selection['candidateId']
    require(chosen in states and digest(states[chosen])==digest(state), 'Selected candidate is not the reviewed current layout')
    require(all(v=='pass' for v in summaries[chosen].values()), 'Selected candidate has failed/unverified hard constraints; benefits cannot offset them')
    require(bool(selection.get('reason')), 'Selection needs a substantive reason')
    rejected=selection['alternatives']
    require(len(rejected)==len(ids)-1 and {x['candidateId'] for x in rejected}==ids-{chosen}, 'Every alternative needs a selection/rejection reason')
    for other in rejected:
        require(bool(other.get('reason')) and bool(other.get('preferredDimensions')) and set(other['preferredDimensions'])<=set(DIMENSIONS), 'Alternative trade-off reasoning required')
    tradeoffs=selection['tradeoffs']; require(bool(tradeoffs), 'Selected layout must disclose trade-offs')
    for t in tradeoffs:
        require(t.get('dimension') in DIMENSIONS and bool(t.get('cost')) and bool(t.get('response')), 'Trade-off cost and response required')
    for condition in selection.get('conditions',[]):
        require(condition.get('text') and condition['text'] in artifact(condition['artifact'],base).read_text(encoding='utf-8'), 'Selection operating condition absent from delivery')
    # Compare only the requested scope; changing an unrelated room is not a free alternative.
    require({'walls','doorStyles','rooms','style'} <= set(block['preservedFields']), 'Preserve structural, room and style comparison context')
    blocked={x['id'] for x in record.get('operationMatrix',{}).get('scenarios',[]) if x['expected']=='blocked'}
    require(blocked <= set(selection.get('useConditionScenarioIds',[])), 'Selection ignores restricted operating states')
    allowed=set(block['allowedChangedIds']); current={f['id']:f for f in state['furniture']}
    for cid,candidate in states.items():
        before={f['id']:f for f in candidate['furniture']}
        require({i for i in set(current)|set(before) if current.get(i)!=before.get(i)}<=allowed, 'Candidate changed objects outside comparison scope')
        for key in block['preservedFields']:
            require(candidate.get(key)==state.get(key), 'Candidate changed preserved context: '+key)
    return {'status':'reviewed_with_tradeoffs','candidates':len(candidates),'selected':chosen,'mode':block['mode'],'viableCandidates':len(eligible),
            'scope':'Evidence and completeness/constraint validation. Judgments supplied by reviewer; no numeric total, automatic aesthetic rating or optimal-layout claim.'}
