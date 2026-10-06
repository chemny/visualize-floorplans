# Third-party code and examples

## Three.js

Bundled browser runtime and imported geometries come from Three.js (version
recorded in `assets/h5/runtime/dependencies.json`). Three.js is MIT licensed;
its complete license is preserved in `assets/h5/runtime/THREE-LICENSE.txt`.
Source maintenance uses existing esbuild; the distributable runtime does not
include esbuild binaries or a node_modules directory.

## Floorplan reference workbench

The H5 interface, furniture symbols, procedural furniture details and portions
of interaction code were adapted from https://github.com/wy51ai/floorplan-3d,
reference commit `a03136c`. Attribution remains in the template. The upstream
repository now declares MIT licensing; its LICENSE added in commit
`fbcb8d56a12090f53551ddaa7ae31ae4886a94d1` was verified on 2026-10-06.
The complete copyright and permission notice is preserved in
`assets/h5/FLOORPLAN-REFERENCE-LICENSE.txt` and applies to the adapted portions.
The earlier local checkout lacked that file; this historical absence is not the
current upstream license status. Dependency metadata records both source and
license revisions.

## Other dependencies and examples

Pillow, PyMuPDF, optional Blender, Chromium, Playwright and other runtimes retain
their licenses. No accounts, API credentials or browser profiles are included. The bundled
Jujian reference case is included at its provider’s explicit publication request;
case materials retain their respective rights and are not relicensed by the
source-code MIT license. The pre-existing published showcase has its recorded owner
permission; it is an early concept example, not the approved current apartment.
Synthetic examples are explicitly labelled and do not carry client approval.
