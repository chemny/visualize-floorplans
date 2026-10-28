---
name: interior-design
description: Start from one floor-plan image with optional furniture/style references, build editable offline H5 2D/3D renovation workbenches, coordinate interior concept images, and create deterministic homeowner camera preflights. Use when the user requests floor-plan confirmation, furniture and finish editing, scheme export, walkthrough planning and local handoff. Preserve structural evidence and versioned approvals. Concept design is not measured CAD or construction documentation; Seedance is a separate optional branch.
metadata:
  version: "0.2.11"
---

# Interior Design · 家装助手

全屋参观生成与修订遵循 `references/tour-planning-contract.md`。三轮复核须检查真实
目标驱动、整房单向性、全部捕获入口和最终帧拍墙/突转；历史通过、数值通过与
三维播放验收分别记录。缺少新契约的旧配置不能直接捕获；当前Blender仅支持静态出图。
当前执行版本为 `homeowner-tour-rules/2`。规则、实现与反例测试的对应关系见
`references/tour-rule-implementation.md`；修改全屋参观引擎时读取该表，禁止只改文档或案例补丁。

## Default guided user workflow

Read `references/guided-user-workflow.md` before starting a new case.
One plan is enough to start; furniture and style references are optional.
Use three concentrated decision rounds: (1) reconstructed plan/access and essential
needs, (2) furniture/function layout, (3) style and agreed output views. Use the same diagnostic H5 workbench from round 1, refine its canonical data
through layout/style, and export confirmation drawings from it. Then
produce the final workbench and agreed images continuously and present them together
for final output review. Keep exact-scope approvals and all quality gates;
three decision rounds are not automatic acceptance of final outputs.
Batch missing consequential questions with recommended options and reasons.
Before asking an undecided user to select a style, show an actual style comparison
image and run `scripts/check_style_selection.py` as specified in
`references/style-selection-gate.md`. Text-only substitution requires an explicit
user waiver; tool/state blockers must be reported rather than silently skipping
the comparison. Diagnostic preset values are not user style choices.
Read dimensions, draw, self-check and repair without asking users to repeat
“continue”. A progress update must not end authorized work within a round.
Only genuine dependencies or consequential decisions justify a pause.
These interaction rounds coordinate the technical stages below; optional video
is not the third user decision round.

## Stage-bound asset cleanup

At confirmed stage boundaries, video verification or accepted handoff, read
`references/stage-cleanup.md`. Use `scripts/stage_cleanup.py scan` to inventory
explicitly obsolete/temporary media, protect source/current/final dependencies
and report unknown files. A batch needs explicit user approval before verified
external-directory backup and reversible quarantine. Recheck project snapshots,
then verify current deliverables; restore if affected. No background scheduler,
permanent deletion or automatic approval. Installing this feature does not
authorize cleanup of existing cases.

## Bundled reference case

For a concrete capability preview, open `assets/reference-cases/jujian-champagne-pearl/index.html` when the user asks to see an example. Read its brief `README.md` for representation boundaries; do not load the mesh or all images unless needed. It contains supplied references, a current 0.2.0 workbench, selected concept images/drawings, scheme data and an H5 tour. This is a case-specific example, not a shared default apartment or fresh acceptance of every representation. Copy case input into a new project before editing; do not modify the bundled example. Existing image/video/mesh sources differ from the newest lighting/material demo. The page uses relative links and does not open automatically when the Skill is loaded.

## Reuse the accepted homeowner tour method

