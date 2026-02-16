#!/usr/bin/env python3
"""Build a sitemap.xml from the search index.

Usage:  python scripts/build-sitemap.py
"""

import argparse
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

SITE_URL = "https://www.sullivanrsteele.com"
INDEX_PATH = "assets/search-index.json"
OUTPUT_PATH = "sitemap.xml"

PRIORITY_MAP = {
    "home": "1.0",
    "work": "0.9",
    "projects": "0.8",
    "project-detail": "0.7",
    "articles": "0.8",
    "article": "0.7",
    "about": "0.6",
    "gallery": "0.6",
    "music": "0.6",
    "shop": "0.6",
}


def build_sitemap(entries: list[dict]) -> str:
    urls = []
    for entry in entries:
        href = entry.get("href", "")
        loc = SITE_URL + href if href.startswith("/") else href
        cat = entry.get("category", "page")
        priority = PRIORITY_MAP.get(cat, "0.5")

        date = entry.get("date", "")
        lastmod = ""
        if date:
            lastmod = date[:10]

        urls.append(
            f"""  <url>
    <loc>{xml_escape(loc)}</loc>
    {f'<lastmod>{lastmod}</lastmod>' if lastmod else ''}
    <priority>{priority}</priority>
  </url>"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""


def main():
    parser = argparse.ArgumentParser(description="Build sitemap.xml")
    parser.add_argument("--root", default=".", help="Repository root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    index_file = root / INDEX_PATH

    if not index_file.exists():
        print(f"Search index not found at {index_file} — run build-search-index.py first.")
        sys.exit(0)

    entries = json.loads(index_file.read_text(encoding="utf-8"))
    sitemap_xml = build_sitemap(entries)

    out = root / OUTPUT_PATH
    out.write_text(sitemap_xml, encoding="utf-8")
    print(f"Generated sitemap with {len(entries)} URLs → {out}")


if __name__ == "__main__":
    main()
