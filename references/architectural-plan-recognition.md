# Architectural plan recognition protocol

Use this protocol to convert a raster or photographed residential plan into
typed geometry before naming rooms. It borrows the useful representation ideas
from floor-plan recognition projects: predict wall junctions and segments as a
graph, keep walls/doors/windows/icons/rooms as separate entity types, and assign
semantics only after geometry is stable.

This is an interpretation protocol, not a substitute for a licensed architect,
the drawing legend, structural documentation, or applicable national drafting
standards.

## 1. Authority order

Apply evidence in this order:

1. explicit drawing legend and labels;
2. user-confirmed correction for the current project;
3. unambiguous standard symbol geometry;
4. multiple independent spatial clues;
5. common residential patterns, marked uncertain.

Keep project-specific legend overrides in the recognition artifact. Never turn
one user's correction into a universal rule.

## 2. Separate graphic layers

Classify visible marks before interpreting spaces:

- `solid_wall`: continuous heavy or filled physical wall linework;
- `outlined_wall`: paired or outlined physical wall linework;
- `column`: isolated structural support footprint;
- `dashed_auxiliary`: dashed guide, alignment, overhead, hidden, or uncertain
  line whose meaning is not proven;
- `dimension_line`: dimension chain, extension line, tick, or dimension text;
- `annotation`: room text, level, leader, or note;
- `unknown_line`: visible line with unresolved meaning.

Default `dashed_auxiliary` to `physical: false`. Promote it to a wall, opening,
overhead element, or boundary only when a legend, explicit label, matching
geometry, or user confirmation supports that interpretation.

Wall weight alone does not certify load-bearing status. Call it a visible solid
or outlined wall until structural evidence exists. A project-specific rule such
as “black fill means locked structural wall in this drawing” may be recorded as
a legend override without becoming a general rule.

## 3. Recover geometry before semantics

1. Remove or mask dimensions, leaders, labels, photo shadows, and paper folds.
2. Find wall endpoints, corners, T-junctions, and cross-junctions.
3. Connect compatible junctions into wall segments.
4. Form bounded zone polygons from physical wall segments.
5. Record unresolved boundary gaps explicitly; do not silently close them.
6. Classify doors, windows, projections, fixtures, and service symbols.
7. Build room adjacency only through confirmed traversable elements.
8. Assign residential functions to the resulting zone IDs.

## 4. Element evidence gates

### Door

Use `entrance_door`, `interior_door`, `sliding_door`, or `balcony_door` only
when at least one strong door signal exists:

- explicit door label;
- visible door leaf;
- visible swing arc;
- recognizable sliding-door tracks/panels;
- user confirmation tied to a precise location.

A break in a wall, a white rectangle, or two nearby wall ends alone is an
`unknown_gap`. When the gap lies on an internal boundary, is the only plausible
access to a bounded habitable zone, and has no window framing, it may be promoted
to `door_candidate`. A door candidate is a useful proposal, but remains
non-traversable until a symbol, drawing label, or user confirmation upgrades it
to a door.

### Window

Use `window` when the element is embedded in a wall and supported by an explicit
window label or recognizable parallel frame/sill lines without a door leaf or
swing. A window is always non-traversable.

### Bay window

Use `bay_window` only when both are present:

- an exterior shallow projection or recessed sill footprint; and
- window/frame/sill evidence.

A bay window is a projection element, not a room, doorway, balcony, or route
edge.

### Open passage

Use `open_passage` only for a clearly walkable floor connection with no sill or
window framing, supported by an explicit label, continuous floor boundary, or
user confirmation. Otherwise use `unknown_gap`.

### Balcony and terrace

Treat an exterior platform as a zone only when its perimeter and floor area are
visible. Classify it as balcony/terrace only from enclosure, railing/parapet,
level, depth, and confirmed access evidence. A shallow framed projection is more
likely a bay window than a balcony.

## 5. Evidence codes

Use these machine-readable codes in recognition JSON:

- `explicit_label`
- `user_confirmed`
- `drawing_legend`
- `door_leaf`
- `swing_arc`
- `sliding_panels`
- `parallel_frame_lines`
- `sill_or_ledge`
- `exterior_projection`
- `clear_walkable_gap`
- `solid_wall_continuity`
- `outlined_wall_geometry`
- `bounded_polygon`
- `sanitary_fixture`
- `drain_symbol`
- `lowered_slab`
- `flue_or_shaft`
- `counter_geometry`
- `exterior_window`
- `adjacency`
- `dimension`
- `dashed_line_only`
- `inferred_pattern`

Free-form evidence may explain the observation, but it does not replace the
codes used by validation.

## 6. Confidence and traversability

- `confirmed`: explicit label, user confirmation, or unambiguous symbol.
- `probable`: at least two independent supporting clues and no contradiction.
- `uncertain`: incomplete, conflicting, or pattern-only evidence.

Only confirmed doors and confirmed open passages enter the access graph. Door
candidates, windows, bay windows, fixed glazing, walls, shafts, dashed lines,
and unknown gaps are always non-traversable.

## 7. Semantic naming gate

Attach a room function only to an existing bounded zone ID. Record:

- geometry evidence;
- functional evidence;
- confidence;
- credible alternatives.

Do not invent a missing kitchen, bedroom, bathroom, balcony, or corridor to make
the layout feel complete. A lowered slab with drains supports a wet-area
candidate; it does not by itself prove `主卫` or `公卫`. Bedroom role, bathroom
role, and kitchen identity require access and adjacency evidence.

## 8. Required recognition outputs

Produce these artifacts before 3D generation:

1. fixed structural base;
2. `recognition.json` containing project legend overrides, linework, elements,
   zones, evidence, and uncertainty;
3. structure overlay showing wall classes and ignored auxiliary lines;
4. access overlay showing doors, windows, bay windows, unknown gaps, and IDs;
5. zoning proposal attached to existing zone IDs;
6. access-topology JSON containing confirmed traversable edges only.

Run:

```bash
python3 scripts/validate_recognition.py --recognition /absolute/path/recognition.json
python3 scripts/validate_access.py --topology /absolute/path/access-topology.json
```

Do not generate a detailed 3D view until both validations pass and the user
confirms the access overlay. If internal access is unresolved, stop at the
second confirmation gate. Run `validate_route.py` later only when video or a
property-tour deliverable is requested.

## 9. Quality gate

Reject the interpretation if any of these occurs:

- a window or bay window is labelled as a door/opening;
- a dashed line becomes a physical boundary without supporting evidence;
- a wall gap becomes traversable without a door/passage signal;
- a room label creates or expands geometry;
- a route crosses a wall, window, bay window, fixed glazing, or unknown gap;
- load-bearing status is asserted from line weight alone;
- the clean base redraws an ambiguous feature as a confident object.
