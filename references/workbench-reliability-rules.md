# Workbench reliability and presentation rules

Read before modifying H5 editing, rendering, persistence, floor coverage or delivery behavior. These are reusable implementation rules, not the bundled apartment's dimensions or palette approval.

## Ceiling and fixture visibility

Orbit/bird views default to hiding ceiling surfaces and ceiling-mounted fixture
models together. Turning on the top view reveals both; walk mode reveals both
without changing the saved orbit top-view preference. Include ceiling fixture
types even when legacy input omits mount. Full wall height does not reveal lamps.
Keep actual light sources, intensities and illumination independent of fixture
mesh visibility. Export includes ceilings and fixtures, then restores viewer state.
Wall lamps and table lamps retain their own visibility rules. Verify mode changes,
manual top toggles, legacy mounts and export restoration before acceptance.

## Rendering and walk safeguards

Plan furniture symbols and their label occlusion use the same stable surface
order, independent of scheme insertion order. Table/desk/dresser tops cover the
overlapping seat portion of tucked chairs. The chair back outside the tabletop
remains visible; never change elevation, shrink or delete a chair to conceal a
physical collision. Check actual 3D nesting separately. `plan-furniture-order.js`,
`test_plan_furniture_order.mjs` and the generated `plan-order` browser check cover
this behavior, including real exported SVG pixels and visible-part selection.

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
Style changes control colors/material finishes, supported furniture bodies under
`furniture-style-linkage.md` and main-fixture bodies under `lamp-style-linkage.md`; they do not override these common behaviors.
Migrate legacy standard TV depths once while retaining nonstandard or already migrated edited sizes.
Kitchen decoration positions and room finish approvals remain case-specific.

Indoor fixture shadows are an optional visual trial, disabled by default until
case-specific review. A configured fixed set is capped at two lights; all other
lights stay on. Never select lights by camera position. Compare shadow artifacts
and cost before adopting the trial. See `references/beta5-workbench-validation.md`.

## Local workbench safeguards

Use bundled `assets/h5/version.json` as the build identity. Rebuild before packaging
shared-source changes; retain independent case acceptance. Run installed-source
regression via `scripts/release_smoke.py`, including interaction modules. Use
`production/synthetic_cases.py` and `test_workbench_browser.mjs` for isolated
cross-shape UI checks with existing browser dependencies; report emulated mobile
separately from physical-device and Windows checks.

### Source freshness and final-artifact verification

Use the shared rebuild entry `scripts/production/rebuild_h5.mjs` with existing
esbuild/dependency paths. It records `assets/h5/engine.provenance.json` for the
source set (including `version.json`), bundled engine and component registry.
`scripts/production/engine_provenance.py check` independently verifies that record;
`h5.py build` runs the same check before generating a workbench. Changed, missing
or additional source inputs, a changed bundle/registry, or a missing provenance
record block generation with a rebuild instruction. Do not refresh the record
without actually rebuilding. Template edits are tracked separately by the build's
template hash and do not require a JavaScript rebuild.

Run the shared browser entry against a newly generated copy, never the user's
saved tab:

```bash
python3 scripts/workbench_browser_suite.py --case /absolute/path/case.json \
  --out /absolute/path/new-evidence-directory --node /existing/node \
  --browser /existing/chrome --playwright-module /existing/playwright/index.js \
  --checks core
```

The `core` selection covers room focus/top fixtures, product copy, persistent
sidebars, day/night, camera presets and header actions. Add the checks for changed
mechanisms (for example `doors` or `shower-resize`) to the delivery review, or use
`full` to select all registered checks. A comma list selects explicit check names.
The runner builds from the installed engine and
current template, serves only its test directory over loopback HTTP, executes
isolated browser contexts and writes one aggregate report. Existing dependencies
are required; the runner never installs software or enables server-side saving.
A missing environment or unsupported fixture is reported as not executed, never
as a pass. Report test failure separately from unavailable environment.

