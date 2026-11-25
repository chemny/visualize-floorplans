"""Room-size tiers for a house tour: how deep to stand, how long to look, how wide to sweep.

A product default, not a standard. The tiers follow floor area; each tier gives a station-depth
cap (measured from the door line), a viewing time and a single one-way sweep. Case rules from the
user (a shallower depth, a different time) override a tier but may only make the depth stricter.
"""

SCHEMA = 'homeowner-room-size-tiers/1'
# (upper bound in m2 exclusive, name). Under 5 m2 a room is shot from its doorway, not entered (user decision 2026-11-15).
BOUNDS = ((5.0, 'under5'), (10.0, '5to10'), (20.0, '10to20'))
LAST = 'over20'
TIERS = {
    'under5': {'label': '5 m2 以下', 'maxEntryDepthMm': 250, 'viewSeconds': 1.5, 'maxSweepDegrees': 40, 'retraceBudgetDegrees': 0},
    '5to10': {'label': '5-10 m2', 'maxEntryDepthMm': 600, 'viewSeconds': 2.25, 'maxSweepDegrees': 60, 'retraceBudgetDegrees': 0},
    '10to20': {'label': '10-20 m2', 'maxEntryDepthMm': 900, 'viewSeconds': 3.0, 'maxSweepDegrees': 80, 'retraceBudgetDegrees': 60},
    'over20': {'label': '20 m2 及以上', 'maxEntryDepthMm': 1200, 'viewSeconds': 4.75, 'maxSweepDegrees': 100, 'retraceBudgetDegrees': 90},
}


def area_m2(poly):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2e6


def tier_of(area):
    """Tier name for a floor area in m2; a boundary area belongs to the larger tier."""
    for bound, name in BOUNDS:
        if area < bound:
            return name
    return LAST


def tier_for_room(room):
    name = tier_of(area_m2(room['poly']))
    return name, TIERS[name]


def stricter_depth(tier_depth, case_depth):
    """The depth cap in force: the tier cap, or a stricter (smaller) case value."""
    return tier_depth if case_depth is None else min(tier_depth, case_depth)


def retrace_budget(area, overrides=None):
    """Degrees a room's sweep may retrace (the smaller of its two opposite swings); 0 means one-way only.

    A little retrace is allowed in bigger rooms, bounded by the tier. The check treats up to 1 degree as noise."""
    name = tier_of(area)
    value = (overrides or {}).get(name, TIERS[name]['retraceBudgetDegrees'])
    return max(1.0, float(value))
