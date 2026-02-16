#!/usr/bin/env python3
"""
sync_docs_to_site.py

Sync HTML documents (e.g. exported Google Docs fragments) into a blog posts directory,
splitting very large posts into fragments for lazy-loading, and wrapping each post
in a clean HTML layout optimized for readability and accessibility.

Usage examples:
  python sync_docs_to_site.py --input-html exports/my-doc.html --posts-dir ../site/posts
  python sync_docs_to_site.py --input-dir exports/ --posts-dir ../site/posts --dry-run
"""

from __future__ import annotations

import argparse
import html as html_escape
import json
import logging
import re
import shutil
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup

# -----------------------
# Configurable constants
# -----------------------
LARGE_DOC_THRESHOLD = 8 * 1024 * 1024  # 8 MB before using chunked processing
CHUNK_SIZE = 2 * 1024 * 1024  # target chunk size for parts (2 MB)
DEFAULT_DATE_FORMAT = "%Y-%m-%d"

# -----------------------
# Logging setup
# -----------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
)
logger = logging.getLogger("sync_docs")


# -----------------------
# Helper dataclasses
# -----------------------
@dataclass
class DocMeta:
    title: str
    author: str
    date: str  # ISO-like string for display (e.g. 2026-02-16)


# -----------------------
# Utilities
# -----------------------
def slugify(value: str, allow_unicode: bool = False) -> str:
    """
    Convert to ASCII if 'allow_unicode' is False. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Lowercase. Good for filenames/slugs.
    """
    value = str(value).strip()
    if allow_unicode:
        value = unicodedata.normalize("NFKC", value)
    else:
        value = unicodedata.normalize("NFKD", value)
        value = value.encode("ascii", "ignore").decode("ascii")
    # Replace non-letter or digits with hyphen
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    value = re.sub(r"[\s_-]+", "-", value)
    value = re.sub(r"(^-+|-+$)", "", value)
    if not value:
        value = "post"
    return value