Use `scripts/browser_artifact_evidence.mjs` for common browser-report binding.
Each result hashes the HTML response actually loaded by the browser and its
embedded engine. Template, original-case and source fingerprints are linked
through the matching build manifest; the browser does not independently rebuild
those inputs. Require receipts for this run's exact target URL and fingerprints,
not just another page's passing report. Build metadata hashes the input and
template bytes actually read, and rejects engine or input changes during build.
A URL, version label or old passing report alone cannot accept a different file.
Rebuilding after a browser check requires a new check on that artifact. Keep
technical interaction results separate from visual, device and human acceptance.

### Independent cross-layout regression

Use `scripts/workbench_cross_layout.py --out NEWDIR --node EXISTING_NODE
--browser EXISTING_CHROME --playwright-module EXISTING_PLAYWRIGHT` for shared UI or
component changes. Its default `core,components,floors` checks run on independent
renamed rectangular, concave/rotated and furniture-free single-room fixtures from
`production/workbench_regression_cases.py`. These are synthetic test data, never
proposed or accepted household designs. No user case or saved tab is imported.
Core copy/history tests discover rooms and editable objects at runtime; a room
material edit tests persistence when furniture is absent. Components are selected
by runtime mechanism/type and dragged along their transformed local axes. Check
actual plan/mesh subparts, undo/redo and reload; no fixed apartment ID or insertion
coordinate may stand in for those checks.
Before measuring a resize grip's screen transform, wait for finite layout
transitions to finish and for the viewport layout to settle. A sidebar transition
can otherwise move the grip during the drag. Verify the pointer hits the grip and
the requested dimension actually changes; an unchanged object cannot certify
fixed-subpart resizing. Keep width/depth directions in local object coordinates.

The matrix requires every declared check and the shower/vanity/bathtub/door scopes
on its equipped fixtures. A passing aggregate component test cannot hide a missing
required mechanism. Missing components and a single-room focus pair are explicitly
not_applicable on the empty fixture; that absence must not be fabricated as a pass.
Do not silently drop a failing fixture or replace it with a copy of another shape.
The suite stops only its temporary HTTP/browser processes and preserves inputs.
`release_smoke.py --with-cross-layout` includes this matrix; browser dependencies
remain explicit and are never installed automatically. Missing tools are blocked,
not successful cross-layout coverage. Keep actual delivery-case checks separate.

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

Treat `model.floorConnections` as reviewed input finish patches bound to an existing room through `materialRoomId`, not as new rooms or inferred room merges. Preserve the source drawing/ownership area basis separately from calculated net finish area. Conflicting material ownership and unsupported geometry require input correction rather than a guessed fill.

The default H5 build normalizer merges these input patches into their material-owning room and emits canonical room polygons plus `.floors.json` evidence; normalized `floorConnections` is empty. Render and export that same normalized geometry/material state in 2D, 3D, standalone HTML and production meshes. Count each resulting floor region once: do not add the original patch area a second time. Current net room finish area may change after wall-overlap removal and patch merging; source-labelled or ownership area does not change. Preserve the input patch IDs and area changes in source/build evidence, not as duplicate rendered floor regions. When normalization is explicitly disabled for a recorded compatibility case, keep its independent patches and count their area separately once; that exception is not finish acceptance. Geometry/ownership changes invalidate finish scope. After wall edits, retain the partition-pending status until a revised layout is confirmed.

## Lighting and visual evaluation

Keep fixed room lights always on and maintain omnidirectional ceiling diffuser behavior in every style. Tune global ambient/hemisphere fill and exposure separately from fixture emission; avoid flattening pale finishes with excessive uniform fill. Day/night changes must alter interior lighting hierarchy, not only the background. Share profiles across bird's-eye and walk views rather than adapting to camera position.

Use same-camera before/after views to assess pale surfaces, floor detail, cabinet tops and ceiling undersides. Numeric brightness parameters are not measured lux. Small local ceiling-finish compensation is a presentation approximation, not physical bounce lighting. Keep tuning values in the renderer/profile or case, not in mandatory Skill rules.

Indoor shadows remain opt-in case trials: fixed IDs, small maps, bounded count and cached updates; never enable all lights or select them by camera proximity. Keep trial/visual-acceptance status explicit. Test costs and artifacts in independent scenes before reviewing the actual case.

