# H5 source, image and camera quality gates

Read before interpreting a new source, generating AI interiors, planning a
homeowner walkthrough or closing a delivery. This adds executable review
contracts to the existing workflow; it does not grant new execution permission.

## Three review stages, four different facts

Keep one case-local `quality-review.json` with `source`, `images` and `tour`
stages. Include only the requested stages in `requiredStages`; accepted delivery
must include `source`. Each stage records these independently:

1. **Technical**: current files, hashes, complete records and applicable numeric
   or actual-model checks. Checking review records is not automatic visual analysis.
2. **Geometry**: named review against the original/actual H5 scheme, with evidence.
3. **Visual**: named inspection of readability, composition, materials and motion.
4. **Acceptance**: explicit human confirmation of exact displayed output bytes.

Generated, encoded or collision-free is not accepted. Missing, stale, failed or
pending stages block accepted delivery. Preview exports and diagnostic captures
remain available, with their failures visible. A generic instruction to generate
or continue must never populate acceptance. Reuse unchanged, genuine acceptance;
do not ask the user to approve the same unchanged scope again.

Use existing runtimes only. Commands below contain path placeholders:

```text
python scripts/production/h5.py review-template --bundle BUNDLE --out NEW_REVIEW_DIR
python scripts/production/h5.py quality --bundle BUNDLE --review REVIEW_JSON --stage source --out NEW_SOURCE_CHECK_DIR
python scripts/production/h5.py quality --bundle BUNDLE --review REVIEW_JSON --out NEW_REVIEW_CHECK_DIR --accepted
```

The template populates current IDs and model values only. Source provenance,
pixel anchors, reviews and acceptance start empty/pending. It intentionally
cannot pass. Paths in a record resolve relative to that record. Artifact records
contain `{path,sha256,role}` with role `input`, `evidence` or displayed `output`.
Changing an artifact requires a new review snapshot, not rewriting old history.

## 1. Original-plan interpretation and calibration

- Declare manual dimension reading or assisted extraction followed by review.
  Do not claim automatic upload recognition when an agent entered geometry.
- Record horizontal and vertical scan calibration separately: source file,
  two pixel positions per anchor, readable dimension ID, mm per pixel, tolerance.
  Anchor coordinates must lie in the actual image and agree with readable mm.
  These checks verify the entered contract, not whether text was read correctly.
- Record width/depth/height and any other used dimension as `source_dimension`,
  `derived` (with basis IDs) or `design_assumption`. Never promote a furniture
  reference, area ratio or illustrative image to dimension evidence.
- Every current room, wall and opening needs a provenance item and source
  comparison evidence. Show junctions, wall returns, entrance pier, opening
  offsets and source/design differences in a source-versus-reconstruction view.
- Record consequential ambiguity as unresolved until the displayed resolution
  is actually confirmed. An unlabelled location interpolated from pixels is
  still derived. An interior door leaf proposed where only an opening is drawn
  is a design assumption. Black wall linework is not engineering bearing proof.
- Bind this review to the current exported **structure scope hash**. A finish
  change alone does not reopen an unchanged source review; structural edits do.
  Keep purchased gross area, outline estimate and net floor sum separate.

## 2. AI interior consistency

Before generation, freeze source/layout/style and per-camera `mustShow` subjects.
After generation, record for each agreed image:

- Output, exact H5 reference PNG, capture metadata and camera-authority files,
  each with its current hash. New H5 captures include `imageSha256`; camera
  metadata must match the frozen view and scheme. Legacy captures need verified
  provenance migration or a fresh capture; a matching filename is insufficient.
- Named evidence for room shape, openings, object identity/count, placement,
  orientation, proportions, materials, lighting and perspective. Each check
  uses `{status,reviewer,evidence}`. Explicitly list allowed conceptual differences.
- Cross-view consistency review and complete agreed `expectedImageIds`.
- Actual pixel ratio versus the agreed output ratio. The default permits 0.1%
  native pixel rounding; exact dimensions can use zero tolerance. Never crop or
  resize an accepted original merely to fit handoff. Aspect success is separate
  from composition quality.

Missing/reversed openings, changed room shape or furniture function, relocation,
or proportion failures require correction before downstream use. Material and
light drift also block the image set until reviewed and corrected. A room can
have several views if one cannot show all main functions; replan explicitly
instead of pretending an occluded object is visible. Two failed targeted retries
follow the existing stop-and-report rule. These validators do not infer visual
pass from pixel similarity, and do not call an image provider.

