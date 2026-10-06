# Current local beta closeout · 2026-10-05

- [x] Extract reusable H5 engine, geometry, components, styles and editor UI.
- [x] Move apartment geometry, furniture/lamp positions, area values, camera starts
      and approval provenance into external case data.
- [x] Provide offline HTML build, actual-mesh export, three drawing exports,
      H5 replay, camera audit/capture, resumable frames, optional FFmpeg encoding.
- [x] Keep Blender as an explicit optional importer of the same mesh stream.
- [x] Add relative-link handoff, hashed manifest and local archive packaging.
- [x] Update bilingual docs, agent entrypoint, dependency and verification status.
- [x] Check source syntax, help entrypoints, same-case HTML construction and local
      package structure/integrity. This is not a regression suite.
- [ ] Run new-floorplan tests and full regression (deferred).
- [ ] Visually accept a fresh end-to-end replay from the extracted generic engine
      (part of the deferred regression work).
- [ ] Execute and accept Seedance video (deferred).

A real H5 homeowner continuous walkthrough has been accepted in the local case;
its acceptance belongs to that case, not to every future project. Public release
is not part of this local closeout. Automated recognition, automatic furniture
layout, construction-grade documentation and usage accounting below are optional
future product work, not unfinished requirements for the current local package.

## Historical roadmap

The entries below record the older workflow and roadmap. They do not override
current capability, verification or acceptance status above.


## 1.0 three-stage product gate

- [x] Organize the user entrypoint as floor-plan confirmation, coordinated
      renovation images, then optional route/video.
- [x] Preserve reconstruction, source comparison, and explicit user confirmation
      as mandatory prerequisites for renovation generation.
- [x] Replace pre-confirmed new-project defaults with an unconfirmed template.
- [x] Bind floor-plan confirmation to an artifact version, explicit scopes,
      confirmed item IDs, review evidence, and unresolved consequential items.
- [x] Allow one response to confirm zones and access elements when both scopes
      were fully presented; do not require two conversational rounds.
- [x] Describe continuous video as unverified until a playable sample passes
      continuity and scheme-consistency review.
- [x] Propagate custom styles and design preferences through relevant image tasks.
- [x] Add targeted revision and dependency invalidation for changed schemes.
- [x] Define concept closeout without automatic construction/measurement expansion.
- [x] Bind production layout acceptance to file content and inject its reference.
- [x] C6: reuse current image acceptance for local handoff after live QA.
- [x] Require per-view/untouched-region inspection and two-failed-retry stop (operational rules).
- [x] Specify faithful contact-sheet assembly without scene regeneration (operational rule).
- [x] Validate one real deterministic H5 indoor move-through-door-and-turn case
      (local homeowner review; does not validate Seedance or all floorplans).

These checks describe implementation status, not visual proof. Unit tests do not
establish image fidelity or continuous-video quality.

2026-09-13 main-flow closeout: the full synthetic regression suite and Skill
format validator must pass in the current checkout; use the live command output
for the exact test count rather than maintaining historical counts here. The
suite covers file/layout binding, stale-reference blocking, revisions, 12-style
planning, structured SVG/PNG rendering, declared layout conflicts, and faithful
contact-sheet assembly. It does not establish visual fidelity, measured accuracy,
construction feasibility, or fresh style-board distinctness.

Vector delivery now uses case-neutral structured inputs for reconstructed plans
and furniture layouts. The tools create independent SVG elements and render the
same revision to PNG. Furniture checks cover declared wall, object-overlap and
door-swing conflicts; remaining operation/clearance checks require review.

- [x] Remove conflicting style-count, stale test-count, and obsolete export wording.
- [x] Add case-neutral structured floor-plan SVG-to-PNG rendering.
- [x] Add reusable furniture symbols and wall/overlap/door-swing checks.
- [x] Add deterministic no-crop/no-resize confirmed-image contact-sheet assembly.
- [x] Cover the new tools with synthetic regression tests and format validation.

## 1.0 floor-plan evidence batch (B1–B3)

