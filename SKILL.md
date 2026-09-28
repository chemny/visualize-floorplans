---
name: visualize-floorplans
description: Use when reviewing residential floor plans, confirming furniture layouts, or creating reference-driven renovation concept images. Preserve room, door, window, and opening evidence. Outputs are concepts, not measured CAD, BIM, construction drawings, or guaranteed accurate 3D models. Continuous video is experimental and only attempted when explicitly requested.
metadata:
  version: "0.1.0-beta.1"
---

# Visualize Floorplans

Create a controlled three-stage workflow for interior designers and marketing
teams:

1. reconstruct and confirm the floor plan;
2. confirm a furniture/equipment layout, choose or specify one renovation direction, generate coordinated images, and
   revise the affected results until the scheme is confirmed;
3. only when requested, confirm a route and attempt a genuinely continuous
   walkthrough video that remains consistent with the confirmed scheme.

The original plan remains the structural authority. Floor-plan reconstruction,
comparison against the source, and user confirmation are mandatory before any
renovation image. A single user response may confirm both zones and access
elements when one complete presentation clearly shows both scopes; do not ask
again for already recorded items. The image workflow is implemented as a
controlled conceptual pipeline. The continuous-video execution path is not yet
validated and must be reported as unavailable or experimental until a real
playable sample passes visual review.

## Scope and stopping point

This is a concept-workflow beta, not a verified architectural reconstruction
engine. Room-perspective images may drift despite preflight. User acceptance,
visual structural review, and automated file checks are separate facts. If the
user stops generation, hand off only the accepted subset with rejected and
unverified outputs explicitly excluded; never mark the abandoned full package
as passed. Blender is not required. Video remains experimental.

Before local script execution, read `references/platform-runtime.md` and run
`scripts/check_environment.py` with the detected Python interpreter. Verify
the host's reference-image generation/editing capability separately. Missing
image tools must not prevent reference review, but must stop image generation.

Complete only the agreed image set. After its images are confirmed and reviewed,
assemble the accepted files, report remaining conceptual uncertainties, and end
the stage. A generic “continue” means finish outstanding agreed views or close
out, not start site measurement, construction detailing, procurement, or video.
Those branches require an explicit request. Site verification is an optional
implementation appendix, never a prerequisite for concept-image handoff.
Do not reopen unchanged approvals or add deliverables just to keep going.

## Non-negotiable boundary

- Use editable SVG plus a same-revision PNG only for the reconstructed floor
  plan and the pre-render furniture/equipment layout, because these two files
  are reusable geometry references for downstream generation. Deliver every
  other image—including zoning/access/route overlays, style boards, furnished
  colour plans, bird's-eyes, room views, and contact sheets—as PNG or JPG only;
  do not create or deliver SVG versions of them. Keep their structured authority
  in the applicable JSON records rather than adding another SVG artifact.
- Call every V0 output an **AI 3D concept image**.
- Call the normalized 2D output an **AI-reconstructed reference plan**, not CAD
  or a measured drawing.
- Never claim dimensional accuracy, arbitrary camera navigation, construction
  readiness, or a real 3D model.
- Do not suggest removing or changing structural walls.
- Mark uncertain room, door, window, orientation, and dimension information.
- Do not silently add zones. Missing geometry may be proposed as an explicit
  hypothesis, shown to the user, and included only after specific acceptance;
  retain its provenance as a hypothesis rather than source evidence.
- Never draw a route through a wall, window, bay window, fixed glazing, or an
  unconfirmed opening.
- Never treat a generic “continue” as confirmation of an undisplayed or
  unresolved room, door, window, opening, or opening direction.
- Never represent slideshows, static-image zooms, 2.5D moves, or stitched room
  clips as a continuous walkthrough.

## Stage 1: confirm the reconstructed floor plan

1. Inspect readability and drawing type. Separate dimensions, text, walls,
   auxiliary lines, columns, doors, windows, projections, fixtures, and unknown
   marks. Read `references/architectural-plan-recognition.md`; do not interpret
   the entire drawing in one semantic pass.
   Record the readable/partial/critical-missing assessment and follow the
   completion branch in `references/floorplan-interpretation.md` for gaps.
