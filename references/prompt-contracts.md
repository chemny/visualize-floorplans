# Image 2 prompt contracts

## Incomplete source and accepted completion

Keep source evidence, user supplements, hypotheses, and unknowns distinct.
Before confirmation, visually label proposed missing geometry as a hypothesis;
do not silently add it to a source-faithful reconstruction. After explicit
acceptance, reference the exact confirmed reconstructed version and repeat each
accepted completion ID and description in structural prompts. Preserve that
completion across views while still identifying it as an assumption in the
project record. Never manufacture measured dimensions or re-infer accepted
geometry independently. Unresolved consequential gaps block generation.

## Normalized 2D top-down reference plan

Build editable architectural linework as SVG, then render the same revision to
PNG for review and image-model references. Do not ask a raster image model to
pretend its output is editable SVG.

The first image task must:

1. Name the uploaded floor plan as the structural authority.
2. Request a clean orthographic top-down architectural reference plan.
3. Correct only perspective, rotation, crop, shadows, folds, and visual noise.
4. Preserve the visible footprint, walls, openings, doors, door swings, windows,
   projections, shafts, steps, and sunken areas.
5. Retain legible source measurements but never invent missing dimensions.
6. Omit room-function guesses, furniture, decoration, materials, and arrows.
7. Label the output as an AI-reconstructed reference plan, not CAD or a measured
   construction drawing.

This output has asset kind `structure_reference_plan`. It cannot satisfy a
planned `furnished_colour_plan` slot.

## Furnished colour plan

Before any renovation render, separately confirm the furniture/equipment layout
under `furniture-layout-review.md`. Use that exact layout as an additional
reference for canonical and derived views. The furnished colour delivery plan
below remains post-primary; it must preserve those approved furniture decisions.

Use the original source, approved 2D base, approved access map, and structural
locks. Add only furniture, floor finishes, restrained material colour, and
room-function presentation. Preserve every wall, opening, door/window type,
projection, bay window, and adjacency. Give this output asset kind
`furnished_colour_plan`; never use a structure-only reference plan under this
name. If the furnished plan cannot pass geometry review, fail or re-plan it
instead of substituting another asset.

## Door and passage overlay

Use the approved or self-checked 2D base as the visual reference. Preserve its
geometry exactly. Add only:

- numbered visible doors, openings, passages, windows, and bay windows;
- the two zone IDs connected by every traversable access point;
- the hinge location and swing-arc zone for every visible swing door;
- explicit sliding-door identity and panel/track evidence;
- a compact certainty legend.

Do not add circulation arrows at this stage. Do not convert a window, wall gap,
or projection into a walkable door. Do not convert a sliding door into a window.

## Style selection boards

Default to the 12 options in `assets/project-template.json`, in three 2x2 boards:

- A: 现代简约;
- B: 原木奶油;
- C: 现代轻奢;
- D: 现代新中式;
- E–H: 中古现代、轻东方宋式、克制法式优雅、意式克制奢华;
- I–L: 香槟珍珠、米兰暖灰、巴黎装饰艺术、奶油雕塑感.

Use the same representative room, camera position, focal length, major furniture
arrangement, daylight direction, and exposure across all panels and boards. Change only
palette, finishes, furniture design language, lighting fixtures, textiles, and
decor. Keep panel boundaries obvious. Add short stable labels and style names; if reliable
text rendering is unavailable, add labels deterministically after generation.

The board is for style choice, not structural approval. Generate it only after
the structural, access and furniture-layout confirmations. Do not generate 12 independent
detailed whole-home views by default. After the user chooses one panel, record
the selected style before compiling the detailed canonical task.

## Functional zoning overlay

Attach labels only to zones already present in the access topology. Use
`residential-space-ontology.md`. Preserve the base geometry and access IDs.

- Use industry role names only with sufficient evidence.
- Use candidates or `待确认空间` when evidence is weak.
- Do not use final ordinal labels such as `卧室1` or `卫生间2`.
- Do not colour exterior blank space or infer a kitchen from one service point.

## Property-tour route overlay

Render only after `scripts/validate_route.py` accepts the topology JSON.

- Draw one continuous route with a visible start, end, and arrow direction.
  Number intermediate stops when present.
- Follow declared confirmed doors and passages for cross-zone steps; an indoor
  move within one zone needs no invented door or passage.
- Show backtracking when required by the real graph.
- Never cross a wall or route through a window, bay window, fixed glazing, or
  uncertain opening.

Do not redraw walls, doors, windows, dimensions, or room boundaries while adding
annotations.

## Canonical view

The canonical task must:

1. Name the source image as the structural authority.
2. Request a cutaway bird's-eye or axonometric concept view.
3. List confirmed rooms and relationships.
4. Repeat every locked element.
5. Forbid adding, removing, merging, or splitting rooms.
6. Use neutral white-model materials unless a style is explicitly required.
7. Avoid visible measurements or labels unless the user asks for them.

## Derived room view

Every derived room task must use:

- reference 1: original floor-plan image;
- reference 2: approved access map;
- reference 3: approved canonical view;
- the same structural constraints;
- the chosen design system;
- one named camera intent only.

Do not generate unrelated rooms independently from only the source plan.

## Client-facing multi-view package

Use `delivery-plan.json` as the shot-list authority. Every generated image must
implement exactly one planned camera intent and include its `must_show` items.
The primary bird's-eye is the visual anchor; complementary bird's-eye and room
views must depend on its approval.
Before composing any provider request, complete the authority and per-camera
spatial map in `pre-generation-preflight.md`. Every prompt must inherit the
same confirmed room/access/layout facts; reverse views must translate the
camera-relative left/right relationships explicitly. A generic instruction to
"keep the same layout" does not resolve a mirrored room arrangement.

For every derived view repeat:

- reference 1: original source floor plan as structural authority;
- reference 2: approved access map as door/window authority;
- reference 3: approved primary bird's-eye as visual authority;
- the named camera intent and `must_show` list;
- the exact `structural_lock_ids` and resolved `must_not_change` list;
- preservation of furniture identity, materials, palette, lighting logic, wall
  thickness, opening geometry, and architectural features across the set.

Do not request a cosmetic camera rotation that adds no new information. Do not
claim that image-only generation is a continuous or freely navigable 3D model.

## Style variant

Change finishes, furniture, lighting, textiles, and decor. Preserve room count,
walls, doors, windows, adjacency, and camera framing. Generate one style change
per task so failures can be isolated.

Style variants generated after canonical approval are optional refinements;
already selected or custom styles do not require a style comparison.

## Correction edit

Separate preservation from correction:

```text
Preserve all areas outside the correction target. Keep the existing camera,
room count, walls, doors, windows, furniture identity, palette, and lighting.
Correct only: <specific structural or visual error>.
```

Use a mask when the edit surface supports it, but still describe the exact
preservation constraints because masks are guidance rather than geometry locks.
Repeat the affected structural-lock IDs in every correction prompt. After a
targeted edit, verify that untouched package assets are byte-identical or record
why a deterministic recomposition changed them.

## Negative constraints

Include these for all structure-sensitive tasks:

- no extra rooms;
- no missing rooms;
- no moved doors or windows;
- no changed room adjacency;
- no impossible openings;
- no visible watermark, logo, or generated annotation;
- no claim of construction accuracy.
