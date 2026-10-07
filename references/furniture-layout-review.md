# Furniture layout and local-revision gate

Follow `guided-user-workflow.md`: missing furniture references do not block
layout design. Everyday living convenience is the default; do not require
ranking abstract storage/work/activity categories. Ask only concrete layout-changing
constraints, and accept no special requirements. Use the round-1 needs to prepare the layout and function/circulation
review together, then collect round-2 decisions in one batch with recommendations.
Continue drafting, checking and correcting before that presentation.

Read `furniture-placement-principles.md` for placement and room-composition rules.
Use the same H5 state for the editable confirmation workbench and exported plan/
layout drawings; follow `guided-user-workflow.md`. Independent renderers remain
a fallback when H5 cannot represent the source, with explicit limitations and
migration parity before any later workbench.

## 1. Confirm use before rendering style

Use the confirmed structure/access base to propose a legible top-down furniture
and equipment layout before style previews, bird's-eyes, or room effects. Keep an
already selected style; do not reopen style selection. This proposal is separate
from the delivery planner's post-primary furnished colour plan.

For the drawing format and visual example, read
`furniture-layout-template.md` and inspect the linked PNG before producing the
layout. Preserve editable geometry when available.

Derive basic items from confirmed room functions without a long questionnaire:
sleeping and clothes storage for bedrooms; seating for living; eating places for
dining; refrigerator, sink, cooking/extraction and preparation space for a
kitchen; toilet, washing and bathing facilities for bathrooms; a work surface,
seat and appropriate storage for a study; a place for laundry equipment where
services permit. Shared functions may span rooms. Respect explicit omissions,
retained items, and household requirements; do not duplicate shared equipment.
Treat extra housekeeping cabinets and decorative furniture as optional rather
than necessities. Present the proposed layout, not a mandatory item-by-item form.

Keep source evidence, user-confirmed facts, proposed placement, and unresolved
conditions distinct. Inspect service symbols, shafts, slab changes and window
conditions before placing fixtures. Unknown symbols are not disposable marks;
record uncertainty. A user's explanation informs this case, not a universal
symbol dictionary. Do not infer a confirmed toilet outlet from nearby circles
alone. Proposed wall recesses are not permission to cut a wall; flag wall
construction and allowable depth for qualified verification.

## 2. Internal equipment and usability checklist

Review the actual drawing, including objects in use rather than footprints only:

- Completeness: use the whole-home inventory in furniture-placement-principles.md,
  verifying IDs, room, drawing representation and actual mesh presence for essentials;
  each required function has equipment or an explicit omission;
  no unnecessary cabinet has been silently made mandatory.
- Doors: proposed room doors normally open inward; compare hinge sides so the
  open leaf rests near a receiving wall, with explicit reasons for exceptions.
  Check the actual 3D pose as well as the 2D sweep. Hinge, swing, closure, jamb/return and handle-side obstructions remain
  consistent with the approved access map; furniture does not block an opening.
- Circulation: entry and room-to-room paths remain continuous, including access
  to kitchen and outdoor spaces. An arrow alone is not proof of a clear path.
- Operation: bed access, cupboard opening, pulled-out dining/work chairs,
  sanitary-fixture use and appliance opening/maintenance have usable space.
- Services/windows: proposed wet fixtures respect evidenced connections;
  bay-window desks and vanities require sill height, legroom and window-opening
  checks, not merely a rectangle that fits in plan.

Use reliable source dimensions and stated furniture dimensions for quantitative
checks, recording their basis. Do not derive precise clearances from an
unscaled or distorted generated image. Record each consequential check as
observed clear, conflicting, or unverified with a brief reason. Correct visible
conflicts before downstream generation; carry unmeasured conditions visibly as
pending verification. Concept approval never certifies construction feasibility.

## 3. Local edits and exact-version acceptance

Translate each requested edit into: target ID/object, spatial anchor, desired
relationship/extent, and unchanged elements. Prefer “toward the kitchen opening,
right end at the study partition” over an unanchored “down/right”. Describe
hinge side and swing destination rather than ambiguous left/right opening terms.
If text and markup conflict materially, resolve that conflict before editing.

