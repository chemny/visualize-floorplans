# Runtime and portability

Target Python 3.11 or newer. Local drawing/tests use Pillow and PyMuPDF from
`requirements.txt`. Planning/validation mostly use the standard library.
PyMuPDF and optional rsvg-convert retain their own licenses; the repository's
license does not relicense dependencies. Review dependency licensing for the
intended redistribution/deployment before release.

Agent installation: detect a working Python interpreter, ask before installing
dependencies, prefer an isolated environment, then run check_environment.py and
the unit tests. No Blender, Node.js or browser automation is required for the Python planning
and drawing tools or H5 HTML construction. Browser export/capture additionally
requires existing Node.js, Playwright and Chromium; animation encoding requires
FFmpeg/ffprobe. Blender remains an optional branch. See
`h5-tools-and-case-schema.md` for explicit flags and dependency detection. rsvg-convert is an optional existing fallback,
not the standard Windows installation path.

From the skill root, with `python` denoting the detected interpreter:

```text
python -m pip install -r requirements.txt
python scripts/check_environment.py
python -m unittest discover -s scripts -p "test_*.py"
```

On macOS the interpreter may be python3; on Windows it may be python or py -3.
Invoke subprocesses using sys.executable, not a hard-coded shell alias. Older
reference commands using POSIX backslash continuations are illustrative: pass
arguments directly or on one line in PowerShell. Resolve paths from the skill
root and project directory; do not assume a drive, user folder, or current shell.
The agent must substitute real paths for documentation placeholders.

Pillow labels search Windows and macOS CJK fonts; FLOORPLAN_FONT overrides the
choice with a user-supplied licensed font path. Fonts are not bundled or
downloaded. A missing font produces a warning, not silent CJK certification.
SVG rendering has separate font fallback behavior: visually inspect Chinese
labels in exported PNGs, even if dependency checks pass.

Image generation is provided by the host agent's tool or an explicitly
configured provider, not by these Python scripts. Check reference-image input,
editing, output handling and user authorization before using it. Do not assume
Codex, Claude Code and OpenClaw have identical tools or credentials. Local CI
does not test those integrations, image quality, or continuous video.

## Local beta checks versus regression

The 0.2.0-beta.1 closeout checked syntax, command help, same-case HTML building,
Skill structure and archive integrity. Full regression and new-floorplan tests
are deferred. Installation must report that status instead of inheriting an old
passing test count. `h5.py doctor` is read-only and does not install or download
anything. Normal single-file HTML generation uses the bundled engine; source
maintenance alone requires existing esbuild and Three.js modules.


Fresh same-case verification on 2026-10-05 subsequently exercised 126 Python
regressions, 26 real browser interaction checks and the H5 media pipeline. See
`local-beta-status.md` for the scope and failed visual subject checks. This does
not remove the new-floorplan/platform or Seedance verification boundaries.


## 0.2.0-beta.3 release review

Production JSON reads/writes explicitly use UTF-8. Unicode and space-containing
paths are exercised through the route CLI; Windows path/file URL adapters, font
discovery and list-based subprocess calls are statically reviewed. Codex/macOS
is exercised; Windows, Claude Code and OpenClaw are not runtime-certified. See
[release validation](release-validation.md) for current checks and boundaries.


The same local evidence command can be run after installation on Windows or
macOS (replace placeholders with real paths):

```text
python scripts/release_smoke.py --out NEW_EMPTY_CHECK_DIR --node NODE_EXECUTABLE
```

It runs installed-source regression and Node subject checks, captures OS/version
and exit codes, and writes UTF-8 evidence. It installs nothing, calls no provider
and cannot approve a case. A successful report is separate from actual host-agent
Skill discovery and real browser/image/video validation.

## beta.4 local regression

`release_smoke.py` now includes the interaction/material/storage/lighting module tests. Source contains a module-type declaration for supported Node imports; ordinary offline HTML construction still requires no Node. Synthetic browser checks require existing Playwright/Chromium and a local HTTP server scoped only to their generated fixtures. They do not certify browser-host pointer-lock policies, Windows or physical phone hardware. Keep those results separately pending and retain the publication hold until actual cross-platform validation is supplied.
