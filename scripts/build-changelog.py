#!/usr/bin/env python3
"""Build a changelog page from recent git commits.

Reads the git log and generates pages/changelog.html with a
grouped-by-date list of recent changes.

Usage:  python scripts/build-changelog.py
"""

import argparse
import subprocess
import sys
from datetime import datetime
from html import escape as html_escape
from pathlib import Path

OUTPUT_PATH = "pages/changelog.html"
MAX_COMMITS = 60


def get_git_log(root: Path, max_count: int = MAX_COMMITS) -> list[dict]:
    """Retrieve recent commits as structured dicts."""
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={max_count}", "--pretty=format:%H|%ai|%s"],
            cwd=str(root),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return []
    except FileNotFoundError:
        return []

    commits = []
    for line in result.stdout.strip().splitlines():
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        sha, date_str, subject = parts
        commits.append({
            "sha": sha[:8],
            "date": date_str[:10],
            "message": subject.strip(),
        })
    return commits


def group_by_date(commits: list[dict]) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = {}
    for c in commits:
        groups.setdefault(c["date"], []).append(c)
    return groups


def generate_page(commits: list[dict]) -> str:
    grouped = group_by_date(commits)
    year = datetime.now().year

    entries_html = []
    for date in sorted(grouped.keys(), reverse=True):
        items = grouped[date]
        li_html = "\n".join(
            f'                        <li><code class="small">{html_escape(c["sha"])}</code> {html_escape(c["message"])}</li>'
            for c in items
        )
        entries_html.append(f"""
            <div class="changelog-group">
                <h3 class="changelog-date">{html_escape(date)}</h3>
                <ul>
{li_html}
                </ul>
            </div>""")

    body = "\n".join(entries_html) if entries_html else '<p class="empty-state">No commits found.</p>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Changelog â€” recent updates to sullivanrsteele.com">
    <title>Changelog | Sullivan Steele</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <link rel="stylesheet" href="../css/main.css">
    <script src="../js/theme.js"></script>
    <script defer data-domain="sullivanrsteele.com" src="https://plausible.io/js/script.js"></script>
    <link rel="alternate" type="application/atom+xml" title="Sullivan Steele" href="/feed.xml">
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
</head>
<body data-route="changelog">
    <a href="#main" class="skip-link">Skip to main content</a>

    <nav>
        <div class="nav-container">
            <a href="../index.html" class="nav-logo">SULLIVAN STEELE</a>
            <button type="button" class="menu-toggle" aria-label="Toggle navigation" aria-expanded="false" aria-controls="nav-links">
                <span></span><span></span><span></span>
            </button>
            <ul class="nav-links" id="nav-links">
                <li><a href="../index.html" data-nav-route="home">Home</a></li>
                <li><a href="my-work.html" data-nav-route="my-work">My Work</a></li>
                <li><a href="projects.html" data-nav-route="projects">Projects</a></li>
                <li><a href="blog.html" data-nav-route="blog">Articles &amp; Reports</a></li>
                <li><a href="gallery.html" data-nav-route="gallery">Gallery</a></li>
                <li><a href="about.html" data-nav-route="about">About</a></li>
                <li><a href="music.html" data-nav-route="music">Music</a></li>
                <li><a href="shop.html" data-nav-route="shop">Shop</a></li>
                <li><button type="button" class="site-search-toggle" aria-label="Search the site"><i class="bi bi-search"></i></button></li>
                <li><button type="button" class="theme-toggle" aria-label="Toggle theme"><i class="bi bi-sun"></i></button></li>
            </ul>
        </div>
    </nav>

    <div class="site-layout">
        <main id="main" class="page-content">

            <section class="hero">
                <h1>Changelog</h1>
                <p class="hero-sub">
                    Recent updates to this site, pulled from the git history.
                </p>
            </section>

            <section class="section-rule changelog-list">
{body}
            </section>

        </main>

        <aside class="sidebar" aria-label="Page navigation">
            <div class="sidebar-section">
                <h4>Pages</h4>
                <ul>
                    <li><a href="../index.html" data-nav-route="home">Home</a></li>
                    <li><a href="my-work.html" data-nav-route="my-work">My Work</a></li>
                    <li><a href="projects.html" data-nav-route="projects">Projects</a></li>
                    <li><a href="blog.html" data-nav-route="blog">Articles &amp; Reports</a></li>
                    <li><a href="gallery.html" data-nav-route="gallery">Gallery</a></li>
                    <li><a href="about.html" data-nav-route="about">About</a></li>
                    <li><a href="music.html" data-nav-route="music">Music</a></li>
                    <li><a href="shop.html" data-nav-route="shop">Shop</a></li>
                </ul>
            </div>
        </aside>
    </div>

    <footer>
        <div class="footer-inner">
            <p>&copy; {year} Sullivan Steele</p>
            <ul class="footer-links">
                <li><a href="mailto:sullivanrsteele@gmail.com">Email</a></li>
                <li><a href="https://github.com/IAmADoctorYes" target="_blank" rel="noopener">GitHub</a></li>
                <li><a href="https://www.linkedin.com/in/sullivan-steele-166102140" target="_blank" rel="noopener">LinkedIn</a></li>
            </ul>
        </div>
    </footer>

    <script src="../js/cart.js"></script>
    <script src="../js/search.js"></script>
    <script src="../js/nav.js"></script>
    <script src="../js/backgrounds.js"></script>
    <script src="../js/enhancements.js"></script>
    <script>if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');</script>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Build changelog page from git log")
    parser.add_argument("--root", default=".", help="Repository root directory")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    print("Reading git logâ€¦")
    commits = get_git_log(root)

    if not commits:
        print("No commits found (or not a git repo). Generating empty page.")

    page_html = generate_page(commits)
    out = root / OUTPUT_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page_html, encoding="utf-8")
    print(f"Generated changelog with {len(commits)} commit(s) â†’ {out}")


if __name__ == "__main__":
    main()
