# H5 tools and case inputs

## What is reusable

For workbench interface maintenance, read `h5-interaction-presentation.md`.
Current UI defaults use direct joystick/keyboard/drag walk, optional pointer
lock and compact bird's-eye annotations. A UI preview still needs case parity
and visual review; old releases do not certify a changed local engine.

`assets/h5/source/` contains the workbench editor, wall/opening geometry,
furniture assemblies, installation envelopes, label placement, six finish
presets, lights, offline first-person navigation and the production contract.
`assets/h5/engine.js` is the compiled offline engine; `template.html` is its UI.
Neither includes a real apartment's wall IDs, furniture positions, camera stops,
area figures or recorded approval quotes. Do not add a case migration back into
the engine. The existing approved case stays in its project folder.

`scripts/production/h5.py` is the local entrypoint. It does not call an image or
video provider, install dependencies, grant approvals, overwrite a nonempty run,
or publish anything. All file arguments below are placeholders to replace with
absolute local paths. Build and package need Python 3.11+ only.

```text
python scripts/production/h5.py doctor
python scripts/production/h5.py review-template --bundle PRODUCTION_BUNDLE --out NEW_REVIEW_DIR
python scripts/production/h5.py quality --bundle PRODUCTION_BUNDLE --review QUALITY_REVIEW --out NEW_QUALITY_DIR
python scripts/production/h5.py build --case CASE_JSON --out NEW_WORKBENCH_HTML
python scripts/production/h5.py export --html WORKBENCH_HTML --out NEW_EXPORT_DIR --node NODE --playwright-module PLAYWRIGHT_MODULE --browser CHROME
python scripts/production/h5.py prepare --bundle PRODUCTION_BUNDLE --out NEW_RUNTIME_DIR
python scripts/production/h5.py audit --runtime RUNTIME_DIR --tour TOUR_JSON --out NEW_AUDIT_DIR --node NODE --playwright-module PLAYWRIGHT_MODULE --browser CHROME
python scripts/production/h5.py capture --runtime RUNTIME_DIR --tour TOUR_JSON --out NEW_CAPTURE_DIR --full --node NODE --playwright-module PLAYWRIGHT_MODULE --browser CHROME
python scripts/production/h5.py handoff --directory DELIVERY_DIR --manifest HANDOFF_JSON
python scripts/production/h5.py package --directory DELIVERY_DIR --archive NEW_ZIP
```

Browser steps require existing Node.js, Playwright or Playwright Core, and a
Chromium executable. Configure flags or `FLOOR_VIS_NODE`,
`FLOOR_VIS_PLAYWRIGHT`, `FLOOR_VIS_BROWSER`; do not assume a global module or
download Chromium. Browser requests are confined to the local renderer server.
New artifact output remains pending human review. `--preview` allows an
unconfirmed preflight export/run; it never labels that output confirmed.

Read `h5-quality-gates.md` for the review contracts. Add `--subjects SUBJECT_PLAN`
to audit/run for a tour's viewing windows. Non-preview run also requires
`--quality-review REVIEW_JSON` with the current source review. Explicit accepted
handoff/package requires `--accepted --bundle BUNDLE --quality-review REVIEW_JSON`.
Default handoff/package is an unaccepted preview/file-integrity operation.

## Reusable homeowner camera

Read `homeowner-tour-method.md` before planning. `plan_route.py` produces the
case spatial path and visit markers; it does not interpret legacy `cameraKeys`.
Apply the public gaze stage explicitly after planning, using new case targets:

```text
python scripts/production/camera_gaze.py --tour PATH_TOUR --config CASE_CAMERA_CONFIG --output NEW_CAMERA_TOUR --retime
```

Start from `assets/h5/tour/camera-config-template.json` and the bundled
`homeowner-profile.json`. Exit 2 means measured motion exceeded review thresholds:
keep it diagnostic, adjust chapter timing/targets and re-run. The gaze stage alone preserves input frame times and positions; `--retime`
applies shared effort-based timing and updates visit markers. Neither is an
automatic room-target finder, mesh audit or comfort certificate. `--output` must be new.
Use the resulting tour for subject/body audit and short dynamic samples before
full capture. No new ad hoc camera implementation is needed for ordinary cases.

## Case contract

Copy `assets/h5/case-template.json` outside the Skill, then fill it after source
review. The blank template intentionally fails build: it cannot fabricate walls.

- `caseId`: unique stable namespace; `initialState.caseId` must match. Local
  browser storage, panel preferences and drawing modes are isolated per case.
