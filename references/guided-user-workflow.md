# Three-round guided design workflow

This is the default user interaction policy. Read before a new floor-plan project.
It coordinates the technical stages in SKILL.md; three user decision rounds are
not the three technical stages (the optional video stage remains separate).

## Start with one plan

One floor-plan image is sufficient to start. A furniture-layout image and style
images are optional references, never prerequisites. If absent, propose furniture
from room functions and household needs, and recommend renovation directions.
Read and reconstruct through the host Agent and existing tools. Do not describe
h5.py build as automatic image recognition: it consumes structured case data.
Clearly separate source dimensions, pixel-derived values and design assumptions.

Use a copy-ready first-use prompt:

> Use visualize-floorplans with this floor-plan image and my stated needs.
> I may have no furniture or style references. Interpret and self-check the plan,
> then present one concise checklist of consequential uncertainties and missing
> needs, with recommended choices. After that round, propose the furniture and
> function layout. Confirm it together, then help me select a renovation style.
> Produce an editable 2D/3D workbench and the agreed concept images. No video.

## Round 1 — plan and essential needs

Before asking, read all supplied material, reconstruct the plan and review walls,
returns, openings, dimensions, source areas and adjacency. Establish the canonical millimetre H5 case data and build a diagnostic workbench
in structure drawing mode. Export the editable structural SVG and same-revision
PNG from that workbench; combine zoning/access information in a review PNG. Present the plan and one concise checklist together, so questions
have visible spatial anchors. Do not collect approvals for successive incomplete
sketches. All dimensions readable from the source are the Agent's work.

Batch only missing consequential information: household composition, required
room functions, retained objects, any concrete special constraints and source ambiguities. Reuse
anything already stated. Give a short recommended option and reason for genuine
choices; permit “follow the recommendations except item X”. An actual source
uncertainty must still be explicitly addressed; recommendations are not facts.

One explicit response can cover structure/functions/access when all those scopes
were displayed. Bind each approval to the exact files/IDs/hashes actually reviewed.
If user replies only to questions, retain those answers as source facts; do not
infer full-plan approval. Repair affected content and show the corrected version
within this round when necessary. Unchanged accepted scopes are not re-asked.

## Everyday convenience is the default

Prioritize comfortable everyday use: clear entry and room access, sensible sleep,
meals, washing and laundry arrangements, usable furniture and reasonable storage.
Do not force users to rank abstract categories such as storage/work/activity or
ask them to select a priority when they have none. Ask about concrete exceptions
only when they change the layout (frequent guests, unusually large storage needs,
two simultaneous workspaces, mobility needs). “No special requirements” is a
valid answer. An explicitly requested study already establishes a work function;
it does not require selecting “office” as a competing household priority.
Record household count without inventing age, family roles or mobility conditions.

## Round 2 — furniture and functions

Read furniture-placement-principles.md. From the confirmed structure and needs,
update the same H5 case data and prepare:

1. The editable workbench in furniture drawing mode plus SVG and same-revision
   PNG exported from it: names, footprints, dimensions, orientation and fixtures.
2. Function/circulation PNG: room uses, primary everyday paths and operation
   envelopes. This is a layout review, not an ordered video tour. Do not create
   a tour route, animation or tour approval for a still-image project.

Check the essential-equipment inventory, inward door destinations/open-leaf wall
relationships, entrance sightlines, headboard anchors, bedside provision, guest-state
conversion, completeness, wall intersections, doors, cupboard/appliance operation,
chair pull-out space and circulation before presenting. Show unmeasured service
or clearance conditions as unverified. Batch only real unresolved trade-offs
(such as work/guest-room use or storage versus open space), with recommendations.
Do not turn the furniture catalog into an item-by-item questionnaire.

Confirm the whole displayed layout together. Local requested edits remain inside
this round; reuse unchanged evidence. Bind the layout through the existing
approve-layout mechanism. Do not bypass structure/access/layout quality gates.

## Round 3 — style

If a style is already explicit, retain it and show one scheme preview/material
summary; do not force another comparison. With no direction, show the six default workbench style directions in one
2-by-3 interior comparison image, explain their differences and recommend
one with a reason. Use an eye-level interior view, not a bird view, and preserve
the confirmed walls, entrance and furniture. A different option count requires
an explicit user request; never silently reduce the default six to three. Keep layout/camera/daylight fixed for visual comparison.
Generate and show one actual comparison board before asking an undecided user
to select a style. Text/material descriptions accompany the board; they do not
replace it. Check the host's available reference-image generation tools before
claiming generation is unavailable. A browser/state access failure does not
establish that image generation is unavailable. Do not use an old disk layout
as the user's saved layout; resolve the necessary current reference, or explain
the specific dependency and keep the visual-selection step pending.