2. Generate a clean orthographic 2D top-down reference plan as an editable SVG
   plus a same-revision PNG preview. When structured geometry is available, read
   `references/deterministic-drawing-tools.md` and use `render_floorplan.py`;
   do not copy coordinates from the bundled furniture example. Preserve visible
   geometry and omit inferred furniture, decoration, and routes. Build a wall-junction graph
   and bounded zone polygons, then classify doors, swings,
   sliding doors, openings, windows, bay
   windows, fixed glazing, and exterior access from positive evidence. A wall
   gap remains `unknown_gap` until resolved.
3. Attach functional names only when supported, then render the zoning and door/window
   information clearly enough to compare against the original. Number each
   access element and record swing direction or sliding evidence. Validate the
   recognition and access artifacts with `validate_recognition.py` and
   `validate_access.py`.
4. Present the reconstructed plan beside the source and perform the self-check
   described in `references/floorplan-interpretation.md`. Ask the user to correct
   only wrong or uncertain items. One confirmation may cover both
   `structure_and_zones` and `access_elements` when both were fully shown;
   otherwise confirm only the shown scope and return with the missing overlay.
5. Record the exact artifact version, confirmed item IDs, evidence, confirmer,
   and unresolved consequential items in `interpretation_artifacts.confirmation`.
   Convert confirmed facts into `structural_locks`. Do not enter Stage 2 until
   `plan_project.py` accepts the confirmation record.
   For generation, use real source/base/overlays/recognition/topology files with
   matching IDs, versions, and confirmed content hashes. Legacy records need
   an explicit review in a new run directory; do not infer approval from old
   status strings. `--allow-missing-input` creates non-executable sample plans.

## Stage 2: create and confirm one coordinated renovation scheme

Before style previews or renovation views, read
`references/furniture-layout-review.md`. Produce and obtain confirmation of a
furniture/equipment layout on the approved structure and access base. Reuse an
already confirmed, unchanged layout rather than asking again. Infer basic
equipment from room functions; keep the checklist internal and ask only about
consequential uncertainty. Known access or operation conflicts require correction;
unmeasured clearances remain explicitly unverified, not passed.

Before the first image-generation call for an agreed image set or revision batch,
read `references/pre-generation-preflight.md` and complete its front-loaded
verification. Freeze one current source/access/layout/style reference bundle and
translate the floor plan into per-camera spatial invariants, including what
changes sides in reverse views. Resolve conflicting historical records before
generation. Prepare every planned view's camera, visible rooms, openings,
furniture, and `must_not_change` constraints together; do not discover these
piecemeal by generating images. A passing file/hash check alone does not prove
the spatial interpretation is correct. Generate the agreed views from that
frozen bundle, then use the existing visual review to catch model deviations,
not to decide the plan after the fact.

Use a dimensioned black-and-white orthographic linework layout by default for
this review, following `references/furniture-layout-template.md` and its bundled
approved PNG/SVG example. Reuse its drafting language, not its apartment geometry
or furniture positions. Deliver an editable SVG plus its same-revision PNG
preview. For structured input, use `render_furniture_layout.py` and resolve its
wall, furniture-overlap, and door-swing conflicts before presentation. Its checks
do not certify unmeasured clearance or construction feasibility. This is a
conceptual reference, not measured CAD.

This pre-render layout is distinct from the post-primary `furnished_colour_plan`
delivery asset. Carry its constraints into `design.scheme` / `design.room_schemes`.
After state creation, bind both files with `approve-layout`
as described in `references/design-and-revisions.md`. For `confirmed_bundle`
production, `can-run` blocks missing, changed or stale layout approval and supplies
the exact layout as a reference. Legacy/synthetic plans do not enforce this gate
and must not be used to bypass it. File binding does not prove visual correctness.
Do not repurpose `approve-primary` to approve a layout proposal.

