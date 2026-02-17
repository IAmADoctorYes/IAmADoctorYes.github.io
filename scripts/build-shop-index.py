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
  "price": 35.00,
  "type": "physical",
  "fulfillment": "handmade",
  "stock": 10,
  "weight": "1.2 lb",
  "shipping": { "domestic": 6.50, "international": 18.00 },
  "variants": [
    { "name": "Size", "options": ["16 oz", "12 oz"] }
  ],
  "tags": ["glasswork", "custom"]
}

The "image" field is auto-set from the matching image file if not provided.
An "images" array can list multiple product photos.

Usage:  python scripts/build-shop-index.py
"""

import json
import re
import sys
from pathlib import Path

PRODUCTS_DIR = Path("assets/products")
OUTPUT = Path("assets/shop.json")
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".svg"}

# Default shipping rates (USD) used when sidecar omits shipping info
DEFAULT_SHIPPING = {"domestic": 6.50, "international": 18.00}


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


def normalise_price(raw) -> float:
    """Accept a number or '$XX.XX' string; always return float."""
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        cleaned = re.sub(r"[^\d.]", "", raw)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


def normalise_product(entry: dict) -> dict:
    """Ensure every product has all required fields with correct types."""
    entry["price"] = normalise_price(entry.get("price", 0))
    entry.setdefault("type", "physical")
    entry.setdefault("fulfillment", "handmade")
    entry.setdefault("tags", [])
    entry.setdefault("description", "")

    # Stock: -1 means unlimited, omitted defaults to -1
    stock = entry.get("stock")
    entry["stock"] = int(stock) if stock is not None else -1

    # Weight
    entry.setdefault("weight", "")

    # Shipping — accept object or omit for defaults
    ship = entry.get("shipping")
    if not isinstance(ship, dict):
        if entry["fulfillment"] == "digital":
            entry["shipping"] = {"domestic": 0, "international": 0}
        else:
            entry["shipping"] = dict(DEFAULT_SHIPPING)
    else:
        entry["shipping"] = {
            "domestic": float(ship.get("domestic", DEFAULT_SHIPPING["domestic"])),
            "international": float(ship.get("international", DEFAULT_SHIPPING["international"])),
        }

    # Variants
    variants = entry.get("variants")
    if not isinstance(variants, list):
        entry["variants"] = []
    else:
        clean = []
        for v in variants:
            if isinstance(v, dict) and "name" in v and "options" in v:
                clean.append({"name": v["name"], "options": list(v["options"])})
        entry["variants"] = clean

    # Images — accept single "image" or "images" array
    images = entry.get("images")
    if not isinstance(images, list):
        img = entry.get("image", "")
        entry["images"] = [img] if img else []
    entry.setdefault("image", entry["images"][0] if entry["images"] else "")

    return entry


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
            # Resolve images array
            imgs = entry.get("images", [])
            if isinstance(imgs, list):
                resolved = []
                for i in imgs:
                    if i and not i.startswith("/") and not i.startswith("http"):
                        resolved.append("/" + (products_dir / i).as_posix())
                    else:
                        resolved.append(i)
                entry["images"] = resolved

            products.append(normalise_product(entry))
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

        image_path = "/" + f.as_posix()

        product = {
            "title": meta.get("title", title_from_filename(f.name)),
            "description": meta.get("description", ""),
            "price": meta.get("price", 0),
            "type": meta.get("type", "physical"),
            "fulfillment": meta.get("fulfillment", "handmade"),
            "stock": meta.get("stock"),
            "weight": meta.get("weight", ""),
            "shipping": meta.get("shipping"),
            "variants": meta.get("variants"),
            "image": image_path,
            "images": meta.get("images", [image_path]),
            "tags": meta.get("tags", []),
        }
        products.append(normalise_product(product))

    return products


def main():
    products = scan_products(PRODUCTS_DIR)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(products, indent=2) + "\n", encoding="utf-8")
    print(f"shop.json: {len(products)} product(s)")
    for p in products:
        price = p.get("price", 0)
        stock = p.get("stock", -1)
        stock_label = "unlimited" if stock == -1 else str(stock)
        print(f"  • {p.get('title', '?')} — ${price:.2f} (stock: {stock_label})")


if __name__ == "__main__":
    main()
