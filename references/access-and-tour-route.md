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

## 6. Design one property-tour route for video or presentation

Define:

- confirmed entry access point;
- ordered room visit sequence;
- confirmed exit access point;
- one continuous list of zone-to-zone steps.

Default sequence when access permits:

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

Run:

```bash
python3 scripts/validate_route.py --topology /absolute/path/topology.json
```

Reject the route when:

- the first step does not enter from `outside` through the declared entrance;
- the last step does not return to `outside` through the declared exit;
- consecutive steps are discontinuous;
- a route step lacks a declared access point;
- the access point does not connect the named zones;
- the access point is uncertain, a window, a bay window, or another
  non-traversable element;
- an arrow would visually cross a wall.

Draw arrows only after the graph validator passes. Use deterministic geometric
drawing on the fixed 2D base for doors, labels, and route lines, but deliver the
overlay as PNG only; its topology JSON remains the structured authority. Do not
create a separate SVG deliverable or ask an image model to redraw the underlying
floor-plan geometry.
