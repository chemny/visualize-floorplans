# Shared schemes, revisions, and live review

## Specify the scheme

First complete the pre-render layout review in `furniture-layout-review.md`.
Populate layout and furniture constraints from that exact approved proposal;
primary-image approval does not replace the earlier layout confirmation.

After linked planning initializes the state, bind the approved layout:

```bash
python3 scripts/delivery_state.py approve-layout --plan run/generation-plan.json \
  --state run/delivery-state.json --file /absolute/path/approved-layout.png \
  --svg /absolute/path/approved-layout.svg \
  --revision L1 --approved-by USER --approval-source explicit_user_confirmation \
  --evidence 'Existing explicit confirmation of this exact layout'
```

The PNG and editable SVG must use the same revision stem. This records both
hashes, revision, scheme digest and confirmation in the existing
state. Production `can-run` checks the binding and includes the layout reference.
Changed bytes block generation/export; replan instead of attaching new approval
to old generated images. Bind the current layout after replan, before generating
more images; retained unaffected pixels still need review against it. Reuse an
unchanged confirmation, not a fresh user question. Legacy runs without a binding
require a new reviewed run; do not fabricate retrospective gate success.

New projects use the 12 `style_options` in `assets/project-template.json`.
Keep four-option historical manifests compatible; do not silently change an
existing selected scheme. Follow `guided-user-workflow.md` for the default
three-direction recommendation and host-tool comparison; a direct choice skips
comparison. The legacy script supports only 4/8/12 options, rendered as four-panel
boards, with `outputs.style_preview: style_comparison_boards`. These are expanded
comparisons when requested, not the default first-use questionnaire. Do not send
three options into that script or silently pad the user's selection scope.
Both paths must pass `references/style-selection-gate.md` before presenting a
style-selection question, and again before selected-style production. A planned
prompt or a text shortlist is not a generated and displayed comparison board.

The expanded catalog consolidates case variants rather than treating aliases as
new styles: 现代雅奢 stays under 现代轻奢; 当代东方 under 现代新中式;
当代法式/法式当代奢雅 under 克制法式优雅; 意式轻奢/深色奢华 under
意式克制奢华. 香槟珍珠、米兰暖灰、巴黎装饰艺术、奶油雕塑感 retain
their separate material/design identities. Do not import case-specific furniture
coordinates, ceiling heights or household preferences into these presets.

Before style choice, compile without `--delivery-plan`. These comparison tasks
use the legacy preview plan, not the primary-image state machine. First complete
the layout confirmation and append its exact approved PNG reference to every
preview request; record the file/hash and camera intent in the case review.
Do not claim `approve-layout` automatically gates this preview-only path.
Use one fixed representative room/camera anchor for all boards; later boards
also reference the first actual board for camera consistency, without copying
its material choices. Inspect cross-board geometry before showing the set.
After selection, create the linked delivery plan/state and bind `approve-layout`.
Use `selected_style: custom` with `custom_style.name` and `description` for a
custom direction; palette and materials are optional. `design.reference_images`
contains actual local image paths. User palette/materials override preset
defaults. `requirements`, `household`, `budget_tier`, and `preserve_furniture`
enter every relevant task.

`design.scheme` holds a `version` and lists of concrete descriptions for
`layout`, `furniture`, and `finishes`. Populate them from the proposed scheme
before primary approval: room layout, furniture identities/positions, and
materials must be reviewable. Approval binds this scheme and the exact primary
image bytes. Do not populate the record with a claim of geometric precision.

`design.room_schemes` maps existing room IDs to specific layout/furniture/finish
requirements. Whole-home views receive all visible room entries; room views
receive entries for their `must_show` rooms. Use global scheme fields for
changes that really apply across the home. If visibility is uncertain, include
the affected room in the task scope; never use narrow scope to hide an impact.

## Resolve the approved references

Production uses linked delivery planning. A dependency reference such as
`asset://primary-birdseye` is not an image path or something to send to a provider.
Run `delivery_state.py can-run` and execute only its `resolved_task` when
`runnable` is true. This points to the actual recorded, approved primary file.
The delivery furnished colour plan depends on that primary and projects its
furniture layout; it does not propose different furniture placement. It is not
the earlier layout proposal. Both it and the primary must match the approved
pre-render layout; resolve contradictions rather than treating primary approval
as permission to silently overwrite furniture decisions.