def safe_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """
    Atomically write text to path (same directory temporary file -> rename).
    Ensures partial writes don't leave corrupt files on failure.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with open(fd, "w", encoding=encoding) as f:
            f.write(text)
        tmp_path = Path(tmp)
        tmp_path.replace(path)
    except Exception:
        # If rename fails, try fallback write
        try:
            with open(path, "w", encoding=encoding) as f:
                f.write(text)
        except Exception as e:
            logger.exception("Failed to write %s: %s", path, e)
            raise
    finally:
        # ensure temp removed if exists
        try:
            if Path(tmp).exists():
                Path(tmp).unlink()
        except Exception:
            pass


def ensure_unique_filename(posts_dir: Path, base: str, ext: str = ".html") -> str:
    """
    Ensure the returned filename (basename + ext) doesn't collide in posts_dir
    by appending -1, -2, etc.
    """
    i = 0
    candidate = f"{base}{ext}"
    while (posts_dir / candidate).exists():
        i += 1
        candidate = f"{base}-{i}{ext}"
    return candidate


def extract_body_fragment(html_str: str) -> str:
    """
    Return inner HTML fragment from <body> if present, otherwise entire HTML string.
    It also strips leading/trailing whitespace-only nodes.
    """
    soup = BeautifulSoup(html_str, "html.parser")
    body = soup.body or soup
    parts = []
    for node in list(body.children):
        s = str(node)
        if not s.strip():
            continue
        parts.append(s)
    if not parts:
        # fallback to the whole HTML
        return html_str
    return "".join(parts)


def parse_date_string(s: Optional[str]) -> Optional[str]:
    """
    Try common date formats to parse a string into ISO-like 'YYYY-MM-DD'.
    If parsing fails, return None.
    """
    if not s:
        return None
    s = s.strip()
    candidates = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%B %d, %Y",
        "%b %d, %Y",
        "%Y.%m.%d",
    ]
    for fmt in candidates:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime(DEFAULT_DATE_FORMAT)
        except Exception:
            continue
    # last-ditch: try to parse YYYYMMDD or numeric timestamp
    m = re.search(r"(\d{4})[-/]?(\d{2})[-/]?(\d{2})", s)
    if m:
        try:
            return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
        except Exception:
            pass
    return None


# -----------------------
# Chunking & HTML builders
# -----------------------
def split_html_into_chunks(html_str: str, approx_chunk_bytes: int = CHUNK_SIZE) -> List[str]:
    """
    Split an HTML fragment into a list of HTML fragments of roughly approx_chunk_bytes each.
    We split at top-level body children to keep logical sections intact.
    """
    soup = BeautifulSoup(html_str, "html.parser")
    body = soup.body or soup
    parts: List[str] = []
    current: List[str] = []
    current_size = 0

    for node in list(body.children):
        s = str(node)
        if not s.strip():
            continue
        b = len(s.encode("utf-8"))
        if current and (current_size + b > approx_chunk_bytes):
            parts.append("".join(current))
            current = [s]
            current_size = b
        else:
            current.append(s)
            current_size += b

    if current:
        parts.append("".join(current))
    if not parts:
        parts = [html_str]
    return parts


def build_post_html(title: str, author: str, date_str: str, doc_content_html: str, parts_filenames: Optional[List[str]] = None) -> str:
    """
    Wrap the extracted doc HTML in site layout, with improved styles and JS for parts lazy-loading.
    """
    esc_title = html_escape.escape(title)
    esc_author = html_escape.escape(author)
    esc_date = html_escape.escape(date_str)
    parts_json = json.dumps(parts_filenames or [])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{esc_title}">
  <title>{esc_title} | {esc_author}</title>

  <!-- Google Fonts for clean reading -->
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&family=Noto+Serif:wght@400;700&display=swap" rel="stylesheet">

  <link rel="stylesheet" href="../../css/main.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">

  <style>
    :root {{
      --bg: #ffffff;
      --text: #0b0b0b;
      --muted: #5b5b5b;
      --accent: #0b66ff;
      --card-bg: #ffffff;
      --code-bg: #f5f5f5;
      --shadow: rgba(11,12,15,0.06);
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #080808;
        --text: #f6f6f6;
        --muted: #cfcfcf;
        --accent: #6ea8ff;
        --card-bg: #0b0b0b;
        --code-bg: #111111;
        --shadow: rgba(0,0,0,0.6);
      }}
    }}
    html,body {{
      height: 100%;
      margin: 0;
      background: var(--bg);
      color: var(--text);
      -webkit-font-smoothing:antialiased;
      font-family: 'Roboto', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
    }}
    .page-content {{ padding: 24px; max-width: 1200px; margin: 0 auto; }}
    .docs-content-container {{
      max-width: 900px;
      margin: 1.25rem auto;
      padding: 2em;
      background: var(--card-bg);
      border-radius: 12px;
      box-shadow: 0 6px 20px var(--shadow);
      line-height: 1.6;
      font-size: 18px;
    }}
    .docs-content-container h1, .docs-content-container h2, .docs-content-container h3 {{
      font-family: 'Noto Serif', Georgia, serif;
      color: var(--text);
      margin-top: 1.2em;
    }}
    .docs-content-container h1 {{ font-size: 2.0rem; }}
    .docs-content-container h2 {{ font-size: 1.5rem; }}
    .docs-content-container p {{ margin: 0.9em 0; color: var(--text); }}
    .docs-content-container img {{ max-width: 100%; height: auto; display:block; margin: .8rem 0; }}
    blockquote {{
      border-left: 4px solid var(--muted);
      margin: 1rem 0;
      padding: 0.6rem 1rem;
      color: var(--muted);
      background: transparent;
      border-radius: 4px;
    }}
    pre, code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, 'Roboto Mono', monospace;
      border-radius: 6px;
      padding: 0.4rem 0.6rem;
      background: var(--code-bg);
      overflow-x: auto;
      display: block;
      margin: 0.75rem 0;
    }}
    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1rem 0;
    }}
    table th, table td {{
      border: 1px solid #ddd;
      padding: 0.5rem;
      text-align: left;
      background: transparent;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .load-more-btn {{
      display:inline-block;
      margin: 1rem 0;
      padding: 0.5rem 0.9rem;
      border-radius: 8px;
      border: none;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <nav> ... </nav>
  <main id="main" class="page-content">
    <div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../blog.html">Blog</a> / {esc_title}</div>
    <article class="article-content">
      <header>
        <h1>{esc_title}</h1>
        <div class="article-meta" style="color:var(--muted);font-size:0.95rem;margin-top:.25rem;">
          <span><i class="bi bi-calendar3"></i> {esc_date}</span>
          <span style="margin-left:1rem;"><i class="bi bi-person"></i> {esc_author}</span>
        </div>
      </header>

      <div id="docs-container" class="docs-content-container">
        {doc_content_html}
      </div>

      <div id="docs-loading-placeholder" style="margin-top: 0.5rem;"></div>
    </article>
  </main>
  <footer> ... </footer>

  <script>
    const PARTS = {parts_json};
    if (Array.isArray(PARTS) && PARTS.length > 1) {{
      const placeholder = document.getElementById('docs-loading-placeholder');
      const btn = document.createElement('button');
      btn.className = 'load-more-btn';
      btn.textContent = 'Load full document';
      btn.onclick = async function() {{
        btn.disabled = true;
        btn.textContent = 'Loading...';
        const container = document.getElementById('docs-container');
        for (let i = 1; i < PARTS.length; i++) {{
          try {{
            const resp = await fetch(PARTS[i]);
            if (!resp.ok) {{
              console.error('Failed to load part', PARTS[i]);
              continue;
            }}
            const html = await resp.text();
            const wrapper = document.createElement('div');
            wrapper.innerHTML = html;
            container.appendChild(wrapper);
          }} catch (e) {{
            console.error('Error loading part', PARTS[i], e);
          }}
        }}
        btn.style.display = 'none';
      }};
      placeholder.appendChild(btn);
    }}
  </script>
  <script src="../../js/nav.js"></script>
</body>
</html>
"""


