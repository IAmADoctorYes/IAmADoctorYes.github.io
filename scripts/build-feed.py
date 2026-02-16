#!/usr/bin/env python3
"""Build an Atom feed from the search index.

Usage:  python scripts/build-feed.py
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

SITE_URL = "https://www.sullivanrsteele.com"
FEED_TITLE = "Sullivan Steele"
FEED_SUBTITLE = "Data scientist, maker, musician — articles, projects, and updates."
AUTHOR_NAME = "Sullivan Steele"

INDEX_PATH = "assets/search-index.json"
OUTPUT_PATH = "feed.xml"

INCLUDE_CATEGORIES = {"article", "project-detail", "work", "music", "shop"}


def build_atom_feed(entries: list[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    items_xml = []
    for entry in entries:
        cat = entry.get("category", "")
        if cat not in INCLUDE_CATEGORIES:
            continue

        href = entry.get("href", "")
        url = SITE_URL + href if href.startswith("/") else href
        title = xml_escape(entry.get("title", "Untitled"))
        preview = xml_escape(entry.get("preview", ""))
        date = entry.get("date", now)
        if not date.endswith("Z") and "+" not in date:
            date = date + "Z" if "T" in date else date + "T00:00:00Z"

        tags_xml = ""
        for tag in entry.get("tags", []):
            tags_xml += f'    <category term="{xml_escape(tag)}"/>\n'

        items_xml.append(
            f"""  <entry>
    <title>{title}</title>
    <link href="{xml_escape(url)}"/>
    <id>{xml_escape(url)}</id>
    <updated>{date}</updated>
    <summary>{preview}</summary>
{tags_xml}  </entry>"""
        )

    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>{xml_escape(FEED_TITLE)}</title>
  <subtitle>{xml_escape(FEED_SUBTITLE)}</subtitle>
  <link href="{SITE_URL}/feed.xml" rel="self" type="application/atom+xml"/>
  <link href="{SITE_URL}/" rel="alternate" type="text/html"/>
  <id>{SITE_URL}/</id>
  <updated>{now}</updated>
  <author>
    <name>{xml_escape(AUTHOR_NAME)}</name>
  </author>
{chr(10).join(items_xml)}
</feed>
"""
    return feed


def main():
    parser = argparse.ArgumentParser(description="Build Atom feed")
    parser.add_argument("--root", default=".", help="Repository root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    index_file = root / INDEX_PATH

    if not index_file.exists():
        print(f"Search index not found at {index_file} — run build-search-index.py first.")
        sys.exit(0)

    entries = json.loads(index_file.read_text(encoding="utf-8"))
    feed_xml = build_atom_feed(entries)

    out = root / OUTPUT_PATH
    out.write_text(feed_xml, encoding="utf-8")
    count = feed_xml.count("<entry>")
    print(f"Generated Atom feed with {count} entries → {out}")


if __name__ == "__main__":
    main()
