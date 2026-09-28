# Deterministic drawing tools

Use these tools after source interpretation has produced structured geometry.
They do not recognize a raster floor plan, choose furniture, call an image model,
or certify measurements.

## Structured floor-plan renderer

Copy `assets/floorplan-input-template.json` into the case run and populate it from
the current confirmed interpretation. Coordinates are image/canvas coordinates,
not assumed millimetres. The input contains a canvas, independent wall records,
bounded room polygons, swing doors, openings, and optional annotations.
Room polygons remain structured metadata by default; set
`canvas.show_room_boundaries: true` only for a review overlay, not the clean
structural base.

```bash
python3 scripts/render_floorplan.py \
  --input /absolute/path/topdown-base-v1.json \
  --svg /absolute/path/topdown-base-v1.svg \
  --png /absolute/path/topdown-base-v1.png
```

The command refuses an existing output, mismatched SVG/PNG stems, unsupported
opening types, out-of-bounds geometry, malformed door arcs, and SVGs that embed
raster images. It writes editable vector elements with stable IDs, then renders
that exact SVG to PNG with PyMuPDF or `rsvg-convert`. A passing command proves
format and declared-geometry checks only; compare the result with the source.

## Furniture-layout renderer and checks

Copy `assets/furniture-layout-input-template.json`. Put the same floor-plan
object under `plan`, keep the same revision value at both levels, and add
furniture objects using the reusable `bed`, `sofa`, `table`, `chair`, `cabinet`,
`sink`, `toilet`, `appliance`, or `generic` top-view symbol.

```bash
python3 scripts/render_furniture_layout.py \
  --input /absolute/path/layout-v1.json \
  --svg /absolute/path/layout-v1.svg \
  --png /absolute/path/layout-v1.png
```

Run `--check-only` without output paths for a non-rendering diagnostic. The
checker rejects furniture outside its declared room, wall intersections,
furniture overlap, and intersections with a sampled door leaf/swing sector.
Use `allow_overlap_with` only for a deliberate scoped relationship such as a
chair tucked under its own table, and keep the reason in the case review.
Axis-aligned footprints are the supported V0 contract. Clearances, pull-out
states, maintenance access, source scale, and construction feasibility remain
manual/unverified checks under `furniture-layout-review.md`.

## Confirmed-image contact sheet

Copy `assets/contact-sheet-input-template.json` and list only accepted source
images. This tool decodes and copies their full pixels to a larger canvas with
labels and spacing; it does not crop, resize, or regenerate them.

```bash
python3 scripts/assemble_contact_sheet.py \
  --input /absolute/path/contact-sheet-v1.json \
  --output /absolute/path/contact-sheet-v1.png \
  --manifest /absolute/path/contact-sheet-v1.manifest.json
```

The manifest records each source path, dimensions, before/after SHA-256, and
exact placement. Source files remain unchanged. The assembled PNG is necessarily
a new file; “preserves source bytes” means the input files are not rewritten and
their decoded pixels are copied without scaling or cropping, not that their file
containers are embedded byte-for-byte inside the PNG.
