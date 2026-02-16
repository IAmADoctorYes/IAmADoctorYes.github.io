#!/usr/bin/env python3
"""Optimize images in asset directories.

Resizes large images and compresses JPEGs/PNGs for faster page loads.
Requires Pillow: pip install pillow

Usage:  python scripts/optimize-images.py
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Pillow not installed — skipping image optimization.")
    print("Install with: pip install pillow")
    sys.exit(0)

SCAN_DIRS = ["assets/gallery", "assets/products", "assets/projects"]
MAX_WIDTH = 1600
MAX_HEIGHT = 1200
JPEG_QUALITY = 82
PNG_OPTIMIZE = True

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def optimize_image(path: Path) -> bool:
    """Resize and compress a single image. Returns True if modified."""
    try:
        img = Image.open(path)
    except Exception as e:
        print(f"  Could not open {path.name}: {e}")
        return False

    original_size = path.stat().st_size
    modified = False

    if img.width > MAX_WIDTH or img.height > MAX_HEIGHT:
        img.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.LANCZOS)
        modified = True

    suffix = path.suffix.lower()
    save_kwargs = {}

    if suffix in (".jpg", ".jpeg"):
        save_kwargs["quality"] = JPEG_QUALITY
        save_kwargs["optimize"] = True
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        modified = True
    elif suffix == ".png":
        save_kwargs["optimize"] = PNG_OPTIMIZE
        modified = True
    elif suffix == ".webp":
        save_kwargs["quality"] = JPEG_QUALITY
        modified = True

    if modified:
        img.save(path, **save_kwargs)
        new_size = path.stat().st_size
        saved = original_size - new_size
        if saved > 0:
            print(f"  {path.name}: {original_size:,}B → {new_size:,}B (saved {saved:,}B)")
        else:
            print(f"  {path.name}: already optimal")
        return True

    return False


def main():
    parser = argparse.ArgumentParser(description="Optimize images for the web")
    parser.add_argument("--root", default=".", help="Repository root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    total = 0

    for scan_dir in SCAN_DIRS:
        d = root / scan_dir
        if not d.is_dir():
            continue

        images = [f for f in d.rglob("*") if f.suffix.lower() in EXTENSIONS]
        if not images:
            continue

        print(f"Optimizing {len(images)} image(s) in {scan_dir}/")
        for img_path in images:
            if optimize_image(img_path):
                total += 1

    print(f"\nOptimized {total} image(s) total.")


if __name__ == "__main__":
    main()
