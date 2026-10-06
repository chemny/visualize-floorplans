# Project manifest contract

Use `schema_version: "0.3"` for new projects. Schema 0.2 remains accepted only
for existing manifests that still use legacy string-only `locked_elements`.
Keep this contract model-independent so a future geometry engine can replace
image-only generation without changing the Skill's user workflow.

## Required fields

| Field | Meaning |
|---|---|
| `project_id` | Stable lowercase identifier using letters, digits, `_` or `-` |
| `input_image` | Absolute or manifest-relative path to the source floor plan |
| `mode` | `conceptual` for V0; reserve `structure_verified` for a later geometry system |
| `use_case` | `renovation`, `property_viewing`, or `real_estate_marketing` |
| `floor_plan.rooms` | Confirmed room objects with unique IDs, names, and types |
| `floor_plan.relationships` | Short adjacency statements confirmed or marked uncertain |
| `interpretation_artifacts.confirmation` | User confirmation bound to the current reconstructed-plan version and review scopes |
| `interpretation_artifacts.topdown_base_svg` | Editable reconstructed plan paired with its same-revision PNG preview |
| `structural_locks` | Confirmed, evidenced structural facts later generations must preserve |
| `design.style_options` | 12 defaults for new projects; 4/8-option subsets supported |
| `design.selected_style` | `null`, a default ID, or `custom` with explicit custom_style |
| `design` | Household, budget tier, palette, materials, and free-form needs |
| `outputs` | Canonical view, room views, style variants, image size, quality, and format |

Optional `delivery` controls the client-facing base-plus-adaptive package. It
does not replace `outputs`; it tells `scripts/plan_delivery.py` which optional
views to include or omit:

```json
{
  "delivery": {
    "mode": "base_plus_floorplan_adaptive",
    "max_images": 24,
    "featured_room_ids": [],
    "omit_room_ids": [],
    "include_bathrooms": false,
    "include_structure_reference": true,
    "include_furnished_plan": true
  }
}
```

Rooms may additionally declare `floor` for multi-floor planning and
`delivery_priority: "featured"` for a space that should receive its own view.
`floor_plan.layout_traits` may include `l_shaped`, `elongated`,
`high_occlusion`, `split_level`, `duplex`, or `multi_floor`. These traits permit
a third bird's-eye view only when it adds material visibility.

Required `interpretation_artifacts` records the confirmation chain:

```json
{
  "source_image": "source/floorplan.jpg",
  "topdown_base": "outputs/interpretation/topdown-base-v1.png",
  "topdown_base_svg": "outputs/interpretation/topdown-base-v1.svg",
  "recognition": "run/recognition.json",
  "structure_map": "outputs/interpretation/topdown-structure-v1.png",
  "access_map": "outputs/interpretation/topdown-access-v1.png",
  "zoning_plan": "outputs/interpretation/topdown-zoning-v1.png",
  "topology": "run/access-topology.json",
  "artifact_version": "interpretation-v1",
  "status": "access_confirmed",
  "confirmation": {
    "confirmed_version": "interpretation-v1",
    "confirmed_by": "user",
    "approval_source": "explicit_user_confirmation",
    "scopes": {
      "structure_and_zones": {
        "status": "confirmed",
        "confirmed_item_ids": ["wall-layout-v1", "living-room", "kitchen"],
        "evidence": ["source and zoning plan shown side by side"]
      },
      "access_elements": {
        "status": "confirmed",
        "confirmed_item_ids": ["D1", "S1", "W1"],
        "evidence": ["access overlay and schedule shown"]
      }
    },
    "unresolved_items": []
  }
}
```

The original source remains the structural authority even after the 2D plan is
confirmed. New templates start with `status: unconfirmed`, empty structural
locks, unconfirmed scopes, and a pending-review item. Use
`status: structure_confirmed` only when the structure scope is complete, and
`status: access_confirmed` only when both scopes are complete for the same
`artifact_version`.

`confirmation.confirmed_version` must equal `artifact_version`; changing the
reconstructed plan creates a new version and invalidates the old confirmation.
Each scope records the stable IDs actually shown and concrete review evidence.
`unresolved_items` contains only consequential blockers such as an unknown door
type, missing opening direction, disputed room boundary, or inaccessible
required room. Non-consequential unknowns such as an unavailable ceiling height
remain in `floor_plan.uncertainties` and need not block image planning.

One explicit user response may confirm both scopes when the source comparison,
zoning, and complete access schedule were all presented together. Record the
same confirmation event under both scopes. If only one scope was shown, mark
only that scope confirmed. A generic “continue” is not confirmation evidence
for missing or unresolved items, and confirmed item IDs should not be asked
again unless their artifact version changes.

## Recognition artifact

### Current confirmation bundle (B3)

