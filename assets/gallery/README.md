# Adding Gallery Images

Drop images into this folder and they'll appear on the Gallery page automatically
after the next push to `main`.

Images in `assets/projects/` are also scanned.

## Adding metadata

Create a JSON sidecar with the same name as the image:

```
assets/gallery/
  etched-glass-closeup.jpg
  etched-glass-closeup.json    ← metadata
  workshop-bench.jpg            ← no sidecar = defaults from filename
```

Or use a bulk `_gallery.json` manifest (same format as `gallery.json`):

```json
[
  {
    "src": "etched-glass-closeup.jpg",
    "alt": "Detail of sand-etched pint glass",
    "title": "Etched Glass Close-up",
    "description": "Custom sand-etched design on a pint glass.",
    "link": "/pages/shop.html",
    "tags": ["glasswork", "craft"]
  }
]
```

### Sidecar fields

```json
{
  "title": "Workshop Bench",
  "alt": "Woodworking bench with tools",
  "description": "Where most of the making happens.",
  "link": "",
  "tags": ["workshop"]
}
```

All fields are optional. If omitted, title and alt text are derived from
the filename.

## Supported image formats

`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`, `.svg`

## What happens

1. You push images (and optional sidecars) to `main`.
2. GitHub Actions runs `scripts/build-gallery-index.py`.
3. `assets/gallery.json` is regenerated and committed.
4. The site deploys and `gallery.js` loads the updated JSON.
