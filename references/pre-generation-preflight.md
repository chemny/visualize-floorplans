# Pre-generation verification for image sets and revision batches

The purpose of this gate is to remove preventable source, layout, camera and
cross-view contradictions **before** image generation. Scale the record to the
requested scope: one room edit needs only its affected locks and adjacent
views; a whole-home set needs all planned views. Generation remains
probabilistic, so a completed preflight does not replace output inspection.

For style-selection previews, first read `style-selection-gate.md`, check actual
host generation capability and retain the current confirmed layout reference.
After generating, inspecting and displaying the board, run the selection check
before asking the user to choose. For selected-style production, run the same
check with `--production` before the first call. Do not treat a diagnostic
workbench preset or a text recommendation as explicit user selection.

## 1. Establish one current authority chain

- Identify the original plan, latest user-confirmed reconstructed version,
  room/zone map, door/window/opening record, and exact approved furniture
  layout. Record file paths and hashes for the artifacts actually used.
- Resolve any disagreement in room boundaries, door leaf/swing, sliding/open
  passage identity, bay-window projection, or accepted renovations before
  composing prompts. A superseded access overlay or historic state marked
  `final_export_ready` is not evidence that a later plan version agrees with it.
- Distinguish confirmed structure, accepted design proposal, and remaining
  unknowns. Do not depict an unconfirmed door leaf, altered wall or new access
  as a confirmed architectural fact. If an unknown materially affects a planned
  shot, resolve it from the user's existing confirmation or ask for that point.
- For an accepted legacy image set, preserve the accepted files and use them as
  style/furniture references only where they agree with the latest confirmed
  plan. Do not retrospectively claim that an old acceptance approved a newly
  created layout file or a changed structure.

## 2. Make a camera-relative spatial map

For each planned view, record camera origin, look direction, visible rooms,
left/right or near/far relations, required opening type and location, furniture
identity, and features that must not change. Derive left/right from the actual
camera direction rather than copying image-screen positions from a different
view. For a reverse camera, explicitly transform both room and furniture
relationships. If two views cannot plausibly show the same floor plan, fix the
shot specification or references before sending either task to the provider.

## 3. Check the full batch before its first call

- Compare every proposed view and reference against the source plan and exact
  approved access/layout artifacts. Inspect image pixels where visual judgment
  is needed; schema validity and hashes are necessary but insufficient.
- Resolve known furniture-versus-opening conflicts, missing rooms, duplicated
  rooms, impossible sight lines and incompatible camera intents. Record
  unmeasured real-world clearance separately; do not certify it from an image.
- Write one case-local preflight record: authority paths/hashes, unresolved
  facts, per-view must-show and preservation constraints, planned reuse/edit/
  regeneration decisions, and the reason each planned image is needed.
- Do not call an image provider while a consequential contradiction or required
  approval remains open. For a previously accepted primary image, a targeted
  derived-view correction can reuse it only for the unchanged details that pass
  this check; include the confirmed floor plan as structural authority.

“Generate in one batch” means freeze the full specification once and run the
agreed image tasks from it. Individual provider calls and an internally ordered
primary/derived dependency may still be necessary. Do not promise a single call
or a guaranteed correct first output. Post-generation review verifies the
frozen specification; it is a fallback for provider drift, not a substitute for
pre-generation decisions. After repeated structural failure, follow the
targeted-retry stop rule in `furniture-layout-review.md`.
