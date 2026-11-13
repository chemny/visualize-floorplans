"""Validate explicit orthogonal finish patches; never infer or repartition rooms."""
from lighting_checks import inside

def solid_wall_rects(walls):
    # Share actual wall-end joins, openings and sill behavior with normalization.
    # Independent square end caps can invent a few mm of solid at a junction.
    from floor_boundaries import wall_rects
    return wall_rects(walls)

def check_floor_connections(model, walls):
    patches=model.get('floorConnections',[])
    if not patches:return
    polys=[model['footprint']]+[r['poly'] for r in model['rooms']]+[p['poly'] for p in patches]
    for poly in polys:
        if any(abs(a[0]-b[0])>1e-6 and abs(a[1]-b[1])>1e-6 for a,b in zip(poly,poly[1:]+poly[:1])):
            raise ValueError('Floor connections currently require orthogonal polygons')
    rects=solid_wall_rects(walls)
    xs=sorted({x for poly in polys for x,y in poly}|{x for a,c,b,d in rects for x in (a,b)})
    ys=sorted({y for poly in polys for x,y in poly}|{y for a,c,b,d in rects for y in (c,d)})
    for x0,x1 in zip(xs,xs[1:]):
        for y0,y1 in zip(ys,ys[1:]):
            pt=((x0+x1)/2,(y0+y1)/2)
            covered=[p['id'] for p in patches if inside(pt,p['poly'])]
            if not covered:continue
            if len(covered)>1:raise ValueError('Floor connections overlap: '+', '.join(covered))
            if not inside(pt,model['footprint']):raise ValueError('Floor connection outside footprint: '+covered[0])
            if any(inside(pt,r['poly']) for r in model['rooms']):raise ValueError('Floor connection overlaps room: '+covered[0])
            if any(a<pt[0]<b and c<pt[1]<d for a,c,b,d in rects):raise ValueError('Floor connection overlaps wall: '+covered[0])