1. Let the user specify a style or choose from the 12 defaults in
   `assets/project-template.json`: 现代简约、原木奶油、现代轻奢、现代新中式、
   中古现代、轻东方宋式、克制法式优雅、意式克制奢华、香槟珍珠、米兰暖灰、
   巴黎装饰艺术、奶油雕塑感. For undecided users, default to three same-room
   2x2 boards (A–D, E–H, I–L), with identical layout/camera/daylight across all
   boards. Read `references/design-and-revisions.md` for comparison execution.
   These are design directions, not popularity rankings. Preserve a user's
   smaller requested comparison; never require comparison after selection.
   Use `selected_style: custom` with `custom_style.name` and
   `description` for a custom direction. Record supplied reference images,
   palette/material overrides, requirements, and preserved furniture in `design`.
   Record shared layout, furniture, and finishes in `design.scheme`; use
   `design.room_schemes` for room-specific changes. See `references/design-and-revisions.md`.
2. Read `references/delivery-standard.md`. Plan a base set plus floor-plan-aware expansion,
   then recommend a small image set for the actual plan and purpose.
   Generate only the
   requested package, room, view, or detail; current planner constraints may
   still require a broader set, which must be disclosed instead of hidden.
3. Compile the adaptive delivery shot list without calling an image API:

   ```bash
   python3 scripts/plan_delivery.py \
     --manifest /absolute/path/project.json \
     --output-dir /absolute/path/run
   ```

4. Create the provider dry-run task plan:

   ```bash
   python3 scripts/plan_project.py \
     --manifest /absolute/path/project.json \
     --delivery-plan /absolute/path/run/delivery-plan.json \
     --output-dir /absolute/path/run
   ```

   For schema 0.3 delivery work, `delivery-plan.json` is the sole shot-list
   authority. The generated provider tasks must preserve its asset order and
   inherit each asset's ID, kind, camera intent, `must_show`,
   `structural_lock_ids`, and `must_not_change`. The structure reference is a
   deterministic copy task; image tasks must not regenerate it. Calls without
   `--delivery-plan` remain legacy-compatible but are not the preferred client
   delivery path.

   This also initializes `delivery-state.json` without overwriting compatible
   state. Before executing any task, run:

   ```bash
   python3 scripts/delivery_state.py can-run \
     --plan /absolute/path/run/generation-plan.json \
     --state /absolute/path/run/delivery-state.json \
     --asset-id TASK_ID
   ```

   Do not execute a task unless it returns `runnable: true`.
   Execute its `resolved_task`, not the unresolved provider plan: this replaces
   asset references with the actual approved files and applies current edit
   instructions. The furnished plan also waits for its primary scheme approval.
