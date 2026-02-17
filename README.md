# IAmADoctorYes.github.io
Personal portfolio & shop — [sullivanrsteele.com](https://www.sullivanrsteele.com)

## Architecture

Static site hosted on GitHub Pages. All content lives in the repo — no external APIs, no databases, no server-side code.

### Content pipeline

| Content type       | Where you put it              | Build step               | Output                   |
|--------------------|-------------------------------|--------------------------|--------------------------|
| Blog posts         | `content/blog/*.md`           | `build-blog.py`          | `pages/blog/*.html`      |
| Project write-ups  | `content/pdfs/*.pdf`          | `convert-pdfs.py`        | `pages/projects/*.html`  |
| Gallery images     | `assets/gallery/`             | `build-gallery-index.py` | `assets/gallery.json`    |
| Music tracks       | `assets/audio/`               | `build-music-index.py`   | `assets/music.json`      |
| Shop products      | `assets/products/`            | `build-shop-index.py`    | `assets/shop.json`       |

### How it deploys

1. You push to `main`
2. **`sync-content.yml`** runs all build scripts and commits generated artifacts
3. **`deploy-site.yml`** publishes the repo to GitHub Pages

### Shop & payments

The shop uses a **client-side cart** (`js/cart.js`) backed by `localStorage` with **PayPal Checkout** for payment processing. No monthly fees — PayPal charges standard per-transaction rates (2.9% + $0.30).

- Products are defined in `assets/shop.json` (auto-built from `assets/products/`)
- Cart persists across pages via localStorage
- Checkout creates a PayPal order with all cart items
- For print-on-demand / dropship items, link to your Printful store or fulfill manually after PayPal payment

#### Setup

1. Create a free [PayPal Business account](https://www.paypal.com/business)
2. Go to [developer.paypal.com](https://developer.paypal.com) → My Apps → Create App
3. Copy your **Client ID** and replace `YOUR_PAYPAL_CLIENT_ID` in `pages/shop.html`

### Adding a product

1. Drop an image in `assets/products/` (e.g. `my-glass.jpg`)
2. Create a matching `.json` sidecar (`my-glass.json`):
   ```json
   {
     "title": "Sand-Etched Pint Glass",
     "description": "Hand-etched with custom WV design",
     "price": 35.00,
     "type": "physical",
     "fulfillment": "handmade",
     "tags": ["glasswork", "drinkware"],
     "variants": [
       { "name": "Style", "options": ["Pint", "Rocks", "Wine"] }
     ],
     "stock": 8,
     "weight": 450,
     "shipping": { "domestic": 5.99, "international": 12.99 }
   }
   ```
3. Push — the pipeline builds `shop.json` automatically

### Local development

Open `index.html` in a browser or run a local server:
```bash
python -m http.server 8000
```

### Legacy sync command

If any workflow or local process still calls `python scripts/sync-google-docs.py`,
that command is now a **local-only compatibility runner**. It does not use Google
Drive or Google Docs APIs; it simply runs the repo build scripts in sequence.

Optional flags:

- `--root <path>`: set repository root
- `--skip-backgrounds`: skip optional background fetch step