If generation is genuinely blocked, record the tool check and concrete blocker.
Report the blocked step, not a text-only style-selection question. A text-only
choice is permitted only when the user explicitly requests/accepts that fallback.
Do not infer that waiver from “continue”, a prior apartment's style, or a default
style ID in the diagnostic workbench.

Before asking for a style choice or starting selected-style production, use
`scripts/check_style_selection.py` with a case-local review record described in
`references/style-selection-gate.md`. This guard applies equally to host-tool
six-panel boards and legacy comparisons. It is an Agent-invoked checkpoint,
not automatic browser interception. Passing checks evidence fields/file hashes;
the Agent must still inspect and show the actual pixels.

The legacy plan_project.py comparison planner supports 4/8/12 options and fixed
four-panel boards. Do not pass six options to it, pad a board silently, or
claim six-option execution is supported. Keep the legacy catalog schema,
record the six default directions in the case brief, use the host reference-
image tool for the six-panel selection board, then record the chosen style
through existing selected_style fields. Use expanded legacy comparisons only
when requested. Host tool limitations or external paid calls require disclosure.

Combine style choice with the agreed final image scope (rooms/views); do not ask
another generic “may I continue?” afterward. Images shown before this round are
selection previews, not accepted final renovation results.

## Produce continuously, then review once

After the decisions, refine the existing H5 case/workbench, run applicable
technical/geometry/visual checks and generate only agreed interior images from
the same confirmed scheme. Present the diagnostic workbench during plan and furniture confirmation, with
uncertainties and pending approval explicit; do not call it a final delivery. Never infer image or workbench
acceptance from plan/layout/style decisions. Present the resulting workbench,
bird view and agreed room images together for final review. That final output
review is separate from the three input/design rounds and may require corrections.
Only accepted actual outputs may enter an accepted handoff/package.

## Do not stop at progress updates

Continue authorized reading, dimension extraction, drawing, self-checks, ordinary
corrections and building within a round. Commentary is a progress update, not a
request for another “continue”. Ask a batch of questions and continue independent
work when possible. Do not end a turn merely because a draft or file was created.
Pause dependent work only for an unanswered consequential ambiguity, a material
design decision, a missing required tool/input, or an unauthorized external cost.
Elapsed time is never consent. Three rounds are a default structure, not a quota;
merge or skip already resolved decisions. Necessary corrections do not restart
all rounds. Preserve all provenance, hash binding and existing quality checks.

## Case-local checkpoints

Prefer the project-backed workbench in `project-save-confirm.md` for confirmation
rounds. Save retains edits without advancing; Confirm and continue saves and binds
the current revision to the displayed stage. Await that event during an active
task; do not require an additional chat confirmation for the same event/scope.
The service does not automatically resume an ended task. Source/layout/image
checks still apply, and unsaved or changed-after-confirmation state is not approved.

Keep a short case brief with known inputs, confirmed needs, recommended defaults,
current round, the one pending question batch, exact reviewed artifacts and
remaining uncertainties. Store replies as case facts, not reusable default
household requirements. Use existing confirmation records for executable gates.

Default review images: plan review; furniture layout; function/circulation;
style board (or single-style preview). The structural and furniture source SVGs
remain editable, other presentation images remain PNG/JPG. Room-effect count
follows the agreed plan and purpose rather than a universal fixed package.

## One scheme, multiple representations

The canonical H5 case/state owns millimetre geometry, stable room/wall/opening/
furniture IDs, orientations, functions and provenance. HTML is its editor/view;
SVG/PNG are exports, not separately redrawn authorities. Use structure and furniture
drawing modes in the same workbench through rounds 1 and 2. 2D and 3D consume the
same state. Style selection changes finishes without independently moving objects.

Legacy drawing data requires one explicit migration with unit/origin/rotation/
opening mapping and a parity report. Preserve source and previous artifacts;
never recopy case coordinates into the shared engine. Unsupported/unknown access
semantics stay visibly unresolved; do not invent a door style or bearing status.
Bind drawings and screenshots to the exported current state hash. A user's edits
require new current-state exports before approval or downstream generation.
AI effects use views from the confirmed scheme and still need drift review.
