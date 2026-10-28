"""Door-mechanism diagnostics shared by layout generation and build receipts.
No automatic changes, product/code certification or implied path acceptance.
"""
import math
from door_checks import effective_openings, door_leaves, is_closed, segment_in_body, sliding_geometry, leaf_segments
from floor_connection_checks import solid_wall_rects

IGNORED={'threshold','doortrim','windowtrim','skirting','floordrain','transition'}

def rect_object(rect):
    a,b,c,d=rect
    return dict(cx=(a+c)/2,cy=(b+d)/2,w=c-a,d=d-b,rot=0)

def point_distance(p,a,b):
    v=[b[k]-a[k] for k in (0,1)];den=sum(x*x for x in v)
    t=max(0,min(1,sum((p[k]-a[k])*v[k] for k in (0,1))/den)) if den else 0
    return math.dist(p,[a[k]+t*v[k] for k in (0,1)])

def segment_distance(a,b,c,d):
    cross=lambda u,v:u[0]*v[1]-u[1]*v[0]
    r=[b[k]-a[k] for k in (0,1)];s=[d[k]-c[k] for k in (0,1)];q=[c[k]-a[k] for k in (0,1)];den=cross(r,s)
    if abs(den)>1e-9 and 0<=cross(q,s)/den<=1 and 0<=cross(q,r)/den<=1:return 0
    return min(point_distance(a,c,d),point_distance(b,c,d),point_distance(c,a,b),point_distance(d,a,b))


def review_doors(case):
    state=case.get('initialState',case.get('state',{}));walls=state['walls'];objects=[f for f in state['furniture'] if f['type'] not in IGNORED and not f.get('planPoint')]
    solids=[(w['id'],r) for w in walls if not w.get('demolished') for r in solid_wall_rects([w])]
    openings=[(w,i,o) for w in walls if not w.get('demolished') for i,o in effective_openings(state,w) if o['kind'] in ('door','sliding')]
    def slide_segments(w,o):
        geometry=sliding_geometry(w,o)
        u=[(w['b'][k]-w['a'][k])/math.dist(w['a'],w['b']) for k in (0,1)];normal=[-u[1],u[0]]
        for panel in geometry['panels']:
            h=[panel['cx'],panel['cy']]
            yield 'panel',[h[k]-u[k]*panel['pw']/2 for k in (0,1)],[h[k]+u[k]*panel['pw']/2 for k in (0,1)],panel['thickness']/2
            if o.get('leaves')==1:
                pull=[h[k]+u[k]*panel['pw']*.34+normal[k]*o.get('slideSide',-1)*30 for k in (0,1)]
                yield 'pull',pull,pull,15
    current=[]
    for w,i,o in openings:
        segments=list(slide_segments(w,o)) if o['kind']=='sliding' else [seg for leaf in door_leaves(w,o,is_closed(state,w,o,i)) for seg in leaf_segments(leaf,leaf['angleDegrees'])]
        if not o.get('leafRemoved'):current.append((o.get('id',w['id']),segments))
    def inspect_segments(segments,door_id,height,other_doors=True):
        hits=[]
        for part,a,b,pad in segments:
            for f in objects:
                if f.get('elevation',0)>=height:continue
                if segment_in_body(a,b,f,pad):hits.append(dict(kind='furniture',part=part,objectId=f['id']))
            for wall_id,rect in solids:
                if segment_in_body(a,b,rect_object(rect),pad):hits.append(dict(kind='wall',part=part,wallId=wall_id))
            if other_doors:
                for other,segments in current:
                    if other==door_id:continue
                    for op,c,d,other_pad in segments:
                        if segment_distance(a,b,c,d)<pad+other_pad-.1:hits.append(dict(kind='other_door',part=part,otherOpeningId=other))
        return hits
    rows=[]
    for w,i,o in openings:
        ident=o.get('id',w['id']);height=o.get('height',2100);hits=[];closed_handle_note='Nominal handles, not a selected hardware product'
        if o.get('leafRemoved'):rows.append(dict(openingId=ident,mechanism='passage',status='pass',conflicts=[]));continue
        if o['kind']=='sliding':
            for frame in range(51):
                for hit in inspect_segments(slide_segments(w,{**o,'slideOpen':frame/50}),ident,height):hits.append({**hit,'slideOpen':frame/50})
            g=sliding_geometry(w,o);mechanism='wall_slide' if o.get('leaves')==1 else 'stacked_slide';extra=dict(netOpeningMm=g['netOpeningMm'],parkingChecked=o.get('leaves')==1)
        else:
            for leaf in door_leaves(w,o):
                steps=max(1,math.ceil(leaf['angleDegrees']/2))
                for step in range(steps+1):
                    angle=leaf['angleDegrees']*step/steps
                    for hit in inspect_segments(leaf_segments(leaf,angle),ident,height):hits.append({**hit,'angleDegrees':round(angle,2),'leafSide':leaf['side']})
            mechanism=o.get('doorModel','single');extra=dict(hingeEnd=o.get('hingeEnd','start'),swing=o.get('swing',1),angleDegrees=o.get('angle',90))
        unique={}
        for hit in hits:
            key=(hit['kind'],hit['part'],hit.get('objectId'),hit.get('wallId'),hit.get('otherOpeningId'),hit.get('leafSide'))
            unique.setdefault(key,hit)
        rows.append(dict(openingId=ident,wallId=w['id'],mechanism=mechanism,status='fail' if unique else 'pass',conflicts=list(unique.values()),**extra))
    paths=[]
    for spec in case.get('doorLayoutPolicy',{}).get('paths',[]):
        from plan_route import Planner
        cfg={'bodyRadiusMm':spec['bodyRadiusMm'],'gridMm':spec.get('gridMm',50),'accessPolygons':spec.get('accessPolygons',[])}
        planner=Planner({'state':state,'model':case['model']},cfg)
        try:
            points=planner.simplify([spec['from']]+planner.astar(spec['from'],spec['to'])+[spec['to']]);paths.append(dict(id=spec['id'],status='pass',points=points,bodyRadiusMm=spec['bodyRadiusMm']))
        except ValueError as error:paths.append(dict(id=spec['id'],status='fail',reason=str(error)))
    return dict(status='fail' if any(r['status']=='fail' for r in rows+paths) else 'pass',doors=rows,paths=paths,pathStatus='checked' if paths else 'not_provided',outsideEntrance='not_inferred',basis='2-degree hinged / 2-percent sliding samples; nominal handles and full parking projection; present other-door poses; no product certification',limitations=['Door-to-door check uses the other door current pose, not every simultaneous motion combination','Receiving-wall preference and main-leaf use need an explicit design review','Track attachment and individual hardware installation are separate checks'])
