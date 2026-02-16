#!/usr/bin/env python3
"""Auto-build shop.json from product listings in assets/products/.

Two ways to list products:

  1. MANIFEST FILE — drop a _products.json in assets/products/ with an
     array of product objects.  This is the easiest bulk approach.

  2. SIDECAR FILES — for each product image, place a matching .json
     sidecar next to it (e.g. etched-glass.jpg + etched-glass.json).

Both methods are merged. Manifest entries come first, then sidecar entries
for any images not already covered by the manifest.

Sidecar / manifest entry example:
{
  "title": "Sand-Etched Pint Glass",
  "description": "Hand-etched glasswork featuring custom designs.",
  "price": "$35",
  "type": "physical",
  "link": "https://etsy.com/listing/...",
  "linkLabel": "Buy on Etsy",
  "tags": ["glasswork", "custom"]
}

The "image" field is auto-set from the matching image file if not provided.

Usage:  python scripts/build-shop-index.py
"""

import json
import re
import sys
from pathlib import Path

PRODUCTS_DIR = Path("assets/products")
OUTPUT = Path("assets/shop.json")
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


def scan_products(products_dir: Path) -> list[dict]:
    if not products_dir.is_dir():
        return []

    products = []
    covered_images = set()

    # 1. Load manifest if it exists
    manifest_path = products_dir / "_products.json"
    manifest = load_json(manifest_path)
    if isinstance(manifest, list):
        for entry in manifest:
            if not isinstance(entry, dict):
                continue
            # Resolve relative image paths
            img = entry.get("image", "")
            if img and not img.startswith("/") and not img.startswith("http"):
                entry["image"] = "/" + (products_dir / img).as_posix()
            elif img and not img.startswith("http"):
                pass  # already absolute
            products.append(entry)
            # Track which images the manifest covers
            if img:
                covered_images.add(Path(img).name)

    # 2. Scan for sidecar-based products
    for f in sorted(products_dir.iterdir()):
        if f.suffix.lower() not in IMAGE_EXTS:
            continue
        if f.name.startswith("_") or f.name.startswith("."):
            continue
        if f.name in covered_images:
            continue

        sidecar = f.with_suffix(".json")
        if not sidecar.exists():
            continue  # require sidecar for shop items (can't guess price)

        meta = load_json(sidecar)
        if not isinstance(meta, dict):
            continue

        product = {
            "title": meta.get("title", title_from_filename(f.name)),
            "description": meta.get("description", ""),
            "price": meta.get("price", ""),
            "type": meta.get("type", "physical"),
            "image": "/" + f.as_posix(),
            "link": meta.get("link", "mailto:sullivanrsteele@gmail.com?subject=Shop%20Inquiry"),
            "linkLabel": meta.get("linkLabel", "Inquire"),
            "tags": meta.get("tags", []),
        }
        products.append(product)

    return products


def main():
    products = scan_products(PRODUCTS_DIR)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(products, indent=2) + "\n", encoding="utf-8")
    print(f"shop.json: {len(products)} product(s)")
    for p in products:
        print(f"  • {p.get('title', '?')} — {p.get('price', 'N/A')}")


if __name__ == "__main__":
    main()
