# Structured H5 production workflow

For every homeowner route or video, first apply `homeowner-tour-method.md`: reuse the accepted subject-key camera method and profile, fill case targets, and review dynamic samples before full capture.

Read `h5-quality-gates.md` for mandatory source calibration, AI reference/camera
consistency, subject time-window checks and accepted-delivery gates. A raw
preflight can complete with reported visual failures; formal delivery cannot.

For shared drawing visibility, installation and lighting checks, homeowner
camera planning, and accepted-package closeout, read
`h5-acceptance-and-handoff.md`. A verified deterministic H5 replay and an
unverified generative final are separate stages.

## Authority and stages

1. Start from the original floor plan. Furniture/style references are optional;
   when absent, propose layout and style using `guided-user-workflow.md`.
   When supplied, review references together. The plan controls structure;
   furniture references suggest placement. Record
   conflicts and accepted resolutions. Unlabelled dimensions/ceiling heights are
   assumptions. Black drawing marks do not certify engineering bearing status.
2. Establish the scheme in the H5 workbench starting at plan confirmation.
   Refine that same data through furniture and style decisions; export structure
   and furniture drawings from its current state, never redraw them independently. Confirm structure, furniture layout,
   and style separately against content hashes. Reuse an existing recorded user
   approval only for the unchanged displayed scope. Node replay of delivered
   defaults must identify itself; it is not the user's unsaved browser state.
3. Export a production bundle with millimetre geometry, openings, furniture,
   finishes, actual Three.js vertices/UV/materials/textures, scheme hash and
   approval evidence. Exclude price data. Exporting a scheme does not approve
   renders that have not yet been shown. Supply editable SVG + PNG for plan and
   pre-render furniture layout only. Other presentation images are PNG/JPG.
4. Generate interior renders from the same geometry. Blender can import the
   actual mesh stream with `scripts/production/import_blender.py`. Record object
   parity, heights and camera coordinates. Rendering lights and color management
   may differ from the workbench and must be documented. Detailed mesh upgrades
   replace objects by stable ID while preserving footprint/height/placement.
   AI renders are a separate optional enhancement; label them conceptual and
   visually check geometry drift before accepting them as downstream references.
5. Plan a route with explicit case stops using
   `scripts/production/plan_route.py`. Check room coverage, body clearance,
   openings, frames and motion. Windows are never traversable. Dead ends may need
   a necessary return; do not claim a global shortest route without proving it.
   Smooth paths must be collision-checked after smoothing. Use arclength-based movement
   and continuous rotations, not a pause at every turn. If the agreed duration
   forces high speed, report it rather than misrepresenting comfort.
   Apply `camera_gaze.py` to the planned path using case `cameraKeys`, following
   `homeowner-tour-method.md`. Reuse the accepted profile; first render difficult
   turn samples and a complete low-cost dynamic preview. Subject checks, motion
   review and actual playback must pass internally before full-resolution capture.
6. Generate the requested final video after preflight review. A Blender animation
   is deterministic geometric playback. Seedance is a generative video branch:
   verify current API/model limits, locally configured credentials, costs and
   reference support before use. Never expose API keys. A tool/credential gap
   blocks that branch and must be reported. Do not silently substitute a Blender
   preview for an approved photorealistic Seedance final. FFmpeg handles encoding,
   sound and assembly; stitched generative segments are not guaranteed continuous
   geometric walkthroughs.

## Invalidation and records

- Structure → invalidates all dependent layout/style/renders/routes/video.
- Furniture geometry → invalidates layout/style/renders and collision checks.
- Materials/colors → invalidates style/renders/video references; geometry route
  may be retained only after confirming that its geometry hash is unchanged.
- Keep bundle hash with every render, Blender scene, route and report. Do not
  reuse a file merely because its filename contains the newest version number.
- Keep case stops, palette selections, dimensions and source image coordinates
  in the case folder, not hardcoded into shared workflow rules.
- Separate automated pass, internal visual review and human acceptance. Record
  completed, failed, unavailable and awaiting-review stages honestly.

## Execution

The base Skill does not require Blender or Node. These are optional existing
runtimes for the structured branch; check local availability without installing
anything by default. Use the bundled `scripts/production/h5.py export` for actual mesh/texture
capture; H5 playback, optional Blender and route tools consume that same bundle.
Read `h5-tools-and-case-schema.md` for the generic template and unified CLI.

Example argument shape (substitute real paths; invoke tools directly):

```
python scripts/production/plan_route.py --bundle production-bundle.json --config tour-config.json --output tour.json
blender --background --python scripts/production/import_blender.py -- --bundle production-bundle.json --route tour.json --out renders --stills --animation
```

The config contains explicit `stops` (`name`, `point` in mm), duration/fps, body
clearance and approved access polygons. External access polygons must describe
only the entrance approach, not invented connections between rooms. The importer
packs textures in the saved `.blend`. Balcony/other sliding leaf animation must
be parameterized by exported opening metadata; do not hide unrelated glazing.

After planning, create a case-local subject plan with explicit observation
windows and main object IDs. Bind it to exact tour bytes, and run
`h5.py audit --subjects ...` before full capture. Use `--preview` for diagnostic
work on an unaccepted or failed camera plan. For non-preview H5 production,
provide `--quality-review` with a current accepted source stage and, for animation,
`--subjects`. New images/video still require their own visual review and approval.

## One-command local replay

`scripts/production/run_production.py` runs H5 by default with existing
runtimes; `--engine blender` explicitly selects the optional Blender branch. It refuses a nonempty output directory, stale confirmations and price
fields. Pass `--bundle`, `--config`, optional `--views`, `--out`, and `--animation`.
For H5, also pass the existing Node, Playwright module and Chromium paths.
An already reviewed tour can be supplied through `h5.py run --tour`.
Override executable locations with `--blender`, `--ffmpeg`, `--ffprobe` when
needed. It checks the encoded video frame count and duration with ffprobe.
Human acceptance of new renders/video remains separate. This CLI never sends a
Seedance request or labels Blender preflight as generative final video.

The optional views file contains `{name, point:[x,y], target:[x,y]}` records in
millimetres. Route stop records can include `roomId` and `lookAt:[x,y]` to direct
camera gaze at actual room furniture while movement continues. Solid walls
occlude those gaze targets. `maxYawDegreesPerSecond` limits head turns and
`exitLookAt` keeps the final view on the home while leaving. `roomSpeedWeights`
can allocate more time to compact rooms; blend the transitions and keep positive
movement rather than inserting stationary holds.
