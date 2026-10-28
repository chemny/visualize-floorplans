"""Bounded passage-gaze selection; final frame/mesh contracts remain authoritative."""
import math,bisect
from plan_route import inside


def gaze(planner,dense,distances,start_yaw,end_yaw,policy):
    from design_homeowner_tour import clear_distance
    from camera_gaze import delta
    polygons=policy['coveragePolygons'];minimum=policy['minimumCoveragePercent']
    if not polygons or not 0<minimum<=100:raise ValueError('Explicit passage coverage geometry/percentage required')
    grid=policy.get('coverageGridMm',300);width=policy.get('coverageBeamWidth',64)
    if grid<=0 or not isinstance(width,int) or not 1<=width<=128:raise ValueError('Bounded passage search required')
    points=[]
    for poly in polygons:
        points.extend([[x,y] for x in range(int(min(q[0] for q in poly))+grid//2,int(max(q[0] for q in poly)),grid)
                       for y in range(int(min(q[1] for q in poly))+grid//2,int(max(q[1] for q in poly)),grid) if inside([x,y],poly)])
    if not points:raise ValueError('Passage coverage needs nonempty samples')
    indices=[0]
    for i,d in enumerate(distances[1:-1],1):
        if d-distances[indices[-1]]>=300:indices.append(i)
    if indices[-1]!=len(dense)-1:indices.append(len(dense)-1)
    angles=[math.radians(i*15) for i in range(24)]+[start_yaw,end_yaw]
    sy,ey=24,25;half=math.radians(policy.get('horizontalFovDegrees',76)/2)
    speed=policy.get('maximumSpeedMps',1.2)*1000;turn=math.radians(policy.get('maxYawDegreesPerSecond',32))
    cap=policy.get('maximumEffortSeconds',float('inf'));masks=[];walls=[]
    for index in indices:
        p=dense[index];visible=[]
        if any(inside(p,poly) for poly in polygons):
            for qi,q in enumerate(points):
                d=math.dist(p,q);a=math.atan2(q[1]-p[1],q[0]-p[0])
                if 100<=d<=7000 and clear_distance(planner,p,a,d)>=d-25:visible.append((qi,a))
        maskrow=[];wallrow=[]
        for a in angles:
            maskrow.append(sum(1<<qi for qi,bearing in visible if abs(delta(a,bearing))<=half))
            wallrow.append(sum(clear_distance(planner,p,a+math.radians(v),900)<900 for v in (-30,-15,0,15,30))/5)
        masks.append(maskrow);walls.append(wallrow)
    # (last angle, coverage bitset, effort, visual cost, winding sign, reversals, path)
    states=[(sy,masks[0][sy],0.,0.,0,0,[sy])]
    for node in range(1,len(indices)):
        options=[ey] if node==len(indices)-1 else range(len(angles));new={}
        remaining=(distances[-1]-distances[indices[node]])/speed
        for last,mask,effort,visual,sign,reversals,keys in states:
            for option in options:
                change=delta(angles[last],angles[option]);seconds=max((distances[indices[node]]-distances[indices[node-1]])/speed,abs(change)/turn)
                total=effort+seconds;floor=max(remaining,abs(delta(angles[option],end_yaw))/turn)
                if total+floor>cap+1e-9:continue
                direction=1 if change>.02 else -1 if change<-.02 else sign
                rev=reversals+int(bool(sign and direction!=sign))
                bits=mask|masks[node][option]
                row=(option,bits,total,visual+walls[node][option]*seconds,direction,rev,keys+[option])
                key=(option,bits,direction)
                if key not in new or (total,rev,row[3])<(new[key][2],new[key][5],new[key][3]):new[key]=row
        if not new:raise ValueError('Passage gaze cannot fit its bounded connection effort')
        def score(row):
            percent=row[1].bit_count()/len(points)*100
            return (max(0,minimum-percent),row[2]+row[3]*.15+row[5]*.15)
        ranked=sorted(new.values(),key=score)
        # Keep alternatives by exit angle, not many near-identical masks at one yaw.
        chosen=[];counts={}
        for row in ranked:
            if counts.get(row[0],0)>=max(2,width//12):continue
            chosen.append(row);counts[row[0]]=counts.get(row[0],0)+1
            if len(chosen)>=width:break
        for row in ranked:
            if len(chosen)>=width:break
            if row not in chosen:chosen.append(row)
        states=chosen
    selected=min(states,key=lambda row:(max(0,minimum-row[1].bit_count()/len(points)*100),row[2]+row[3]*.15+row[5]*.15))
    values=[angles[selected[-1][0]]]
    for key in selected[-1][1:]:values.append(values[-1]+delta(values[-1],angles[key]))
    anchors=[distances[i] for i in indices];result=[]
    for d in distances:
        k=max(0,min(len(indices)-2,bisect.bisect_right(anchors,d)-1));u=(d-anchors[k])/max(1e-9,anchors[k+1]-anchors[k])
        result.append(values[k]+(values[k+1]-values[k])*u)
    return result
