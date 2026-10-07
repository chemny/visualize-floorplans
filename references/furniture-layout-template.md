# Black-and-white furniture layout reference

## Synthetic visual template

This fictional studio demonstrates reusable linework and furniture symbols.
It is not a client's apartment or an approved real design.

- [Preview PNG](../assets/synthetic-layout-v1.png)
- [Editable SVG](../assets/synthetic-layout-v1.svg)
- [Structured source](../assets/synthetic-layout-v1.json)

Inspect the preview for drafting language; use the SVG as an editable visual
example, not a parametric generator or a surveyed base for another property.
The apartment, dimensions, object coordinates, labels and furniture choices in
the asset are illustrative case content, not defaults for new plans.

## Reusable drawing requirements

- Default pre-render furniture layouts to white-background, black/gray,
  orthographic linework. Avoid rendered furniture, textures, shadows and
  perspective. Explicit user requests may select another presentation.
- Keep wall outlines continuous at intended junctions, with heavier wall lines
  or fill than furniture and dimension lines. Preserve confirmed openings,
  jambs, hinge positions and swing arcs; do not alter them to make furniture fit.
- Draw recognizable top-view furniture symbols: bed frame/headboard/pillows,
  seating/backrests, cabinet extents, sink basins, toilet tank/bowl orientation
  and appliance outlines. Use consistent detail and line weights, not a mixture
  of elevations and plan symbols. CAD-like appearance is not certification of
  compliance with a drafting standard.
- Show room names, retained access IDs, a restrained legend, units and revision.
  Put overall and chained dimensions outside the plan using verified source
  values. Identify copied source dimensions separately from proposed furniture
  dimensions; do not invent missing measurements or a print scale. Add furniture
  sizes/clearances only when their basis is known; otherwise label unverified.
- Resolve alignment against the appropriate wall face or bay-window edge,
  distinguishing cabinet back, front and endpoints. Ordinary furniture must stay
  inside room boundaries without intersecting walls or other furniture. A
  proposed wall recess is a separately flagged, unverified construction intent,
  not a generic exception allowing furniture to cross walls.
- Furniture intentionally placed wholly within a confirmed bay-window outline may
  declare that exact opening as its scoped placement area. The bay window must be
  connected to the item's room; sill height, load, legroom and operability remain
  unverified and must be carried into review.
- A wall-recess cabinet proposal must name only the exact intersected wall IDs and
  record its proposal reason. Render it dashed, exempt only those declared wall
  intersections, and keep construction feasibility and allowable recess depth
  pending qualified verification. It is not an exception for other walls.
- Use differentiated dashed outlines for proposed extents and moving/expanded
  furniture states, with a legend. Review doors, chair pull-out, cabinet use and
  fold-out beds as well as closed footprints, per `furniture-layout-review.md`.
- Prefer editing the existing vector geometry for local corrections. Export a
  viewable preview and keep the editable source. Inspect the actual full export
  for clipping, broken lines, overlapping labels and unintended geometry drift.
  Geometric overlap checks supplement visual review; they do not establish
  real-world operating clearance or construction feasibility.
- Every accepted layout revision must include `layout-name-vN.svg` and its
  rendered `layout-name-vN.png`. Keep identical revision stems and generate the
  PNG from the SVG. A raster embedded in an SVG container without editable wall,
  opening, furniture and dimension elements does not satisfy this requirement.

## Scope of this sample

Coordinates are arbitrary canvas units, not surveyed dimensions. Furniture is
schematic and real operating clearances are not certified.

The synthetic sample is not a generator. Use the case-neutral structured renderer
and reusable symbols in `scripts/render_furniture_layout.py`; do not transfer this
sample's coordinates. Its declared-geometry checks cover wall intersections,
furniture overlap and door-swing conflicts, while real operating clearances stay
subject to review. Production delivery-state binds the approved layout file pair
with `approve-layout`; it verifies SVG syntax, paired revision names and both
hashes, but does not rerun geometry checks. The preview-only style-selection path still uses a manual layout
confirmation record; see `design-and-revisions.md`.

Regenerate the example from its JSON using render_furniture_layout.py with a
new output stem; the renderer deliberately refuses overwriting existing files.

## Shared-workbench drawing authority

For an H5-supported source, use the canonical H5 case and its current furniture
drawing export. Preserve the drawing language below where supported, but never
redraw positions to imitate an example. Use the Python drawing fallback only
when H5 cannot represent the source, disclosing limitations and checking migration
parity before a later workbench. PNG must render the exact exported SVG.