## Maintenance evidence boundaries

Check current files directly before claiming a browser restriction. If a tool rejects access, report its concrete reason and stop that blocked operation; never bypass through another browser or serving a copy. User-supplied screenshots can support visual discussion, but are not evidence that the edited version was inspected.

Keep synthetic tests, actual-case visual acceptance, emulator checks, platform reviews and physical-device tests separate. Rebuild the engine and delivery files after source changes; verify manifests and current/bundled parity. Keep old images, tours and mesh sources labelled by their actual revision instead of inheriting new acceptance. Preserve diagnostic history outside the curated reference case.

## Wall and floor junction review

Check a door-carrying wall segment against its adjacent wall axes and finished
faces; do not mix centerline and inner-face coordinates. Flag unintended offsets
before layout review. Compare each floor polygon with actual wall inner faces in
2D and 3D. Explicit reviewed finish patches can fill uncovered perimeter bands
without changing room-area polygons; reject overlaps with walls or other rooms.
Keep source calibration uncertainty visible rather than hiding it behind precise
labels.


## Browser save, portable output and revision migration

Collaborative project mode is documented in `project-save-confirm.md`. Its Save
writes the project file; Confirm and continue binds that saved version. Browser
cache saving remains distinct in portable mode. Do not show project-save success
until the service acknowledges the write, or carry a service token into exports.

State explicitly that browser Save does not rewrite the original HTML. Verify
current snapshot readback after writing; failures must never receive a saved
status. Keep a clearly named download-current-scheme HTML action that embeds the
validated edited state, escapes script terminators, carries a fresh export storage
identity and reports export errors. Exported documents never consult project
predecessor caches; their seed yields only to their own later saves.

For code/presentation-only fixes with unchanged baseline geometry, preserve the
case ID and actual entry-file path so the browser can reopen its existing cache.
Keep a recoverable original file before replacing the local entry. When a new
layout baseline requires a revision ID, keep a stable project identity and declare
compatible predecessor IDs with their source baseline states. Inspect only those
caches; do not scan arbitrary homes or silently import another export. Older raw
cache must remain intact, including corrupt data.

Compare old default, saved user state and new default by stable object IDs and
fields. Transfer edits only when they do not compete with a new default change;
list conflicts explicitly and retain old values in a downloadable review. Let the
user initiate migration from a nonblocking optional action, validate its result,
reset old design approvals, preserve undo and leave old caches unchanged. Filter
runtime-owned assemblies and regenerate them rather than duplicate them. A
migration validation failure does not authorize partial silent data loss.
Do not automatically save fresh defaults before checking for predecessor edits.

Browser storage availability and file-origin scoping vary by host. If old caches
are inaccessible, explain the need to export from the old page; no cross-file,
cross-browser or cross-device recovery guarantee can be inferred from unit tests.
Actual save/reopen and portable-download/reopen checks must be distinguished from
source/storage-helper tests. Never claim a user's current edits were read or
preserved unless their actual data was inspected or the same cache reopened.

## Component completeness and restrained finishes

Generate skirting from the floor-level wall union boundary, including short corner
returns and jambs. Keep ordinary windowsill bases continuous, doors and demolition
open, room switches respected and rotated fixed joinery avoided. Avoid per-wall
midpoint room assignment and arbitrary end shortening. Include explicitly approved
`model.floorConnections` when assigning the room owner of an exposed wall edge;
a narrow finish-only bridge must not cause missing skirting between the wall and
the room polygon. Do not move room polygons or guess new bridges. This is an axis-aligned
concept-wall implementation; new wall shapes need separate verification.
These checks cover synthetic geometry and input/build behavior; browser appearance
and frame performance remain unverified for this revision.

Toilets include a seat, lid, hinges and closed pedestal base within their saved
envelope. Refrigerator door divisions follow the component proportions; preserve
explicit product design if supplied rather than inferring a real model from width.
Close thin chair back edges, cabinet joint backing and curtain-box end caps while
keeping intentional openings such as curtain slots and basin bowls open. Match
door-trim width to the nominal clear aperture; do not narrow the usable doorway.