- [x] Add partial/critical input branches and explicitly accepted completion provenance.
- [x] Render door leaves and swing arcs, sliding tracks, passages, windows, and bay outlines.
- [x] Reject missing/out-of-bounds geometry and overlapping zones; warn on uncovered regions.
- [x] Cross-check room/opening IDs, functions, connections, operation, versions, and actual files.
- [x] Bind confirmation to input content and check for changes before executing new plans.
- [x] Run regression tests and inspect the synthetic overlay fixture for the B1–B3 batch.
- [ ] Verify reconstruction accuracy against representative real complete and incomplete plans.

Use `python3 -m unittest discover -s scripts -p 'test_*.py'` for the full test suite.
Historical samples with missing evidence are non-executable dry runs; create a
new confirmed evidence bundle before production generation. This batch does not
establish image-generation consistency or continuous-video feasibility.

## Phase 0: local V0 foundation

The C1/C2/C4/C5 local batch adds shared scheme records, actual approved-primary
reference resolution, revision/replan commands, and file-bound mandatory review.
Use `design-and-revisions.md` for this workflow. Its synthetic regression tests
do not establish image-generation fidelity; representative actual image checks
and the video sample remain separate acceptance work.

- [x] Define the conceptual-image product boundary.
- [x] Define a lightweight model-independent manifest.
- [x] Make the canonical view a hard dependency for derived views.
- [x] Add deterministic dry-run planning.
- [x] Add local regression tests.
- [x] Run the first real GPT Image 2 request with a user-approved floor plan.
- [ ] Record actual latency and cost.

## Phase 1: controlled Image 2 pilot

- [ ] Assemble 20 test floor plans with permission to use them.
- [ ] Add floor-plan readability checks.
- [x] Add the normalized 2D top-down reconstruction protocol.
- [x] Add separate room-function and door/window access overlay protocols.
- [x] Add a controlled residential space and industry naming ontology.
- [x] Add door, opening, passage, and window classification rules.
- [x] Add graph-based property-tour route validation.
- [x] Add deterministic overlay rendering for access and zoning layers.
- [x] Add deterministic ordered route rendering after internal access is confirmed.
- [ ] Validate 2D reconstruction fidelity across the pilot dataset.
- [x] Add a conversation-level interpretation and confidence protocol.
- [x] Add a proposal-first confirmation contract.
- [x] Split confirmation into structure/function and door/window access gates.
- [x] Add access-only validation for swing direction, sliding doors, and
      unreachable rooms.
- [x] Add 4/8/12-option comparison planning, with 12 defaults across three 2x2 boards.
- [x] Add evidence-coded recognition artifacts and deterministic validation.
- [x] Compile provider tasks directly from the approved delivery shot list.
- [x] Propagate asset kind, camera intent, must-show, and structural locks into generation tasks.
- [ ] Add automated vision-assisted recognition extraction.
- [x] Add canonical-view correction and explicit user-approval state.
- [x] Add file-bound package review and current package acceptance for local export;
      keep the extra final-export authorization command as legacy compatibility.
- [x] Bind strict delivery reviews to the exact delivery-plan SHA-256.
- [ ] Generate three fixed room views from dual references.
- [ ] Generate and visually review the currently scoped style-comparison boards.
- [ ] Score every run against `evaluation.md`.

## Phase 2: product loop

- [x] Add design-scheme persistence and dependent-output version history (local state/replan implementation).
- [ ] Add preview versus final-quality routing.
- [ ] Add usage and cost accounting.
- [ ] Add partial retry without duplicate billing.
- [ ] Add 2K/4K export presets.
- [ ] Add a recoverable continuous-video execution chain after feasibility is
      proven; keep slideshow/2.5D output explicitly labelled as a substitute.

## Phase 3: upgrade based on evidence

- [ ] Add floor-plan recognition if room extraction fails repeatedly.
- [x] Add structured H5 geometry as the editable architectural authority.
- [x] Add Three.js and an optional actual-mesh Blender importer.
- [ ] Add layout generation only after rule templates reach their limit.
- [x] Add actual continuous camera paths and scoped local acceptance.