- `model`: `width`, `depth`, `height` in mm, `footprint` polygon, `rooms` array.
  A room needs `id`, `name`, `poly`, and explicit `at:[x,y]` label position.
- `model.floorConnections`: optional reviewed input finish patches `{id,poly,materialRoomId}` assigned to an existing room, not extra rooms. Under default `floorBoundaryPolicy`, build normalizes wall/footprint overlaps and merges patches into that room, leaving normalized `floorConnections:[]`; plan, mesh and area use those same canonical polygons. Record source patches and merge/area evidence, count each floor region once, and keep source-labelled/ownership area separate from current net finish area. If normalization is explicitly disabled for a documented compatibility case, independent patches follow their owner material and contribute their area separately once. Neither mode authorizes inferred room merges; geometry changes invalidate finish approval.
- `initialState.rooms`: matching room IDs with `{name,mat}`. Floor material keys
  are `wood`, `walnut`, `tile800`, `tile600`, `marble`, `antislip`, `terrazzo`,
  `carpet`. Room names and materials are editable.
  For reviewed legacy peripheral finish strips, `floorBoundaryPolicy.retainConnections`
  names existing patches with `id,maximumWidthMm,reason`; those remain independently
  validated finish regions, not extra usable rooms. See `reference-case-upgrade.md`.
- `initialState.walls`: each `{id,a:[x,y],b:[x,y],t,height,bearing,demolished,
  opens:[]}`. Current H5 geometry supports orthogonal walls. Do not advertise
  diagonal-wall support. Protect documented structural walls; black marks alone
  are not engineering verification.
- An opening has `{id,kind,at,width,swing,hingeEnd,angle}` plus optional
  `sillHeight`, `height`, `entry`. `at` is measured along the wall start→end,
  not an absolute room coordinate. `hingeEnd` is `start` or `end`; `swing` is
  +1 or -1; `angle` is the opening extent in degrees (5–180, normally 90), not
  the current closed pose. `kind` is `door`, `sliding`, or `window`.
  `entranceOpenings` explicitly names entrance opening/wall IDs. The structure
  drawing keeps that door symbol and shows other doors as blank openings.
- `furniture`: stable `id`, `type`, `name`, `cx,cy,w,d,h,elevation,rot,color`.
  All sizes/positions are mm; `rot` is degrees. Optional `fitToCeiling`,
  `topToCeiling`, `mount`, `supportId`, `assemblyOwner`, `fixedToWalls`,
  `lightOn`, `lightTemperature`, `lightIntensity` carry actual object behavior.
  Inspect catalog keys through `window.homeStudio.getCatalog()`; hidden technical
  parts remain available to owned assemblies, not standalone clutter.
- `ceilings`: `{id,roomId,mode,drop,band}` and optional `poly` for local zones.
  Mode is `flat` or `perimeter`; finished height comes from the zone under the
  object, not a fixed 2750 mm room. Cabinet tops, curtains and recessed lights
  bind to that height. Lamp positions are explicit case data, not auto-generated.
- `doorStyles`: indexed by the workbench's opening key. Select a door in the
  workbench to edit single/double/sliding/hidden style, opening side and pose.
  Avoid creating duplicate door furniture. Slider leaves remain in their
  exported pose during replay; do not hide glazing to create a passage.
- `dimensionChains`: optional `top,bottom,left,right` arrays. Values sum to the
  respective width/depth; `dimensionChainStarts` permits a recessed exterior
  side to start below/after the bounding-box origin. Omit chains to show overall
  dimensions rather than invent source annotations.
- `areaMetadata`: `gross` requires a documented external source; `suite` is an
  explicitly described outline estimate. Room polygon areas are net floor
  estimates. Do not infer gross area by multiplying net area by an arbitrary
  factor. Unknown gross area displays an em dash. Pricing is excluded.
- `walkStart`: optional `{point,lookAt,eyeMm,roomId}`. If omitted, use a clear
  room landing; never reuse the example entrance coordinates. Tour stops belong
  in a separate tour config.
- `presentation.renderProfile.hiddenTypes`: presentation-only visibility.
  Optional `catalogHiddenTypes` and `editorHiddenTypes` override curation.
  Optional `render.shadowFixtureIds` limits costly shadow maps by actual IDs.
  `render.indoorShadowBudget` is 0 by default, 1 or 2 for a reviewed local-shadow
  trial; `render.indoorShadowMapSize` accepts 512 or 1024 (default 1024).
  `render.batchFurniture:false` opts out of opaque within-object batching.
  Rendering diagnostics expose `homeStudio.renderStatus()`; temporary
  `homeStudio.setShadowPreview(true/false)` does not change stored scheme data.
