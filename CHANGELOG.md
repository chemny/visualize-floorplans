# Changelog

## 0.2.0-beta.5 · workbench reliability and presentation · 2026-10-06

- Follow-up: apply thin-TV legacy defaults across styles rather than only the
  reference case. Ceiling diffuser emission, fixed lighting, native resolution
  and presentation cuts already share common implementations.

- Follow-up: champagne style revision 6 removes warm wood-grain cabinet
  finishes in favor of champagne lacquer or pearl white. Apply approved case
  living/dining/entrance marble and cabinet colors once to cached schemes.

- Follow-up: add independent dining/coffee tabletop accessories and scoped
  kitchen-corner decor. Preserve body-height normalization, picking and walk
  footprint; batch opaque accessory surfaces separately. Kitchen fixtures and
  working space remain authoritative for placement.

- Follow-up: add subtle champagne upholstery/headboards and partial cabinet
  fronts; retain pearl base, plain floors and lighting. Later revision 6 replaces wood finishes.
  Silver metallic fridge finish uses fine brushed relief; TV depth is 35 mm.
  Upgrade untouched champagne defaults while preserving custom palette choices.

- Follow-up: presentation cut clips architecture, doors/windows and opening
  trims only; keep complete furniture to prioritize layout/decoration. Preserve
  closed architectural caps, fixed lights, picking and full-height/walk restore.

- Follow-up: render wall cuts as unlit black; round/square/panel ceiling
  diffusers emit on their side faces and use omnidirectional fixed illumination.
  Preserve fixture envelopes, group budgets and native pixel ratio.

- Follow-up: remove adaptive render-resolution reductions and the DPR2 cap.
  Render at native display pixel ratio during idle/motion/high frame cost.
  Retain batching, on-change rendering and fixed light groups.

- Test furniture collision against standing-body height instead of ignoring all
  furniture mounted above 1100 mm.
- Merge plain opaque static parts within one furniture body/material; preserve
  actual triangle surfaces, dimensions, picking and production export.
- Render camera/scene changes immediately; skip repeated GPU and label rendering
  when idle, and cache unchanged shadow maps.
- Add fixed, capped indoor-shadow trials independent of viewpoint. Keep them
  disabled by default pending case-specific visual review; no new UI toggle.
- Extend synthetic collision, dimension, shadow-budget and idle-render checks.
- Rebuild the reference workbench while preserving scheme, original inputs,
  selected AI images and older media bytes. Media re-export deferred by user.
- Consolidate reusable rendering, persistence and floor-connection safeguards in
  `references/workbench-reliability-rules.md`; retain case-specific choices in case data.
- Isolate independent HTML export caches; restore edits after refresh.
- Add validated finish-only connection patches with synchronized 2D/3D and
  production export; report their areas without changing room boundaries.
- Reduce uniform lighting fill and night amplification; the example uses one
  fixed 512-pixel dining-shadow trial and local ceiling presentation compensation.
- Published technical evidence remains distinct from fresh case visual acceptance.

## 0.2.0-beta.4 · local workbench stabilization · 2026-10-06

- Added shared version identity in HTML/build evidence and a matching local archive.
- Added room-area pending detection after wall geometry changes, with undo restoration;
  original room polygons remain authoritative until a new layout is confirmed.
- Added non-mutating main-light coverage, room assignment and finished-ceiling warnings.
- Made marble veins case-configurable in SVG and Canvas; bind material presentation
  to style approval scopes and production exports.
- Extracted storage, pointer-lock diagnostics, material presentation, label anchors,
  room-area status and permanent lighting rig into tested modules.
- Added reusable unit/browser fixtures for rectangle, concave and nine-room stress
  cases; storage, export/reopen, joystick, keyboard and refusal fallback checks.
- Corrected verification API wall toggling to use the same implementation as the UI.
- Remains local only; embedded native permission, Windows and physical mobile
  checks do not inherit desktop/synthetic acceptance.

## Historical local interaction refinement · 2026-10-06

- Simplified walk to a full-width scene with compact on-demand controls,
  removing room jumps, duplicate sidebars/HUD and entry/resume modals.
- Restored desktop/touch joystick and drag/keyboard defaults; native pointer
  lock is optional, with automatic nonblocking fallback on rejection.
- Replaced two-line room cards with compact single-line annotations, progressive
  zoom-out detail and measured overlap handling.
- Added optional imported-case preservation for explicit bed model choices and
  unchanged window trim dimensions. No apartment data is embedded in the engine.
- Rebuilt the local engine. The existing beta.3 installation archive and release
  validation describe the prior snapshot; no archive or remote release is updated
  by this local UI revision. New UI acceptance remains pending user review.

## 0.2.0-beta.3 · release preparation · 2026-10-06

- Added optional explicit camera observation cues, bounded smooth turning, and
  validation of timing, target coordinates and rotation limits. Camera intent
  remains separate from actual sustained-subject visibility.