Before every route/camera/video task, read `references/tour-planning-contract.md`
(the unified generation/revision/acceptance contract), then
`references/homeowner-tour-method.md` for the reusable method and reference evidence.
Prioritize the viewing purpose and public → primary → secondary → service stages
before distance minimization. Full tours enter and leave the same confirmed door;
do not finish inside a bedroom. Each observation records its viewing purpose.
Normal walking faces travel (prefer within 60°); final-frame `tour_forward_motion.py`
rejects facing over 90° away for more than 0.5s while moving above 0.2m/s,
including across chapter boundaries. Camera turning and movement join naturally
along the route. Stationary turns are excluded from the walking check.
Before planning, derive core functions from the actual furniture and
`assets/h5/tour/core-functions.json`. Planning binds omitted core targets; final
contract and mesh checks reconstruct them independently. Require 0.5s readable
core fixtures in the first room-viewing episode; later pass-throughs cannot fill
omissions. One shot can show multiple functions. Never drop a hard-to-frame
fixture to improve candidate scores; see the planning contract for scope.
Production is strictly sequential: confirm route, generate and review silent video,
then obtain explicit user acceptance of that exact video before narration/subtitles/music.
Use `h5.py narration-prepare` before any TTS or subtitle work and
`h5.py narration-compose` for composition; both enforce hash-bound
`homeowner-video-approval/1`. Never chain video encoding directly into narration.
Page packaging enforces the same acceptance. Review capture releases and samples
never authorize narration; pending records must not be automatically approved.
Use `references/tour-presentation-pages.md` for the shared three-page workflow, templates, media binding and interactions. Treat that document as the single presentation SOP and use its rule-to-implementation checklist. Regenerate through the shared CLI in a fresh directory and verify actual generated interactions; test counts alone do not certify appearance. Do not recreate case-local page shells. Keep the three stage tabs at the top; embed only the pure route-map component in auxiliary 3D previews, never a full stage page.
For a new tour or a revision, read `references/unified-tour-production.md` and use
`h5.py plan-tour --job --out` for the bounded joint-candidate/repair workflow and
three-stage presentation in `references/tour-presentation-pages.md`: route-only first, then video review, then narrated playback. Actual 3D checks remain a separate camera preview. This entry never captures video or grants approval.
The lower-level `h5.py design-tour --bundle --brief --out` remains available to compare room
order, select doorway/shallow observation points and emit semantic gaze. Do not
write case-local timed path-chasing camera generators or compulsory viewing moves.
Use `references/tour-native-revision.md` for native doorway composition repairs,
explicit frozen revision scope, synchronized before/after review and a conclusive
engineering-stage report. Existing helpers are connected to `plan-tour`; scoped
repairs must not call global smoothing or silently modify passed observations.
Read `revisionOutcome` before reporting success: retaining a checked baseline is
not a successful repair, and selecting a revision does not grant visual acceptance.
Require explicit case `coveragePolicy.enabled` and `minimumPercent`, plus a case
`maximumSeconds`; never fill a shared apartment coverage percentage or total duration.
Every room must meet that case minimum; failures block route acceptance unless the
case explicitly chose the reference-area mode in `unified-tour-production.md`.
That mode retains measured gaps for visual review and never waives core-fixture,
collision, motion or actual playback checks.
The shared horizontal-area screen detects omissions but cannot certify actual 3D visibility.
Keep actual 3D visibility pending until its own review; do not exempt small rooms or
shrink the denominator to force a pass. For one-pass room viewing, require shallow inside-room stations, declare each
room’s signed left-to-right or right-to-left sweep, and protect that direction
through final smoothing. Complete each room in one continuous viewing episode before visiting the next
room. Normal exits and later pass-throughs are navigation, not another scan. Do not
split the same room into entry-side and return-side viewing episodes; enforce
`roomViewingPolicy.singleEpisode` against real room IDs, not observation labels.
Default to one observation station per real room, at most two. A second station
requires a concrete occlusion/distinct-area reason; furniture targets and navigation
vertices are not separate stops. Use `observationPointPolicy` (1.5–2.5s recommended,
3s maximum per point, simultaneous position/gaze hold at most 0.5s). These are
product defaults, not industry standards. Recheck actual
retimed point durations with `tour_observation_points.py`; failures block capture.
When room time limits are confirmed, persist `roomBudgetPolicy` and check the
complete entry/view/exit window with `tour_room_budgets.py`, not observation
chapters alone. Over-budget rooms block capture; do not raise speed or silently
relax coverage/time limits to pass. `tour_contract.py` unifies final-frame checks
for generation, revisions, rehearsal and capture; retain numeric, actual-3D and
human acceptance separately. Preserve per-window `viewingDurationFloors` when
revising without reducing viewing time. Inspect design-report.json and the timed rehearsal before requesting approval.
Read `references/route-rehearsal-gate.md` and show the timed, interactive plan-based
route animation before **any** video capture, including low-resolution previews
and local turn samples. Require explicit user approval of that displayed artifact,
path, independent camera facing and exact timing. Text itineraries are insufficient.
`--route-review` is required by both Python and direct browser capture; neither
`--preview` nor `--range` bypasses this gate. Rehearse a compact case-specific
duration budget first; over-budget routes must be revised before capture.
Start from its accepted-reference profile and public `scripts/production/camera_gaze.py`
subject-key gaze method; adapt case targets and time budgets, not the algorithm
from scratch. The 56-second example is a method reference, not a fixed duration
or transferable apartment path. Require dynamic turn samples, a complete low-cost
preview and subject visibility checks before high-resolution full capture.
The primary `h5.py run --config` now applies shared gaze/timing/chapter checks.
Full production/HD capture requires a hash-bound actual dynamic preview review;
low-cost diagnostic previews remain possible only after timed route-animation approval. Use `tour_tools.py` for chapter
motion reports, bounded corrections and pending review templates.
Keep source, motion, viewport integrity and user visual acceptance separate.
For explicitly authorized, unaccepted review videos with disclosed issues, use
the scoped `--review-release` path in `route-rehearsal-gate.md`; ordinary capture
and formal delivery gates remain unchanged. Never copy a case's issue count or
repair parameters into shared rules.
Use the closeout checklist in that reference. Separate room-only gaze/pitch edits
from transit/global orientation; approach the usable doorway before turning.
The second accepted tour example is linked there; its case parameters and user
acceptance do not replace a new case's dynamic review.

