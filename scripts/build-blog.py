#!/usr/bin/env python3
"""Convert Markdown blog posts in pages/blog/ to HTML pages.

Reads .md files with YAML front-matter, converts the body to HTML,
and writes full site-themed pages into the same directory.

Usage:  python scripts/build-blog.py
"""

import argparse
import re
import sys
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path

BLOG_DIR = "pages/blog"

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_front_matter(text: str) -> tuple[dict, str]:
    """Split YAML front-matter from Markdown body."""
    m = FRONT_MATTER_RE.match(text)
    meta = {}
    body = text
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key == "tags":
                    meta[key] = [t.strip() for t in val.split(",") if t.strip()]
                else:
                    meta[key] = val
        body = text[m.end():]
    return meta, body


def md_to_html(md: str) -> str:
    """Minimal Markdown-to-HTML converter (no external deps)."""
    lines = md.split("\n")
    html_parts = []
    in_code = False
    in_ul = False
    in_ol = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("```"):
            if in_code:
                html_parts.append("</code></pre>")
                in_code = False
            else:
                lang = stripped[3:].strip()
                code_class = f' class="language-{html_escape(lang)}"' if lang else ""
                html_parts.append(f"<pre><code{code_class}>")
                in_code = True
            continue

        if in_code:
            html_parts.append(html_escape(line))
            continue

        if not stripped:
            if in_ul:
                html_parts.append("</ul>")
                in_ul = False
            if in_ol:
                html_parts.append("</ol>")
                in_ol = False
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_ul:
                html_parts.append("<ul>")
                in_ul = True
            html_parts.append(f"<li>{inline(stripped[2:])}</li>")
            continue

        ol_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
        if ol_match:
            if not in_ol:
                html_parts.append("<ol>")
                in_ol = True
            html_parts.append(f"<li>{inline(ol_match.group(2))}</li>")
            continue

        if in_ul:
            html_parts.append("</ul>")
            in_ul = False
        if in_ol:
            html_parts.append("</ol>")
            in_ol = False

        if stripped.startswith("#### "):
            html_parts.append(f"<h4>{inline(stripped[5:])}</h4>")
        elif stripped.startswith("### "):
            html_parts.append(f"<h3>{inline(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            html_parts.append(f"<h2>{inline(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            html_parts.append(f"<h1>{inline(stripped[2:])}</h1>")
        elif stripped.startswith("!["):
            img_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", stripped)
            if img_match:
                alt = html_escape(img_match.group(1))
                src = html_escape(img_match.group(2))
                html_parts.append(f'<img src="{src}" alt="{alt}" loading="lazy">')
            else:
                html_parts.append(f"<p>{inline(stripped)}</p>")
        elif stripped.startswith("> "):
            html_parts.append(f'<blockquote class="callout"><p>{inline(stripped[2:])}</p></blockquote>')
        elif stripped.startswith("---"):
            html_parts.append("<hr>")
        else:
            html_parts.append(f"<p>{inline(stripped)}</p>")

    if in_ul:
        html_parts.append("</ul>")
    if in_ol:
        html_parts.append("</ol>")
    if in_code:
        html_parts.append("</code></pre>")

    return "\n".join(html_parts)


def inline(text: str) -> str:
    """Convert inline Markdown (bold, italic, code, links)."""
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"__(.+?)__", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"_(.+?)_", r"<em>\1</em>", text)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    return text


def build_tags_html(tags: list[str]) -> str:
    colors = ["tag-green", "tag-orange", "tag-blue", ""]
    parts = []
    for i, tag in enumerate(tags):
        cls = colors[i % len(colors)]
        extra = f" {cls}" if cls else ""
        parts.append(f'<span class="tag{extra}">{html_escape(tag)}</span>')
    return "\n                        ".join(parts)


def generate_blog_page(meta: dict, body_html: str) -> str:
    title = html_escape(meta.get("title", "Untitled"))
    description = html_escape(meta.get("description", ""))
    date = meta.get("date", "")
    tags = meta.get("tags", [])
    tags_html = build_tags_html(tags)
    route = meta.get("route", "blog")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <title>{title} | Sullivan Steele</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <link rel="stylesheet" href="../../css/main.css">
    <script src="../../js/theme.js"></script>
    <script defer data-domain="sullivanrsteele.com" src="https://plausible.io/js/script.js"></script>
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
    <link rel="alternate" type="application/atom+xml" title="Sullivan Steele" href="/feed.xml">
    <meta property="og:title" content="{title} | Sullivan Steele">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="https://www.sullivanrsteele.com/assets/portrait.jpg">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{title}">
    <meta name="twitter:description" content="{description}">
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
                <a href="../../index.html">Home</a>
                <span class="sep">/</span>
                <a href="../blog.html">Articles &amp; Reports</a>
                <span class="sep">/</span>
                {title}
            </div>

            <article class="article-content">
                <header class="article-header">
                    <h1>{title}</h1>
                    <div class="article-meta">
                        <span><i class="bi bi-calendar3"></i> {html_escape(date)}</span>
                        <span><i class="bi bi-person"></i> Sullivan Steele</span>
                    </div>
                    <div class="article-tags">
                        {tags_html}
                    </div>
                </header>

                <section id="content">
{body_html}
                </section>
            </article>
        </main>

        <aside class="sidebar" aria-label="Page navigation">
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
"""


def main():
    parser = argparse.ArgumentParser(description="Convert Markdown blog posts to HTML")
    parser.add_argument("--root", default=".", help="Repository root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    blog_dir = root / BLOG_DIR

    if not blog_dir.is_dir():
        print(f"No blog directory at {blog_dir} â€” nothing to convert.")
        return

    md_files = sorted(blog_dir.glob("*.md"))
    md_files = [f for f in md_files if f.name.lower() != "readme.md"]

    if not md_files:
        print("No Markdown posts found in pages/blog/ â€” nothing to convert.")
        return

    print(f"Found {len(md_files)} Markdown post(s)")
    for md_path in md_files:
        print(f"  Converting: {md_path.name}")
        raw = md_path.read_text(encoding="utf-8")
        meta, body_md = parse_front_matter(raw)

        if not meta.get("title"):
            meta["title"] = md_path.stem.replace("-", " ").title()
        if not meta.get("date"):
            mtime = md_path.stat().st_mtime
            meta["date"] = datetime.fromtimestamp(mtime, tz=timezone.utc).strftime("%Y-%m-%d")

        body_html = md_to_html(body_md)
        page_html = generate_blog_page(meta, body_html)

        out_path = md_path.with_suffix(".html")
        out_path.write_text(page_html, encoding="utf-8")
        print(f"  â†’ {out_path.relative_to(root)}")

    print(f"Converted {len(md_files)} post(s).")


if __name__ == "__main__":
    main()
