# H5 interaction and room annotations

Read for workbench UI maintenance. These are presentation defaults, not case
geometry or a new production stage.

## Walk controls

- Enter walk directly with drag-to-look, keyboard movement and the bottom-left
  joystick on both desktop and touch. Do not add an entry or resume modal.
- Keep WASD/arrows, E for the facing door, Esc to pause and Space/canvas/joystick
  to resume. Inputs keep their normal keyboard behavior.
- Native pointer lock is optional and needs an explicit click. Locked movement
  uses the keyboard; Esc releases and pauses, restoring the joystick. A rejected
  lock resumes drag controls with a nonblocking notice. Never request lock again
  just because the user clicked the scene or resumed walking.
- Walk temporarily hides header, rails, sidebars, room HUD and bird's-eye tools.
  Do not overwrite stored editor pane preferences. Return restores them.
- A small toolbar provides return, day/night, fullscreen, optional mouse lock,
  and collapsed settings/help. Fade it during use; keep joystick and short footer
  hint available. Preserve keyboard focus and open settings/help.
- Joystick capture must not rotate the camera. Release recenters it and smoothly
  stops movement; pause/blur clears keys and velocity.
- Do not add per-room camera jumps or duplicate room navigation lists. Keep
  bird's-eye room area statistics and editable 2D room properties.

## Room annotations

- Bird's-eye only, enabled by default with a display switch. Use one compact
  line: name plus area to one decimal; detail statistics keep two decimals.
- Use the same room polygons as 2D for area. Do not modify polygons or stored
  label anchors just to improve presentation.
- Use intrinsic width, about 24px height, subtle warm translucent background,
  faint border and no shadow. Avoid large two-line white cards.
- Choose an anchor inside each room, preferring empty floor around the supplied
  anchor. Project above the selected wall cut like the reference UI.
- Measure rendered label sizes for collision handling. On zoom-out hide area
  first, then omit overlapping labels or those outside the viewport.
- Recompute anchors after furniture placement changes. Validate rotation,
  zoom-out, display toggles and night readability with actual screenshots.

## Imported-case preservation

A presentation-only migration must compare its scheme with the original case.
Two optional case-level settings preserve older explicit details:

- `presentation.preserveImportedDetailModels`: do not force an existing bed to
  the engine's current detail model. Explicit model markers are still honored.
- `presentation.preserveImportedOpeningTrim`: retain supplied window trim height
  and elevation while its opening kind/position/width/height/sill stay unchanged.
  Actual opening edits use the current derived trim rules.

These flags contain no apartment IDs or measurements. They belong to the
imported case; do not change new-case geometry to match an old case.

## Verification and acceptance

Use a separate case namespace and a new HTML path for UI previews. Preserve the
formal workbench and pre-change Skill files. Check desktop/touch controls,
native lock and rejection, mode return, exported HTML reopening, labels and
case-data equality. Record technical results separately from human approval.
Do not inherit acceptance of a new UI or rebuild a video as a side effect.

## Stable illumination and performance

Room illumination must stay on independently of camera position, distance, view direction and mode. Do not allocate a moving subset of active lights. All enabled fixture records contribute to permanent spatial fill groups anchored at each main light; secondary lights join the nearest main in the same room. Rebuild groups only when fixture geometry changes; explicit switches, intensity, color and day/night update cached contributions. No camera-driven brightness fades.

Keep fixture lens appearance, authoritative scheme/exported illumination, and runtime approximation separate. Runtime fills have no local shadows. Use adaptive resolution and other rendering optimizations for performance. `render.performanceLighting=false` uses all original real-time fixtures for comparison. Check all group positions and intensities remain identical while traversing rooms and turning; verify explicit lamp switches and benchmark the host. New lighting visuals require case-level acceptance.

The lighting menu exposes day/night and sunlight time only. Remove the global fixture off toggle: normal viewing keeps fixture illumination enabled. Preserve case-level fixture configuration for scheme editing and exported provenance.

## Optional pointer lock diagnostics

Keep requestPointerLock synchronous with the user's click. Capture error name/message and focus, visibility, activation and API availability; preserve promise rejection details when the native error event also arrives. Hide the optional button after a confirmed refusal or missing API for the current session; focus/document-state errors may be retried. Keep drag, joystick and keyboard usable and avoid entry modals. Expose diagnostics through walkStatus without changing host permissions. A standalone browser result does not certify an embedded browser.

## Room area validity

Changing a wall's position, thickness, presence or demolition state marks current room/floor partitions and their area labels as original-reference data pending confirmation. Keep the visible warning synchronized after load/import, edit and undo. Opening-only changes do not change the room-area basis. Production export carries the same status. Do not automatically merge names/materials or pretend the old area describes the new partition.

## Case material presentation

Keep plain marble as `presentation.materials.marble.veins:false` in the case. Shared defaults may retain veins; do not hardcode a client's finish preference across all twelve styles. SVG and Canvas use the same setting; preserve base palette, grout and roughness. Bind the setting to style scopes and production output.
