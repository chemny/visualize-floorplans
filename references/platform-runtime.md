# Runtime and portability

Target Python 3.11 or newer. Local drawing/tests use Pillow and PyMuPDF from
`requirements.txt`. Planning/validation mostly use the standard library.
PyMuPDF and optional rsvg-convert retain their own licenses; the repository's
license does not relicense dependencies. Review dependency licensing for the
intended redistribution/deployment before release.

Agent installation: detect a working Python interpreter, ask before installing
dependencies, prefer an isolated environment, then run check_environment.py and
the unit tests. No Blender, Node.js, browser automation, or other private skill
is required for the local tools. rsvg-convert is an optional existing fallback,
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
