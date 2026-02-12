#!/usr/bin/env python3
"""
Sync Google Docs from a Drive folder to HTML posts under pages/blog.

Usage:
    - Provide DRIVE_FOLDER_ID and CREDS_FILE via environment or CLI args.
    - Example env:
        export DRIVE_FOLDER_ID="..."
        export CREDS_FILE="/tmp/creds.json"
    - Run: python scripts/sync_docs.py
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from bs4 import BeautifulSoup
import zipfile

# ----- Configuration -----
DEFAULT_STATE_PATH = Path("scripts") / "sync-state.json"
DEFAULT_POSTS_DIR = Path("pages") / "blog"
DEFAULT_BLOG_INDEX = Path("pages") / "blog.html"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ----- Logging -----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("docs-sync")

# ----- Types -----
StateType = Dict[str, str]


# ----- Utilities -----
def slugify(name: str) -> str:
    """Create a safe slug from a filename/title."""
    name = name.strip().lower()
    name = re.sub(r"[’'\"`]", "", name)  # remove quotes
    name = re.sub(r"[^\w\s-]", "", name)  # remove punctuation except -/_
    name = re.sub(r"\s+", "-", name)
    name = re.sub(r"-{2,}", "-", name)
    return name.strip("-_")


def atomic_write_json(path: Path, data, *, indent=2) -> None:
    """Write JSON to a file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, sort_keys=True)
    tmp.replace(path)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


# ----- Google Drive helpers -----
def get_drive_service(creds_file: str) -> object:
    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return build("drive", "v3", credentials=creds)


def get_docs_service(creds_file: str) -> object:
    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return build("docs", "v1", credentials=creds)


# ----- Data classes -----
@dataclass
class DriveDoc:
    id: str
    name: str
    modified_time: str  # iso8601


# ----- Core functionality -----
def list_docs_in_folder(drive_service, folder_id: str) -> List[DriveDoc]:
    """List Google Docs (mimeType=google docs) in a folder (non-trashed)."""
    query = (
        f"'{folder_id}' in parents and mimeType='application/vnd.google-apps.document' "
        "and trashed=false"
    )
    docs: List[DriveDoc] = []
    page_token = None
    while True:
        resp = drive_service.files().list(
            q=query,
            spaces="drive",
            fields="nextPageToken, files(id, name, modifiedTime)",
            pageSize=100,
            pageToken=page_token,
        ).execute()
        for f in resp.get("files", []):
            docs.append(DriveDoc(id=f["id"], name=f["name"], modified_time=f["modifiedTime"]))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return docs