Material-only changes preserve geometry, palette, layout and light settings.
Share small non-colour roughness maps, distinguish fabric/lacquer/stone/metal,
and exclude transparent glass and emissive fixture lenses from blanket overrides.
Do not interpret geometry or build passes as visual/performance acceptance.

Maintenance checks: scripts/test_component_details.mjs, test_skirting_outline.mjs
and test_material_finishes.mjs use INTERIOR_TEST_NODE_MODULES pointing to existing
Three.js/esbuild dependencies; they never install packages.


## Embedded floor image lifecycle

Use `floor-texture-runtime.js` with the optional per-case finishes documented in
`h5-interaction-presentation.md`. Preserve the current procedural map until
successful image decoding; do not blank the floor on load/failure. Decode only
selected embedded images, share cached floor materials and release replaced or
retired maps, including callbacks that arrive after a style switch. Physical UV
scale, sRGB colour space and albedo roughness must be explicit. Test success,
failure, disposal before completion, unsupported/default selections and offline
HTML inclusion with `scripts/test_floor_textures.mjs`.

### Exact room/wall finish boundaries
H5 build normalizes orthogonal room finish polygons against the same wall-face/endpoint geometry used in the mesh. Merge explicit threshold/finish patches into their material-owning room, subtract actual floor-level solid walls and clip to footprint. Repair only small connected gaps (default120mm maximum travel); never fill large unknown space or cross a wall. Tiny detached overruns (at most tolerance² area) may join the physically adjacent room, with reported owner/area changes. Ambiguous free overlaps, unsupported topology or unassigned large gaps fail with a `.floors.json` report instead of a silent bounding-box fill. Normalization must be idempotent. Store the resulting room polygons as the canonical model so plan, mesh, area and labels use the same boundary. Walls, openings, furniture and manual finish choices stay unchanged. Material boundaries in real open passages remain passable. Explicit floorBoundaryPolicy.enabled=false is a recorded compatibility exception, not acceptance.

### Production image transport and replay lighting

- Production exports serialize decoded HTMLImageElement/ImageBitmap as well as Canvas
  textures through `production-textures.js`. Preserve repeat, offset, centre,
  rotation, flipY, wrapping and colour space; deduplicate by texture UUID.
  Missing/undecoded/tainted images are errors, never silently `map:null`.
- Both production capture entry points await embedded floor texture loading;
  required-image fallback or timeout blocks export rather than certifying a plain floor.
- Replay defaults reduce flat fill (hemisphere .72, ambient .16), fit the sun
  shadow camera to the apartment bounds, and use 3mm normal bias. These are
  presentation defaults, not calibrated physical illumination or photoreal acceptance.
- Optional `presentationProfile.replayLighting.fixtureShadowIds` (or prepared
  `renderSettings.lighting.fixtureShadowIds`) specifies at most two unique enabled
  exported fixtures. No camera-dependent light selection. All other fixtures retain
  their exported illumination; shadow maps remain static across camera movement.
- Validate real image decode → mesh serialization → replay, including missing-image
  failure, plus same-camera static images. Run `scripts/test_production_textures_browser.mjs --playwright-module EXISTING_MODULE --browser EXISTING_BROWSER`
  and `scripts/test_replay_lighting_browser.mjs --url HTTP_RENDERER_URL --tour EXACT_TOUR --playwright-module EXISTING_MODULE --browser EXISTING_BROWSER`. Static image approval
  does not certify full-tour performance, motion, or construction accuracy.
- A legacy export with a missing map may only restore an explicitly identified
  canonical asset, with provenance and unchanged geometry/state checks. Do not
  fabricate a new texture or imply that a repaired replay is a fresh full export.

- Replay fixture housings remain visible but do not cast shadows: schematic light
  emitters can be embedded inside the housing and otherwise create false long
  silhouettes. Furniture/architecture shadows remain enabled. This approximation
  must not be described as physical luminaire photometry.
