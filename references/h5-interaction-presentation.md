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
- Do not add per-room walk teleports or duplicate room navigation lists. Room
  label focus stays in bird's-eye/orbit mode; walk remains an explicit action.
  Keep bird's-eye room area statistics and editable 2D room properties.

## Room annotations

- Bird's-eye only, enabled by default with a display switch. Use one compact
  line: name plus area to one decimal; detail statistics keep two decimals.
- Use the same room polygons as 2D for area. Do not modify polygons or stored
  label anchors just to improve presentation.
- Use intrinsic width with a readable single-line hit area (at least 32px high),
  subtle warm translucent background and faint border. Avoid large two-line cards.
- Choose an anchor inside each room, preferring empty floor around the supplied
  anchor. Project above the selected wall cut like the reference UI.
- Measure rendered label sizes for collision handling. On zoom-out hide area
  first, then omit overlapping labels or those outside the viewport.
- Recompute anchors after furniture placement changes. Validate rotation,
  zoom-out, display toggles and night readability with actual screenshots.

## Room label focus and return

- Make the entire label capsule clickable, including name, area and padding.
  Override competing pointer-event rules at the final CSS specificity; use a
  pointer cursor and visible hover/keyboard focus. Child text must not shrink the
  parent hit target. Support Enter/Space and a separate accessible exit button.
- Click a label (or double-click visible empty room floor) to smoothly focus the
  orbit camera on that room's geometry. Keep bird's-eye mode, ceiling/cut state,
  lighting and scheme data unchanged. Never implicitly enter walk mode.
- Show “×” beside the focused room's label only. Stop its click/key propagation
  so closing cannot trigger focus again. Keep its own pointer events enabled,
  even when label text ignores pointer events. Prioritize this label during
  decluttering so another label cannot hide the exit control.
- Capture the pre-focus whole-home pose once. Switching focused rooms must not
  replace that return pose. Closing restores it and removes focus state; a later
  focus starts a new session. Respect reduced motion for focus and return.
- Test the final runtime camera function, including later wrappers, rather than
  only the first function declaration. Check stylesheet precedence, whole-label
  hit areas, focus A → B → exit, repeated exit, mode guards, keyboard behavior
  and generated single-file HTML. Logic tests are separate from browser review.
  Do not copy reference-apartment coordinates, room IDs or furniture into defaults.

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

Run isolated UI tests in a fresh browser context; a separate test case namespace
is optional for synthetic fixtures. For a user-facing UI-only upgrade with the
same scheme baseline, preserve caseId/storage identity and the entry origin so
saved edits remain available. A new filename or UI version alone is not a reason
to reset that identity. Retain the original workbench for rollback; file-origin
upgrades also need the persistence checks in workbench-reliability-rules.md.
Check desktop/touch controls, native lock and rejection, mode return, exported
HTML reopening, labels and case-data equality. Record technical results separately
from human approval. Do not inherit acceptance of a new UI or rebuild a video as
a side effect.

## Stable illumination and performance

Room illumination must stay on independently of camera position, distance, view direction and mode. Do not allocate a moving subset of active lights. All enabled fixture records contribute to permanent spatial fill groups anchored at each main light; secondary lights join the nearest main in the same room. Rebuild groups only when fixture geometry changes; explicit switches, intensity, color and day/night update cached contributions. No camera-driven brightness fades.

Keep fixture lens appearance, authoritative scheme/exported illumination, and runtime approximation separate. Runtime fills have no local shadows. Use native display resolution and on-change rendering for performance. `render.performanceLighting=false` uses all original real-time fixtures for comparison. Check all group positions and intensities remain identical while traversing rooms and turning; verify explicit lamp switches and benchmark the host. New lighting visuals require case-level acceptance.

The lighting menu exposes only day/night (日照 / 夜景), with no time slider or hour label. Retain sunlight time as internal case configuration, not a menu control. Normal viewing keeps fixture illumination enabled; do not add a global fixture-off toggle. Preserve case-level fixture configuration for scheme editing and exported provenance.

