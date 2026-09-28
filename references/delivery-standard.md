# Client-facing residential visualization delivery standard

Use a **base package plus floor-plan-aware expansion**. The standard defines
what the client receives; the four internal modules below define how the Skill
plans and controls that delivery. Internal JSON, recognition overlays, and QA
reports are production artifacts, not default client deliverables.

## Client-facing base package

Create these assets when the confirmed floor plan contains the relevant space:

1. one source-faithful structure/dimension reference plan when the user needs a
   review or delivery baseline;
2. one furnished colour floor plan when included in the agreed scope;
3. one primary cutaway bird's-eye view from the entry side toward the dominant
   daylight side;
4. one complementary bird's-eye view from the reverse or most informative side;
5. one living-area view from entry toward daylight;
6. one reverse public-area view toward dining and entry;
7. one primary-bedroom view;
8. one kitchen view.

The structure reference and furnished colour plan are different asset kinds.
The first preserves source structure and dimensions; the second communicates a
furniture and finish concept. Never label one as the other or silently use one
to satisfy the other's planned slot. Use `delivery.include_structure_reference`
and `delivery.include_furnished_plan` to declare scope before planning.

Do not manufacture a missing room merely to complete the nominal seven assets.
Combine living and dining views when a small or studio plan cannot support two
meaningfully different views.

## Adaptive expansion

Add one view for each confirmed secondary bedroom, children's room, study, or
multi-function room. Add one view for a confirmed balcony, terrace, garden,
staircase, double-height space, or other feature space when it adds sales or
design value. Bathrooms, utility rooms, and closets are optional unless the
room is marked `delivery_priority: featured` or the user asks for it.

Add a third bird's-eye view only when it reveals material information hidden in
the first two. Typical triggers are `l_shaped`, `elongated`, `high_occlusion`,
`split_level`, `duplex`, and `multi_floor`. For a multi-floor home, plan the
bird's-eye views per floor rather than forcing the entire building into one
image.

Use `delivery.max_images` as a review threshold, not a silent truncation rule.
If the planned package exceeds the threshold, present the complete plan and ask
the user which optional views to omit.

## Four internal modules

### 1. Deliverable-list planner

Run `scripts/plan_delivery.py` after access confirmation, pre-render furniture
layout confirmation (`furniture-layout-review.md`), and style selection. The
pre-render proposal is not the post-primary `furnished_colour_plan` asset.
The planner does not grant approval: bind it with `approve-layout` after state
creation. Production `can-run` enforces that file-bound prerequisite.
It compiles the base package and adaptive views from confirmed rooms, floor
levels, layout traits, and explicit feature priorities. Its JSON is an internal
shot list, not a finished deliverable.

Pass that exact file to `scripts/plan_project.py --delivery-plan`. Do not rebuild
an independent list from `outputs.room_views`. Provider tasks must preserve the
delivery asset order and carry through `id`, `kind`, `camera_intent`,
`must_show`, `structural_lock_ids`, and `must_not_change` without reinterpretation.
The approved top-down structure reference uses a deterministic copy task rather
than an image-generation request.

Linked task planning also creates `delivery-state.json`. Every task runner must
call `scripts/delivery_state.py can-run` before generation. A complementary
bird's-eye or room view remains blocked after the primary file is generated and
is unlocked only by an explicit user approval recorded with review evidence.
Never treat internal QA, model judgment, or file existence as user approval.
After all assets are generated, the state becomes `package_pending_review`.
The complete evidence-bearing review must pass before the state becomes
`package_review_passed`. Record existing explicit image-set acceptance with
`approve-package`; current acceptance and passing live review yield
`final_export_ready` without a second export question. Use `can-export` as the
final machine gate.

### 2. Camera selector

Every planned view must include one camera intent, one subject, a short
`must_show` list, and resolved `must_not_change` constraints from the confirmed
structural-lock registry. Select cameras by information value:

- primary bird's-eye: entry side toward dominant daylight;
- complementary bird's-eye: reverse or feature side, with substantial new
  visibility rather than a cosmetic rotation;
- room views: near a real confirmed access point, looking toward daylight or
  the room's primary feature;
- use approximately 35–45 degree elevation for bird's-eye concepts and a
  natural eye-level camera for room views;
- avoid extreme wide-angle distortion and impossible cameras through walls.

### 3. Structural quality gate

Treat any of these as a hard failure: an added or missing room, wrong wall,
wrong door/window type or location, reversed confirmed swing, blocked access,
sliding door rendered as a window, ordinary window/bay-window confusion, or
changed adjacency. Correct the failed image before continuing.

### 4. Multi-image consistency gate

Before final export, compare the whole set for furniture identity and placement,
material and colour continuity, opening geometry, wall thickness, lighting
logic, and repeated architectural features. A set fails if individual images
could not plausibly depict the same approved design.

Use `scripts/validate_delivery.py` on the completed review record. Review schema
0.3 requires matching planned/actual asset kinds, reviewed authority references,
and non-empty evidence for every structural and package check. A boolean without
evidence is incomplete. An approved exception is reported explicitly; it cannot
override a forbidden asset-kind substitution.
The review also stores `delivery_plan_sha256`; validation fails if any planned
asset, camera, kind, structural lock, or scope changed after the review was made.

## Preview and final delivery

Complete the source/layout/camera preflight in `pre-generation-preflight.md`
for the full agreed shot list before the first provider call. Decide the exact
reference packet and preservation constraints for all views together. This
front-loaded gate is where plan interpretation and cross-view orientation are
settled; the later quality gate checks whether the provider followed them.

Generate low- or medium-quality previews first. Review the primary bird's-eye
before generating dependent views. Then review the complete preview set as one
contact sheet. Assemble accepted images by deterministic layout/compositing,
preserving content, aspect ratio and full frame. Never ask an image model to
redraw accepted scenes just to combine them; do not crop out defects. Follow
available tools' editing permissions. If faithful assembly is unavailable,
deliver original files with an index and disclose the limitation, rather than
silently regenerating the board.

Deliver approved bytes. Explicitly requested higher-resolution generation makes
new candidates requiring review and acceptance; preview approval does not certify
changed pixels. Do not add regeneration when approved files satisfy the scope.

After the agreed images are accepted, reviewed and delivered, stop. “Continue”
means finish agreed work or closeout, not add measurement, construction, shopping
or video. Unknown installation dimensions can remain in an optional appendix;
they are not concept-delivery prerequisites.

Recommended final naming:

```text
01-structure-reference-plan.png
02-furnished-colour-plan.png
03-primary-birdseye.png
04-complementary-birdseye.png
05-living-toward-daylight.png
06-public-reverse.png
07-primary-bedroom.png
08-kitchen.png
```

Keep the AI-concept boundary visible in the handoff. Use a structured 3D, CAD,
or BIM workflow when the customer needs exact multi-view geometry, free camera
navigation, construction dimensions, 360-degree continuity, or a true walk-through.