Production planning requires all seven real files in `interpretation_artifacts`:
`source_image`, `topdown_base`, `topdown_base_svg`, `zoning_plan`, `access_map`,
`recognition`, and `topology`. The SVG and PNG must share one revision stem.
Recognition and topology carry the same `artifact_version` as the
manifest. Recognition source paths resolve relative to its own JSON directory;
manifest artifact paths resolve relative to the manifest directory.

Manifest room IDs match all interior zones in recognition/topology. Recognition
`proposed_function` matches topology `kind`. Every traversable element has the
same ID, type, certainty, `connects`, and door-operation fields in both files.
Windows and other non-traversable openings remain in recognition and must be
included in `access_elements.confirmed_item_ids`. Unknown door/gap candidates
cannot become confirmed access without updating their original evidence record.
Resolve conflicts by checking the source and recording a specific user update;
never select whichever file permits generation.

After the source comparison and scope presentation, inspect the candidate bundle:

```bash
python3 scripts/interpretation_authority.py --manifest /absolute/path/project.json
```

This read-only command prints `candidate_only` hashes, not approval. After the
user explicitly accepts the displayed version, record `artifact_sha256` and
`facts_sha256` inside `interpretation_artifacts.confirmation` alongside the A2
confirmation record. The latter binds `floor_plan`, `structural_locks`, and
`input_assessment`. Never stamp old approvals onto freshly computed hashes.
Production planning reads and checks these files. Execution checks the bundle
again through `delivery_state.py can-run`; a changed or missing file blocks it.
Hashes prove content identity, not correctness of source interpretation.
Also record `confirmation.source_self_check` with `method: visual_comparison`
and a specific `evidence` string describing the source/reconstruction comparison
and any uncovered-region review. This records work actually performed; never
fill it merely because the script passed.

Existing schema 0.2/0.3 projects with no complete bundle remain usable for
non-executable dry-run samples via `--allow-missing-input`. For actual generation,
preserve their originals and prepare a new run with verified current evidence
and explicit confirmation. No automatic historical migration is performed.

### Deterministic overlay geometry (B2)

Coordinates are pixels of the unchanged base image. All interior zones require
`render_polygon`; only `outside` is exempt. Every element requires `render_point`
for its numbered label and these extra `render_geometry` fields when applicable:

| Kind | Geometry |
|---|---|
| Swing door | `hinge`, `closed_tip`, `open_tip`, `arc_direction` |
| Sliding door / open passage / window / fixed glazing | `start`, `end` |
| Bay window | `outline`, a polygon tracing the visible projection |

Swing directions are `clockwise` or `counterclockwise` in screen coordinates
(positive y points down). The hinge-to-tip lengths must match and the arc must
be 0–180 degrees, excluding zero. Use `swing_into` plus the associated zone to
check the visual direction. Unknown operation needs source/user clarification;
the renderer must not guess an arc.

`coverage_polygon` defines the footprint to review for omissions.
`coverage_exclusions` optionally holds `{polygon, reason}` records for walls,
shafts, or other areas outside room polygons. Missing footprint coverage emits
an explicit warning. Overlapping zones and out-of-bounds/degenerate polygons
fail. Review uncovered regions and the displayed source before confirmation;
the raster checks alone cannot prove all source regions were detected.

### Incomplete input (B1)

`input_assessment` is required for production planning. Its `condition` is
`readable`, `partial`, or `critical_missing`; its `items` distinguish source
evidence, user supplementation, hypotheses, and unknowns. See
`floorplan-interpretation.md` for the item fields and completion workflow.
Critical missing structure and consequential unknowns block generation.
Accepted hypotheses retain their provenance and must be included in the current
reconstructed version and confirmation. Missing measurements never justify
invented precision.

Use `schema_version: "0.2"` for `recognition.json`. Keep graphic linework,
architectural elements, and semantic zones in separate arrays. Every record
requires machine-readable `evidence_codes`; see
`architectural-plan-recognition.md`. Validate this artifact before creating the
access topology:

```bash
python3 scripts/validate_recognition.py --recognition /absolute/path/recognition.json
```

An `unknown_gap` or `door_candidate` remains in the recognition artifact but
must not appear in `access_points`. Only confirmed traversable elements are
copied into topology.

## Spatial topology

Create access topology before generating a 3D view. A route is optional:

```json
{
  "zones": [
    {
      "id": "outside",
      "label": "户外",
      "kind": "outside",
      "certainty": "confirmed",
      "evidence": ["special exterior node"]
    },
    {
      "id": "central-public-zone",
      "label": "客餐厅候选",
      "kind": "living_dining",
      "certainty": "uncertain",
      "evidence": ["visible bounded zone", "central circulation"]
    }
  ],
  "access_points": [
    {
      "id": "entry-door",
      "kind": "entrance_door",
      "connects": ["outside", "central-public-zone"],
      "hinge_location": "source-image left jamb",
      "swing_into": "central-public-zone",
      "certainty": "confirmed",
      "evidence": ["user-marked entrance"]
    }
  ]
}
```

