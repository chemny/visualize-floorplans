# Coordinated wall-decoration styles

Use `wall-decoration-style.js` as the shared authority for finishes, moulding
patterns and existing artwork/panel style. All current styles and the legacy
preset have explicit profiles. Decorative artwork is procedural concept art,
not an externally sourced painting. No network assets or added lights.

Default wall faces, artwork and panels follow the current style. Manual wall
finish selection fixes that face. Artwork/panel `decorStyleMode=fixed` freezes
its `decorStyleId`; returning to follow resolves the current style. Keep explicit
color locks and independent fixture types. Validate persisted enums on import.

Resolve actual inside wall faces from wall thickness and confirmed room polygons;
never copy apartment IDs. A physical wall side can border several rooms: generate
millimetre `segments` at exact polygon intersections, not one majority room for
the whole side. Keep the dominant header for legacy UI compatibility only.
Generate missing interior face records without moving walls or openings.
Kitchen and bathroom inward-facing walls on all sides use an independent neutral
white finish, including shared walls next to living rooms. The opposite living-room
face continues following that room's style. Explicit fixed user finishes retain
precedence; changing the global style does not replace independent wet defaults.
Door jambs and corner returns are partitioned using their real exposed face plane.
Rendering splits existing triangles at room boundaries and preserves surface area,
winding, openings and structural positions. Do not assign a long triangle by its
centroid alone. 2D finish marks use the same canonical intervals, including after
save/reload. Service/unknown rooms use restrained painted walls.
Furniture bodies and the service palette follow `furniture-style-linkage.md`.
Short faces do not receive frames. Accent-only profiles use existing art/TV or
actual bed-head anchors; other walls retain paint. French/European dry-room
profiles permit full-panel repeats. Preserve explicitly fixed face records.

Frame/grid patterns are represented by local surface textures and shallow bump,
not fabrication-ready gypsum profiles. Align their repeat phase to actual wall
length; existing wall apertures clip the surface. Do not cover doors/windows with
new independent panel geometry. Independent wall panels retain their footprints.

Main components: plain minimal / oak slat + botanical / walnut lower panel + retro
geometry / Chinese wood frame + ink / champagne frame + neutral art / European
classic frame + landscape / French frame + floral / Italian panel + warm abstract /
Paris geometric frame + navy/gold art. These are design defaults, not universal
room requirements or cultural/style authenticity certification.

Preserve positions, sizes, furniture count, door mechanisms, floors and lights.
Artwork styling changes style scope only; moving/resizing it still changes layout.
Store canonical face/decoration fields in JSON and portable HTML; exercise real
style changes, fixed/follow, undo/redo, save/reopen and actual 3D on final artifacts.
`node --test scripts/test_wall_decoration_style.mjs` checks policy and counterexamples;
its result does not substitute for screenshots or final-page acceptance.

`wall-surface-segments.js` clips only the rendering surface; it does not subdivide
the editable wall object or change collision/door geometry. `test_wall_surface_segments.mjs`
covers short wet sections, opposite faces, concave/rotated rooms, saved records,
triangle area and winding. `test_wet_wall_browser.mjs` inspects actual material
assignments on rendered triangles facing wet rooms across all nine presets, then
checks save/reload and 2D marks. It is registered as `workbench_browser_suite
--checks wet-walls`. On the actual case, also verify four directional wall faces
in each enclosed service room and inspect real screenshots.
