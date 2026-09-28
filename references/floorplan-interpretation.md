# Floor-plan interpretation contract

Apply this contract before creating a manifest or generating an AI 3D concept
image. Review structure/functions and doors/windows/connectivity as two scopes,
which may share one complete presentation and one explicit confirmation. A tour route is optional and belongs to
the later video branch.

## 1. Establish image coordinates

- Refer to `top`, `bottom`, `left`, and `right` as they appear in the uploaded
  image.
- Use compass directions only when a north arrow or explicit orientation exists.
- Correct obvious photo rotation or perspective mentally, but disclose ambiguity
  that affects interpretation.

## 2. Extract visible facts first

First record `input_assessment.condition`: `readable`, `partial`, or
`critical_missing`. Record each gap or proposed completion in `items` with a
stable `id`, `description`, `origin` (`source`, `user`, `hypothesis`, `unknown`),
`evidence`, and boolean `consequential`.

- Readable: trace visible geometry, check it against the source, then show the
  complete interpretation for confirmation.
- Partial: identify the exact gap. Request a high-resolution crop for symbols,
  a photo for a specific doorway, one known dimension for scale, or a user
  description of an obscured connection. Photos supplement the plan; they do
  not independently establish the entire home.
- Critical missing: identify the smallest additional material needed to locate
  walls, boundaries, entrances, or required access. Keep generation blocked
  until that evidence is supplied or a clearly labelled proposal is accepted.
  Reassess the condition as `partial` or `readable` only after the consequential
  gaps are resolved in the current reconstructed version.

A completion proposal must state the assumed geometry, affected IDs, reason,
and impact. Show it as a hypothesis in the overlay and ask about that exact
proposal. Preserve its `origin: hypothesis` after acceptance and add
`acceptance` with `approval_source: explicit_user_confirmation`, `confirmed_by`,
and concrete `evidence`. Update the reconstruction, recognition, topology, and
artifact version; compare and confirm that complete version. An accepted
proposal is not a measured source fact. Do not invent precise dimensions.
Unknown consequential items block generation; non-consequential unknowns remain
visible limitations. A proposal is never silently approved by “continue”.

Record only what the drawing directly supports:

- exterior outline and visible wall segments;
- labelled rooms, dimensions, levels, and ceiling heights;
- doors, swing arcs, sliding panels, windows, bay windows, and openings;
- plumbing stacks, drains, flues, counters, fixtures, and sunken slabs;
- balconies, terraces, equipment platforms, stairs, and shafts;
- connected openings and blocked boundaries.

Do not equate a thick line with a certified load-bearing wall. Treat it as a
locked visible wall until structural documentation proves otherwise.

## 3. Reconstruct the 2D top-down base

Produce both `outputs/interpretation/topdown-base-v1.svg` and its rendered
`outputs/interpretation/topdown-base-v1.png` preview. The SVG is the editable
structural source; the PNG is the viewable review and generation reference.
They must share one revision stem. Edit the SVG first, then regenerate its PNG;
never maintain two independently redrawn versions.

When the interpreted geometry is structured, use `scripts/render_floorplan.py`
under `deterministic-drawing-tools.md`. Its schema is case-neutral and writes
independent wall, room, door, opening, and annotation elements before rendering
the exact SVG to PNG. Tool success is not source-comparison or accuracy proof.

- Correct only perspective, rotation, crop, shadows, folds, and visual noise.
- Preserve the visible footprint, walls, openings, door leaves and swing arcs,
  windows, projections, columns, shafts, steps, and sunken areas.
- Retain only legible source measurements and symbols. Never invent dimensions
  or silently complete missing geometry. Keep specifically accepted completion
  hypotheses visibly identified and recorded with their provenance.
- Omit inferred room labels, furniture, decoration, materials, and arrows.
- If the source is already a clean orthographic plan, enhance or trace it rather
  than redesigning it.

Compare the base against the source before continuing. Preserve ambiguous source
forms and flag them instead of silently completing them.

## 4. Build zones and propose functions

Build wall junctions and bounded zone polygons before assigning semantics. Use
evidence in this order:

1. explicit labels and standard plan symbols;
2. fixtures, service points, openings, and adjacency;
3. proportion, privacy, daylight, and circulation logic;
4. common residential patterns, marked uncertain.

Apply `residential-space-ontology.md`. Attach every proposed function to an
existing bounded zone. Never create geometry to make the home seem complete.
When two interpretations remain credible, show one primary proposal and one
targeted alternative only for the ambiguous zone.

Assign confidence:

- `high`: explicit label or unambiguous symbol;
- `medium`: two or more independent clues;
- `low`: mainly proportion or common pattern.

## 5. Structure and room-function review scope

Present:

1. the clean 2D structural SVG plus same-revision PNG preview;
2. a zoning overlay with room proposals and confidence;
3. directly readable labels, dimensions, and symbols;
4. a concise zone table with evidence and confidence;
5. consequential ambiguities and locked structural references.

Ask the user to correct only wrong or uncertain items. A short response such as
“布局正确” is sufficient. This gate confirms walls, bounded zones, and room
functions; it does not confirm door opening direction or a tour route. If the
user corrects a wall or boundary, repair the fixed base before continuing.

## 6. Build the door/window access map

On the reconstructed base, produce
`outputs/interpretation/topdown-access-v1.png`, an access schedule, and access
topology JSON.

- Number every door, sliding door, opening, passage, window, bay window, and
  fixed glazing element.
- Record the two zones connected by each traversable element.
- For each swing door, record the hinge location and the connected zone
  containing the visible swing arc. Use source-relative evidence, not convention.
- For each sliding door, record its connected zones and visible panel/track
  evidence. Never simplify a sliding door to a window.
- Keep windows, bay windows, fixed glazing, unknown gaps, and door candidates
  non-traversable.
- Preserve uncertain access as uncertain.
- Validate the confirmed graph with `scripts/validate_access.py`.

Do not create circulation arrows or an ordered tour route here.

## 7. Doors, windows, and connectivity review scope

Present:

1. the numbered access overlay on the unchanged 2D base;
2. a schedule listing type, connected zones, hinge location, swing-arc zone or
   sliding evidence, and certainty;
3. any room without confirmed access.

Ask only for corrections to type, location, hinge side, inward/outward swing,
sliding-door identity, or connectivity. A short response such as “门窗正确” is
sufficient. Do not proceed to style preview or detailed 3D while a required room
is inaccessible or a consequential access element remains unconfirmed.

Sections 5 and 7 may be shown together. Confirm only the scopes and IDs actually
displayed; one explicit acceptance can cover both. Keep already confirmed
unchanged content out of repeat questions. Record version, IDs, review evidence,
remaining issues, file hashes, and manifest facts as described in
`project-schema.md`. Compare the actual reconstruction against the source before
requesting this acceptance; scripted field checks cannot perform this review.

## 8. Handoff to visual generation

After both scopes are confirmed:

- preserve the original source as structural authority;
- preserve the approved 2D base as geometry reference;
- preserve the approved access map as door/window authority;
- obtain or reuse the selected renovation style; show the default style comparison
  only when needed;
- create a route only if the user later requests video or a property-tour plan.

## 9. Failure handling

- If the image is unreadable, identify the region and request a clearer source.
- If the reconstructed base changes geometry, correct it before room naming.
- If entrance or wet-area ambiguity changes the whole layout, show up to two
  candidates and recommend the better-supported one.
- If a required room lacks confirmed access, stop before 3D generation.
- Route planning belongs to the video phase; confirm indoor or outdoor start/end
  according to that phase's constraints.
- Record user corrections as project facts, not universal architectural rules.
