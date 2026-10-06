# beta.5 local collision and rendering checks · 2026-10-06

Scope: shared source and isolated synthetic fixtures on macOS/Chromium. No actual
client-apartment browser inspection, embedded pointer-lock approval, Windows
WebGL or physical phone certification. Current workbench is a rebuilt preview,
not fresh human visual acceptance. No Git commit/push/release performed.

## Changes and checks

- Furniture vertical-overlap collision: 700 mm hanging cabinet at elevation
  1300 mm blocks a 1600 mm eye-height walk; elevation 1800 mm remains clear.
  Ground placement blocks as before; rotated footprints and taller users are
  included in module tests. Decorative exclusions remain approximate.
- Opaque furniture batching stays inside the same ID/body/material. In a
  synthetic rectangle actual production export, before/after state is equal;
  per-object triangle count, world bounds and surface area agree within
  0.01 mm and 1e-5 square metres. Export mesh count 41 → 35.
- 108-chair pressure fixture: 1147 → 391 main-frame draw calls (756 saved,
  approximately 66%), unchanged 397678 triangles and unchanged height audits.
  Settled idle scene: 0 repeated renders in 3 seconds versus 181 before.
  Actual camera translation, 30-second same-browser checks: approximately
  56.7 rendered FPS before and 59.3 after. FPS is machine/workload-specific;
  requestAnimationFrame callbacks are not counted as rendered FPS.
- Final 1024-pixel, two-light shadow trial: 1790 actual renders in 30.0055
  seconds, approximately 59.7 FPS, 391 draw calls. Shadows stay on fixed IDs;
  all other fixture fills remain permanently enabled.
- 100 alternating furniture/floor edits: geometries 35 → 35, textures 5 → 6
  (second floor material cache populated). No monotonic geometry growth shown;
  this is not an hours-long heap or GPU leak certification.
- Source regression: 168 Python tests, 8 subject checks, 27 interaction/module
  checks. Isolated rectangle/concave/stress and emulated touch cover 57 browser
  assertions including hanging-cabinet collision, batching dimensions,
  shadow budget, idle rendering, lighting continuity and export/reopen.

## Visual decision and case boundary

Local indoor shadows improve desk-under and rear contact depth, but a synthetic
wall edge still shows fine banding. Keep indoor shadows disabled by default;
use temporary shadow previews or an explicitly configured budget of 1–2 for
case-specific review. Do not enable all fixture shadow maps or revive a lamp UI
switch. The lamps themselves remain always on.

The bundled workbench is rebuilt from its unchanged case input using beta.5.
Its case/scheme, supplied inputs, accepted AI image bytes, older drawings,
compressed source mesh and video stay unchanged. Media re-export is deferred
by the user's instruction. Index/manifest explicitly retain the source-version
differences; no old acceptance is transferred to the new rendering.

Detailed diagnostic snapshots and pre-change backup remain in the user's
external project workspace, not inside the curated reference case.

## Native-resolution follow-up

The user subsequently requested removal of resolution reductions. Native display
pixel ratio now applies to initialization, movement, idle and slow frames, even
when fixed lighting is disabled; moving the window to a different-DPR display
updates that ratio. There is no DPR2 cap. Earlier FPS/resource measurements above
used the then-current adaptive resolution and must not be presented as current
native-resolution performance. Geometry/batching and on-change rendering remain.

Native-resolution follow-up checks passed: 168 Python, 8 subject, 29 module and
60 isolated browser assertions. DPR2 is retained in idle and moving synthetic
rectangle/concave/stress fixtures. Module checks also cover slow frame intervals,
DPR3, fractional display changes and original-lighting opt-out. Native buffers on
physical multi-monitor systems remain unverified; no actual client-page browser
inspection was performed. Existing media remains unchanged.

## Black cuts and ceiling diffuser follow-up

Wall-cut material is unlit black (#111111), independent of day/night exposure.
Round/square/panel ceiling lamps have luminous outer diffusers and use fixed
omnidirectional runtime lights positioned at the diffuser center. Other lamp
types retain their directional behavior. Spatial light-group count is unchanged;
optional point-light shadows cost six faces, so shadows remain off by default.
Native pixel ratio and always-on illumination are preserved.

Local source regressions and rectangle/concave/stress browser checks pass.
Synthetic checks verify black material, point-light distribution, no added light
groups, day/night continuity and native DPR2. Full-height synthetic lamp/cabinet
dimensions pass; audits during the entrance growth animation are not final-size
audits. These checks do not certify the actual apartment's visual acceptance.

## Architectural presentation cut

The user clarified that the purpose is viewing complete furniture layouts and
decoration. The strict whole-model section was superseded: use local material
clipping on architecture, doors/windows and opening trims only. Wardrobes and
bookshelves retain complete geometry and materials. Full-model clipping is
disabled. Closed architectural cut surfaces receive caps; holes remain open.
Fixed lights stay enabled when upper fixture meshes are hidden. Full height and
walk restore complete architecture; saved scheme dimensions stay unchanged.

Independent synthetic checks cover an intact rotated 2700 mm cabinet during a
1200 mm architectural cut, unclipped cabinet materials, lighting and DPR2,
height changes, full-height/walk restoration and stable geometry counts. Actual
apartment visual acceptance remains pending user review.

## Champagne finish refinement

Champagne style revision 5 adds warm upholstery/headboards, one accent wardrobe
front and warm wood for small furniture, retaining pearl cabinet bodies. Silver
fridge body uses metalness .78, roughness .42 and subtle brushed relief. TV screen
and housing stay within the 35 mm case envelope. Case and scheme data are
synchronized; case-specific legacy TV depths migrate once and explicit custom
palette choices remain preserved. Synthetic checks verify 35 mm TV depth, silver
metal/bump roles, champagne and pearl cabinet materials, default-color migration
and native DPR2. Original images/video remain older representations. Actual
apartment visual acceptance remains pending.

## Tabletop accessories

Dining/coffee decorations are independent accessory groups above the normalized
furniture body. Opaque parts are batched within each accessory assembly; they
retain the parent's picking identity and production geometry. Kitchen corners
require explicit case placements, separate from sink/stove cutouts and prep
space. Existing accessories:false disables additions. Synthetic checks passed
for supported bottom height, within-table footprints, unchanged body dimensions,
DPR2 and disabled-decoration behavior. Accessories do not add collision objects.
The actual reviewed kitchen placements are case parameters, not shared defaults.

## Cross-style common components

Legacy standard 80/90 mm TV bodies upgrade to 35 mm across all styles, rather
than depending on a reference-case setting. Other nonstandard depths and
already-migrated edits remain. Ceiling diffusers, fixed lighting, appliance
material behavior, native resolution and architectural cutaways share component
implementations. Independent synthetic checks passed for every installed preset:
35 mm default TV, retained 42 mm custom TV, omnidirectional ceiling light groups,
day/night continuity and DPR2. Palette colors remain distinct between styles.

## Final beta.5 follow-up checks

Latest installed-source regression: 174 Python tests, eight subject checks and
37 interaction modules pass. Independent Chromium export/edit/refresh checks
verify document cache isolation, denied-storage seed fallback, connection patch
2D/3D material parity and production mesh preservation. Case static coverage
patches total approximately 0.84 m²; original room boundaries/state are unchanged.

Independent before/after lighting fixtures verify native DPR2, permanent groups,
fixed one-light shadows and bounded geometry/texture counts after 16 edits and
day/night switches. They do not certify actual-apartment brightness or prolonged
physical-device performance. The user's supplied apartment screenshots are
pre-adjustment evidence; latest visual acceptance remains separate.