When and only when a video or property-tour deliverable is requested, add a
route. A complete tour retains the existing outside-to-outside form (the
`full_tour` mode is implicit for older records):

```json
{
  "tour_route": {
    "entry_access": "entry-door",
    "exit_access": "entry-door",
    "steps": [
      {
        "order": 1,
        "from": "outside",
        "to": "central-public-zone",
        "via": "entry-door",
        "stop": "进入公共区"
      },
      {
        "order": 2,
        "from": "central-public-zone",
        "to": "outside",
        "via": "entry-door",
        "stop": "结束看房并离开"
      }
    ]
  }
}
```

For a short indoor segment, use this form instead. `route_render_points` are
coordinates on the current confirmed plan, not invented access edges:

```json
{
  "tour_route": {
    "mode": "indoor_segment",
    "start_zone": "central-public-zone",
    "end_zone": "central-public-zone",
    "start_label": "客厅起点",
    "end_label": "餐厅终点",
    "camera_facing": "toward dining area",
    "steps": []
  },
  "route_render_points": [[500, 500], [500, 600]]
}
```

For an indoor segment between distinct zones, `steps` must list real confirmed
access points from `start_zone` to `end_zone` in order. Keep `outside` in the
underlying access graph, but do not insert it into an indoor route. With
`validate_route.py --recognition ...`, same-zone path segments are checked
against the zone polygon; furniture clearance still requires visual review.

For a tour beginning at the entry and ending indoors, use
`mode: "entry_to_interior"`, `entry_access`, `end_zone`,
`required_visit_zones`, and ordered `steps`. The first step comes from
`outside`; the final step reaches `end_zone`. Omit `exit_access` and never
insert a return to `outside` solely to pass validation. The validator reports
access edges traversed more than once so unavoidable dead-end returns can be
distinguished from unnecessary backtracking.

Every zone requires source evidence. Unknown function is represented by
`unassigned_space`, not by creating a plausible room. Every route step must use
a confirmed traversable access point connecting the two named zones.

Each confirmed swing door in `access_points` also requires `hinge_location` and
`swing_into`; `swing_into` must name one of its connected zones. Each confirmed
sliding door requires `slide_axis` and positive sliding-panel evidence. Validate
the access-only graph with `scripts/validate_access.py`. Validate the optional
route later with `scripts/validate_route.py`.

## Interpretation provenance

Before filling the room list, present the interpretation proposal defined in
`floorplan-interpretation.md`, compare the reconstruction with the source, and
obtain user confirmation. Store general uncertainties in
`floor_plan.uncertainties` and consequential confirmation blockers in
`interpretation_artifacts.confirmation.unresolved_items`. Set a room to
`confirmed` only when it is explicit in the drawing or the user has confirmed
the proposal; otherwise keep it `uncertain`.

## Room object

```json
{
  "id": "living-room",
  "name": "客厅",
  "type": "living_room",
  "certainty": "confirmed"
}
```

`certainty` is `confirmed` or `uncertain`. Never silently convert uncertainty
into a precise claim.

## Structural-lock registry

Do not store confirmed structure as untraceable free-form reminders. Before
renovation planning, every schema 0.3 project requires at least three structured
locks:

```json
{
  "structural_locks": [
    {
      "id": "lock-balcony-opening",
      "kind": "sliding_door",
      "applies_to": ["living-room", "balcony"],
      "rule": "Keep the confirmed sliding door between the living room and balcony",
      "source": "confirmed_access",
      "evidence": ["approved access-map element S1"],
      "status": "confirmed"
    }
  ]
}
```

Requirements:

- `id` is unique and stable across revisions;
- `kind` is one of `room_count`, `wall`, `door`, `sliding_door`, `opening`,
  `window`, `bay_window`, `adjacency`, `projection`, or `other`;
- `applies_to` contains `all` or the affected zone/element IDs;
- `rule` states the exact invariant in generation-ready language;
- `source` is `original_plan`, `confirmed_2d`, `confirmed_access`, or
  `user_confirmation`;
- `evidence` records at least one concrete source, element ID, or user approval;
- only `status: confirmed` locks may enter generation and delivery planning.

`scripts/plan_delivery.py` resolves applicable locks into every asset's
`structural_lock_ids` and `must_not_change`. Global locks apply to all assets;
scoped locks apply when their zone intersects the asset's `must_show` list.

Schema 0.2 `locked_elements` strings are normalized as global legacy locks for
backward compatibility. Do not create new projects in that form.

## Plan asset identity and review evidence

The structure reference and furnished plan are separate deliverables:

- `structure_reference_plan`: source-faithful structure/dimension reference,
  without decorative furniture;