# -----------------------
# Metadata extraction
# -----------------------
def extract_doc_meta(html_str: str, source_path: Optional[Path]) -> DocMeta:
    """
    Extract title, author, date from the HTML or fallback to sensible defaults.
    """
    soup = BeautifulSoup(html_str, "html.parser")

    # Title: try meta og:title, <title>, then first h1
    title = None
    for name in ("og:title", "twitter:title"):
        tag = soup.find("meta", property=name)
        if tag and tag.get("content"):
            title = tag["content"].strip()
            break
    if not title:
        tag = soup.find("meta", attrs={"name": "title"})
        if tag and tag.get("content"):
            title = tag["content"].strip()
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    if not title and source_path:
        title = source_path.stem

    # Author: try meta author, byline selectors
    author = None
    for m in ("author", "article:author"):
        tag = soup.find("meta", attrs={"name": m}) or soup.find("meta", attrs={"property": m})
        if tag and tag.get("content"):
            author = tag["content"].strip()
            break
    if not author:
        # common byline patterns
        byline = soup.select_one(".byline, .author, [rel='author']")
        if byline:
            author = byline.get_text(strip=True)
    if not author:
        author = "Unknown"

    # Date: try meta date published
    date_str = None
    for key in ("article:published_time", "date", "publication_date", "publishdate", "dc.date"):
        tag = soup.find("meta", attrs={"name": key}) or soup.find("meta", attrs={"property": key})
        if tag and tag.get("content"):
            date_str = parse_date_string(tag["content"].strip())
            if date_str:
                break
    if not date_str:
        # look for time element
        time_tag = soup.find("time")
        if time_tag and (time_tag.get("datetime") or time_tag.get_text()):
            date_str = parse_date_string(time_tag.get("datetime") or time_tag.get_text())
    if not date_str and source_path:
        try:
            mtime = datetime.fromtimestamp(source_path.stat().st_mtime)
            date_str = mtime.strftime(DEFAULT_DATE_FORMAT)
        except Exception:
            date_str = datetime.utcnow().strftime(DEFAULT_DATE_FORMAT)
    if not date_str:
        date_str = datetime.utcnow().strftime(DEFAULT_DATE_FORMAT)

    # Normalize title and author
    title = title or "Untitled"
    author = author or "Unknown"

    return DocMeta(title=title, author=author, date=date_str)


