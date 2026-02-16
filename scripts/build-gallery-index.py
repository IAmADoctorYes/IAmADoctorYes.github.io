#!/usr/bin/env python3
"""Auto-build gallery.json from images in assets/gallery/ and assets/projects/.

Scans for image files. Metadata comes from an optional JSON sidecar
next to each image (same name, .json extension), or from a bulk
_gallery.json manifest in the scanned directory.

Sidecar example  (assets/gallery/etched-glass-closeup.json):
{
  "title": "Etched Glass Close-up",
  "alt": "Detail of sand-etched pint glass",
  "description": "Custom sand-etched design on a pint glass.",
  "link": "/pages/shop.html",
  "tags": ["glasswork", "craft"]
}

Fields the sidecar doesn't supply get sensible defaults from the filename.

Usage:  python scripts/build-gallery-index.py
"""

import json
import re
import sys
from pathlib import Path

SCAN_DIRS = [Path("assets/gallery"), Path("assets/projects")]
OUTPUT = Path("assets/gallery.json")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}


def title_from_filename(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"[-_]+", " ", stem).strip().title()


def load_json(path: Path) -> dict | list | None:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return None


def scan_dir(scan_dir: Path) -> list[dict]:
    if not scan_dir.is_dir():
        return []

    items = []
    covered = set()

    # Bulk manifest
    manifest_path = scan_dir / "_gallery.json"
    manifest = load_json(manifest_path)
    if isinstance(manifest, list):
        for entry in manifest:
            if not isinstance(entry, dict):
                continue
            src = entry.get("src", "")
            if src and not src.startswith("/") and not src.startswith("http"):
                entry["src"] = "/" + (scan_dir / src).as_posix()
            items.append(entry)
            if src:
                covered.add(Path(src).name)

    # Sidecar-based entries
    for f in sorted(scan_dir.iterdir()):
        if f.suffix.lower() not in IMAGE_EXTS:
            continue
        if f.name.startswith("_") or f.name.startswith("."):
            continue
        if f.name in covered:
            continue

        sidecar = f.with_suffix(".json")
        meta = load_json(sidecar) if sidecar.exists() else {}
        if not isinstance(meta, dict):
            meta = {}

        item = {
            "src": "/" + f.as_posix(),
            "alt": meta.get("alt", title_from_filename(f.name)),
            "title": meta.get("title", title_from_filename(f.name)),
            "description": meta.get("description", ""),
            "link": meta.get("link", ""),
            "tags": meta.get("tags", []),
        }
        items.append(item)

    return items


def main():
    all_items = []
    for d in SCAN_DIRS:
        all_items.extend(scan_dir(d))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(all_items, indent=2) + "\n", encoding="utf-8")
    print(f"gallery.json: {len(all_items)} item(s)")
    for item in all_items:
        print(f"  • {item.get('title', '?')}")


if __name__ == "__main__":
    main()
