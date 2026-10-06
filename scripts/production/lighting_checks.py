"""Non-mutating concept light coverage checks; never invent fixture positions."""
import math,re
from pathlib import Path
MAIN_TYPES={'ceilinground','ceilingsquare','lightpanel','pendant','linearlight'}
_source=(Path(__file__).resolve().parents[2]/'assets/h5/source/renovation-components-v12.js').read_text(encoding='utf-8')
LIT_TYPES={'pendant','downlight','tracklight'}|set(re.findall(r"def\('([^']+)'[^\n]*,true\)",_source))
def inside(point,poly):
    x,y=point;on=False
    for i,(a,b) in enumerate(poly):
        c,d=poly[i-1]
        if ((b>y)!=(d>y)) and x<(c-a)*(y-b)/(d-b)+a:on=not on
    return on

def lighting_report(case):
    rooms=case['model']['rooms'];state=case['initialState'];fixtures=[f for f in state['furniture'] if f['type'] in LIT_TYPES]
    warnings=[];coverage=[]
    for r in rooms:
        local=[f for f in fixtures if inside((f['cx'],f['cy']),r['poly'])]
        main=[f for f in local if f['type'] in MAIN_TYPES and f.get('lightOn',True) and f.get('lightIntensity',3)>0]
        required=r.get('mainLightingRequired',True)
        coverage.append({'roomId':r['id'],'mainRequired':required,'mainIds':[f['id'] for f in main],'fixtureCount':len(local)})
        if required and not main:warnings.append({'code':'missing-main-light','roomId':r['id'],'message':'功能区缺少已启用的主灯；灯位需设计确认。'})
    for f in fixtures:
        matches=[r for r in rooms if inside((f['cx'],f['cy']),r['poly'])]
        if not matches:warnings.append({'code':'fixture-outside-rooms','fixtureId':f['id']})
        if len(matches)>1:warnings.append({'code':'fixture-room-ambiguity','fixtureId':f['id'],'roomIds':[r['id'] for r in matches]})
        top=f.get('elevation',0)+f['h'];height=case['model']['height']
        # Installed ceiling faces must not be hidden above a finished flat ceiling.
        for c in state.get('ceilings',[]):
            room=next((r for r in rooms if r['id']==c['roomId']),None)
            if room and c['mode']=='flat' and inside((f['cx'],f['cy']),c.get('poly') or room['poly']):height=min(height,case['model']['height']-c['drop'])
        if f['type'] in MAIN_TYPES|{'downlight'} and top>height+2 and not f.get('recessedCeiling') and f.get('mount')!='ceiling':
            warnings.append({'code':'fixture-above-finished-ceiling','fixtureId':f['id'],'finishedHeight':height})
    return {'status':'warning' if warnings else 'pass','coverage':coverage,'warnings':warnings,'scope':'Input checks only; actual emitting-face occlusion and room brightness require mesh/visual inspection.'}
