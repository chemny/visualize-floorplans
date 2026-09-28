"""Read-only local dependency check. Does not certify image-provider access."""
import importlib.metadata
import json
import platform
import sys


def main():
    errors = []
    versions = {}
    if sys.version_info < (3, 11):
        errors.append("Python 3.11 or newer is required")
    for name in ("Pillow", "PyMuPDF"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            errors.append(f"Missing dependency: {name}")
    selected = None
    if "Pillow" in versions:
        from platform_support import find_font
        selected = find_font()
    print(json.dumps({"status": "FAIL" if errors else "PASS", "os": platform.system(),
                      "python": platform.python_version(), "dependencies": versions,
                      "font_found": selected is not None,
                      "warnings": [] if selected else ["CJK font unavailable: configure FLOORPLAN_FONT and visually inspect labels"],
                      "image_provider": "not checked; agent must verify reference-image editing capability",
                      "errors": errors}, ensure_ascii=True, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
