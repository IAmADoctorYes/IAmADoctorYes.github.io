#!/usr/bin/env python3
"""
build-homegrown-site.py
=======================
Builds a standalone copy of the Homegrown Spirits shop website
for deployment to homegrownspirits.com (IAmADoctorYes/homegrown-spirits-website).

Source: shop/ directory + shared js/ and assets/ from the personal website.
Output: /tmp/homegrown-site/ (ready to push to homegrown-spirits-website repo).

Path transformations applied:
  - All /shop/ URL prefixes → / (root)
  - ../js/theme.js → js/theme.js  (top-level pages)
  - ../js/cart.js  → js/cart.js   (top-level pages)
  - ../../js/theme.js → ../js/theme.js  (artist/ subdir pages)
  - ../../js/cart.js  → ../js/cart.js   (artist/ subdir pages)
  - og:url / og:image absolute URLs → homegrownspirits.com
  - Footer portfolio links href="/" → https://www.sullivanrsteele.com
  - cart.js: .nav-links → .hs-nav-links
  - cart.js: PayPal order description → homegrownspirits.com
  - artists.json: shopPage /shop/artist/ → /artist/
"""

import os
import re
import shutil
from datetime import datetime, timezone

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO_ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_SHOP    = os.path.join(REPO_ROOT, 'shop')
SRC_JS      = os.path.join(REPO_ROOT, 'js')
SRC_ASSETS  = os.path.join(REPO_ROOT, 'assets')
OUT_DIR     = '/tmp/homegrown-site'


# ── Helpers ───────────────────────────────────────────────────────────────────

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def read(path):
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def write(path, content):
    ensure_dir(os.path.dirname(path))
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)


# ── Transformation helpers ────────────────────────────────────────────────────

def fix_shop_urls(content):
    """Replace all /shop/ URL prefix references with /."""
    # Specific href/src patterns first (most reliable)
    content = content.replace('href="/shop/"', 'href="/"')
    content = content.replace('href="/shop/catalog.html', 'href="/catalog.html')
    content = content.replace('href="/shop/artists.html', 'href="/artists.html')
    content = content.replace('href="/shop/policies.html', 'href="/policies.html')
    content = content.replace('href="/shop/artist/', 'href="/artist/')
    # Catch any remaining /shop/ references in href/src attributes
    content = re.sub(r'(href|src)="/shop/', r'\1="/', content)
    return content


def fix_og_urls(content):
    """Update Open Graph absolute URLs to use homegrownspirits.com."""
    content = content.replace(
        'https://www.sullivanrsteele.com/shop/',
        'https://www.homegrownspirits.com/'
    )
    content = content.replace(
        'https://www.sullivanrsteele.com/assets/portrait.jpg',
        'https://www.homegrownspirits.com/assets/portrait.jpg'
    )
    return content


def fix_portfolio_links(content):
    """Rewrite footer links that point back to the personal portfolio site."""
    # href="/">← Portfolio Site</a>
    content = re.sub(
        r'href="/">← Portfolio Site</a>',
        'href="https://www.sullivanrsteele.com">← Portfolio Site</a>',
        content
    )
    # href="/">sullivanrsteele.com</a>
    content = re.sub(
        r'href="/">sullivanrsteele\.com</a>',
        'href="https://www.sullivanrsteele.com">sullivanrsteele.com</a>',
        content
    )
    # href="/" title="Back to Sullivan Steele's portfolio"
    content = re.sub(
        r'href="/" title="Back to Sullivan Steele\'s portfolio"',
        'href="https://www.sullivanrsteele.com" title="Back to Sullivan Steele\'s portfolio"',
        content
    )
    return content


# ── Per-file-type transformations ─────────────────────────────────────────────

def transform_toplevel_html(content):
    """Transform HTML files at the root level of the shop site."""
    content = fix_og_urls(content)
    content = fix_portfolio_links(content)
    content = fix_shop_urls(content)
    # Relative JS paths from top-level page: ../js/ → js/
    content = content.replace('src="../js/theme.js"', 'src="js/theme.js"')
    content = content.replace('src="../js/cart.js"', 'src="js/cart.js"')
    return content


