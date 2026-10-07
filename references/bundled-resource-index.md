# Bundled resource index

Paths below resolve from the Skill root. Consult when selecting a helper script or template.

## Bundled resources

- `scripts/project_service.py`: loopback project save, conflict detection,
  stage-bound confirmation and bounded Agent waits. See `project-save-confirm.md`.

- `scripts/check_style_selection.py`: check case-local visual selection evidence
  before asking for a style choice or starting selected-style production. Read
  `references/style-selection-gate.md`; this does not inspect image semantics.

- `scripts/plan_project.py`: validate a manifest and compile deterministic Image
  2 task prompts without calling an external API.
- `scripts/plan_delivery.py`: compile the client-facing base package, adaptive
  views, semantic camera intents, and a delivery-review template.
- `scripts/delivery_state.py`: bind layout/image acceptance to files, gate
  execution and live review, and permit local handoff without duplicate approval.
- `scripts/validate_delivery.py`: enforce per-image structural checks and
  package-level multi-image consistency before final export.
- `scripts/test_workflow.py`: local regression tests for validation, dependency
  ordering, and structural constraints.
- `scripts/test_interpretation.py`: synthetic input-completion, overlay geometry,
  cross-file authority, and changed-file regression tests.
- `scripts/interpretation_authority.py`: inspect evidence bundles and candidate
  content hashes; does not grant user approval or replace source comparison.
- `scripts/validate_access.py`: validate confirmed room connectivity, swing-door
  direction, and sliding-door metadata without requiring a tour route.
- `scripts/validate_route.py`: reject discontinuous routes and steps that do not
  use confirmed doors or passages.
- `scripts/validate_recognition.py`: reject unsupported doors, windows, bay
  windows, traversable gaps, physical dashed lines, and semantic zones without
  geometry evidence.
- `scripts/render_interpretation.py`: render deterministic access and zoning
  overlays on the fixed 2D base without asking an image model to redraw walls.
- `scripts/render_floorplan.py`: render generic structured wall/access geometry
  to independent SVG elements, then export the exact same revision to PNG.
- `scripts/render_furniture_layout.py`: render reusable top-view furniture
  symbols and reject declared wall, furniture-overlap, and door-swing conflicts.
- `scripts/assemble_contact_sheet.py`: copy complete confirmed image pixels into
  a labelled canvas without cropping, resizing, or generative redraw.
- `scripts/vector_tools.py`: shared validation, geometry, atomic-write, and
  deterministic SVG-to-PNG support for the drawing tools.
- `assets/project-template.json`: copy and fill for a new project.
- `assets/sample-project.json`: runnable sample manifest for dry-run verification.
- `assets/sample-topology.json`: runnable access graph and ordered tour-route
  validation sample.
- `assets/sample-recognition.json`: synthetic recognition-record example for
  local validation; not a user-confirmed production plan.
- `assets/floorplan-input-template.json`, `assets/furniture-layout-input-template.json`,
  and `assets/contact-sheet-input-template.json`: case-neutral structured inputs;
  fill them in a run directory rather than editing the templates in place.

## Example and historical validation resources

- `assets/reference-cases/jujian-champagne-pearl/data`: example scheme and retained media-source metadata.
- `assets/reference-cases/jujian-champagne-pearl/images`: thirteen selected concepts, linked by its case index.
- `assets/reference-cases/jujian-champagne-pearl/licenses`: retained upstream notices.
- `assets/reference-cases/jujian-champagne-pearl/tour`: the retained tour and its route/source records.
- `assets/reference-cases/jujian-champagne-pearl/manifest.json`: per-file purpose and hash index.
- `assets/reference-cases/jujian-champagne-pearl/workbench/index.build.json`: retained example build evidence.
- `assets/renovation-concept-showcase.png`: historical concept illustration.
- `references/beta4-workbench-validation.md`: historical bounded checks, not current acceptance.
- `references/release-validation.md`: current release boundaries and historical evidence.
- `references/local-beta-status.md`: historical technical and visual scope limitations.
