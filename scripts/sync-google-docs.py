#!/usr/bin/env python3
"""
sync-google-docs.py

Sync Google Docs in a Drive folder to static blog posts under pages/blog/,
splitting very large posts into parts, and updating pages/blog.html's
AUTO block to reflect the files actually present.

Prereqs:
  - service account JSON available at path given by env var CREDS_FILE
  - env var DRIVE_FOLDER_ID set to the Drive folder to read
  - google-api-python-client, google-auth, beautifulsoup4 installed

Designed to run in GitHub Actions.
"""
from __future__ import annotations
import os
import re
import io
import json
import time
import html
import logging
import tempfile
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Tuple

from bs4 import BeautifulSoup

# Google API imports
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ---------------- CONFIG ----------------
LARGE_DOC_THRESHOLD = 8 * 1024 * 1024  # 8 MB triggers chunking
CHUNK_SIZE = 2 * 1024 * 1024  # approx size per chunk
POSTS_DIR = Path("pages/blog")
BLOG_HTML = Path("pages/blog.html")
STATE_FILE = Path("scripts/sync-state.json")

# environment-controlled
DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
CREDS_FILE = os.environ.get("CREDS_FILE")
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
log = logging.getLogger("sync")

# ---------------- utilities ----------------
def retry(func, attempts: int = 3, delay: float = 2.0):
    last = None
    for i in range(attempts):
        try:
            return func()
        except Exception as e:
            last = e
            log.warning("Attempt %d/%d failed: %s", i + 1, attempts, e)
            time.sleep(delay)
    raise last

def slugify(text: str) -> str:
    if not text:
        return "post"
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+", "-", text)
    return text or "post"

