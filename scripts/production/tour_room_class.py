"""Which rooms are the main rooms of a home, by what they are used for (not by what they are called).

A room is a main room when it holds something people live in or live from: sleeping, sitting, dining,
cooking, working. Bathrooms, balconies, passages, bay windows and storage are other rooms. A case can
name a room's class when the facilities say otherwise (coveragePolicy.roomClasses).
"""
MAJOR_FUNCTIONS = frozenset({'sleep', 'seating', 'dining', 'cooking', 'kitchen_wash', 'work', 'television'})
CLASSES = ('major', 'other')


def classify(bundle, overrides=None):
    from tour_core_targets import inventory
    functions = {room: {f['function'] for f in rows} for room, rows in inventory(bundle).items()}
    out = {r['id']: 'major' if functions.get(r['id'], set()) & MAJOR_FUNCTIONS else 'other' for r in bundle['model']['rooms']}
    for room, value in (overrides or {}).items():
        if room not in out or value not in CLASSES:
            raise ValueError('roomClasses needs a known roomId and major or other: ' + str(room))
        out[room] = value
    return out