- `references.plan` / `references.furniture`: optional PNG paths relative to
  the case file. They are embedded into the HTML. No private case is distributed
  with the Skill. `referenceNote` explains case-specific resolutions.
- `productionApprovals`: empty for new cases. Approval scopes are content hashes
  plus provenance from explicit user confirmation. Never create an approval as
  a side effect of building, exporting or replaying a case.

## One-command production and recovery

```text
python scripts/production/run_production.py --engine h5 --bundle BUNDLE_JSON --config TOUR_CONFIG --out NEW_RUN_DIR --animation --node NODE --playwright-module PLAYWRIGHT_MODULE --browser CHROME --ffmpeg FFMPEG --ffprobe FFPROBE
```

H5 is the default. `h5.py run` also accepts an already reviewed `--tour` instead
of replanning. Use `--views` for explicit still cameras; view entries contain
`name`, `point`, `target`, optional `roomId`, `heightMm`,
`horizontalFovDegrees`, `shiftY`, `mustShow` and `size:[width,height]`.
Default output is 1280×720, eye 1600 mm, horizontal field of view 76°, no head
bob or synthetic handheld shake. These are starting points to review, not a
universal room-camera solution.

Route planning checks the supplied rooms/obstacles and approved entrance
approach polygons, smooths and samples the path, then computes motion audits.
Runtime `audit` additionally probes actual mesh clearance, required-object view
bounds, luminous faces and ceiling materials. Ray probes do not replace visual
review, prove a global shortest path or certify full solid-body clearance.

`capture` without `--full` produces one-second samples; with `--full`, every
frame. A full run encodes with FFmpeg and checks frame count/duration with
ffprobe. `capture --resume --range start:end` retains matching frames only when
scene, geometry, renderer, tour/views and mode fingerprints match. Changed
inputs require a new revision directory. A failed step preserves completed
outputs. Encoding never makes a deterministic preflight a Seedance final.

`--engine blender` retains the existing importer as an optional branch.
Blender consumes the same exported mesh stream; it does not establish a second
architectural authority. The older Blender flags remain available under that
engine. No Blender is needed for the H5 branch.

## Handoff

`handoff-template.json` contains relative `items` with `path,title,accepted` and
`acceptanceEvidence` for already accepted assets. The index displays confirmed
only when both the flag and evidence are present. It validates local file links;
it does not infer acceptance from filenames. Without a manifest, discovered
artifacts are marked pending. `package` excludes caches, adds per-file SHA-256,
creates a new ZIP outside the folder, and checks ZIP integrity. Do not use it to
overwrite an approved deliverable directory with a draft.

## Maintenance and verification status

`rebuild_h5.mjs` updates the compiled engine from bundled source using explicitly
supplied existing esbuild and Three.js module paths. Normal HTML building needs
neither npm nor esbuild. Three.js runtime and its license are included for replay.
Read `THIRD_PARTY_NOTICES.md` before redistributing inherited reference code.

The 2026-10-05 local closeout performed source syntax, CLI help, same-case HTML
construction, Skill structure and package-integrity checks. New-floorplan tests,
full regression, fresh end-to-end visual review of the generic engine, and
Seedance are deferred. Existing accepted case evidence is retained separately;
it does not prove the new generic template's portability or fidelity.

## Workbench beta.4 maintenance and evidence

- `assets/h5/version.json` is the shared build identity. HTML has the version in its header/body; `.build.json` contains engine, template, case and HTML hashes plus light checks.
- Rebuild regenerates `component-types.json`; unsupported furniture types fail before HTML generation. Normal build still requires only Python and the bundled assets.
- `presentation.materials.marble.veins` is boolean (default true). Set false for plain stone; both SVG and Canvas retain palette, grout and roughness. Production bundles preserve this configuration, and style scope hashes include it.
- Room `mainLightingRequired:false` exempts an explicit nonfunctional region. Build reports missing enabled main lights, lights outside/ambiguously inside room polygons and nonfollowing lights above flat finished ceilings. The report does not prove actual mesh emission visibility or brightness.
- Wall location, thickness, addition/removal or demolition invalidates original room partitions/areas. `homeStudio.areaStatus()` exposes changed wall IDs; a nonblocking notice remains until geometry is restored or a separately confirmed new partition is imported. Opening-only edits preserve the area basis. This release does not infer new room names or floor-material ownership.
- Runtime modules isolate pointer diagnostics, storage, labels, material presentation, area state and fixed spatial lighting. Existing source-maintenance dependency flags are unchanged.