def transform_artist_html(content):
    """Transform HTML files inside the artist/ subdirectory."""
    content = fix_og_urls(content)
    content = fix_portfolio_links(content)
    content = fix_shop_urls(content)
    # Relative JS paths from artist/ subdir: ../../js/ → ../js/
    content = content.replace('src="../../js/theme.js"', 'src="../js/theme.js"')
    content = content.replace('src="../../js/cart.js"', 'src="../js/cart.js"')
    # artist-page.js and nav.js are in ../js/ (shop/js/ → js/), already relative
    # src="../js/artist-page.js" stays as-is (correct relative path in output)
    # src="../js/nav.js" stays as-is
    return content


def transform_shop_js(content):
    """Transform shop-specific JS files (featured, artists, catalog, artist-page, nav)."""
    # Data fetch URLs
    content = content.replace('/shop/assets/products.json', '/assets/products.json')
    content = content.replace('/shop/assets/artists.json', '/assets/artists.json')
    # Generated links inside JS
    content = content.replace('/shop/catalog.html', '/catalog.html')
    content = content.replace('/shop/artist/', '/artist/')
    # nav.js active-link detection
    content = content.replace("'/shop/' + navVal", "'/' + navVal")
    content = content.replace("path === '/shop/'", "path === '/'")
    content = content.replace("path === '/shop/index.html'", "path === '/index.html'")
    return content


def transform_cart_js(content):
    """Transform shared cart.js for the standalone shop."""
    # Inject cart icon into the shop nav (.hs-nav-links) instead of main site nav (.nav-links)
    content = content.replace(
        "document.querySelector('.nav-links')",
        "document.querySelector('.hs-nav-links')"
    )
    # Update PayPal order description
    content = content.replace(
        "'Order from sullivanrsteele.com'",
        "'Order from homegrownspirits.com'"
    )
    return content


def transform_artists_json(content):
    """Fix shopPage paths in artists.json."""
    content = content.replace('/shop/artist/', '/artist/')
    return content


# ── Service worker ────────────────────────────────────────────────────────────

SW_JS_TEMPLATE = """\
var CACHE_NAME = 'hs-site-{version}';
var STATIC_ASSETS = [
    '/',
    '/index.html',
    '/css/shop.css',
    '/js/theme.js',
    '/js/nav.js',
    '/js/cart.js',
    '/assets/products.json',
    '/assets/artists.json'
];

self.addEventListener('install', function (event) {{
    event.waitUntil(
        caches.open(CACHE_NAME).then(function (cache) {{
            return cache.addAll(STATIC_ASSETS);
        }})
    );
    self.skipWaiting();
}});

self.addEventListener('activate', function (event) {{
    event.waitUntil(
        caches.keys().then(function (names) {{
            return Promise.all(
                names
                    .filter(function (name) {{ return name !== CACHE_NAME; }})
                    .map(function (name) {{ return caches.delete(name); }})
            );
        }})
    );
    self.clients.claim();
}});

self.addEventListener('fetch', function (event) {{
    if (event.request.method !== 'GET') return;

    event.respondWith(
        fetch(event.request)
            .then(function (response) {{
                if (response && response.status === 200 && response.type === 'basic') {{
                    var clone = response.clone();
                    caches.open(CACHE_NAME).then(function (cache) {{
                        cache.put(event.request, clone);
                    }});
                }}
                return response;
            }})
            .catch(function () {{
                return caches.match(event.request).then(function (cached) {{
                    if (cached) return cached;
                    if (event.request.destination === 'document') {{
                        return caches.match('/index.html');
                    }}
                    return new Response('', {{ status: 503, statusText: 'Offline' }});
                }});
            }})
    );
}});
"""


# ── Main build ────────────────────────────────────────────────────────────────