## Optional pointer lock diagnostics

Keep requestPointerLock synchronous with the user's click. Capture error name/message and focus, visibility, activation and API availability; preserve promise rejection details when the native error event also arrives. Hide the optional button after a confirmed refusal or missing API for the current session; focus/document-state errors may be retried. Keep drag, joystick and keyboard usable and avoid entry modals. Expose diagnostics through walkStatus without changing host permissions. A standalone browser result does not certify an embedded browser.

## Room area validity

Changing a wall's position, thickness, presence or demolition state marks current room/floor partitions and their area labels as original-reference data pending confirmation. Keep the visible warning synchronized after load/import, edit and undo. Opening-only changes do not change the room-area basis. Production export carries the same status. Do not automatically merge names/materials or pretend the old area describes the new partition.

## Case material presentation

Keep plain marble as `presentation.materials.marble.veins:false` in the case. Shared defaults may retain veins; do not hardcode a client's finish preference across all twelve styles. SVG and Canvas use the same setting; preserve base palette, grout and roughness. Bind the setting to style scopes and production output.

## Optional photographic wood floors

The generated 3D workbench supports two bundled straight-laid wood albedo options:
`presentation.materials.wood.texture: "oak-straight"` and
`presentation.materials.walnut.texture: "walnut-straight"`.
They apply only to rooms/connections already using `wood` / `walnut`; do not
change room materials or geometry to force a texture. Omitted, `procedural` or
unknown choices retain the style's procedural floor and palette. These are
optional image finishes, not a universal colour preference or a herringbone rule.
Record an explicitly selected finish in the case before building. The 2D schematic
retains its material symbol; it is not a photographic render. Existing concept
images and videos require their own regeneration/review.

Embed the compressed JPEGs inside the standalone HTML; no remote service or
provider key is required. Decode only selected finishes and cache one material
per kind. Repeat by physical tile size (2.4 × 1.08 m for these assets), use sRGB
for albedo and cap texture anisotropy at four without reducing renderer DPR.
Keep the procedural fallback visible during loading and after decode failure.
Invalidate on completion, dispose replaced fallback textures, and discard late
callbacks for retired materials during style changes. Newly loaded finishes need
actual visual/performance review; unit and build passes do not provide it.

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

When migrating an accepted styled case, regenerate with the installed engine and
preserve its case material/door fields; do not copy an older standalone engine.
French `french_panel` wall finishes are surface compatibility, not a furniture
geometry change. On-change rendering must invalidate after label visibility
changes (including the final 2D→3D transition); otherwise built labels can remain
absent from the DOM. Source-function tests are not evidence of a delivered HTML
click working. Bind browser findings to the final HTML and build engine/template
fingerprints, and repeat a label A→B→exit plus top off→on→off on that artifact.

For final-artifact browser regression, run `scripts/test_generated_workbench_browser.mjs
HTTP_URL REPORT.json` with `INTERIOR_PLAYWRIGHT_MODULE` and `INTERIOR_BROWSER`
pointing to existing installations. It checks actual pointer hits, label A→B→exit,
top off→on→off, camera return and scheme preservation. Keep its report bound to
the delivered HTML fingerprint; it does not provide visual or device acceptance.
Use `scripts/workbench_browser_suite.py --case CASE --out NEWDIR --checks core`
for the shared build/serve/browser entry, with existing Node, browser and
Playwright paths as needed. Its isolated tests and final-artifact evidence follow
the Source freshness and final-artifact verification section in
`workbench-reliability-rules.md`. Missing checks remain unexecuted, not accepted.

## Compact object editing and persistent history