For main-fixture style changes, follow `references/lamp-style-linkage.md`: preserve
positions and actual light contributions, resolve body/plan parity, respect fixed
choices, and verify save/reload independently from visual samples.

Wall-surface patterns, existing wall panels and artwork follow
`references/wall-decoration-linkage.md`; use the shared style/room/face policy,
respect fixed choices and preserve architecture and decoration placement.

## Workbench maintenance and regeneration

Before regenerating an H5 workbench after shared UI changes, apply
`references/workbench-reliability-rules.md` and
`references/h5-interaction-presentation.md`. The standard build verifies
`assets/h5/engine.provenance.json`; rebuild stale source through
`scripts/production/rebuild_h5.mjs`, never by rewriting a checksum alone.
Run `scripts/workbench_browser_suite.py --case CASE --out NEWDIR --checks core`
with existing browser dependencies to exercise the newly generated artifact.
Browser findings must bind HTML/engine/template/case fingerprints; unavailable
checks are not passing checks. Keep UI-only upgrades on the original storage
identity, preserve scheme/materials, and retain separate visual/human acceptance.
For shared workbench regressions, run `scripts/workbench_cross_layout.py --out NEWDIR`
with existing browser tools. It generates independent renamed rectangular,
concave/rotated and empty single-room fixtures, verifies required mechanism scopes,
and keeps synthetic capability evidence separate from the actual-case review.
Use `scripts/check_component_capabilities.py --component TYPE` to inspect indexed
resize and mechanism boundaries; an indexed test path is not a passing case result.
This workflow does not enable server saving, video generation or publication.

## Required quality gates

Before source interpretation, AI interior generation, homeowner camera planning
or accepted handoff, read `references/h5-quality-gates.md`. Keep case-local
source calibration/provenance, image/reference/camera consistency and subject
time-window records. Use `h5.py review-template`, `quality` and
`audit --subjects`; never infer acceptance from generated files or a collision
pass. Formal handoff/package use `--accepted --bundle --quality-review` and
require technical, geometry, visual and explicit human acceptance separately.
Diagnostic previews remain available with failures and pending statuses visible.

## Wall-backed furniture generation

Apply the wall-contact section in `references/furniture-placement-principles.md`
when generating or revising furniture layouts. Anchor cabinet backs and mounted
TVs to actual finished wall faces, record installation exceptions, and audit the
relationship after edits. Use `scripts/wall_anchor_layout.py` for deterministic
placement and checking; floor/door collision passes alone do not prove adjacency.
Protect connected passage strips including pulled-out dining chairs before placing
the dining group. Prefer viable two-wall cabinet corners and check front access.
Use `scripts/layout_access_checks.py` and the corner-anchor helpers for generation
and review; these are not persistent automatic editor constraints.

## Workbench reliability rules