def download_export(drive_service, file_id: str, mime_type: str) -> BytesIO:
    """Download an exported representation of the file into memory and return BytesIO."""
    out = BytesIO()
    request = drive_service.files().export_media(fileId=file_id, mimeType=mime_type)
    downloader = MediaIoBaseDownload(out, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    out.seek(0)
    return out


def extract_html_zip(zip_bytes: BytesIO, extract_to: Path) -> Optional[Path]:
    """Extract a Google Docs HTML zip to a folder; return path to found .html file or None."""
    ensure_dir(extract_to)
    with zipfile.ZipFile(zip_bytes) as z:
        z.extractall(extract_to)
    # Search recursively for first .html file
    for p in extract_to.rglob("*.html"):
        return p
    return None


def doc_to_text_via_docs_api(docs_service, document_id: str) -> str:
    """Best-effort plain text extraction from Google Docs via the Docs API."""
    try:
        doc = docs_service.documents().get(documentId=document_id).execute()
        chunks: List[str] = []
        for elem in doc.get("body", {}).get("content", []):
            if "paragraph" in elem:
                for pe in elem["paragraph"].get("elements", []):
                    tr = pe.get("textRun")
                    if tr:
                        chunks.append(tr.get("content", ""))
        return "".join(chunks).strip()
    except Exception as e:
        logger.debug("Docs API text extraction failed: %s", e)
        return ""


def build_post_html(title: str, author: str, date_str: str, doc_content_html: str) -> str:
    """Wrap the extracted doc HTML in your site layout (kept close to original)."""
    # NOTE: kept most of the original style block & head content but simplified for readability
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{title}">
  <title>{title} | {author}</title>
  <link rel="stylesheet" href="../../css/main.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
  <style>
    .docs-content-container {{
      max-width: 800px; margin: 2em auto; padding: 2em; background: var(--docs-bg,#fff);
      border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }}
    .docs-content-container h1, .docs-content-container h2 {{ margin-top: 1.2em; }}
    .docs-content-container p {{ margin: 1em 0; }}
    pre, code {{ background:#222;color:#fff;padding:0.2em 0.4em;border-radius:4px;font-family:monospace; }}
    @media (prefers-color-scheme:dark) {{
      .docs-content-container {{ background:#222;color:#fff; }}
      pre, code {{ background:#fff;color:#222; }}
    }}
  </style>
</head>
<body>
  <nav> ... </nav>
  <main id="main" class="page-content">
    <div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../blog.html">Blog</a> / {title}</div>
    <article class="article-content">
      <header>
        <h1>{title}</h1>
        <div class="article-meta"><span><i class="bi bi-calendar3"></i> {date_str}</span><span><i class="bi bi-person"></i> {author}</span></div>
      </header>
      <div class="docs-content-container">{doc_content_html}</div>
    </article>
  </main>
  <footer> ... </footer>
  <script src="../../js/nav.js"></script>
</body>
</html>
"""


# ----- Main sync flow -----
def sync_folder(
    drive_service,
    docs_service,
    folder_id: str,
    posts_dir: Path,
    state_path: Path,
    blog_index_path: Path,
    author_name: str = "Sullivan Steele",
) -> None:
    ensure_dir(posts_dir)
    state: StateType = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Couldn't read state file (%s): %s", state_path, e)
            state = {}

    docs = list_docs_in_folder(drive_service, folder_id)
    logger.info("Found %d docs in folder", len(docs))
    posts_for_index: List[Dict] = []
    seen_ids = set()

    for docmeta in docs:
        seen_ids.add(docmeta.id)
        # parse modified time and form date/time pieces
        try:
            mod_dt = datetime.fromisoformat(docmeta.modified_time.replace("Z", "+00:00"))
        except Exception:
            mod_dt = datetime.utcnow()
        mod_date = mod_dt.strftime("%Y-%m-%d")
        mod_time = mod_dt.strftime("%H-%M-%S")

        slug = slugify(docmeta.name)
        post_basename = f"{mod_date}-{mod_time}-{slug}.html"
        image_rel_dir = f"{mod_date}-{mod_time}-{slug}_images"
        images_dir = posts_dir / image_rel_dir
        post_path = posts_dir / post_basename

        prev_mod = state.get(docmeta.id)
        if prev_mod == docmeta.modified_time and post_path.exists():
            logger.info("Skipping (unchanged): %s", docmeta.name)
            posts_for_index.append(
                {
                    "title": docmeta.name,
                    "date": mod_date,
                    "filename": post_basename,
                    "summary": state.get(f"summary_{docmeta.id}", ""),
                }
            )
            continue

        logger.info("Processing: %s -> %s", docmeta.name, post_basename)

        # Try to export zipped HTML
        html_zip = None
        try:
            html_zip = download_export(drive_service, docmeta.id, "application/zip")
        except HttpError as e:
            logger.debug("Export zip failed for %s: %s", docmeta.name, e)

        # Temporary workspace for extraction and intermediate files
        with tempfile.TemporaryDirectory(prefix=f"gdocs_{docmeta.id}_") as tmpdir:
            tmpdir_path = Path(tmpdir)

            if html_zip:
                try:
                    html_file = extract_html_zip(html_zip, tmpdir_path)
                except Exception as e:
                    logger.warning("Failed to extract HTML zip for %s: %s", docmeta.name, e)
                    html_file = None
            else:
                html_file = None

            doc_content_html = ""
            # If HTML exists, copy images and adjust src
            if html_file and html_file.exists():
                # copy images (top-level files in zip may be images)
                ensure_dir(images_dir)
                # Copy all image files from tmpdir (common extensions)
                for ext in ("*.png", "*.jpg", "*.jpeg", "*.gif", "*.svg", "*.webp"):
                    for img in tmpdir_path.rglob(ext):
                        try:
                            shutil.copy(img, images_dir / img.name)
                        except Exception:
                            logger.debug("Failed to copy image %s", img)

                # Read HTML and rewrite image srcs to local image_rel_dir
                raw = html_file.read_text(encoding="utf-8")
                soup = BeautifulSoup(raw, "html.parser")
                # Standardize <img> srcs to the blog images dir
                for img in soup.find_all("img"):
                    src = img.get("src", "")
                    if not src:
                        continue
                    # The zip structure may put images next to the HTML file or in subfolders.
                    # Use basename and reference the copied image if it exists.
                    basename = Path(src).name
                    if (images_dir / basename).exists():
                        img["src"] = f"{image_rel_dir}/{basename}"
                    else:
                        # leave external URLs intact
                        logger.debug("Image %s not found among extracted images; leaving src as-is", basename)
                # Extract inner body content if possible
                body = soup.body
                doc_content_html = body.decode_contents() if body else str(soup)
                logger.info("Converted HTML for %s (with images)", docmeta.name)
            else:
                # Fallback: try download as DOCX and compress it, or extract text using Docs API
                logger.info("Falling back to DOCX/Docs API for %s", docmeta.name)
                # First try DOCX export
                docx_bytes = None
                try:
                    docx_bytes = download_export(drive_service, docmeta.id, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
                except Exception as e:
                    logger.debug("DOCX export failed: %s", e)
                    docx_bytes = None

                text_from_docs_api = doc_to_text_via_docs_api(docs_service, docmeta.id)
                if docx_bytes:
                    # Save docx and create a zip next to posts dir for archival
                    zip_name = f"{mod_date}-{mod_time}-{slug}.zip"
                    zip_path = posts_dir / zip_name
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tdocx:
                        tdocx.write(docx_bytes.getvalue())
                        tdocx.flush()
                        # create zip that contains the docx
                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                            zf.write(tdocx.name, arcname=Path(tdocx.name).name)
                    logger.info("Saved DOCX archive for large/complex doc: %s", zip_path)
                    # Provide a simple HTML stub linking to the zip file plus any extracted text
                    doc_content_html = "<p>This document is large or had complex content. The DOCX has been archived with this post.</p>"
                    if text_from_docs_api:
                        doc_content_html += "<div class='extracted-text'><pre>{}</pre></div>".format(
                            BeautifulSoup(text_from_docs_api, "html.parser").get_text()
                        )
                    # clean up named temp file
                    try:
                        os.remove(tdocx.name)
                    except Exception:
                        pass
                else:
                    # No docx available: rely on docs API text
                    if text_from_docs_api:
                        # convert paragraphs into <p>
                        paragraphs = [f"<p>{BeautifulSoup(p, 'html.parser').get_text()}</p>" for p in text_from_docs_api.splitlines() if p.strip()]
                        doc_content_html = "\n".join(paragraphs)
                        logger.info("Used Docs API text extraction for %s", docmeta.name)
                    else:
                        doc_content_html = "<p>Unable to extract content from this document.</p>"
                        logger.warning("No content could be extracted for %s", docmeta.name)

            # Build final page HTML and write to posts dir
            final_html = build_post_html(title=docmeta.name, author=author_name, date_str=mod_date, doc_content_html=doc_content_html)
            try:
                post_path.write_text(final_html, encoding="utf-8")
            except Exception as e:
                logger.error("Failed to write post file %s: %s", post_path, e)
                continue

            logger.info("Wrote post: %s", post_path)
            # Update state and posts_for_index
            state[docmeta.id] = docmeta.modified_time
            summary_key = f"summary_{docmeta.id}"
            if summary_key not in state:
                state[summary_key] = ""
            posts_for_index.append(
                {
                    "title": docmeta.name,
                    "date": mod_date,
                    "filename": post_basename,
                    "summary": state.get(summary_key, ""),
                }
            )

    # Remove state entries for docs that no longer exist
    def prune_state(s: StateType, seen: set) -> StateType:
        new = {}
        for k, v in s.items():
            if k.startswith("summary_"):
                # keep summaries for now only if their doc id still exists
                docid = k.split("summary_", 1)[-1]
                if docid in seen:
                    new[k] = v
            else:
                if k in seen:
                    new[k] = v
        return new

    state = prune_state(state, seen_ids)

    # Persist state atomically
    try:
        atomic_write_json(state_path, state)
    except Exception as e:
        logger.warning("Failed to write state: %s", e)

    # Update blog index
    update_blog_index(posts_for_index, blog_index_path, posts_dir)

    logger.info("Sync complete.")


def update_blog_index(posts: List[Dict], blog_index_path: Path, posts_dir: Path) -> None:
    """Replace the AUTO section in the blog index with an ordered list of post cards."""
    if not blog_index_path.exists():
        logger.debug("Blog index not found at %s; skipping index update.", blog_index_path)
        return
    try:
        html = blog_index_path.read_text(encoding="utf-8")
    except Exception as e:
        logger.warning("Failed reading blog index: %s", e)
        return

    start_tag = "<!-- AUTO:START -->"
    end_tag = "<!-- AUTO:END -->"
    si = html.find(start_tag)
    ei = html.find(end_tag)
    if si == -1 or ei == -1 or ei < si:
        logger.debug("Auto markers not found or malformed in blog index; skipping.")
        return

    posts_sorted = sorted(posts, key=lambda p: p["date"], reverse=True)
    cards: List[str] = []
    for post in posts_sorted:
        summary_html = f'<p class="article-summary">{post["summary"]}</p>' if post.get("summary") else ""
        # link is relative to the blog index, which expects blog/<filename>
        link = f"blog/{post['filename']}"
        cards.append(
            "                <article class=\"article-preview\">\n"
            "                    <div class=\"preview-meta\">\n"
            f"                        <span>{post['date']}</span>\n"
            "                        <span class=\"tag tag-green\">Doc</span>\n"
            "                    </div>\n"
            f"                    <h3><a href=\"{link}\">{post['title']}</a></h3>\n"
            f"                    {summary_html}\n"
            "                </article>"
        )

    section_body = "\n\n".join(cards) if cards else (
        '                <div class="placeholder-section">\n'
        '                    <p>Synced posts will appear here after the workflow runs.</p>\n'
        '                </div>'
    )

    new_section = (
        start_tag + "\n"
        "            <section class=\"section-rule\" id=\"docs\">\n"
        "                <h2>Synced Docs</h2>\n"
        + section_body + "\n"
        "            </section>\n"
        + "            " + end_tag
    )

    new_html = html[:si] + new_section + html[ei + len(end_tag):]
    try:
        blog_index_path.write_text(new_html, encoding="utf-8")
        logger.info("Updated blog index at %s", blog_index_path)
    except Exception as e:
        logger.warning("Failed to write blog index: %s", e)


# ----- CLI Entrypoint -----
def main(argv=None):
    p = argparse.ArgumentParser(description="Sync Google Docs folder to blog posts")
    p.add_argument("--folder", help="Drive folder id (overrides env DRIVE_FOLDER_ID)")
    p.add_argument("--creds", help="Path to service account JSON (overrides env CREDS_FILE)")
    p.add_argument("--posts-dir", default=str(DEFAULT_POSTS_DIR), help="Directory for posts")
    p.add_argument("--state", default=str(DEFAULT_STATE_PATH), help="Path to sync state file")
    p.add_argument("--index", default=str(DEFAULT_BLOG_INDEX), help="Blog index HTML path")
    args = p.parse_args(argv)

    folder_id = args.folder or os.getenv("DRIVE_FOLDER_ID")
    creds_file = args.creds or os.getenv("CREDS_FILE")
    if not folder_id:
        logger.error("DRIVE_FOLDER_ID not set (env or --folder). Exiting.")
        sys.exit(1)
    if not creds_file:
        logger.error("CREDS_FILE not set (env or --creds). Exiting.")
        sys.exit(1)
    if not Path(creds_file).exists():
        logger.error("Credentials file not found at %s. Exiting.", creds_file)
        sys.exit(1)

    drive = get_drive_service(creds_file)
    docs = get_docs_service(creds_file)
    sync_folder(
        drive_service=drive,
        docs_service=docs,
        folder_id=folder_id,
        posts_dir=Path(args.posts_dir),
        state_path=Path(args.state),
        blog_index_path=Path(args.index),
    )


if __name__ == "__main__":
    main()