- Door actions stay in the near-object floating menu. Use a compact single-row toolbar with down-arrow dropdowns for type, hinge, direction, preset angle and material; keep deletion visually distinct at the end. Expand only the requested dropdown, clamp it within the work area and flip upward near the bottom. No permanent three-row property panel or redundant labels. Show only operations meaningful for the mechanism. Clamp the menu inside the work area and keep CSS2D labels below it.
- In 2D, a protected wall uses the plain label “实体墙” without a lock icon; its full unknown/load-bearing reason may remain in a tooltip. Hide its impossible delete action. In 3D orbit, protected walls are inert occluders: no selection, popup or picking through them. Never imply an unknown wall has been professionally identified as load-bearing.
- Keep undo/redo visible before Save in the top navigation in 2D and 3D orbit, using the same icon-only button geometry as the neighboring furniture/properties/fullscreen controls; Save is icon-only too. Preserve aria-labels and hover titles. Disabled history buttons retain readable outlines instead of near-zero opacity. Existing Edit menu/shortcuts remain. Disable when history is empty or editing is unavailable. A drag, deletion, mechanism edit or applied size form is one transaction. Undo/redo must restore the complete scheme and actual mesh; camera navigation is not an edit transaction.
- Furniture quick actions include “尺寸”, except shower quick menus; showers retain 2D resize handles and property editing. Its compact width/length, depth and height form works in 2D and orbit, has explicit Apply/Cancel, integer mm and validated bounds, and reuses existing commit/undo. Cabinet width is labeled length consistently in this form and the sidebar. Cancel/no-op must not create an edit; changing length must not silently change height/fitted-ceiling settings or material. Derived trim parts redirect to their owner rather than resizing independently. Keep the existing 2D handles; this entry does not add 3D resize handles.
- Use `scripts/test_editor_usability_browser.mjs HTTP_URL REPORT.json` against the final generated artifact: actual menu clicks, finish disclosure, short lock notice, size apply/cancel with actual mesh extent, undo/redo of resize and deletion, complete scheme restoration, and narrow-screen fit. Existing room focus/top fixture and shower browser regressions still apply. Browser tests run in isolated storage using existing dependencies, not the user's saved tab.

### Compact connected door menu
Use one shared toolbar surface with thin separators: 门型、铰链、方向、角度、材质、删除. Dropdowns use short pure-text rows without icons/checkmarks; selected rows use a background and aria-pressed. Keep popup width content-sized (64–100px), one open at a time, clamped to stage. Door labels: 平开、侧滑、推拉、对开、隐形、无门. Angle UI offers 60/90/110/135° presets only; opening a menu must preserve existing custom approved angles. 材质 offers 实心、玻璃、磨砂. Do not expose trim/threshold/transition controls or opening-dimension forms in this compact menu; preserve their saved values. Retain mechanism-specific slider actions and header undo/redo/save icons.

Lighting quick menu exposes only 日照 / 夜景. Do not show time sliders or hour labels in viewport or View menu. Preserve existing daylight-hour configuration internally and keep lighting-mode changes independent of furniture/layout.

Lighting dropdown: content-sized narrow panel (64px), 日照 above 夜景 as two vertically stacked text rows, matching compact door dropdown styling.

Whole-house camera presets: one compact dropdown, default summary 全屋, vertically stacked 全屋 / 俯视. Selecting updates summary and selected row, closes popup, restores whole-house camera framing without modifying scheme; retain room-focus exit and other toolbar actions. Match narrow lighting popup styling.

Library presentation: omit long instructional paragraphs and optional badges from component cards. Do not offer utility-point components (laundrypower/waterinlet/drainoutlet) for insertion; retain saved-plan rendering compatibility. In 2D, the protected-wall context label is plain 实体墙 without a lock icon; structural edit permissions remain unchanged. In orbit, use the inert-wall behavior below.

Orbit interaction: structural/unknown protected walls (`bearing`) are inert occluders: clicking them must not select the wall, show a context tip/property form, or pick objects behind it. Do not alter door/opening selection or ordinary partition selection. Clear any protected-wall selection carried over from 2D when entering orbit; retain 2D inspection and structural restrictions. No orbit 实体墙 tooltip is shown.