- `furnished_colour_plan`: designed colour plan with furniture and finishes.

Neither asset kind may substitute for the other. If scope changes, regenerate
the delivery plan so its `kind` matches the intended output.

For client delivery, compile provider tasks from the approved shot list:

```bash
python3 scripts/plan_project.py \
  --manifest /absolute/path/project.json \
  --delivery-plan /absolute/path/run/delivery-plan.json \
  --output-dir /absolute/path/run
```

The resulting generation plan uses the same asset IDs and order. Primary
bird's-eye tasks use the confirmed source, 2D base, and access map. Every
complementary bird's-eye and room view depends on, and references, the primary
bird's-eye for its floor. The legacy no-`--delivery-plan` mode remains available
for old projects and non-client experimental tasks only.

## Delivery approval state

For shared scheme fields, actual output resolution, revisions, partial reuse,
and the current file-bound review workflow, read `design-and-revisions.md`.
`can-run.resolved_task` is the executable task; `asset://` references in the
stored generation plan are unresolved placeholders. Image records now include
SHA-256 content identity. A scheme change needs a new plan/state binding; do not
edit an existing state's plan digest to keep old approvals.

Linked generation planning initializes `run/delivery-state.json`. Its SHA-256
binding prevents approvals from surviving a changed generation plan. The
complete state sequence is:

```text
primary_ready
  -> primary_pending_approval
  -> primary_approved_derived_ready
  -> package_pending_review
  -> package_review_passed
  -> final_export_ready
```

Before every task, call `delivery_state.py can-run`. After the primary image file
exists, call `record-generated`. This still leaves all dependent tasks blocked.
Call `approve-primary` only after the user explicitly approves the displayed
primary view:

```bash
python3 scripts/delivery_state.py approve-primary \
  --plan run/generation-plan.json \
  --state run/delivery-state.json \
  --asset-id primary-birdseye \
  --approved-by user \
  --approval-source explicit_user_confirmation \
  --evidence "User approved after comparison with source and access map"
```

The script refuses approval before generation, rejects non-user approval
sources, and unlocks only tasks whose declared primary dependencies are all
approved. Re-running planning does not overwrite an existing state file; a plan
digest mismatch requires a new state rather than silently retaining approvals.

After all planned assets are generated, use `sync-state`, then
`record-package-review`. The latter re-runs strict delivery validation and binds
the successful result to both the delivery plan SHA-256 and the generation-plan
state. It refuses an incomplete package, a stale review, or a different asset
order. Record existing image acceptance with `approve-package`, before or after
review; `can-export` requires both current acceptance and passing live review,
not a second export question. `authorize-final-export` remains a legacy command.

Review schema 0.3 records `planned_kind`, `actual_kind`, `authority_refs`, and
an evidence-bearing object for each check:

```json
{
  "delivery_plan_sha256": "sha256-of-the-exact-delivery-plan",
  "planned_kind": "furnished_colour_plan",
  "actual_kind": "furnished_colour_plan",
  "authority_refs": ["source/floorplan.png", "outputs/interpretation/access.png"],
  "exception": null,
  "hard_checks": {
    "layout_matches_source": {
      "passed": true,
      "evidence": "Compared all bounded zones with the approved 2D base"
    }
  }
}
```

Exceptions must state a reason and `approved_by_user: true`. Exceptions never
permit an asset-kind mismatch when the plan's substitution policy is
`forbidden`; re-plan that asset instead.

## Output configuration

V0 supports one canonical view and a small set of derived views. Use dimensions
whose edges are multiples of 16 and do not exceed the active provider limits.

For new renovation projects, copy the 12 options from `assets/project-template.json`.
Registered IDs are `modern_minimal`, `wood_cream`, `modern_luxury`, `modern_chinese`,
`midcentury_modern`, `song_eastern`, `contemporary_french`, `italian_luxury`,
`champagne_pearl`, `milan_greige`, `paris_art_deco`, and `sculptural_cream`.
The script accepts 4, 8 or 12 distinct registered options. Before selection,
use `selected_style: null` and `style_preview: style_comparison_boards`: four
options per board, three boards for the default twelve. Legacy `four_style_grid`
requires exactly four options. After selection, use an included ID or `custom` and
compile the detailed canonical plan directly. A custom direction requires
`design.custom_style.name` and `description`. The output preview may be null
when a style is already specified. See `design-and-revisions.md` for preferences,
reference images, and shared/per-room scheme records.

```json
{
  "style_preview": "style_comparison_boards",
  "canonical_view": "cutaway_birdseye",
  "room_views": ["living_room_from_entry", "primary_bedroom_from_door"],
  "style_variants": ["warm_minimal", "modern_wood"],
  "size": "1536x1024",
  "quality": "medium",
  "format": "png"
}
```

Generate the comparison only when needed for selection. The compiler only
plans tasks; it does not make paid API requests.