The primary image needs explicit approval after visual comparison; internal
review alone cannot unlock dependent tasks. Moving a generated result to a
different output location is supported when the actual file is recorded.
Changing bytes after approval blocks dependent tasks.

## Correct an image or revise the scheme

For an image error relative to the unchanged confirmed scheme:

```bash
python3 scripts/delivery_state.py revise --plan run/generation-plan.json \
  --state run/delivery-state.json --asset-id ROOM_ASSET \
  --reason 'Correct the rendered item to match the confirmed scheme'
```

`reject` and `reopen` are aliases. Supply multiple `--asset-id` arguments when
the same error affects multiple views. The command retains previous files,
adds revision instructions and an edit reference, and reopens dependencies.
Execute the newly resolved task, save to a new file, then `record-generated`.
Primary replacements require a new `approve-primary`. The output path receives
a revision suffix; never overwrite the previous reference image.

For a real scheme change, update the corresponding global or room-specific
design record and scheme version. For structural changes, also re-confirm the
current interpretation bundle. Compile to a new run directory. Then:

```bash
python3 scripts/delivery_state.py replan --plan old-run/generation-plan.json \
  --state old-run/delivery-state.json --new-plan new-run/generation-plan.json \
  --new-state new-run/migrated-state.json
```

Continue using `migrated-state.json`. Reuse requires unchanged task constraints,
unchanged relevant authority, and identical actual output bytes. A scoped room
change may keep unaffected room images even when the whole-home primary needs
regeneration. All retained images must be reviewed against the updated primary
before package approval; reuse is not inherited acceptance. Changed source
structure invalidates the affected reference bundle. Replanning failure must
leave prior plan/state files intact. Revisions clear package review/approval and
mark video invalidated; the video-generation chain remains a later module.

## Perform real visual review

Create a pending review with actual file bindings:

```bash
python3 scripts/delivery_state.py prepare-review --plan run/generation-plan.json \
  --state run/delivery-state.json --delivery-plan run/delivery-plan.json \
  --review run/review-r1.json
```

This fills paths and hashes only. It leaves checks, actual kind, observations,
and inspection method unfinished. Open each output plus its source/access and
approved scheme references; compare them spatially, not just stylistically.
Account for camera reversal before inferring a left/right contradiction.
Check all mandatory fields, actual camera intent, visible room coverage,
door/window operation, balcony access, bay-window projection, relative
proportions, furniture placement, and materials. Mark a check passed only for
what was actually inspected. Explain hidden/not-applicable features in the
check's evidence; if a required feature cannot be seen, reframe/re-plan rather
than marking it passed. Record specific observations and unresolved `issues`.
An issue or missing mandatory check blocks passing review. User acceptance is
not a waiver for a known structural contradiction.

Set `inspection_method: visual_comparison` only after that work. The script can
validate evidence fields and byte identity, but cannot prove that a person or
model truly inspected pixels. This is an operational review contract, not an
automated vision detector. Use actual image inspection as a separate step.

Save the complete review, run `validate_delivery.py --require-files`, and then
`record-package-review`. Review records must match the exact recorded outputs,
scheme digest, actual task authorities, and saved JSON. Diagnostic
`--allow-missing-files` reviews never authorize export. `can-export` rechecks
all image bytes, reviewed authority files, and review/plan files; changed data
requires a new review. Acceptance and QA are separate records, not necessarily
separate user interactions.

## Image acceptance and ordinary local handoff

Record existing image-set acceptance, before or after internal review:

```bash
python3 scripts/delivery_state.py approve-package --plan run/generation-plan.json \
  --state run/delivery-state.json --approved-by USER \
  --approval-source explicit_user_confirmation \
  --evidence 'Exact user confirmation(s) of these current image files'
python3 scripts/delivery_state.py can-export --plan run/generation-plan.json \
  --state run/delivery-state.json
```

Acceptance binds all current asset hashes and the plan. Passing live review is
still necessary, but a second export question is not. When one view changed,
combine its new acceptance with prior exact-file confirmations of unaffected
views in the evidence; never approve undisplayed changes. The legacy command
`authorize-final-export` stays compatible, not a required extra step.

Use `delivery-state.json` as the sole machine status authority. A short client
index can point to it: distinguish pending files, confirmed files and superseded
history, not competing “latest” lists. Revisions retain files/history and clear
affected outputs and package acceptance. This is not publication authorization.
Close the agreed concept stage after local delivery; optional implementation
checks do not prevent closeout.