Before H5 source maintenance, read `references/workbench-reliability-rules.md`.
It governs body-height collision, dimension-preserving batching, native
resolution, on-change rendering, presentation cuts, common component behavior,
fixed room lighting, independent export persistence and finish-only connection
patches. Keep room repartition separately confirmed. Rendering tests do not
transfer visual acceptance to the actual case or older media.

## Local workbench entrypoint

For collaborative editing use `references/project-save-confirm.md`: local project
Save and version-bound Confirm and continue coexist. The Agent launches/opens the
project service and awaits a stage-specific confirmation during an active task;
the service cannot wake an ended task. Portable HTML retains independent saving.
Never treat an old seed as recovered browser edits or use this service to bypass
an existing access denial.

For H5 interface changes, read `references/h5-interaction-presentation.md`.
Chinese room/passage display names must be at most three characters; retain
functional explanations separately and validate model/state naming before build.
Preserve direct joystick/keyboard/drag walk without blocking entry modals;
pointer lock is optional. Keep case parity and new-interface visual acceptance
separate from earlier scheme approvals.

Read `references/h5-tools-and-case-schema.md` when building or operating the
workbench. Fill `assets/h5/case-template.json` in the case folder after reference
review, then use `scripts/production/h5.py`: `build`, `export`, `prepare`,
`audit`, `capture`, `run`, `handoff`, `package`; `doctor` reports dependencies.
H5 is the default deterministic engine; Blender is optional via
`run_production.py --engine blender`. Never hardcode case coordinates, palette
selections, lamp counts, floor areas or approval evidence in the shared engine.
Keep the existing approved case unchanged during generic-template maintenance.

Prefer the structured H5 workflow when an editable 2D/3D workbench is available:

**Reference review → H5 scheme confirmation → interior renders → continuous camera preflight → requested final video.**

Read `references/h5-production-workflow.md`. Export actual scheme meshes/materials,
retain scope hashes and approval provenance, and drive every downstream artifact
from that export. A changed wall invalidates structure/layout/style; furniture
movement invalidates layout/style; a changed finish invalidates style. Do not
reconstruct a second independent apartment in Blender.

For H5 quality checks and accepted-version closeout, read
`references/h5-acceptance-and-handoff.md`. Record an actual playable H5 preview's
technical result and user acceptance per case; neither validates a Seedance
generation chain. Preserve the accepted subset and distinguish current drawings
from older accepted AI images with different lighting or source revisions.

Without a structured workbench, reconstruct and confirm the floor plan, then
confirm furniture and a design direction before coordinated image generation.
A route and genuinely continuous video remain a separately requested branch.

The original plan remains the structural authority. Floor-plan reconstruction,
comparison against the source, and user confirmation are mandatory before any
renovation image. A single user response may confirm both zones and access
elements when one complete presentation clearly shows both scopes; do not ask
again for already recorded items. The image workflow is implemented as a
controlled conceptual pipeline. Generative continuous-video execution is not
validated by a deterministic H5 preview and remains unavailable or experimental
until its own playable sample passes visual review. H5 playback results and
acceptance are verified per case.

## Scope and stopping point

This is a concept workflow, not a verified architectural reconstruction
engine. Room-perspective images may drift despite preflight. User acceptance,
visual structural review, and automated file checks are separate facts. If the
user stops generation, hand off only the accepted subset with rejected and
unverified outputs explicitly excluded; never mark the abandoned full package
as passed. Blender is not required. Generative video remains experimental;
deterministic H5 previews require actual case-specific playback checks.

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
- For image-only outputs, never claim dimensional accuracy, arbitrary camera
  navigation, construction readiness, or a real 3D model. For actual exported
  meshes, describe them as a data-derived editable 3D scene; document source
  dimensions, assumptions, coordinate conversion and verified parity. Never
  claim measured accuracy or construction readiness from reference drawings.
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
2. Establish the canonical H5 case for supported geometry, then generate a clean
   orthographic 2D top-down reference plan as an editable SVG
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
4. Complete the reconstruction and self-check before the round-1 question batch.
   Present structure/functions and access together by default. Collect only
   missing consequential household needs with recommended choices.
   Present the reconstructed plan beside the source and perform the self-check
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
equipment from room functions; run the version-bound layout/group/revision gate
in `furniture-layout-review.md` before presentation, with case-specific evidence.
Keep the checklist internal and ask only about
consequential uncertainty. Known access or operation conflicts require correction; restricted-use designs
need verified usable states and visible conditions, never unconditional passes.
For whole-assembly revisions, declare the required intent/state/final-output
checks in `references/layout-use-and-representation-contract.md`. Unmeasured
clearances remain explicitly unverified, not passed.

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
preview. For H5-supported structured input, edit the canonical case/workbench and export
its structure/furniture SVG+PNG modes rather than independently redrawing. Read
`references/furniture-placement-principles.md` and apply its layout-synthesis sequence
before choosing furniture coordinates. Compare wall anchors and operating states
internally, and record room-level review evidence before presentation. If H5 cannot represent the source,
use the explicit drawing fallback with limitations; `render_furniture_layout.py` resolves its
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