Run `scripts/release_smoke.py --out NEW_EMPTY_DIR --node NODE_EXECUTABLE` for Python, subject and interaction module checks. With existing Chromium/Playwright, create synthetic fixtures with `scripts/production/synthetic_cases.py --out NEW_DIR`, serve that directory locally, then invoke `test_workbench_browser.mjs --playwright-module MODULE --browser EXECUTABLE --base-url URL --fixture-dir NEW_DIR --out NEW_REPORT_DIR`. It uses new isolated contexts; do not point it at a blocked user browser page as a workaround. The browser script emits screenshots, FPS and resource counts and tests export/reopen. Emulated touch is not physical-phone certification.

Independent HTML exports use a fresh document storage identity: first open reads the embedded seed, later opens restore edits from that document cache. New exports never borrow another document or the base case cache. Legacy exports without an identity keep their original seed behavior until re-exported with the updated engine. Local browser storage is origin/browser specific; exporting is still required to transfer new edits to another computer.

## Full-video preview gate

`h5.py run --config` now applies shared camera keys and timing automatically.
After dynamic diagnostic viewing, create a pending record with
`tour_tools.py review-template --tour TOUR --runtime RUNTIME --output REVIEW`.
Fill only actual viewing results and artifact hashes; no automatic approval.
Pass `--preview-review REVIEW` to `run`/`capture` before full production or HD
capture. Direct `h5_browser.mjs capture` enforces the same gate. For low-cost
full diagnostic capture use `--preview` and a runtime no larger than 1280×720;
its new output remains pending. Config-based planning/retiming changes the tour
hash: bind a new subject plan/review to the generated tour, then reuse `--tour`
for the reviewed production run. The initial failed run retains its generated
path, camera and reports for diagnosis; do not fabricate a passed review.

### Single wall-sliding leaf

A single opaque wall-side sliding door uses `kind:"sliding"`, `doorModel:"sliding"`,
`leaves:1`, `slideMount:"wall"`, `slideSide:-1|1`, `slideOverlap:0..100` (mm),
`slideDirection:-1|1`, and `slideOpen:0..1`. Side is relative to the wall's left
normal; direction follows wall start/end. The panel slides entirely beside the
opening, not inside a double-leaf stack. Check the wall-side parking strip,
handles and overhead track in the actual case; this does not create a wall pocket.
JS and Python use the same panel projection for plan, mesh and navigation.
Two/three-leaf aperture stacking remains unchanged. See `test_single_wall_slide.mjs`.

Style linkage: room `function` (bedroom/study/child/guest/living/dining/entrance/hall/closet/bathroom/kitchen/balcony) is authoritative over names. State rooms support `floorStyleMode:"follow"|"fixed"`, furniture `colorStyleMode:"fixed"`, wall faces `styleMode:"fixed"|"follow"`. These flags preserve explicit manual choices during style changes. `presentation.materials.wood.styleMode:"fixed"` retains exact embedded albedo color; omitted follows palette tint. Main fixture defaults are resolved with `defaultPlacement:"room-center"` and roomId only once, recorded as placementOrigin after resolution.

Fixed room floor finishes also persist `floorStyleId`, retaining palette and roughness in 2D/3D across later style choices, with independently cached floor materials and fixed SVG patterns. Switching back to follow restores current-style mapping.

Operable shower `showerDoor.width` is fixed leaf width in mm, independent of enclosure w/d. Legacy values resolve once to w−40; extra front width becomes fixed glass on latch side. Width must be finite, at least300 and no greater than enclosure w−40. This is concept geometry, not a product opening specification.

Vanity `basinLayout` stores width/depth (one bowl), count, gap (between bowls), alignment left/center/right, backGap and faucetInset in mm. Resolve once from legacy sizes; preserve through resize/export. Single/double count changes reinitialize to a fitting default. Local left/right follows object rotation. Python generation validation and JS plan/mesh share this contract. Independent kitchen ksink components are unaffected.

Bathtub `bathtubBody:{width,depth,alignment}` persists fixed physical body dimensions and local left/center/right position inside editable surround w/d. Resolve once from legacy body footprint. Surround must contain the fixed body. Python generation validation mirrors JS body geometry.

`floorBoundaryPolicy` controls orthogonal room/wall boundary normalization during H5 build (enabled by default; toleranceMm default120, allowed0–200). It merges explicit floorConnections into their materialRoomId room and emits normalized polygons plus `.floors.json` evidence. Repair does not move walls/openings/furniture. Large missing zones and ambiguous free overlaps require explicit input correction. Room net finish areas may update after removing wall overlap and including their former connection patches.
