"""Stops and starts must be eased: a walk may not go from a brisk pace to standing still in a blink.

Product thresholds, not a comfort standard. A case may state tighter or looser numbers explicitly.
"""
import math

SCHEMA='homeowner-stop-smoothness/1'
DEFAULTS={'dropMps':.8,'windowSeconds':.4,'stillMps':.1,'minimumStillSeconds':.2}

def speeds(frames,fps):
    return [math.dist(a['pointMm'],b['pointMm'])*fps/1000 for a,b in zip(frames,frames[1:])]

def inspect(tour,config):
    policy={**DEFAULTS,**config.get('stopPolicy',{})}
    for key,value in policy.items():
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError('Positive finite stop policy value required: '+key)
    fps=tour['fps'];v=speeds(tour['frames'],fps);window=max(1,round(policy['windowSeconds']*fps));still=max(1,round(policy['minimumStillSeconds']*fps));issues=[];i=0
    while i<len(v):
        if v[i]>=policy['stillMps']:i+=1;continue
        j=i
        while j<len(v) and v[j]<policy['stillMps']:j+=1
        if j-i>=still:
            before=max(v[max(0,i-window):i],default=0);after=max(v[j:j+window],default=0)
            if i>0 and before>=policy['dropMps']:issues.append({'code':'abrupt_stop','edge':'stop','atSeconds':i/fps,'fromMps':before,'withinSeconds':window/fps})
            if j<len(v) and after>=policy['dropMps']:issues.append({'code':'abrupt_stop','edge':'start','atSeconds':j/fps,'toMps':after,'withinSeconds':window/fps})
        i=max(j,i+1)
    return {'schema':SCHEMA,'status':'needs_revision' if issues else 'pass','issues':issues,'policy':policy,'peakSpeedMps':max(v,default=0)}
