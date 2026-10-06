# Workbench reliability and presentation rules

Read before modifying H5 editing, rendering, persistence, floor coverage or delivery behavior. These are reusable implementation rules, not the bundled apartment's dimensions or palette approval.

## Rendering and walk safeguards · beta.5

Walk collision uses the vertical overlap of the furniture body and a standing
viewer (eye height plus 150 mm head allowance); do not skip all hanging objects
above 1100 mm. This remains a plan-footprint approximation, not a certified human
clearance test. Preserve decorative exclusions and clear overhead passage.

Batch plain opaque furniture leaves only within the same object and dimensional
body group. Preserve transformed surfaces, material roles, semantic accessories,
picking, bounding dimensions and production export. Recheck state and geometry
parity; fewer meshes do not prove lower-detail or changed geometry.

Render at the native display pixel ratio in every mode. Do not lower resolution
for motion, slow frames or idle state, and do not cap high-DPR displays at 2.
Render unchanged scenes on demand while retaining the animation/input loop.
Camera, editing, resizing, doors and day/night must resume rendering immediately;
shadow maps update for geometry/light changes, not for every camera frame.

Presentation cutaways prioritize furniture layout and decoration. Lower/cut
architecture, doors, windows and opening trims, while keeping wardrobes, shelves
and all other furniture complete at their true heights. This is a presentation
view, not a strict whole-model section. Preserve fixed illumination even when
upper lamp meshes are hidden. Cap closed architectural surfaces, preserve holes,
and ignore clipped architectural hits during picking. Full-height and walk
restore complete architecture; never alter saved scheme dimensions.

Common component behavior must remain consistent across styles: thin default TV
geometry (35 mm), side-emitting ceiling diffusers, fixed always-on room lighting,
native display resolution and complete furniture in presentation cutaways.
Style changes control colors/material finishes rather than these behaviors.
Migrate legacy standard TV depths once while retaining nonstandard or already migrated edited sizes.
Kitchen decoration positions and room finish approvals remain case-specific.

Indoor fixture shadows are an optional visual trial, disabled by default until
case-specific review. A configured fixed set is capped at two lights; all other
lights stay on. Never select lights by camera position. Compare shadow artifacts
and cost before adopting the trial. See `references/beta5-workbench-validation.md`.

## Local workbench safeguards · beta.4

Use bundled `assets/h5/version.json` as the build identity. Rebuild before packaging
shared-source changes; retain independent case acceptance. Run installed-source
regression via `scripts/release_smoke.py`, including interaction modules. Use
`production/synthetic_cases.py` and `test_workbench_browser.mjs` for isolated
cross-shape UI checks with existing browser dependencies; report emulated mobile
separately from physical-device and Windows checks.

Wall geometry edits mark original room/floor partitions and their areas as
pending; undoing to the original geometry clears that state. Do not silently
rename, merge or split rooms. Repartition requires a separately confirmed layout.
Build evidence reports room main-light coverage and placement warnings; never
invent approved fixture positions. `mainLightingRequired:false` exempts an
explicit nonfunctional region. Actual mesh emission/occlusion remains a gate.
Keep material presentation case-local: `presentation.materials.marble.veins:false`
uses plain marble consistently in 2D/3D. Material changes invalidate style scopes.

## Independent HTML persistence

Every exported HTML owns a new document storage identity. First open uses its embedded seed; later refresh restores that document's latest valid saved state. Never borrow another export or the base case cache. Re-export creates a separate identity while retaining current scheme data. Preserve corrupt raw data and provide recovery; if storage is unavailable, still open the seed and explain how to export edits. Browser-local storage is not cross-device synchronization.

Verify export, edit, refresh, second export and isolation from the original. Also verify ordinary JSON import and base-workbench persistence. A successful first reopen alone does not verify later editing.

## Explicit floor connection finishes

Keep approved room boundaries and room area semantics unchanged. For reviewed connection bands, use explicit `model.floorConnections` finish-only polygons bound to an adjacent room through `materialRoomId`. They are not new rooms. Reject overlapping patches, overlap with rooms/walls, invalid material links and geometry outside the footprint.

Render the same polygons/materials in 2D and 3D; retain them in standalone HTML and production meshes, with stable IDs. Show connection area separately, count it once in material/floor totals, and do not inflate individual room or ownership areas. Changes to patch geometry/ownership invalidate finish scope. Do not silently infer new patches after wall edits; existing partitions remain pending until a revised layout is confirmed.

## Lighting and visual evaluation

Keep fixed room lights always on and maintain omnidirectional ceiling diffuser behavior in every style. Tune global ambient/hemisphere fill and exposure separately from fixture emission; avoid flattening pale finishes with excessive uniform fill. Day/night changes must alter interior lighting hierarchy, not only the background. Share profiles across bird's-eye and walk views rather than adapting to camera position.

Use same-camera before/after views to assess pale surfaces, floor detail, cabinet tops and ceiling undersides. Numeric brightness parameters are not measured lux. Small local ceiling-finish compensation is a presentation approximation, not physical bounce lighting. Keep tuning values in the renderer/profile or case, not in mandatory Skill rules.

Indoor shadows remain opt-in case trials: fixed IDs, small maps, bounded count and cached updates; never enable all lights or select them by camera proximity. Keep trial/visual-acceptance status explicit. Test costs and artifacts in independent scenes before reviewing the actual case.

## Maintenance evidence boundaries

Check current files directly before claiming a browser restriction. If a tool rejects access, report its concrete reason and stop that blocked operation; never bypass through another browser or serving a copy. User-supplied screenshots can support visual discussion, but are not evidence that the edited version was inspected.

Keep synthetic tests, actual-case visual acceptance, emulator checks, platform reviews and physical-device tests separate. Rebuild the engine and delivery files after source changes; verify manifests and current/bundled parity. Keep old images, tours and mesh sources labelled by their actual revision instead of inheriting new acceptance. Preserve diagnostic history outside the curated reference case.