Shower selection uses compact connected toolbar and narrow text dropdowns for 淋浴门 (打开/关闭) and 铰链 (左侧/右侧). No angle input or explanation text. Preserve rotate/copy/delete and the saved shower angle; the quick menu has no dimension shortcut, while 2D resize handles and property editing remain available. Do not change the saved angle merely by selecting the fixture.
Default main lamps use each actual room polygon center, never its text-label `at` coordinate. Generation can mark `defaultPlacement:"room-center"` with roomId; h5 build resolves the anchor. Manual lamps remain unmarked and retain positions. Irregular-room centers must lie inside the polygon.

Style application uses room function/usage/role, stable room IDs, then display-name aliases; renamed child/guest/dining/living zones must remain classified. Public floors use livingKind; bedrooms/closet use woodKind; wet-room types remain case materials. Explicit floorStyleMode=fixed, colorStyleMode=fixed and wallFinish.styleMode=fixed preserve manual choices. Room floor follow/fixed is visible in room properties; manual floor/color/wall finish edits set fixed. Unmarked imported wall faces follow the next explicit style choice, not initial loading. Embedded wood albedo retains grain but is palette-tinted unless presentation.materials[kind].styleMode=fixed. Style choice changes finishes, never furniture/door geometry. Descriptions must match actual flooring pattern. Shower quick menu omits the furniture dimension shortcut.

Resizing an operable shower changes its enclosure only. Persist showerDoor.width as actual leaf width (legacy initialization w−40 mm). Keep leaf width independent of enclosure width/depth; fill extra front width on latch side with fixed glass and a jamb, using identical SVG/3D/collision/use-review segments. Clamp drag width to leaf width+40 mm and depth to500 mm; numeric edits below that minimum reject rather than shrink the door. Open/close, hinge flip, undo/export retain leaf width.

Vanity resize preserves basinLayout bowl width/depth and group spacing. Extra size extends cabinet/countertop only. Water-bowl alignment offers 居左/居中/居右 in a narrow dropdown; bowl, matching countertop holes, drain and faucet share local coordinates in SVG and mesh, including rotation. Depth resizing retains back-edge offsets. Persist basinLayout; clamp drag to its minWidth/minDepth and reject undersize numeric edits. An explicit single/double basin count change may establish new bowl defaults; plain resizing must not.

Bathtub resize preserves bathtubBody.width/depth; the editable w/d footprint grows a surrounding deck, never scales the original shell, cavity or faucet assembly. 缸体 dropdown offers 居左/居中/居右 in local object coordinates. Plan and mesh share body offsets; clamp drag and reject numeric footprints smaller than the body. Preserve the original bathtub mesh/style and undo/export metadata. No bathtub is added to a case solely to enable this component behavior.

Header sidebar toggles: left-panel icon lives immediately after the brand/version, right-panel icon is the last header action after fullscreen. Use matching rectangular panel glyphs with left/right divider, no visible text. Active fill/background plus aria-expanded and dynamic 展开/收起左栏/右栏 labels represent state. Left toggle preserves the selected furniture/style library page rather than switching to furniture. Retain existing shortcuts and history/save actions.

Explicit sidebar open/close actions persist as UI preferences (pinLib/pinPanel alongside hide flags). Canvas pointerdown, object actions, drag-out and crossing the1100px breakpoint must not dismiss a manually opened pane. Only that pane’s toggle, close button, shortcut or explicit restore-layout action changes its manual intent. A temporary unpinned drawer may still close. Preserve selected library page and correct aria-expanded across2D/3D and responsive transitions. These UI preferences never alter the scheme or furniture.

### Product-facing copy
Do not surface build/review notes, engine compatibility wording, old-video acceptance state, commit IDs or prototype labels in the normal workbench. Preserve original source attribution in References/About; source commit may remain in collapsed About details. Remove component initial/default/design-range explanations from property panels without weakening validation. Keep current dimensions, units, save time/scope, disabled-action reasons and recovery errors. Installation notes are short, optional details. Room geometry edits retain a concise stale-area warning. Keep operation help current with actual UI positions and behavior; no repeated instruction paragraphs in ordinary panels. Stage confirmations and production bundle export live under File → Advanced. UI-only revisions retain caseId/storage identity so saved layouts and material choices load unchanged.
