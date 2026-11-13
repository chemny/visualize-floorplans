# Furniture style linkage

## Native shape scope

Style switching changes real bodies for sofa/sofabed/armchair, chair/barstool,
TV cabinet/nightstand/wardrobe, table/desk/dresser and bed. Keep positions,
rotation, nominal body width/depth/height and component IDs. Decorative accessories
stay separate from body dimensions. Preserve actual mechanisms (e.g. shower doors)
and keep unsupported types on their existing specialized model.

Nine presets map to bounded shape families: modern minimal linear, wood cream
soft, midcentury exposed timber, modern Chinese lattice, Champagne Pearl tailored,
European luxury classic, contemporary French curved frames, Italian luxury low,
and Paris Art Deco stepped geometry. Core sofa/chair/TV cabinet geometry differs
across nine presets; secondary types may share family details. This is a lightweight
concept representation, not a catalog of manufactured products or photoreal models.

`furnitureStyleMode=follow|fixed` is independent of `colorStyleMode`. Fixed stores
an explicit `furnitureStyleId`, survives style switching, undo/redo and browser
save/reload. Missing/invalid fixed IDs fail validation. Furniture shape identity
belongs in production style scope, not layout placement scope. Fixed color and
finish choices retain their existing precedence.

2D footprints use the same dimensions/positions. Supported style symbols carry
the same style ID; French upholstered chairs and sofas have matching plan symbols.
Detailed modelling need not be redrawn as exact topological 2D lines.

## Room policy

Room semantic function/usage/role takes precedence over fallback names/IDs.
Kitchen and bathrooms retain neutral white walls and light service finishes and
cabinet colours when following style. No decorative repeated moulding is added
there. All inward wall faces are resolved per room interval, including shared walls
and short corner/jamb returns; see `wall-decoration-linkage.md`. Explicit fixed user finishes/colors remain fixed. Preserve existing service
fixtures, floor safety material categories and approved door operations.

Closet follow-mode main lights use compact flush bodies capped at 280mm concept
width/depth. Fixed selected fittings are respected. A case may explicitly set
`mainLightingRequired=false` when omitting a main light; do not remove lighting
without the case's functional intent. Actual illumination and fixture visibility
remain separate per workbench reliability rules. This is not an illuminance test.

## Desk placement

Honor family needs before adding desks. A particular child room without a desk
is not a shared no-desk policy. Prefer a usable wall/window location away from
entry operations; declare `deskPlacementPolicy.minimumOpeningDistanceMm` per
case. `required=true` blocks generation on failure; absent policy reports
not_provided. No shared 900mm or room-specific ID is inferred. Check desk, chair,
seated/pulled use, doors and paths together through the layout-use contract.

## Implementation and verification

- `assets/h5/source/furniture-style.js`: bounded style geometry and metadata.
- `room-style-policy.js`, `wall-decoration-style.js`, `styles-v8.js`: semantic
  service-room default palette; `lamp-style.js`: compact closet bodies.
- `production/desk_placement.py`: room-adjacent opening distance, `.desks.json`.
- `test_furniture_styles.mjs`: actual vertex bounds/height, core geometry diversity,
  nonmutation, neutral semantic rooms and a per-body triangle budget.
- `test_furniture_style_browser.mjs`: actual generated meshes across nine styles,
  unchanged placement/doors, neutral floors, fixed shape, real undo/redo/save/reload.
  Registered as `workbench_browser_suite --checks furniture-styles`.
- `test_wall_decoration_style.mjs`: shape changes invalidate only style scope.
- `production/test_desk_placement.py`: negative and rotated/opening tests.

Inspect actual final room views and furniture closeups. Compare baseline and new
load time/render cost on the same device, browser, viewport and DPR. Numerical
shape diversity and test counts do not certify aesthetics or all devices.
