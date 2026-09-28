# V0 evaluation gates

Evaluate the image workflow on at least 20 varied residential floor plans before
calling it a usable MVP.

## Per-project checklist

- [ ] Reconstructed 2D base matches the source footprint and visible wall layout.
- [ ] Recognition JSON passes `scripts/validate_recognition.py`.
- [ ] Dimension, annotation, and dashed auxiliary lines are separated from
      physical wall geometry.
- [ ] Every door has a door symbol, label, or project-specific user confirmation.
- [ ] Every window and bay window has positive frame/sill evidence and remains
      non-traversable.
- [ ] Every unresolved wall break remains `unknown_gap` and is excluded from the
      route graph.
- [ ] No source door, window, opening, projection, or sunken area is lost or invented.
- [ ] Every door, opening, passage, window, and bay window is classified before zoning.
- [ ] Both structural/zoning and access scopes are confirmed for the current version;
      one complete presentation may support a combined confirmation.
- [ ] Every confirmed swing door records hinge location and the zone containing
      the swing arc.
- [ ] Every sliding door remains a sliding door in the access map and 3D view.
- [ ] Every required room has a confirmed access connection before 3D generation.
- [ ] Still-image projects do not require a tour route.
- [ ] Video/property-tour projects validate and confirm the route before motion planning.
- [ ] Every functional label attaches to an existing visible zone.
- [ ] No kitchen, study, bedroom, bathroom, balcony, or other zone is invented.
- [ ] Final labels use industry roles rather than unresolved ordinal names.
- [ ] Functional labels and access overlays do not alter the 2D base geometry.
- [ ] When video is requested, the tour route has an explicit entry, ordered
      stops, and explicit exit.
- [ ] When video is requested, every route step uses a confirmed door or passage
      and no arrow crosses a wall.
- [ ] When video is requested, route topology passes `scripts/validate_route.py`.
- [ ] Uncertain room assignments are visibly distinguished from confirmed facts.
- [ ] Room count matches confirmed manifest.
- [ ] The default 12-style preview uses three 2x2 boards with the same scene and
      camera across every panel; a user-scoped 4/8-option comparison stays smaller.
- [ ] A style is selected before detailed canonical generation.
- [ ] The canonical 3D view passes a door-by-door comparison against the approved
      access map before delivery.
- [ ] No room is added, removed, merged, or split.
- [ ] Major adjacency matches the source plan.
- [ ] Balcony, kitchen, and bathroom remain in the correct relative locations.
- [ ] Doors and windows do not visibly contradict the source plan.
- [ ] Style matches the requested direction.
- [ ] Derived views resemble the approved canonical view.
- [ ] Local edits do not rewrite unrelated rooms.
- [ ] The client-facing shot list uses the base package plus floor-plan-aware expansion.
- [ ] Every planned view has one camera intent and a non-empty must-show list.
- [ ] Every confirmed structural fact is stored as an evidenced structural lock.
- [ ] Every planned view resolves applicable locks into non-empty `must_not_change` constraints.
- [ ] Provider tasks preserve the approved delivery-plan asset order and metadata.
- [ ] Every derived room or complementary bird's-eye task depends on its floor's primary bird's-eye.
- [ ] The state file is bound to the exact generation-plan digest.
- [ ] Derived tasks remain non-runnable until the generated primary view has explicit user approval.
- [ ] Primary approval records the approver, explicit-user source, evidence, and timestamp.
- [ ] Structure reference and furnished colour plan remain distinct asset kinds.
- [ ] Planned and actual asset kinds match; no silent substitution is accepted.
- [ ] Every hard check and package-consistency check includes concrete review evidence.
- [ ] Every delivery exception has a reason and explicit user approval.
- [ ] The complementary bird's-eye adds material visibility rather than duplicating the primary view.
- [ ] Every planned client-facing asset has a completed structural review.
- [ ] Room count, walls, openings, adjacency, and access pass as hard gates in every view.
- [ ] Furniture, materials, opening geometry, lighting, and repeated architectural features are consistent across the set.
- [ ] `scripts/validate_delivery.py` passes before final-resolution export.
- [ ] Output is labelled as an AI concept image.

## File-bound visual review and revisions

- [ ] Open actual images and their current source/primary references; record concrete observations.
- [ ] All kind-specific mandatory checks from `review_contract.py` are present.
- [ ] Camera intent, visible-room coverage, openings, balcony/bay-window geometry,
      furniture arrangement, and materials agree with the current scheme.
- [ ] Image hashes and authority hashes match the actual files inspected.
- [ ] No unresolved visual issues are hidden behind a user's general acceptance.
- [ ] Primary replacement clears dependent approvals; a view correction retains unrelated files.
- [ ] Changed schemes require a new plan; retained images are re-reviewed against the new primary.
- [ ] A failed replan leaves the preceding valid plan and state unchanged.
- [ ] Export rechecks image, reference, plan, and review files.

See `design-and-revisions.md` for commands and the distinction between a
field-validation result and actual visual inspection. Hashes and completed
checklists cannot prove that an image was visually inspected.

## Pilot thresholds

- At least 80% of canonical views have no missing room.
- At least 70% of derived views have no obvious structural contradiction.
- At least 80% of style variants match the requested style.
- At least 60% of projects become usable within two correction rounds.
- At least 50% of test users choose to save or share an output.

## Escalation rule

If the same structural failure appears in 20% or more of tested projects, do not
hide it with prompt changes. Add it to the structured recognition/3D backlog.
