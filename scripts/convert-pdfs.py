#!/usr/bin/env python3
"""Convert PDFs in content/pdfs/ to site HTML pages.

Reads each .pdf, extracts text with PyMuPDF (fitz), wraps it in the
site template, and writes pages/projects/<slug>.html.  Originals are
copied to assets/pdfs/ so every generated page can offer a download link.

If a .json sidecar exists next to the PDF it supplies metadata (title,
description, date, tags, type, route, category).  Otherwise the script
derives sensible defaults from the filename and PDF contents.

Requires: PyMuPDF  (pip install pymupdf)

Usage:
    python scripts/convert-pdfs.py             # from repo root
    python scripts/convert-pdfs.py --root .    # explicit root
"""

import argparse
import json
import os
import re
import shutil
import sys
import textwrap
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:
    print(
        "PyMuPDF is required.  Install it with:  pip install pymupdf",
        file=sys.stderr,
    )
    sys.exit(1)

PDF_SOURCE = "content/pdfs"
PDF_DEST = "assets/pdfs"
PAGE_DEST = "pages/projects"

BODY_CHAR_LIMIT = 6000


def slug_from_filename(name: str) -> str:
    stem = Path(name).stem
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug


def extract_pdf_text(pdf_path: Path) -> str:
    doc = fitz.open(str(pdf_path))
    parts = []
    for page in doc:
        parts.append(page.get_text())
    doc.close()
    return "\n".join(parts)


def load_sidecar(pdf_path: Path) -> dict:
    json_path = pdf_path.with_suffix(".json")
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def title_from_filename(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"[-_]+", " ", stem).strip().title()


def make_preview(text: str, limit: int = 200) -> str:
    clean = re.sub(r"\s+", " ", text).strip()
    if len(clean) > limit:
        clean = clean[:limit].rsplit(" ", 1)[0] + "..."
    return clean


def text_to_html_sections(raw_text: str) -> str:
    """Turn raw PDF text into simple HTML paragraphs."""
    text = raw_text[:BODY_CHAR_LIMIT]
    lines = text.split("\n")
    paragraphs = []
    buf = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
        else:
            buf.append(stripped)
    if buf:
        paragraphs.append(" ".join(buf))

    html_parts = []
    for para in paragraphs:
        if not para:
            continue
        escaped = html_escape(para)
        html_parts.append(f"                    <p>{escaped}</p>")

    return "\n".join(html_parts)


def build_tags_html(tags: list[str]) -> str:
    if not tags:
        return ""
    colors = ["tag-green", "tag-orange", "tag-blue", ""]
    parts = []
    for i, tag in enumerate(tags):
        cls = colors[i % len(colors)]
        extra = f" {cls}" if cls else ""
        parts.append(
            f'<span class="tag{extra}">{html_escape(tag)}</span>'
        )
    return "\n                        ".join(parts)