Apply only the requested changes to the current baseline. After generation,
compare actual geometry against every requested change and spot-check untouched
structure, doors/windows, furniture and equipment. A label saying “full length”
is not proof that the cabinet reaches its endpoint; a successful tool call is
not a passed edit. If two targeted retries fail to resolve the same defect,
stop blind regeneration, report the unresolved item, and propose an editable
geometry workflow within the user's authorization instead of claiming success.

Keep a short case-local record (plain Markdown is sufficient):

- baseline and candidate absolute file paths, revision and content hashes;
- requested changes and preservation constraints;
- observed results and unresolved conditions;
- exact file accepted, confirmer and confirmation evidence.

Reuse prior explicit acceptance only if its scope and exact file are unchanged.
Version names alone are insufficient. If the user says one version but attaches
another, disclose the discrepancy and resolve which exact file is authoritative
before recording approval or generating downstream assets. Do not silently
overwrite accepted files. A layout change reopens affected downstream views;
update scheme constraints and replan rather than attaching new approval to stale
state. Bind production to the exact approved layout with `approve-layout` in
the existing state; see `design-and-revisions.md`. Keep observations and unresolved
conditions in the case review, not a competing approval registry. The file gate
is not automatic collision detection or proof of genuine visual inspection.

Before each generation, verify current references and target constraints. After
generation, inspect placement, counts, orientation, proportions, omissions and
wall intersections before proceeding. For edits, record target results and
untouched-region observations in existing `must_not_change_preserved` evidence.
Track the same defect across retries even if its wording changes. Two failed
targeted retries require stopping and reporting. This is an operational rule,
not an automatic vision detector.

Store object coordinates, room-specific preferences and particular fixture
placements in the case, not in this Skill or long-term memory.


## Circulation and storage anchor evidence

Reject a furniture proposal if its dining group blocks a required passage in an
occupied state. Include a case-local connected route plan with design-width
assumptions, chair movement envelopes and wall/door obstacles; list the exact
checked endpoints and remaining gaps in evidence. Recheck after edits.
For viable storage corners, record back and end wall IDs, measured model gaps,
opening avoidance and usable front access. A one-wall gap pass does not certify
corner fitting, and a standing-area pass does not certify hinged cabinet doors.


## Bed-size and cabinet-length evidence

Before accepting a bedroom proposal, compare viable bed sizes against the room's
actual functions and complete furniture group; do not infer a single bed from
“secondary bedroom” alone. Record the selected size and its reason, using bed
frame outer dimensions or explicitly marking that selection remains pending.
For storage, derive length from a continuous finished-wall run and record both
corner anchors, opening/installation allowances and front operating space.
Distinguish along-wall end clearance from passage width. Recheck daily and
converted guest layouts after resizing. Case dimensions are not universal
minimums; see `furniture-placement-principles.md` for the generation workflow.


For double beds, verify headboard back orientation and contact with the actual
finished solid wall; explain any necessary installation exception. Check both
bedside positions when space allows. Record desk/chair and sofa/coffee-table
edge distances and operating states. A rotated wall-adjacent dining table must
retain usable household seats and occupied circulation. Do not certify an
outward entry swing when exterior corridor geometry is unavailable.


Check curtain travel and stacking envelopes before locating window-side furniture
or furniture beside a curtained balcony slider. Record selection assumptions.
Entry storage is optional and must be justified by household needs and available
space; inventory completeness must not force a shoe cabinet into the entry route.


Dimension displays use integer millimetres while geometry retains precision.
Default to exterior overall/positioning chains with a consistent font size;
merge short adjacent spans without changing chain endpoints or total length.
Avoid internal dimension annotations in the furniture presentation. Distinguish
original drawing readings from model-derived dimensions; do not force an
unreconciled source chain onto inconsistent geometry. Regenerate displayed chains when their supporting geometry changes, and verify
segment sums against their declared endpoints. Detailed opening dimensions are
reserved for a separately requested technical drawing.
