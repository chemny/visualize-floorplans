# Access topology and optional property-tour route

Build and confirm access topology before any 3D generation. Build a route only
when the user requests video or a property-tour presentation. A route is an
ordered walk through confirmed connections, not a set of decorative arrows.

## 1. Identify bounded zones

- Assign an ID to every visible enclosed or meaningfully bounded zone.
- Include `outside` as a special node.
- Do not assign a functional name yet.
- Do not create a node over blank exterior space, a dimension margin, or an
  unbounded graphical gap.

## 2. Classify and describe access points

Record each access point once with its position, the two zones it connects,
evidence, swing or opening direction when visible, and certainty.

For swing doors, record:

- `connects`: exactly two zones;
- `hinge_location`: a precise source-relative location or image coordinate;
- `swing_into`: the connected zone containing the visible swing arc;
- `certainty` and positive evidence.

For sliding doors, record `kind: sliding_door`, the connected zones, and
`sliding_panels` or explicit-label evidence. Never convert a sliding door into a
window merely because both use parallel linework.

Allowed traversable types:

- `entrance_door`
- `interior_door`
- `sliding_door`
- `balcony_door`
- `open_passage`
- `confirmed_opening`
- `stair`

Non-traversable elements:

- `window`
- `bay_window`
- `fixed_glazing`
- `wall`
- `shaft`

A gap is not automatically a door. Use `open_passage` only when the plan shows a
walkable connection. If the evidence is ambiguous, mark it uncertain and do not
route through it before confirmation.

## 3. Build the connection graph

- Treat zones as nodes and confirmed traversable access points as edges.
- Record the entrance as an edge between `outside` and the first internal zone.
- Record corridors and passages as zones when they have meaningful length or
  connect multiple rooms.
- Never create adjacency merely because two zones appear visually close.

## 4. Assign room functions

Apply `residential-space-ontology.md` only after the zone and access graph exists.
Functional labels must attach to existing zone IDs. They must not create, expand,
merge, or split geometry.

## 5. Stop after access confirmation for still-image projects

Run `scripts/validate_access.py` and obtain user confirmation of the access map
and schedule. If the request is only for still renovation images, do not create
route arrows, visit order, entry/exit sequence, or a tour-route approval step.

## 6. Design a route for video or presentation

Choose the route mode before adding steps:

- `full_tour` enters from `outside` and returns to `outside`. This is the
  existing property-tour mode and remains the default for older records.
- `entry_to_interior` enters through a confirmed exterior access point, visits
  the declared interior zones, and ends in one of them. Do not add a fake exit
  merely to satisfy the complete-tour format. Count unavoidable retraced
  access edges and choose an order that minimizes them.
- `indoor_segment` starts and ends in confirmed interior zones. Declare
  `start_zone`, `end_zone`, and at least two `route_render_points`. Omit
  `entry_access` and `exit_access`. A move within one zone has `steps: []`;
  never invent a doorway to represent motion inside an open room. A move between
  zones lists each real, confirmed access point in ordered `steps`.

For either mode, confirm the actual start/end positions, camera facing,
approximate pace, and intended visible furniture. A zone graph cannot prove
that the camera avoids walls or furniture. Check the drawn path against the
current approved structure and furniture layout before presenting it.

For a complete property tour, define:

- confirmed entry access point;
- ordered room visit sequence;
- confirmed exit access point;
- one continuous list of zone-to-zone steps.

Default complete-tour sequence when access permits:

1. enter through the confirmed entrance;
2. introduce foyer and public living/dining spaces;
3. visit balcony or terrace from its real access point;
4. visit kitchen and public wet areas;
5. visit secondary private rooms and study;
6. visit the primary bedroom and its ensuite last among private spaces;
7. return through confirmed passages and exit through a confirmed exterior door.

This order is a presentation preference, not permission to invent access. If the
graph requires backtracking, show it. If there is only one exterior door, enter
and exit through the same door.

## 7. Validate before drawing

Run for a complete tour, or add `--recognition /absolute/path/recognition.json`
to check same-zone indoor route points against its confirmed zone polygon:

```bash
python3 scripts/validate_route.py --topology /absolute/path/topology.json
```

Reject a complete tour when:

- the first step does not enter from `outside` through the declared entrance;
- the last step does not return to `outside` through the declared exit;
- consecutive steps are discontinuous;
- a route step lacks a declared access point;
- the access point does not connect the named zones;
- the access point is uncertain, a window, a bay window, or another
  non-traversable element;
- an arrow would visually cross a wall.

For `entry_to_interior`, require the first step from `outside` through
`entry_access`, a confirmed interior `end_zone`, and explicit
`required_visit_zones`. Reject a return to `outside` or an omitted required
zone. The validator reports repeated access IDs; their necessity must be
explained from the actual floor-plan graph.

Reject an indoor segment when its endpoint zones are unconfirmed, a cross-zone
step lacks a confirmed opening, or a same-zone path leaves its zone polygon.
The polygon check does not certify furniture clearance or camera width. Inspect
the approved furniture plan; record any unmeasured clearance as unresolved.

Draw arrows only after the graph validator passes. Use deterministic geometric
drawing on the fixed 2D base for doors, labels, and route lines, but deliver the
overlay as PNG only; its topology JSON remains the structured authority. Do not
create a separate SVG deliverable or ask an image model to redraw the underlying
floor-plan geometry.

For a same-size confirmed plan and furniture image, `render_route_preview.py`
draws an indoor path on both images. It verifies the plan, furniture, and
recognition SHA256 hashes against `reference_sha256` in the topology record, and performs
the polygon check before writing the PNG:

```bash
python3 scripts/render_route_preview.py --plan /absolute/path/confirmed-plan.png \
  --furniture /absolute/path/confirmed-furniture.png \
  --topology /absolute/path/indoor-route.json \
  --recognition /absolute/path/recognition.json \
  --output /absolute/path/route-preview.png
```

The preview is for route confirmation. It does not prove a camera-width path,
furniture clearance, or a continuous video.

For an `entry_to_interior` itinerary, `render_tour_overview.py` places numbered
camera stops on the confirmed plan and lists their intended first-person views.
It checks the stop coordinates against the recognition zone polygons and binds
the plan, furniture reference, and recognition file by SHA256. The numbered
overview is a visit-order proposal, not a drawn collision-free camera path:

```bash
python3 scripts/render_tour_overview.py --plan /absolute/path/confirmed-plan.png \
  --furniture /absolute/path/confirmed-furniture.png \
  --recognition /absolute/path/recognition.json \
  --topology /absolute/path/entry-tour.json \
  --output /absolute/path/tour-overview.png
```