def main():
    print(f"Building standalone Homegrown Spirits site → {OUT_DIR}")

    # Clean output directory
    if os.path.exists(OUT_DIR):
        shutil.rmtree(OUT_DIR)
    ensure_dir(OUT_DIR)

    # ── Top-level HTML pages ──────────────────────────────────────────────────
    for fname in ['index.html', 'catalog.html', 'artists.html', 'policies.html']:
        src = os.path.join(SRC_SHOP, fname)
        if os.path.exists(src):
            content = transform_toplevel_html(read(src))
            write(os.path.join(OUT_DIR, fname), content)
            print(f"  HTML  {fname}")

    # ── artist/ subdir HTML pages ─────────────────────────────────────────────
    artist_src_dir = os.path.join(SRC_SHOP, 'artist')
    artist_out_dir = os.path.join(OUT_DIR, 'artist')
    if os.path.isdir(artist_src_dir):
        for fname in os.listdir(artist_src_dir):
            if fname.endswith('.html'):
                content = transform_artist_html(read(os.path.join(artist_src_dir, fname)))
                write(os.path.join(artist_out_dir, fname), content)
                print(f"  HTML  artist/{fname}")

    # ── CSS ───────────────────────────────────────────────────────────────────
    css_src = os.path.join(SRC_SHOP, 'css', 'shop.css')
    css_out = os.path.join(OUT_DIR, 'css', 'shop.css')
    ensure_dir(os.path.join(OUT_DIR, 'css'))
    shutil.copy2(css_src, css_out)
    print(f"  CSS   css/shop.css")

    # ── Shop-specific JS files ────────────────────────────────────────────────
    ensure_dir(os.path.join(OUT_DIR, 'js'))
    for fname in ['featured.js', 'artists.js', 'catalog.js', 'artist-page.js', 'nav.js']:
        src = os.path.join(SRC_SHOP, 'js', fname)
        if os.path.exists(src):
            content = transform_shop_js(read(src))
            write(os.path.join(OUT_DIR, 'js', fname), content)
            print(f"  JS    js/{fname}")

    # ── Shared JS: theme.js (unchanged) ──────────────────────────────────────
    shutil.copy2(os.path.join(SRC_JS, 'theme.js'), os.path.join(OUT_DIR, 'js', 'theme.js'))
    print(f"  JS    js/theme.js")

    # ── Shared JS: cart.js (transformed) ─────────────────────────────────────
    content = transform_cart_js(read(os.path.join(SRC_JS, 'cart.js')))
    write(os.path.join(OUT_DIR, 'js', 'cart.js'), content)
    print(f"  JS    js/cart.js")

    # ── Data JSON files ───────────────────────────────────────────────────────
    ensure_dir(os.path.join(OUT_DIR, 'assets'))
    shutil.copy2(
        os.path.join(SRC_SHOP, 'assets', 'products.json'),
        os.path.join(OUT_DIR, 'assets', 'products.json')
    )
    print(f"  JSON  assets/products.json")

    content = transform_artists_json(read(os.path.join(SRC_SHOP, 'assets', 'artists.json')))
    write(os.path.join(OUT_DIR, 'assets', 'artists.json'), content)
    print(f"  JSON  assets/artists.json")

    # ── Image assets ──────────────────────────────────────────────────────────
    for fname in ['portrait.jpg', 'favicon.png', 'apple-touch-icon.png']:
        src = os.path.join(SRC_ASSETS, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(OUT_DIR, 'assets', fname))
            print(f"  IMG   assets/{fname}")
        else:
            print(f"  WARN  assets/{fname} not found — skipping")

    # ── Service worker (with build-time cache version for cache invalidation) ──
    build_version = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
    sw_content = SW_JS_TEMPLATE.format(version=build_version)
    write(os.path.join(OUT_DIR, 'sw.js'), sw_content)
    print(f"  SW    sw.js (cache version: hs-site-{build_version})")

    print(f"\nBuild complete: {OUT_DIR}")


if __name__ == '__main__':
    main()
