# Adding Products

Drop product images and metadata into this folder and they'll appear on the Shop
page automatically after the next push to `main`.

## Two ways to add products

### Option 1: Bulk manifest (easiest)

Create a single `_products.json` file in this folder:

```json
[
  {
    "title": "Sand-Etched Pint Glass",
    "description": "Hand-etched glasswork featuring custom designs.",
    "price": "$35",
    "type": "physical",
    "image": "etched-glass.jpg",
    "link": "https://etsy.com/listing/...",
    "linkLabel": "Buy on Etsy",
    "tags": ["glasswork", "custom"]
  },
  {
    "title": "3D Printed Planter",
    "description": "Geometric planter, printed in PLA.",
    "price": "$20",
    "type": "physical",
    "image": "planter.jpg",
    "link": "https://etsy.com/listing/...",
    "linkLabel": "Buy on Etsy",
    "tags": ["3d-print"]
  }
]
```

Image paths in the manifest are relative to this folder.

### Option 2: Sidecar files (per-product)

Place an image and a matching `.json` sidecar:

```
assets/products/
  etched-glass.jpg
  etched-glass.json    ← metadata
  planter.png
  planter.json         ← metadata
```

### Sidecar fields

```json
{
  "title": "Sand-Etched Pint Glass",
  "description": "Hand-etched glasswork featuring custom designs.",
  "price": "$35",
  "type": "physical",
  "link": "https://etsy.com/listing/...",
  "linkLabel": "Buy on Etsy",
  "tags": ["glasswork", "custom"]
}
```

| Field       | Required? | Default                     |
|-------------|-----------|-----------------------------|
| title       | No        | Derived from filename       |
| description | No        | empty                       |
| price       | No        | empty                       |
| type        | No        | "physical"                  |
| link        | No        | mailto inquiry email        |
| linkLabel   | No        | "Inquire"                   |
| tags        | No        | empty array                 |

**Note:** Images without a sidecar `.json` are skipped — the build script
can't guess prices, so a sidecar is required for each product.

### Product types

Use `"type"` to categorize:

- `"physical"` — tangible goods (glasswork, wood items, stickers)
- `"digital"` — downloadable files (3D models, prints, templates)
- `"custom"` — commission / made-to-order

The shop page shows filter buttons when multiple types exist.

## Supported image formats

`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.svg`

## What happens

1. You push images + metadata to `main`.
2. GitHub Actions runs `scripts/build-shop-index.py`.
3. `assets/shop.json` is regenerated and committed.
4. The site deploys and `shop.js` loads the updated JSON.