def generate_page(
    slug: str,
    title: str,
    description: str,
    date_str: str,
    doc_type: str,
    route: str,
    tags: list[str],
    body_html: str,
    pdf_download_path: str,
) -> str:
    tags_html = build_tags_html(tags)
    return textwrap.dedent(f"""\
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{html_escape(description)}">
    <title>{html_escape(title)} | Sullivan Steele</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <link rel="stylesheet" href="../../css/main.css">
    <script src="../../js/theme.js"></script>
    <script defer data-domain="sullivanrsteele.com" src="https://plausible.io/js/script.js"></script>
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
    <meta property="og:title" content="{html_escape(title)} | Sullivan Steele">
    <meta property="og:description" content="{html_escape(description)}">
    <meta property="og:image" content="https://www.sullivanrsteele.com/assets/portrait.jpg">
    <meta property="og:url" content="https://www.sullivanrsteele.com/pages/projects/{slug}.html">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{html_escape(title)}">
    <meta name="twitter:description" content="{html_escape(description)}">
    <meta name="twitter:image" content="https://www.sullivanrsteele.com/assets/portrait.jpg">
</head>
<body data-route="{html_escape(route)}">
    <a href="#main" class="skip-link">Skip to main content</a>

    <nav>
        <div class="nav-container">
            <a href="../../index.html" class="nav-logo">SULLIVAN STEELE</a>
            <button type="button" class="menu-toggle" aria-label="Toggle navigation" aria-expanded="false" aria-controls="nav-links">
                <span></span><span></span><span></span>
            </button>
            <ul class="nav-links" id="nav-links">
                <li><a href="../../index.html" data-nav-route="home">Home</a></li>
                <li><a href="../my-work.html" data-nav-route="my-work">My Work</a></li>
                <li><a href="../projects.html" data-nav-route="projects">Projects</a></li>
                <li><a href="../blog.html" data-nav-route="blog">Articles &amp; Reports</a></li>
                <li><a href="../gallery.html" data-nav-route="gallery">Gallery</a></li>
                <li><a href="../about.html" data-nav-route="about">About</a></li>
                <li><a href="../music.html" data-nav-route="music">Music</a></li>
                <li><a href="../shop.html" data-nav-route="shop">Shop</a></li>
                <li><button type="button" class="site-search-toggle" aria-label="Search the site"><i class="bi bi-search"></i></button></li>
                <li><button type="button" class="theme-toggle" aria-label="Toggle theme"><i class="bi bi-sun"></i></button></li>
            </ul>
        </div>
    </nav>

    <div class="site-layout">
        <main id="main" class="page-content">
            <div class="breadcrumb">
                <a href="../../index.html" data-nav-route="home">Home</a>
                <span class="sep">/</span>
                <a href="../my-work.html" data-nav-route="my-work">My Work</a>
                <span class="sep">/</span>
                {html_escape(title)}
            </div>

            <article class="article-content">
                <header class="article-header">
                    <h1>{html_escape(title)}</h1>
                    <div class="article-meta">
                        <span><i class="bi bi-calendar3"></i> {html_escape(date_str)}</span>
                        <span><i class="bi bi-person"></i> Sullivan Steele</span>
                        <span><i class="bi bi-file-earmark-text"></i> {html_escape(doc_type)}</span>
                    </div>
                    <div class="article-tags">
                        {tags_html}
                    </div>
                    <div class="pdf-actions">
                        <a href="{pdf_download_path}" class="btn btn-primary pdf-btn" download>
                            <i class="bi bi-download"></i> Download PDF
                        </a>
                        <a href="{pdf_download_path}" class="btn btn-secondary pdf-btn" target="_blank" rel="noopener">
                            <i class="bi bi-file-earmark-pdf"></i> View PDF
                        </a>
                    </div>
                </header>

                <section id="content">
                    <h2>Contents</h2>
{body_html}
                </section>

                <div class="callout info">
                    <p>
                        This page was generated from a PDF.
                        For best formatting, <a href="{pdf_download_path}" target="_blank" rel="noopener">view or download the original</a>.
                    </p>
                </div>
            </article>
        </main>

        <aside class="sidebar" aria-label="Table of contents">
            <div class="sidebar-section">
                <h4>Pages</h4>
                <ul>
                    <li><a href="../../index.html" data-nav-route="home">Home</a></li>
                    <li><a href="../my-work.html" data-nav-route="my-work">My Work</a></li>
                    <li><a href="../projects.html" data-nav-route="projects">Projects</a></li>
                    <li><a href="../blog.html" data-nav-route="blog">Articles &amp; Reports</a></li>
                    <li><a href="../gallery.html" data-nav-route="gallery">Gallery</a></li>
                    <li><a href="../about.html" data-nav-route="about">About</a></li>
                    <li><a href="../music.html" data-nav-route="music">Music</a></li>
                    <li><a href="../shop.html" data-nav-route="shop">Shop</a></li>
                </ul>
            </div>
            <div class="sidebar-section">
                <h4>Document</h4>
                <ul>
                    <li><a href="{pdf_download_path}" download><i class="bi bi-download"></i> Download PDF</a></li>
                    <li><a href="{pdf_download_path}" target="_blank" rel="noopener"><i class="bi bi-file-earmark-pdf"></i> View PDF</a></li>
                </ul>
            </div>
        </aside>
    </div>

    <footer>
        <div class="footer-inner">
            <p>&copy; {datetime.now().year} Sullivan Steele</p>
            <ul class="footer-links">
                <li><a href="mailto:sullivanrsteele@gmail.com">Email</a></li>
                <li><a href="https://github.com/IAmADoctorYes" target="_blank" rel="noopener">GitHub</a></li>
                <li><a href="https://www.linkedin.com/in/sullivan-steele-166102140" target="_blank" rel="noopener">LinkedIn</a></li>
            </ul>
        </div>
    </footer>

    <script src="../../js/cart.js"></script>
    <script src="../../js/search.js"></script>
    <script src="../../js/nav.js"></script>
    <script src="../../js/backgrounds.js"></script>
    <script src="../../js/enhancements.js"></script>
    <script>if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');</script>
</body>
</html>
""")


