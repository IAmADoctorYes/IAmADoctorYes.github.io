import json
import html
import os
import re
from datetime import datetime, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# ================= CONFIG =================
DEFAULT_OUTPUT_DIR = "pages/blog"
DEFAULT_INDEX_FILE = "assets/search-index.json"
MAX_POSTS = 150
# ==========================================

DOCS_SCOPE = "https://www.googleapis.com/auth/documents.readonly"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


def get_env(name, fallback=""):
    value = os.getenv(name, "").strip()
    return value or fallback


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text.strip("-")


def extract_tags(text):
    match = re.search(r"^tags:(.*)$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return []

    return [t.strip() for t in match.group(1).split(",") if t.strip()]


def remove_tags_line(text):
    return re.sub(r"^tags:.*$", "", text, flags=re.IGNORECASE | re.MULTILINE).strip()


def normalize_preview(text, limit=220):
    condensed = re.sub(r"\s+", " ", text).strip()
    if len(condensed) <= limit:
        return condensed
    return condensed[:limit].rstrip() + "…"


def parse_doc_json_text(doc):
    content = doc.get("body", {}).get("content", [])
    text = ""
    for element in content:
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for el in paragraph.get("elements", []):
            text_run = el.get("textRun")
            if text_run:
                text += text_run.get("content", "")
    return text.strip()


def markdownish_to_html(text):
    blocks = [b.strip() for b in re.split(r"\n\s*\n", text) if b.strip()]
    if not blocks:
        return "<p>No content was available for this document.</p>"

    rendered = []
    for block in blocks:
        safe = html.escape(block).replace("\n", "<br>\n")
        rendered.append(f"<p>{safe}</p>")
    return "\n".join(rendered)


def render_post_html(title, content, tags, modified_time):
    safe_title = html.escape(title)
    tag_markup = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in tags)

    date_markup = ""
    if modified_time:
        date_markup = (
            '<span><i class="bi bi-calendar3"></i> '
            + html.escape(modified_time)
            + "</span>"
        )

    content_html = markdownish_to_html(content)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{safe_title}">
    <title>{safe_title} | Sullivan Steele</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <link rel="stylesheet" href="../../css/main.css">
    <script src="../../js/theme.js"></script>
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
</head>
<body>
    <a href="#main" class="skip-link">Skip to main content</a>
    <nav>
        <div class="nav-container">
            <a href="../../index.html" class="nav-logo">SULLIVAN STEELE</a>
            <button class="menu-toggle" aria-label="Toggle navigation" aria-expanded="false" aria-controls="nav-links">
                <span></span><span></span><span></span>
            </button>
            <ul class="nav-links" id="nav-links">
                <li><a href="../../index.html">Home</a></li>
                <li><a href="../my-work.html">My Work</a></li>
                <li><a href="../passion-projects.html">Passion Projects</a></li>
                <li><a href="../blog.html">Articles &amp; Reports</a></li>
                <li><a href="../about.html">About</a></li>
                <li><a href="../music.html">Music</a></li>
                <li><a href="../shop.html">Shop</a></li>
                <li><button class="theme-toggle" aria-label="Toggle theme"><i class="bi bi-sun"></i></button></li>
            </ul>
        </div>
    </nav>

    <div class="site-layout">
        <main id="main" class="page-content article-content">
            <header class="article-header">
                <h1>{safe_title}</h1>
                <div class="article-meta">{date_markup}</div>
                <div class="article-tags">{tag_markup}</div>
            </header>
            {content_html}
            <nav class="article-nav" aria-label="Article navigation">
                <a href="../blog.html"><span class="label">Back</span>Articles &amp; Reports</a>
            </nav>
        </main>
    </div>

    <footer>
        <div class="footer-inner">
            <p>&copy; 2025 Sullivan Steele</p>
            <ul class="footer-links">
                <li><a href="mailto:sullivanrsteele@gmail.com">Email</a></li>
                <li><a href="https://github.com/IAmADoctorYes" target="_blank" rel="noopener">GitHub</a></li>
                <li><a href="https://www.linkedin.com/in/sullivan-steele-166102140" target="_blank" rel="noopener">LinkedIn</a></li>
            </ul>
        </div>
    </footer>

    <script src="../../js/nav.js"></script>
    <script src="../../js/backgrounds.js"></script>
