# Visual style-selection checkpoint

Before a style-selection question, run:

```bash
python3 scripts/check_style_selection.py /absolute/path/style-selection-review.json
```

Before production with the chosen style, run again with `--production`.
Exit 1 means the relevant step remains pending. Do not replace a missing board
with prose or fabricate a passing review. This is a required Agent checkpoint
for both the six-style host path and the legacy 4/8/12 planner; it is not wired
to every chat turn or an automatic generator hook.

Write a case-local JSON object with these fields:

- `mode`: `visual` (default), `direct_choice`, or `text_fallback`.
- `options`: distinct style IDs; default host comparison uses all six workbench
  styles in one 2-by-3 eye-level interior board. Other counts require an explicit
  request. The generic checker accepts at least two for those user-scoped cases;
  a passing count check does not authorize reducing the default six.
- `layout`: `{ "path": "...", "sha256": "..." }` for the exact current
  confirmed layout image. A supplied saved-layout screenshot may be the visual
  reference; explicitly record its scope, and do not claim editable-state parity.
- `boards`: list of `{ "path": "...", "sha256": "...", "style_ids": [...],
  "shown_to_user": true }`, containing actual PNG/JPG files. Across the boards,
  cover all options. Plan files and prompts are not board evidence.
- `comparison_review`: `{ "fixed_layout_camera_light": true,
  "visually_distinct_styles": true, "evidence": "..." }` after pixel inspection.
  Record concrete inspected layout/camera/material features, not just “passed”.
- `tool_check`: `{ "checked": true, "evidence": "..." }` with the tool inspected
  and its actual availability/result; needed for visual and fallback routes.
- `user_evidence`: the actual user's explicit style choice for `direct_choice`,
  or explicit permission to choose through text for `text_fallback`.
- `blocker`: concrete failed prerequisite/tool outcome; required for fallback.
- `selection`: `{ "style_id": "...", "user_evidence": "..." }` for production.

All evidence file paths resolve relative to the review JSON. A direct user style
choice skips comparison, but a workbench's default style does not qualify.
The text fallback requires both a real blocker/tool check and explicit user
permission. It is not triggered automatically by missing browser access.

The checker validates evidence presence, file type signatures and hash integrity.
It cannot prove image fidelity, actual user consent or that an image was displayed;
the Agent remains responsible for truthful records and visual review. Passing
style selection does not waive geometry, saved-state parity or final-image gates.