1. Let the user specify a style or choose from the nine defaults in
   `assets/project-template.json`, in this fixed row-major order:
   现代简约、原木奶油、 中古现代；现代新中式、香槟珍珠、欧式奢华；
   法式风格、意式暖奢、巴黎艺术. For an undecided user, generate and show
   ONE 3x3 eye-level interior comparison board with all nine, preserving the
   same confirmed layout, camera and daylight. Read each option's
   `generation_prompt` and `references/prompt-contracts.md`; naming changes
   alone do not define a new visual. Keep broad residential appeal and quality.
   Follow `references/guided-user-workflow.md` and the style-selection gate.
   The planner supports one nine-panel board; 4/8/12 remain legacy-compatible.
   These are design directions, not popularity rankings. Preserve a user's
   explicitly requested smaller comparison; never require comparison after an
   explicit selection. Do not add excluded styles to the default nine.
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
   First generate and display the timed route animation using
   `route_rehearsal.py` and the current furniture PNG. Confirm its start/end,
   visits, independent camera facing, total duration and observe/transit rhythm.
   Bind the explicit user reply to that exact animation with `--route-review`
   before any video/samples, including diagnostic low-resolution capture. A text
   itinerary or a static path does not satisfy this gate. Indoor starts and
   ends are valid. Use `indoor_segment` for an interior clip,
   `entry_to_interior` for a tour that enters the home and finishes inside, and
   `full_tour` for outside-to-outside tours; a move inside one open zone has no
   fake door step. A graph-valid route is only a first check; the camera path
   must also avoid walls and furniture. Check indoor route points against the
   current zone polygon and visually inspect the approved furniture layout.
2. Before any paid or external generation, name the available tool, input
   limits, test scope, likely cost, and stopping condition. The present Skill
   has route validation but no verified generative continuous-video execution
   chain. A separately verified H5 preview may be handed off as that case's
   deterministic walkthrough, with its own checks and human acceptance.
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

See `references/bundled-resource-index.md` for scripts, templates and their roles.

## Completion report

Read `references/completion-report.md` and report confirmed scopes, uncertainties,
quality failures, agreed artifacts and their reference chains.

门型及家具选型、支持边界与检查入口见 `references/component-use-and-capabilities.md`；门型变更同时读 `references/door-selection.md`。

新布局及门型修改须执行 `references/door-selection.md` 的布局前后门机制复核，核对构建 `.doors.json` 与声明通道；门扇/把手/停车区失败不得仅凭构建成功声称已通过。常用门窗从建筑构件入口插入并绑定墙洞，不能用独立家具门替代。

修改卫浴、衣帽间或其门后，按 `references/facility-use-checks.md` 为受影响设施声明接近、开启、使用、退出流程；正式验收设置 facilityUsePolicy.required=true 并包含全部受影响设施。未配置的淋浴门不按可开启门验收，设施报告失败不得靠只提供房间入口路径绕过。家具不动优先比较真实门机制；个例铰链/角度、人体包络、站位只保存在案例。

Room finish boundaries use the shared H5 build normalizer in `scripts/production/floor_boundaries.py` and the contract in `references/workbench-reliability-rules.md`. Align to actual wall faces and explicit opening spans, not approximate room label boxes. Treat unresolved gaps/overlaps as input errors; do not hide them with another case-only overlay. Retain canonical normalized room polygons for plan/mesh/area consistency.

Local stage closeout and version boundaries: `references/local-version-closeout.md`. Use `scripts/release_smoke.py` for the consolidated module checks; actual generated-browser, device, video and user approvals remain separate. Never infer case acceptance from local version freeze.
