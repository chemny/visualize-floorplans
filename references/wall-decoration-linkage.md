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
never copy apartment IDs. Generate missing interior face records, but do not
place new artwork, move existing decorations, change structural walls or openings.
Wet rooms use tiled finishes; service/unknown rooms use restrained painted walls.
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