def process_pdf(pdf_path: Path, root: Path) -> dict | None:
    slug = slug_from_filename(pdf_path.name)
    meta = load_sidecar(pdf_path)

    raw_text = extract_pdf_text(pdf_path)
    if not raw_text.strip():
        print(f"  Skipping {pdf_path.name}: no extractable text")
        return None

    title = meta.get("title") or title_from_filename(pdf_path.name)
    description = meta.get("description") or make_preview(raw_text)
    date_str = meta.get("date") or datetime.fromtimestamp(
        pdf_path.stat().st_mtime, tz=timezone.utc
    ).strftime("%Y-%m-%d")
    doc_type = meta.get("type", "Document")
    route = meta.get("route", "my-work")
    tags = meta.get("tags", [])
    category = meta.get("category", "project-detail")

    body_html = text_to_html_sections(raw_text)
    pdf_download_path = f"/assets/pdfs/{slug}.pdf"

    dest_pdf = root / PDF_DEST / f"{slug}.pdf"
    dest_pdf.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pdf_path, dest_pdf)
    print(f"  Copied PDF -> {dest_pdf.relative_to(root)}")

    page_html = generate_page(
        slug=slug,
        title=title,
        description=description,
        date_str=date_str,
        doc_type=doc_type,
        route=route,
        tags=tags,
        body_html=body_html,
        pdf_download_path=pdf_download_path,
    )

    dest_html = root / PAGE_DEST / f"{slug}.html"
    dest_html.parent.mkdir(parents=True, exist_ok=True)
    dest_html.write_text(page_html, encoding="utf-8")
    print(f"  Generated   -> {dest_html.relative_to(root)}")

    return {
        "slug": slug,
        "title": title,
        "description": description,
        "href": f"/pages/projects/{slug}.html",
        "date": date_str,
        "tags": tags,
        "category": category,
    }


def main():
    parser = argparse.ArgumentParser(description="Convert PDFs to site pages")
    parser.add_argument("--root", default=".", help="Repository root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    src_dir = root / PDF_SOURCE

    if not src_dir.is_dir():
        print(f"No PDF source directory at {src_dir} â€” nothing to convert.")
        return

    pdfs = sorted(src_dir.glob("*.pdf"))
    if not pdfs:
        print("No PDFs found in content/pdfs/ â€” nothing to convert.")
        return

    print(f"Found {len(pdfs)} PDF(s) in {src_dir.relative_to(root)}")
    converted = []
    for pdf_path in pdfs:
        print(f"Processing: {pdf_path.name}")
        result = process_pdf(pdf_path, root)
        if result:
            converted.append(result)

    print(f"\nConverted {len(converted)} PDF(s) to HTML pages.")


if __name__ == "__main__":
    main()