- Re-ran real-model observation diagnostics without changing the declared
  visibility thresholds; timing and review evidence remain case-local.
- Updated bilingual agent installation, capability and platform boundaries.
- Verified and bundled the reference workbench's current upstream MIT notice,
  retaining source and license revision attribution alongside Three.js notices.
- Made production/source interpretation JSON encoding explicitly UTF-8 and
  added a Unicode/space-path CLI regression.
- Rebuilt distributable source archive and exercised clean-directory checks.
  Different-floorplan, cross-host runtime and Seedance verification remain deferred.

## 0.2.0-beta.2 · local quality gates · 2026-10-06

- Added independent technical, geometry, visual and human-acceptance states;
  source/image/tour review contracts, case-local template and strict accepted
  handoff/package gates. A preview manifest boolean cannot grant acceptance.
- Added separate image-axis calibration, dimension and geometry provenance,
  critical ambiguity checks and structure-scope binding.
- Bound AI outputs to current H5 reference bytes, exact capture cameras, scheme,
  agreed image sets and recorded per-image/cross-view checks. Native aspect
  rounding is explicit; no image-recognition capability is inferred.
- Added actual-mesh subject visibility/extent and near-wall measurements across
  observation time windows, route/intent binding and current physical envelope.
  Diagnostic previews retain failures; formal camera production rejects them.
- Added targeted negative/positive regressions and same-case window inspection.
  No images or video were regenerated, and no prior accepted case was changed.
  This is a local source update, not a rebuilt installation archive or release.

## Unreleased · fresh verification fixes · 2026-10-05

- Exercised a fresh original-plan-to-H5-to-AI-image-and-H5-video same-case run,
  excluding Seedance and historical generated media/model/camera artifacts.
- Corrected window sill/height handling, wall origin, export readiness, hanging
  fixture anchors, preview route gating, false trim obstacles, sliding panel
  poses, wall end joins, ordered visit binding and tight-corner sampling.
- Added a rejecting luminous-face visibility gate and five route regression tests
  relative to the prior baseline; local regression count is 126.
- Recorded 26 UI checks plus resume/revision/approval gate checks. Visual subject
  probes still identify camera focus/time-allocation limitations; no claim of
  automatic visual approval, cross-floorplan certification or public release.

## 0.2.0-beta.1 · local closeout · 2026-10-05

- Added reusable single-file H5 template, source engine and component models;
  separated case geometry, furniture, fixtures, areas and camera parameters.
- Added `h5.py` build, actual-mesh/drawing export, preparation, camera audit,
  capture/resume, production, handoff and package commands.
- Made H5 the deterministic production default; retained explicit Blender branch.
- Added ceiling/fixture visibility, homeowner motion, dimensional envelopes,
  source-version binding and handoff guidance from the accepted local workflow.
- Updated bilingual README, agent entrypoint, runtime guidance and verification
  status; included Three.js runtime license and reference-code attribution.
- Performed limited syntax/entrypoint/build/package checks. New-floorplan tests,
  full regression and Seedance remain deferred. No remote release was made.

## 0.1.0-beta.1

- Existing floor-plan interpretation, reviewed layout, conceptual-image planning,
  scoped delivery approval and deterministic SVG/PNG tools.

- Local preview: fixed four-light runtime budget with room-aware fades and adaptive pixel ratio; fixture meshes/exported illumination preserved. Performance and visual acceptance remain case-specific.

- Local brightness preview: broad downward runtime fills, view-facing main-light priority, stronger night main lighting and reduced day fill; visual acceptance pending.

- Fix: remove camera-driven light selection. All enabled fixtures now contribute to permanent spatial illumination groups; adaptive resolution remains independent of lamp state. Prior moving-budget previews superseded.

- Remove the global fixture light toggle and its public setter; day/night keeps fixtures enabled. Roof and pointer-lock controls are unchanged pending discussion.

- Local preview: preserve pointer-lock rejection diagnostics, hide refused optional lock control, retain focus retry and fallback controls; synchronize plain marble presentation in 2D/3D.

## Local reference case · 2026-10-06

- Bundle supplied inputs, selected concept images/drawings, current beta.4 workbench and scheme, retained H5 tour and compressed source mesh under assets/reference-cases/jujian-champagne-pearl.
- Add offline index and bilingual discovery links; keep representation differences explicit without retaining intermediate versions or audit history.
- Exclude Finder .DS_Store metadata from local Skill archives. No engine changes or GitHub publication.

## Beta.4 publication preparation · 2026-10-06

- Include the provider-authorized full reference case and preserve original upstream notices. Clarify current demo versus retained media sources.
- Exclude uncurated historical furniture-reference files from distributable archives; keep local originals.
- Fresh macOS source, Python, Node subject and interaction regressions pass. Windows physical/runtime checks remain deferred as agreed.
