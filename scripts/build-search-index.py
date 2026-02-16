#!/usr/bin/env python3
"""Build a site-wide search index by crawling all HTML files in the repo.

No Google API credentials needed — this script reads the HTML on disk,
extracts metadata (title, description, tags, body text), and writes
assets/search-index.json.

Usage:
    python scripts/build-search-index.py          # from repo root
    python scripts/build-search-index.py --root .  # explicit root
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

INDEX_FILE = "assets/search-index.json"

# Directories / filenames to skip entirely
SKIP_DIRS = {".git", ".github", "node_modules", "__pycache__", "scripts"}
SKIP_FILES = {"_TEMPLATE.html"}

# Category rules: path prefix → (category label, icon class)
CATEGORY_RULES = [
    ("pages/blog/", "article", "bi-journal-text"),
    ("pages/projects/", "project-detail", "bi-file-earmark-text"),
    ("pages/my-work", "work", "bi-briefcase"),
    ("pages/projects.html", "projects", "bi-kanban"),
    ("pages/music", "music", "bi-music-note-beamed"),
    ("pages/shop", "shop", "bi-bag"),
    ("pages/about", "about", "bi-person"),
    ("pages/blog.html", "articles", "bi-journal-text"),
    ("pages/gallery", "gallery", "bi-images"),
    ("pages/passion-projects", "projects", "bi-kanban"),
    ("index.html", "home", "bi-house"),
]


class HTMLMetaExtractor(HTMLParser):
    """Lightweight HTML parser that pulls metadata + visible text."""

    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.keywords = []
        self.body_text_parts = []
        self._in_title = False
        self._in_body = False
        self._in_nav = False
        self._in_footer = False
        self._in_aside = False
        self._in_script = False
        self._in_style = False
        self._current_tag = None
        self._h1 = ""
        self._in_h1 = False

    # ---- tag tracking ----
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._current_tag = tag

        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._in_h1 = True
        elif tag == "body":
            self._in_body = True
        elif tag == "nav":
            self._in_nav = True
        elif tag == "footer":
            self._in_footer = True
        elif tag == "aside":
            self._in_aside = True
        elif tag == "script":
            self._in_script = True
        elif tag == "style":
            self._in_style = True
        elif tag == "meta":
            name = attrs_dict.get("name", "").lower()
            content = attrs_dict.get("content", "")
            if name == "description":
                self.description = content
            elif name == "keywords":
                self.keywords = [k.strip() for k in content.split(",") if k.strip()]

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag == "h1":
            self._in_h1 = False
        elif tag == "nav":
            self._in_nav = False
        elif tag == "footer":
            self._in_footer = False
        elif tag == "aside":
            self._in_aside = False
        elif tag == "script":
            self._in_script = False
        elif tag == "style":
            self._in_style = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_h1:
            self._h1 += data
        # Collect visible body text (skip nav/footer/aside/script/style)
        if (
            self._in_body
            and not self._in_nav
            and not self._in_footer
            and not self._in_aside
            and not self._in_script
            and not self._in_style
        ):
            stripped = data.strip()
            if stripped:
                self.body_text_parts.append(stripped)

    @property
    def clean_title(self):
        """Return the title without ' | Sullivan Steele' suffix."""
        raw = self.title.strip()
        return re.sub(r"\s*\|\s*Sullivan Steele$", "", raw).strip() or raw

    @property
    def heading(self):
        return self._h1.strip()

    @property
    def body_text(self):
        return " ".join(self.body_text_parts)


def categorize(rel_path: str):
    """Return (category, icon) based on the file's relative path."""
    normalized = rel_path.replace("\\", "/")
    for prefix, cat, icon in CATEGORY_RULES:
        if normalized.startswith(prefix) or normalized == prefix:
            return cat, icon
    return "page", "bi-file-earmark"


def index_file(filepath: Path, root: Path) -> dict | None:
    """Parse a single HTML file and return an index entry."""
    try:
        raw = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    parser = HTMLMetaExtractor()
    try:
        parser.feed(raw)
    except Exception:
        return None

    rel = filepath.relative_to(root).as_posix()
    title = parser.clean_title or parser.heading or rel
    category, icon = categorize(rel)

    # Build a preview from description or body text
    preview = parser.description or parser.body_text[:250]
    preview = re.sub(r"\s+", " ", preview).strip()
    if len(preview) > 250:
        preview = preview[:247] + "..."

    # Tags: combine explicit keywords + category
    tags = list(parser.keywords)
    if category not in tags:
        tags.append(category)

    # Use file modification time as date
    mtime = filepath.stat().st_mtime
    date_str = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

    # Build the URL path (relative to site root for href)
    href = "/" + rel if not rel.startswith("/") else rel

    return {
        "title": title,
        "slug": rel,
        "href": href,
        "preview": preview,
        "tags": tags,
        "category": category,
        "icon": icon,
        "date": date_str,
    }


def build_index(root: Path) -> list[dict]:
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skipped directories
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]

        for fname in filenames:
            if not fname.endswith(".html") or fname in SKIP_FILES:
                continue
            filepath = Path(dirpath) / fname
            entry = index_file(filepath, root)
            if entry:
                entries.append(entry)

    entries.sort(key=lambda e: e["date"], reverse=True)
    return entries


def main():
    parser = argparse.ArgumentParser(description="Build site-wide search index")
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument("--output", default=INDEX_FILE, help="Output JSON path")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {root} for HTML files...")
    entries = build_index(root)

    out_path = root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    print(f"Indexed {len(entries)} pages → {out_path}")

    # Print a summary by category
    cats = {}
    for e in entries:
        cats.setdefault(e["category"], []).append(e["title"])
    for cat, titles in sorted(cats.items()):
        print(f"  {cat}: {len(titles)}")
        for t in titles[:3]:
            print(f"    • {t}")
        if len(titles) > 3:
            print(f"    … and {len(titles) - 3} more")


if __name__ == "__main__":
    main()