5. Generate the detailed canonical cutaway bird's-eye view using the original
   floor plan, approved 2D base, approved door/window overlay, and selected style
   as references, together with the confirmed furniture/equipment layout.
   Preserve all confirmed door types, opening directions, equipment identities,
   and furniture positions; styling must not independently rearrange the layout.
   After saving the primary bird's-eye, record it with `delivery_state.py
   record-generated`; this changes it to `pending_primary_approval` and does not
   unlock derived views.
6. Before showing it as accepted output, compare every visible room and access
   element against the approved references. Reject or correct missing room doors,
   reversed swing directions, and sliding doors rendered as windows. Then ask the
   user to approve or correct the canonical view. Only after an explicit user
   approval, record `approve-primary` with `--approval-source
   explicit_user_confirmation`, a non-empty approver, and concrete review
   evidence. Internal self-review is not user approval. Use image editing for
   targeted corrections instead of starting independent generations.
7. Generate the complementary bird's-eye and adaptive room views from the
   approved canonical view. Follow each planned camera intent and `must_show`
   list. Treat each asset's `must_not_change` and `structural_lock_ids` as hard
   generation constraints. Generate one view at a time from the original plan,
   approved access map, and approved canonical view; preserve all locked elements.
8. Inspect each generated view before progressing: room/opening positions,
    object counts, orientation, proportions, omissions and wall intersections;
    after edits also inspect untouched areas. Follow the two-failed-retry stop
    rule in `references/furniture-layout-review.md`. These are internal checks,
    not another questionnaire. Assemble the complete preview contact sheet from
    actual accepted images with `assemble_contact_sheet.py`, not a newly generated
    depiction. Do not crop or resize the source images. Record one structural
    review per planned asset and one package-level consistency review, then run:

   ```bash
   python3 scripts/validate_delivery.py \
     --plan /absolute/path/run/delivery-plan.json \
     --review /absolute/path/run/delivery-review.json \
     --require-files
   ```

   Do not export the final package until both gates pass. Review schema 0.3 must
   record `planned_kind`, `actual_kind`, the authority references inspected, and
   non-empty evidence for every check. Asset-kind mismatch is a hard failure:
   re-plan instead of silently substituting. Any other exception must state its
   reason and have explicit user approval. Treat room-count, wall, door/window,
   adjacency, and access failures as hard failures; treat furniture, material,
   lighting, and repeated-feature drift as package failures.
   Review schema 0.3 is cryptographically bound to the exact delivery plan.
   After every planned asset is generated, synchronize the state and record the
   passing package review:

   ```bash
   python3 scripts/delivery_state.py sync-state \
     --plan /absolute/path/run/generation-plan.json \
     --state /absolute/path/run/delivery-state.json

   python3 scripts/delivery_state.py record-package-review \
     --plan /absolute/path/run/generation-plan.json \
     --state /absolute/path/run/delivery-state.json \
     --delivery-plan /absolute/path/run/delivery-plan.json \
     --review /absolute/path/run/delivery-review.json

   ```

9. For a view correction that preserves the scheme, use `delivery_state.py revise`
   with the affected asset IDs and a concrete correction. It reopens dependent
   images, clears package approval, and invalidates video while preserving old
   files. For a design/structural change, update the manifest, create a new plan,
   and use `replan` to retain only unchanged outputs. Retained images still need
   package review against the new primary. Record existing image-set acceptance
   with `approve-package` before or after internal review, then use `can-export`.
   Current acceptance plus passing live review permits ordinary local handoff:
   no duplicate “allow export?” question. Changed images require review and
   acceptance of the changed scope. External publication and paid work still
   require their own actual authorization. After the agreed set is delivered, stop.

## Stage 3: confirm a route and validate a continuous video

Run this stage only when video is requested and the Stage 2 scheme is current.

1. Plan the route after image approval, not during floor-plan or style review.
   Confirm start, end, rooms visited, and approximate pace. Indoor starts and
   ends are valid. A graph-valid route is only a first check; the camera path
   must also avoid walls and furniture.
2. Before any paid or external generation, name the available tool, input
   limits, test scope, likely cost, and stopping condition. The present Skill
   has route validation but no verified continuous-video execution chain.
3. A successful task call or a prompt is not proof. Play the result and inspect
   continuity, route adherence, wall crossings, sudden jumps, and changes to
   rooms, doors, windows, furniture, and materials. If no playable sample passes,
   report Stage 3 as incomplete. Offer a slideshow or 2.5D alternative only as
   an explicitly labelled substitute, never as “一镜到底”.

Record evaluation results and structural failures. Escalate recurring image
failures to the future structured-geometry track.

## Generation routing

- Prefer GPT Image 2 for reference-driven generation and editing.
- Use an available image-generation tool when it can accept the required
  references and output size.
- If direct OpenAI API execution is configured, use the Image API for individual
  generation/edit requests and keep provider credentials outside this skill.
- Do not silently fall back to a model that cannot accept image references.
- Never incur API cost without the user's current execution authorization.

## Required references

- Read `references/furniture-layout-review.md` before proposing or revising
  furniture placement, confirming a layout, or starting renovation images.
- Read `references/pre-generation-preflight.md` before any renovation image
  generation or revision batch; use the completed case preflight as the input
  contract for every view in that batch.
- Read `references/floorplan-interpretation.md` for every newly uploaded or
  replaced floor plan, before asking the user to confirm room functions.
- Read `references/architectural-plan-recognition.md` before classifying any
  wall line, dashed line, door, window, opening, bay window, or balcony.
- Read `references/residential-space-ontology.md` before naming rooms or exterior
  spaces.
- Read `references/access-and-tour-route.md` before identifying doors and
  passages. Re-read its route section only when a video or property-tour route
  is requested.
- Read `references/project-schema.md` when creating or repairing a manifest.
- Read `references/delivery-standard.md` when planning any client-facing image set.
- Read `references/prompt-contracts.md` before generating or editing images.
- Read `references/design-and-revisions.md` when specifying a custom scheme,
  resolving generation references, revising images, or reviewing the package.
- Read `references/evaluation.md` when checking a run or making a go/no-go
  decision.
- Read `references/development-checklist.md` when advancing the product beyond
  the current V0 phase.
- Read `references/deterministic-drawing-tools.md` before using the structured
  SVG/PNG renderers or the confirmed-image contact-sheet assembler.

## Bundled resources

- `scripts/plan_project.py`: validate a manifest and compile deterministic Image
  2 task prompts without calling an external API.
- `scripts/plan_delivery.py`: compile the client-facing base package, adaptive
  views, semantic camera intents, and a delivery-review template.
- `scripts/delivery_state.py`: bind layout/image acceptance to files, gate
  execution and live review, and permit local handoff without duplicate approval.
- `scripts/validate_delivery.py`: enforce per-image structural checks and
  package-level multi-image consistency before final export.
- `scripts/test_workflow.py`: local regression tests for validation, dependency
  ordering, and structural constraints.
- `scripts/test_interpretation.py`: synthetic input-completion, overlay geometry,
  cross-file authority, and changed-file regression tests.
- `scripts/interpretation_authority.py`: inspect evidence bundles and candidate
  content hashes; does not grant user approval or replace source comparison.
- `scripts/validate_access.py`: validate confirmed room connectivity, swing-door
  direction, and sliding-door metadata without requiring a tour route.
- `scripts/validate_route.py`: reject discontinuous routes and steps that do not
  use confirmed doors or passages.
- `scripts/validate_recognition.py`: reject unsupported doors, windows, bay
  windows, traversable gaps, physical dashed lines, and semantic zones without
  geometry evidence.
- `scripts/render_interpretation.py`: render deterministic access and zoning
  overlays on the fixed 2D base without asking an image model to redraw walls.
- `scripts/render_floorplan.py`: render generic structured wall/access geometry
  to independent SVG elements, then export the exact same revision to PNG.
- `scripts/render_furniture_layout.py`: render reusable top-view furniture
  symbols and reject declared wall, furniture-overlap, and door-swing conflicts.
- `scripts/assemble_contact_sheet.py`: copy complete confirmed image pixels into
  a labelled canvas without cropping, resizing, or generative redraw.
- `scripts/vector_tools.py`: shared validation, geometry, atomic-write, and
  deterministic SVG-to-PNG support for the drawing tools.
- `assets/project-template.json`: copy and fill for a new project.
- `assets/sample-project.json`: runnable sample manifest for dry-run verification.
- `assets/sample-topology.json`: runnable access graph and ordered tour-route
  validation sample.
- `assets/sample-recognition.json`: synthetic recognition-record example for
  local validation; not a user-confirmed production plan.
- `assets/floorplan-input-template.json`, `assets/furniture-layout-input-template.json`,
  and `assets/contact-sheet-input-template.json`: case-neutral structured inputs;
  fill them in a run directory rather than editing the templates in place.

## Completion report

Report:

- confirmed and uncertain structural facts;
- reconstructed plan SVG and same-revision PNG preview paths;
- furniture-layout SVG and same-revision PNG preview paths;
- approved door/window schedule and access-map path;
- selected or custom style, plus comparison-board paths only when used;
- generated views and their reference chain;
- structural-lock registry plus each asset's `must_not_change` constraints;
- planned base-package and floor-plan-adaptive deliverables;
- planned and actual asset kinds, including approved exceptions;
- camera intent and must-show elements for every client-facing image;
- structural-gate and multi-image consistency-gate results;
- failed quality gates;
- output paths and sizes;
- route and video artifacts only when that optional branch was requested;
- whether results remain conceptual or were upgraded by a structured 3D system.
