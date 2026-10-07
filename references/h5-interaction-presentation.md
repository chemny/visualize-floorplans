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

Keep fixture lens appearance, authoritative scheme/exported illumination, and runtime approximation separate. Runtime fills have no local shadows. Use native display resolution and on-change rendering for performance. `render.performanceLighting=false` uses all original real-time fixtures for comparison. Check all group positions and intensities remain identical while traversing rooms and turning; verify explicit lamp switches and benchmark the host. New lighting visuals require case-level acceptance.

The lighting menu exposes day/night and sunlight time only. Remove the global fixture off toggle: normal viewing keeps fixture illumination enabled. Preserve case-level fixture configuration for scheme editing and exported provenance.

## Optional pointer lock diagnostics

Keep requestPointerLock synchronous with the user's click. Capture error name/message and focus, visibility, activation and API availability; preserve promise rejection details when the native error event also arrives. Hide the optional button after a confirmed refusal or missing API for the current session; focus/document-state errors may be retried. Keep drag, joystick and keyboard usable and avoid entry modals. Expose diagnostics through walkStatus without changing host permissions. A standalone browser result does not certify an embedded browser.

## Room area validity

Changing a wall's position, thickness, presence or demolition state marks current room/floor partitions and their area labels as original-reference data pending confirmation. Keep the visible warning synchronized after load/import, edit and undo. Opening-only changes do not change the room-area basis. Production export carries the same status. Do not automatically merge names/materials or pretend the old area describes the new partition.

## Case material presentation

Keep plain marble as `presentation.materials.marble.veins:false` in the case. Shared defaults may retain veins; do not hardcode a client's finish preference across all twelve styles. SVG and Canvas use the same setting; preserve base palette, grout and roughness. Bind the setting to style scopes and production output.

## Door, demolition and save editing

Door leaves are editable separately from structural apertures. Provide direct
selection with hinge/swing switches, door model and leaf deletion in the nearby
context menu on the right of the selected object when space permits. Do not put
these quick actions in the property form. Leaf deletion keeps an existing passage. Filling an aperture is a distinct action, allowed only on an
editable partition. Protect bearing/unknown wall geometry without preventing
ordinary door-leaf edits. Use actual plan-side hinge labels to avoid ambiguous
left/right handedness. Check the resulting 2D swing and 3D pose together.

Editable partitions support whole removal or full-height removal over an entered
along-wall range. Cuts cannot truncate a window/door aperture; include it fully
or choose a separate span. Preserve source wall IDs and removal intervals for
undo/export; omit removed geometry and red demolition traces from the current
plan and 3D. Put whole-wall deletion in the selected wall context menu. Use shared undo/redo,
not per-wall restore buttons. Structural or
unknown walls stay protected until their classification is evidenced.

Keep Save in the top-right navigation, independent of sidebar visibility. Show
last successful save time beside the bottom-right saved status; preserve that
time across refresh instead of substituting the refresh time. Errors must remain
explicit. Browser-local save is not cross-device storage or approval
of the design. Retain downloadable JSON/HTML handoff. Partial removal invalidates
room-area/finish partition status just as whole removal does.


## Concise Chinese room names

Keep Chinese room and passage display names at most three characters across 2D,
3D, the room list and exported scheme. Use familiar distinct names such as 主卧,
次卧, 书房, 客厅, 餐厅, 卫生间, 厨房, 过道, 阳台 and 飘窗. Do not turn
labels into functional descriptions or truncate long text blindly. Select a
semantically clear short name; retain dual-use roles and access relationships in
case `functionNote` or the design brief, rather than appending them to the label.
Keep stable room IDs, source geometry, room areas and furniture relationships.
Synchronize model and state names and verify daily/guest scheme variants.
Run `scripts/validate_room_labels.py CASE.json` before building Chinese case
previews. This is a case generation check, not a three-character limit on English
translations or on detailed design explanations. No automatic room renaming is
introduced on load/import: existing user data needs an explicit migration.


## Compact menus and component insertion

Use short action labels; explain consequential distinctions in tooltips. Door
“删除” removes the leaf and preserves its aperture. Keep browser Save distinct
from Download Workbench, and preserve the successful save timestamp. Put Copy
before Delete for furniture/decor; reuse the existing duplicate and undo pipeline.

In 2D, right-click on empty plan space offers a curated common-component list
and More Components; object/wall clicks offer permitted context actions. The
common list is a product default, not usage-frequency evidence. Convert client
coordinates through the current SVG transform and reuse catalog insertion.
Retain structural protection. Do not introduce a context menu in walk mode.
Clamp the menu to viewport edges; close on outside click, Escape, resize and zoom.
Exclude transient menus from portable HTML exports.

More Components explicitly opens the furniture pane and selects its furniture
page; it must not toggle an already-open pane closed. Verify narrow-window drawer
classes and desktop pane state, including return from the styles page.

Keep the library compact with readable names/dimensions, reduced whitespace and
responsive width rules placed after competing rules. Specific pixel widths are
presentation defaults, not case geometry. Verify visible and collapsed states.

## Editable wall decoration

Keep wall paintings in a discoverable decor catalog category. A wall-mounted
decor item remains furniture/decor for display and selection; mounting on a wall
does not make it a hidden construction detail. Show its footprint in furniture
layout mode and its complete model in 3D. Reuse object insertion, size/elevation,
rotation, copy/delete, undo and persistence. Verify catalog visibility, existing
instances and insertion in the actual rebuilt workbench. Room count, painting
positions and dimensions stay in case data.

## Dimension presentation

Use integer millimetre labels without rounding saved geometry. In furniture
presentation, keep dimension annotations outside the plan, use a consistent font
and merge short adjacent spans while preserving endpoints and total length.
No unsolicited diagnostic prose is drawn on the canvas. Preserve source/model
uncertainties in case provenance/review. Diagram cleanliness does not certify
source dimension closure. Internal technical dimensions belong to a separately
requested detailed drawing, not the default furniture view.

## Furniture alignment

In 2D, Shift-click adds/removes furniture from a transient selection. Multi-selection
commands belong in the object quick menu and its right-click mirror, not the property
form. Edge and centre alignment use the first selected item as anchor. Equal spacing
uses rotated footprint edges, preserves the two endpoints, and requires three items.
Drag snapping displays temporary guides at a fixed screen-distance threshold; Alt
bypasses snapping. Keep generated assembly children attached to their owners. Each
group operation is one undo step and edits canonical scheme coordinates for 3D and
project saving. Reject newly increased wall/furniture penetration; this footprint
check does not replace doorway, circulation or ergonomic layout review.
