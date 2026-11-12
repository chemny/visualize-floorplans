"""Case lighting profile for the Blender branch: checked keys and per-fixture power.

Importable outside Blender. The profile lives in the case; nothing here knows a room or a number.
Fixture power in Blender watts is intensity x watts-per-intensity, where the intensity comes from the
scene and the watts-per-intensity is chosen by fixture id, then by fixture type, then globally.
"""
import math

SCHEMA_KEYS={'worldColor','worldStrength','cameraBackgroundColor','cameraBackgroundStrength','fixtureWattsPerIntensity',
             'fixtureWattsByType','fixtureWattsById','spotFixturesAsCones','excludeFixtureHousingShadows','exposure','lights','materials'}
MAXIMUM_WATTS_PER_INTENSITY=200.

def _number(value,low,high,name):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError(f'{name} must be a finite number in [{low}, {high}]')

def _colour(value,name):
    if not isinstance(value,(list,tuple)) or len(value)!=3:raise ValueError(f'{name} needs three channels')
    for v in value:_number(v,0,1,name)

def validate(profile):
    unknown=set(profile)-SCHEMA_KEYS
    if unknown:raise ValueError('Unknown lighting profile key: '+', '.join(sorted(unknown)))
    for key in ('worldColor','cameraBackgroundColor'):
        if key in profile:_colour(profile[key],key)
    for key in ('worldStrength','cameraBackgroundStrength'):
        if key in profile:_number(profile[key],0,10,key)
    if 'fixtureWattsPerIntensity' in profile:_number(profile['fixtureWattsPerIntensity'],0,MAXIMUM_WATTS_PER_INTENSITY,'fixtureWattsPerIntensity')
    for key in ('fixtureWattsByType','fixtureWattsById'):
        value=profile.get(key,{})
        if not isinstance(value,dict):raise ValueError(key+' must be an object')
        for name,watts in value.items():_number(watts,0,MAXIMUM_WATTS_PER_INTENSITY,key+'.'+str(name))
    if ('fixtureWattsByType' in profile or 'fixtureWattsById' in profile) and 'fixtureWattsPerIntensity' not in profile:
        raise ValueError('Per-type or per-fixture power needs a global fixtureWattsPerIntensity for every other fixture')
    if 'spotFixturesAsCones' in profile and type(profile['spotFixturesAsCones']) is not bool:raise ValueError('spotFixturesAsCones must be true or false')
    return profile

def watts_per_intensity(profile,fixture_id,kind):
    """Fixture id first, then its furniture type, then the global value."""
    by_id=profile.get('fixtureWattsById',{})
    if fixture_id in by_id:return by_id[fixture_id]
    by_type=profile.get('fixtureWattsByType',{})
    if kind in by_type:return by_type[kind]
    return profile['fixtureWattsPerIntensity']

def fixture_power(profile,fixture_id,kind,intensity):
    return intensity*watts_per_intensity(profile,fixture_id,kind)

def power_table(profile,illumination,kinds):
    """Rows for reporting: which fixtures got how many watts, grouped by type."""
    rows=[]
    for l in illumination:
        if not l.get('enabled',True):continue
        kind=kinds.get(l['fixtureId'])
        rows.append({'fixtureId':l['fixtureId'],'type':kind,'intensity':l['intensity'],'watts':fixture_power(profile,l['fixtureId'],kind,l['intensity'])})
    return rows

def brightness_report(means,low=140,high=170):
    """Mean luminance (0 to 255) of sampled frames against a review band. Product thresholds, not standards."""
    mean=sum(means)/len(means)
    return {'mean':mean,'minimum':min(means),'maximum':max(means),'band':[low,high],
            'status':'too_dark' if mean<low else 'too_bright' if mean>high else 'in_band'}