# -----------------------
# Main processing flow
# -----------------------
def process_single_file(source_path: Path, posts_dir: Path, dry_run: bool = False, force_overwrite: bool = False) -> Optional[Path]:
    """
    Process one HTML file: extract metadata, build final post HTML, split if large, write files.
    Returns path to written main post (or None on failure or dry-run).
    """
    logger.info("Processing %s", source_path)
    try:
        raw_html = source_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.exception("Failed to read %s: %s", source_path, e)
        return None

    docmeta = extract_doc_meta(raw_html, source_path)
    fragment = extract_body_fragment(raw_html)

    # decide post basename/slug
    base_slug = slugify(docmeta.title)
    post_basename = ensure_unique_filename(posts_dir, base_slug, ext=".html") if not force_overwrite else f"{base_slug}.html"
    post_path = posts_dir / post_basename

    # Decide whether to chunk
    try:
        doc_bytes_len = len(fragment.encode("utf-8"))
    except Exception:
        doc_bytes_len = 0

    if doc_bytes_len >= LARGE_DOC_THRESHOLD:
        logger.info("Document is large (%d bytes) -> splitting into parts", doc_bytes_len)
        parts_html = split_html_into_chunks(fragment, approx_chunk_bytes=CHUNK_SIZE)
        base_noext = post_basename[:-5]  # remove .html
        parts_filenames: List[str] = []
        for idx, part_html in enumerate(parts_html):
            part_name = f"{base_noext}.part{idx+1}.html"
            part_path = posts_dir / part_name
            if dry_run:
                logger.info("Would write part: %s (size: %d bytes)", part_path, len(part_html.encode("utf-8")))
            else:
                try:
                    safe_write_text(part_path, part_html)
                except Exception as e:
                    logger.exception("Failed writing part file %s: %s", part_path, e)
            parts_filenames.append(part_name)
        # keep first part inline
        doc_content_html = parts_html[0]
    else:
        parts_filenames = None
        doc_content_html = fragment

    final_html = build_post_html(title=docmeta.title, author=docmeta.author, date_str=docmeta.date, doc_content_html=doc_content_html, parts_filenames=parts_filenames)

    if dry_run:
        logger.info("Dry-run: would write main post %s (size: %d bytes). parts: %s", post_path, len(final_html.encode("utf-8")), parts_filenames or [])
        return None

    # Write final post file atomically
    try:
        safe_write_text(post_path, final_html)
        logger.info("Wrote post: %s", post_path)
        return post_path
    except Exception as e:
        logger.exception("Failed writing post %s: %s", post_path, e)
        return None


def process_input(input_html: Optional[Path], input_dir: Optional[Path], posts_dir: Path, dry_run: bool = False, force_overwrite: bool = False) -> None:
    """
    Entry point that processes either one input_html or all .html files in input_dir.
    """
    if not input_html and not input_dir:
        raise ValueError("Either input_html or input_dir must be provided")

    posts_dir.mkdir(parents=True, exist_ok=True)

    if input_html:
        process_single_file(input_html, posts_dir, dry_run=dry_run, force_overwrite=force_overwrite)
    else:
        # iterate .html files in input_dir
        files = sorted([p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in (".html", ".htm")])
        if not files:
            logger.warning("No HTML files found in %s", input_dir)
            return
        for f in files:
            try:
                process_single_file(f, posts_dir, dry_run=dry_run, force_overwrite=force_overwrite)
            except Exception:
                logger.exception("Processing of file %s failed; continuing", f)


# -----------------------
# CLI
# -----------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sync_docs_to_site", description="Sync HTML docs to blog posts with chunking + nice wrapper.")
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--input-html", type=Path, help="Path to single input HTML file")
    group.add_argument("--input-dir", type=Path, help="Path to directory containing HTML files (will process all .html/.htm files)")
    p.add_argument("--posts-dir", type=Path, required=True, help="Path to output posts directory (e.g., site/posts)")
    p.add_argument("--dry-run", action="store_true", help="Do not write files; show what would be done")
    p.add_argument("--force-overwrite", action="store_true", help="Allow overwriting existing filenames with deterministic slug (no suffixes). Use with caution.")
    p.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    input_html = args.input_html
    input_dir = args.input_dir
    posts_dir = args.posts_dir.expanduser().resolve()

    logger.debug("Args: input_html=%s input_dir=%s posts_dir=%s dry_run=%s", input_html, input_dir, posts_dir, args.dry_run)

    try:
        process_input(input_html=input_html, input_dir=input_dir, posts_dir=posts_dir, dry_run=args.dry_run, force_overwrite=args.force_overwrite)
    except Exception as e:
        logger.exception("Fatal error: %s", e)
        return 2

    logger.info("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