def atomic_write(path: Path, data: str, encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with open(fd, "w", encoding=encoding) as f:
            f.write(data)
        tmp_path = Path(tmp)
        tmp_path.replace(path)
    except Exception:
        # fallback: try direct write (best-effort)
        with open(path, "w", encoding=encoding) as f:
            f.write(data)
    finally:
        try:
            if Path(tmp).exists():
                Path(tmp).unlink()
        except Exception:
            pass

def ensure_unique_filename(posts_dir: Path, base: str, ext: str = ".html") -> str:
    candidate = f"{base}{ext}"
    i = 0
    while (posts_dir / candidate).exists():
        i += 1
        candidate = f"{base}-{i}{ext}"
    return candidate

def extract_body_fragment(html_str: str) -> str:
    soup = BeautifulSoup(html_str, "html.parser")
    body = soup.body or soup
    parts = []
    for node in list(body.children):
        s = str(node)
        if not s.strip():
            continue
        parts.append(s)
    return "".join(parts) if parts else html_str

def parse_date_string(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = s.strip()
    # try ISO-ish and common formats
    fmts = ("%Y-%m-%d", "%Y/%m/%d", "%B %d, %Y", "%b %d, %Y", "%Y.%m.%d")
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except Exception:
            pass
    # fallback: find y-m-d pattern
    m = re.search(r"(\d{4})[-/\.]?(\d{2})[-/\.]?(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    return None

# ---------------- Google Drive helpers ----------------
def build_service():
    """
    Build Drive API service. Pass cache_discovery=False to avoid oauth2client file_cache warning.
    """
    if not CREDS_FILE:
        raise RuntimeError("CREDS_FILE environment variable not set")
    creds = service_account.Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    # IMPORTANT: disable discovery caching to avoid the oauth2client file_cache warning
    return build("drive", "v3", credentials=creds, cache_discovery=False)

def fetch_doc_list(service) -> List[Dict]:
    q = f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
    resp = retry(lambda: service.files().list(q=q, fields="files(id,name,modifiedTime)").execute())
    return resp.get("files", [])

def download_doc_html(service, file_id: str) -> str:
    request = service.files().export_media(fileId=file_id, mimeType="text/html")
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return fh.read().decode("utf-8")

# ---------------- HTML building & chunking ----------------
def split_html_into_chunks(html_str: str, approx_chunk_bytes: int = CHUNK_SIZE) -> List[str]:
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
    esc_title = html.escape(title)
    esc_author = html.escape(author)
    esc_date = html.escape(date_str)
    parts_json = json.dumps(parts_filenames or [])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{esc_title}">
  <title>{esc_title} | {esc_author}</title>
  <link rel="stylesheet" href="../../css/main.css">
</head>
<body>
  <main id="main" class="page-content">
    <article class="article-content">
      <header>
        <h1>{esc_title}</h1>
        <div class="article-meta">{esc_date} • {esc_author}</div>
      </header>
      <div id="docs-container" class="docs-content-container">
        {doc_content_html}
      </div>
      <div id="docs-loading-placeholder"></div>
    </article>
  </main>
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
</body>
</html>
"""

# ---------------- blog index updater ----------------
AUTO_START = "<!-- AUTO:START -->"
AUTO_END = "<!-- AUTO:END -->"

def build_auto_section_html(posts: List[Dict[str,str]]) -> str:
    """
    posts: list of dicts with keys: date, file, title
    returns HTML fragment to put between markers
    """
    items = []
    for p in posts:
        title_escaped = html.escape(p["title"])
        items.append(f"""
                <article class="article-preview">
                    <div class="preview-meta">
                        <span>{p['date']}</span>
                        <span class="tag tag-green">Doc</span>
                    </div>
                    <h3><a href="blog/{p['file']}">{title_escaped}</a></h3>
                </article>
""")
    return f"""
            <section class="section-rule" id="docs">
                <h2>Synced Docs</h2>
{''.join(items)}
            </section>
"""

def update_blog_index_from_files(posts_dir: Path, blog_html_path: Path) -> None:
    # scan posts_dir for *.html (skip part files)
    files = sorted([p for p in posts_dir.glob("*.html") if p.is_file() and not p.name.endswith(tuple(".part{}.html".format(i) for i in range(1, 100)))])
    posts = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8")
            soup = BeautifulSoup(text, "html.parser")
            # Title: prefer <h1>, else filename
            h1 = soup.find("h1")
            title = h1.get_text(strip=True) if h1 else p.stem
            # Date: from meta text in .article-meta or from filename prefix
            date = None
            meta_div = soup.select_one(".article-meta")
            if meta_div:
                # pick first date-like token
                m = re.search(r"\d{4}-\d{2}-\d{2}", meta_div.get_text())
                if m:
                    date = m.group(0)
            if not date:
                m = re.match(r"(\d{4}-\d{2}-\d{2})", p.name)
                if m:
                    date = m.group(1)
            if not date:
                date = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d")
            posts.append({"date": date, "file": p.name, "title": title})
        except Exception as e:
            log.warning("Failed to parse post file %s: %s", p, e)
    # sort posts by date desc
    posts.sort(key=lambda x: x["date"], reverse=True)

    # load blog_html, replace AUTO block or insert if missing
    if not blog_html_path.exists():
        log.error("Blog index file %s not found; cannot update index", blog_html_path)
        return
    text = blog_html_path.read_text(encoding="utf-8")

    auto_fragment = build_auto_section_html(posts)

    if AUTO_START in text and AUTO_END in text:
        # replace between markers
        before, rest = text.split(AUTO_START, 1)
        _, after = rest.split(AUTO_END, 1)
        new_text = before + AUTO_START + "\n" + auto_fragment + "\n" + AUTO_END + after
        atomic_write(blog_html_path, new_text)
        log.info("Replaced AUTO block in %s with %d posts", blog_html_path, len(posts))
    else:
        # insert auto_fragment after the hero section if we can find </section> for hero, else append before </main>
        inserted = False
        # try to insert before first occurrence of '<section class="section-rule" id="tutorials">'
        marker = '<section class="section-rule" id="tutorials">'
        if marker in text:
            new_text = text.replace(marker, AUTO_START + "\n" + auto_fragment + "\n" + AUTO_END + "\n\n" + marker, 1)
            atomic_write(blog_html_path, new_text)
            inserted = True
            log.info("Inserted AUTO block before tutorials in %s", blog_html_path)
        else:
            # fallback: try before closing </main>
            if "</main>" in text:
                new_text = text.replace("</main>", AUTO_START + "\n" + auto_fragment + "\n" + AUTO_END + "\n</main>", 1)
                atomic_write(blog_html_path, new_text)
                inserted = True
                log.info("Inserted AUTO block before </main> in %s", blog_html_path)
        if not inserted:
            # as last resort append to file
            atomic_write(blog_html_path, text + "\n" + AUTO_START + "\n" + auto_fragment + "\n" + AUTO_END)
            log.info("Appended AUTO block to %s", blog_html_path)

# ---------------- state handling ----------------
def load_state() -> Dict[str, str]:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            log.warning("Unable to parse state file; starting fresh")
            return {}
    return {}

def save_state(state: Dict[str, str]) -> None:
    atomic_write(STATE_FILE, json.dumps(state, indent=2))

# ---------------- main flow ----------------
def main() -> int:
    if not DRIVE_FOLDER_ID:
        log.error("DRIVE_FOLDER_ID environment variable not set. Exiting.")
        return 2
    if not CREDS_FILE:
        log.error("CREDS_FILE environment variable not set. Exiting.")
        return 2

    POSTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        service = build_service()
    except Exception as e:
        log.exception("Failed to build Drive service: %s", e)
        return 2

    try:
        files = fetch_doc_list(service)
    except Exception as e:
        log.exception("Failed to list Docs: %s", e)
        return 2

    state = load_state()
    any_written = False

    for f in files:
        try:
            fid = f.get("id")
            name = f.get("name", "untitled")
            modified = f.get("modifiedTime")
            if not fid:
                continue
            # skip if state matches
            if state.get(fid) == modified:
                log.debug("Unchanged: %s", name)
                continue
            log.info("Processing doc: %s", name)
            html_doc = download_doc_html(service, fid)
            # extract metadata
            soup = BeautifulSoup(html_doc, "html.parser")
            # title
            title = None
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            if not title:
                h1 = soup.find("h1")
                if h1:
                    title = h1.get_text(strip=True)
            title = title or name
            # author
            author = "Unknown"
            meta_author = soup.find("meta", attrs={"name":"author"}) or soup.find("meta", attrs={"property":"author"})
            if meta_author and meta_author.get("content"):
                author = meta_author["content"].strip()
            # date
            date = None
            for key in ("article:published_time","date","publication_date","publishdate"):
                tag = soup.find("meta", attrs={"name": key}) or soup.find("meta", attrs={"property": key})
                if tag and tag.get("content"):
                    date = parse_date_string(tag.get("content"))
                    if date:
                        break
            # fallback: use modified time if available
            if not date:
                try:
                    dt = datetime.strptime(modified[:19], "%Y-%m-%dT%H:%M:%S")
                    date = dt.strftime("%Y-%m-%d")
                except Exception:
                    date = datetime.utcnow().strftime("%Y-%m-%d")

            # prepare filename: date-slug.html, ensure uniqueness
            base_slug = f"{date}-{slugify(title)}"
            filename = ensure_unique_filename(POSTS_DIR, base_slug, ext=".html")
            post_path = POSTS_DIR / filename

            fragment = extract_body_fragment(html_doc)

            # chunk if necessary
            parts_filenames = None
            if len(fragment.encode("utf-8")) >= LARGE_DOC_THRESHOLD:
                parts = split_html_into_chunks(fragment, approx_chunk_bytes=CHUNK_SIZE)
                parts_filenames = []
                for idx, part_html in enumerate(parts):
                    part_name = f"{filename[:-5]}.part{idx+1}.html"
                    part_path = POSTS_DIR / part_name
                    atomic_write(part_path, part_html)
                    parts_filenames.append(part_name)
                # use first chunk inline
                fragment = parts[0]

            # build final page and write
            page_html = build_post_html(title=title, author=author, date_str=date, doc_content_html=fragment, parts_filenames=parts_filenames)
            atomic_write(post_path, page_html)
            log.info("Wrote post: %s", post_path.as_posix())
            state[fid] = modified
            any_written = True

        except Exception as e:
            log.exception("Failed to process doc %s: %s", f.get("name"), e)
            continue

    # save state
    try:
        save_state(state)
    except Exception as e:
        log.exception("Failed to save state file: %s", e)

    # update blog index by scanning files to ensure blog.html matches what's actually present
    try:
        update_blog_index_from_files(POSTS_DIR, BLOG_HTML)
    except Exception as e:
        log.exception("Failed to update blog index: %s", e)

    if any_written:
        log.info("Sync complete: wrote new/updated posts")
    else:
        log.info("No changes")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
