# Changelog

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