</body>
</html>
"""


def save_file(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf8") as f:
        f.write(text)


def get_services(creds_path):
    creds = service_account.Credentials.from_service_account_file(
        creds_path,
        scopes=[DRIVE_SCOPE, DOCS_SCOPE],
    )
    drive_service = build("drive", "v3", credentials=creds)
    docs_service = build("docs", "v1", credentials=creds)
    return drive_service, docs_service


def list_docs(drive_service, folder_id):
    results = drive_service.files().list(
        q=(
            f"'{folder_id}' in parents and "
            "mimeType='application/vnd.google-apps.document' and trashed=false"
        ),
        fields="files(id,name,modifiedTime)",
        pageSize=1000,
        orderBy="modifiedTime desc",
    ).execute()
    return results.get("files", [])


def fetch_text_from_docs_api(docs_service, file_id):
    doc = docs_service.documents().get(documentId=file_id).execute()
    return parse_doc_json_text(doc)


def fetch_text_from_drive_export(drive_service, file_id):
    raw = drive_service.files().export(
        fileId=file_id,
        mimeType="text/plain",
    ).execute()
    return raw.decode("utf-8", errors="replace").strip()


def looks_like_docs_api_disabled(err):
    message = str(err)
    return "docs.googleapis.com" in message and "SERVICE_DISABLED" in message


def format_modified_date(date_str):
    if not date_str:
        return ""

    try:
        parsed = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
    except ValueError:
        return date_str

    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d")


def main():
    folder_id = get_env("DRIVE_FOLDER_ID")
    if not folder_id:
        raise SystemExit("Missing DRIVE_FOLDER_ID env variable.")

    creds_path = get_env("CREDS_FILE", "credentials.json")
    if not os.path.exists(creds_path):
        raise SystemExit(f"Credentials file not found: {creds_path}")

    output_dir = get_env("BLOG_DIR", DEFAULT_OUTPUT_DIR)
    index_file = get_env("SEARCH_INDEX_FILE", DEFAULT_INDEX_FILE)

    drive_service, docs_service = get_services(creds_path)
    docs = list_docs(drive_service, folder_id)

    posts = []
    docs_api_available = True

    for file in docs[:MAX_POSTS]:
        file_id = file["id"]
        title = file["name"].strip() or "Untitled post"

        text = ""
        if docs_api_available:
            try:
                text = fetch_text_from_docs_api(docs_service, file_id)
            except HttpError as err:
                if looks_like_docs_api_disabled(err):
                    docs_api_available = False
                    print("Warning: Google Docs API disabled; falling back to Drive export.")
                else:
                    print(f"Warning: Docs API failed for {title}: {err}")

        if not text:
            try:
                text = fetch_text_from_drive_export(drive_service, file_id)
            except HttpError as err:
                print(f"Warning: Drive export failed for {title}: {err}")
                continue

        text = text.strip()
        if not text:
            print(f"Warning: Empty document skipped: {title}")
            continue

        tags = extract_tags(text)
        cleaned_text = remove_tags_line(text)
        slug = slugify(title) + ".html"

        modified_time_raw = file.get("modifiedTime", "")
        modified_time_display = format_modified_date(modified_time_raw)

        html_output = render_post_html(title, cleaned_text, tags, modified_time_display)
        save_file(os.path.join(output_dir, slug), html_output)

        posts.append(
            {
                "title": title,
                "slug": slug,
                "preview": normalize_preview(cleaned_text),
                "tags": tags,
                "date": modified_time_raw,
            }
        )

    posts.sort(key=lambda x: x.get("date", ""), reverse=True)

    save_file(index_file, json.dumps(posts, indent=2))
    print(f"Synced {len(posts)} posts")


if __name__ == "__main__":
    main()