The image stage uses `viewsArtifact`, `images`, `setConsistency` and
`aspectPolicy`. Each image has `id`, `viewName`, `referenceArtifact`,
`captureArtifact`, `outputArtifact`, all nine `checks`, and `allowedDifferences`.
Record geometry and visual stage review separately from the individual checks.

## 3. Homeowner camera and time windows

Plan **function → subject → observation angle → connection → duration**.
Avoid blank-wall turns, repeated introductions, entering too deeply, and
door-frame closeups. Shallow entry and offset returns are preferences subject
to actual clearance. Necessary return routes are allowed; do not invent a loop.

Copy `assets/h5/subject-plan-template.json` to the case directory. Bind the
scheme hash and exact tour-file SHA256. Give every chapter actual stable subject
IDs, a functional purpose and explicit start/end seconds. Keep waypoints, target
IDs, time allocations, speed/body envelope and policy overrides in the case.
Choose total duration from distance, useful views and readable subjects; never
pad to 60 seconds or increase pace solely to hit a target.

An optional `cameraCues` array in the route config gives ordered, nonoverlapping
`startSeconds`, `endSeconds` and `targetMm:[x,y,z]` observation windows. The
planner keeps camera positions unchanged, follows the declared target during
the window and smoothly connects targets under the yaw limit. This is an intent,
not proof that the target is already in view: a late target can still fail because
turning takes time. Run the actual subject audit after every timing/gaze change.
Leave enough connection time rather than loosening the visibility policy.


```text
python scripts/production/h5.py audit --runtime RUNTIME --tour TOUR --subjects SUBJECT_PLAN --out NEW_AUDIT --preview --node NODE --playwright-module PLAYWRIGHT --browser CHROME
```

The inspector uses actual visible meshes and camera orientation. It checks:

- Multiple frames across the viewing window, not an arrival frame alone.
- Each required subject has sustained unoccluded samples and meaningful screen
  extent. A momentary glimpse or a few edge pixels is insufficient.
- Frequent near-wall/door architecture filling the view. Diagnostic chapter
  screenshots, per-frame measurements and failures remain in the case report.
- Actual mesh collision with the route's declared body envelope, after smoothing.
  A camera radius is not proof of comfortable human passage. A named walking
  clearance review must also inspect narrow paths, doorway pose and shallow entry.
- Enabled and visible lamps, then actual playable video duration, continuity,
  movement and frame count. Bind playback evidence to exact video bytes.

Default policies (2 Hz, 2 continuous seconds, minimum sampled fraction/extent,
near-architecture limits) are adjustable concept checks, not legal or construction
standards. Triangle samples and projected bounds are approximate; discrete
sampling can miss short obstructions. They never replace visual playback review.

`subjects.json` stores the scheme/tour/intent-plan hashes, every chapter and its
metrics. Its pass does not grant human acceptance. Formal animation requires a
subject plan and current source review; a missing or failing subject gate can
only be retained as explicitly unaccepted diagnostic preview.

The tour review binds `tourArtifact`, `subjectPlanArtifact`, `subjectAuditArtifact`,
`meshAuditArtifact`, `videoArtifact` and `videoProbeArtifact`. Include `purpose`,
`paceRationale`, reviewed `walkingClearance` and reviewed `playback` with the
video hash. A route or intent change invalidates subject/motion/playback review.

## Formal handoff versus preview

```text
python scripts/production/h5.py run --bundle BUNDLE --tour TOUR --subjects SUBJECT_PLAN --quality-review REVIEW_JSON --out NEW_RUN --animation --node NODE --playwright-module PLAYWRIGHT --browser CHROME
python scripts/production/h5.py handoff --directory DELIVERY --manifest ITEMS_JSON --bundle BUNDLE --quality-review REVIEW_JSON --accepted
python scripts/production/h5.py package --directory DELIVERY --archive NEW_ZIP --bundle BUNDLE --quality-review REVIEW_JSON --accepted
```

Formal generation checks the source stage first; new output remains pending.
Formal handoff/package require every requested stage to pass all four facts and
current scheme approvals. Accepted outputs must be present in delivery under
their reviewed paths/hashes. Preview handoff cannot promote an `accepted:true`
manifest claim. ZIP integrity applies to supporting files; only the reviewed
displayed output scopes carry acceptance. Paid/external work and Seedance remain
separate requests and gates. No archive or local check certifies every floorplan.
