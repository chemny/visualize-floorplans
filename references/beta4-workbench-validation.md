# Workbench stabilization · 0.2.0-beta.4

Local execution on 2026-10-06. No GitHub commit, push or publication. Reusable source changes and an independent case preview; no promotion over the formal workbench.

## Completed

- Shared build version and hashes, header version, matching local source archive.
- Tested modules for storage, pointer-lock diagnostics, material presentation, area validity, labels and permanent illumination.
- Wall-geometry changes visibly mark source room/floor partitions and areas pending. Undo restores status. Automatic repartition is explicitly deferred by the user; no automatic naming/material ownership.
- Main-light input coverage, room assignment and applicable finished-ceiling warnings. Unsupported component types and invalid fixture/material configuration fail before build; no silent invented light placement.
- Plain marble is case-local, identical in SVG/Canvas and exported metadata, included in style scope binding. Palette, grout and roughness remain unchanged.
- Fixed lighting independent of camera; adaptive pixel ratio. Storage/JSON/HTML export/reopen, controls and refusal fallback tested on fresh isolated synthetic fixtures.

## Executed checks

- 168 Python regression tests, eight subject-window Node checks, 21 module checks.
- 49 browser checks across rectangle, concave, nine-region pressure fixtures and emulated touch. Actual Chromium on macOS, isolated contexts; no user browser/profile access.
- Pressure scene: 108 chairs, 27 fixture records, nine permanent illumination groups; roughly 397,678 triangles and 1,147 draw calls. Sampled static/moving rates approximately 60 FPS (2 seconds per phase at 1440×900, DPR 2; effective DPR 1.5 idle/1 moving). This is a short local benchmark, not hardware-independent certification.
- Repeated edits: geometry and texture counts returned to baseline across all three fixtures. This bounded test is not a long-duration memory-leak proof.
- Synthetic screenshot inspection checked floor presentation, compact bird labels, night illumination and touch joystick. Not client visual approval.
- Current case input retains exactly the earlier walls, furniture, ceiling zones, fixtures and palette, except independent namespace and explicit plain-marble setting. Nine functional zones have enabled main lights; input check has no warnings.

## Pending boundaries

- Windows runtime and physical phones unavailable. Emulated touch cannot substitute for hardware.
- Embedded native pointer-lock permission remains controlled by the host. Only simulated refusal fallback was exercised here; no host permission bypass or installed application modification.
- Newly built client preview requires its own visual review; unchanged formal output remains preserved.
- No new real reference floorplan was interpreted. Cross-shape tests use synthetic data, not reconstruction-quality certification.
- Automatic repartition, Seedance and optional Blender are outside this agreed stabilization run.

## Reproduce

Use `release_smoke.py` for installed source, module and subject checks. For browser checks generate `synthetic_cases.py` fixtures and serve only that directory, then run `test_workbench_browser.mjs` with existing Playwright, Chromium, base URL, fixture and output paths. No test installs dependencies or grants approval. Component registry is regenerated with the bundled engine by `rebuild_h5.mjs`.
