import os
import re
import json
import html
import shutil
import tempfile
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2 import service_account

# ================= CONFIG =================
DOCS_FOLDER_ID = "YOUR_FOLDER_ID"
OUTPUT_DIR = "pages/blog"
INDEX_FILE = "assets/search-index.json"
MAX_POSTS = 150
CREDENTIALS_FILE = "credentials.json"
LEGACY_CREDENTIALS_ENV = "CREDS_FILE"
LEGACY_FOLDER_ENV = "DRIVE_FOLDER_ID"
# ==========================================

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def get_credentials():
    """Load Google credentials from env var JSON or a local file."""
    raw_service_account = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_service_account:
        try:
            info = json.loads(raw_service_account)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "GOOGLE_SERVICE_ACCOUNT_JSON is set but is not valid JSON."
            ) from exc

        return service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )

    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if not credentials_path:
        credentials_path = os.getenv(LEGACY_CREDENTIALS_ENV, CREDENTIALS_FILE)
    if os.path.exists(credentials_path):
        return service_account.Credentials.from_service_account_file(
            credentials_path, scopes=SCOPES
        )

    raise RuntimeError(
        "Google credentials not found. Provide one of the following:\n"
        "1) Create a service-account key file and save it to credentials.json\n"
        "2) Set GOOGLE_APPLICATION_CREDENTIALS (or legacy CREDS_FILE) to your key file path\n"
        "3) Set GOOGLE_SERVICE_ACCOUNT_JSON to the raw key JSON"
    )


def get_docs_folder_id():
    folder_id = os.getenv("GOOGLE_DOCS_FOLDER_ID")
    if not folder_id:
        folder_id = os.getenv(LEGACY_FOLDER_ENV, DOCS_FOLDER_ID)
    if folder_id == "YOUR_FOLDER_ID":
        raise RuntimeError(
            "Google Docs folder ID is not configured. Set GOOGLE_DOCS_FOLDER_ID "
            "(or legacy DRIVE_FOLDER_ID) or replace DOCS_FOLDER_ID in scripts/sync-google-docs.py."
        )
    return folder_id


def slugify(text):
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text.strip("-")


def extract_text(doc):
    content = doc.get("body").get("content")
    text = ""

    for element in content:
        if "paragraph" in element:
            for el in element["paragraph"]["elements"]:
                if "textRun" in el:
                    text += el["textRun"]["content"]

    return text.strip()


def extract_tags(text):
    match = re.search(r"^tags:(.*)$", text, re.IGNORECASE | re.MULTILINE)
    if not match:
        return []

    tags = match.group(1)
    return [t.strip() for t in tags.split(",") if t.strip()]


def get_docs(drive_service, docs_folder_id):
    results = drive_service.files().list(
        q=f"'{docs_folder_id}' in parents and mimeType='application/vnd.google-apps.document'",
        fields="files(id, name, modifiedTime)",
    ).execute()

    return results.get("files", [])


def index_local_html(output_dir, existing_slugs):
    """Index hand-written HTML files in the blog directory that weren't synced from Google Docs.

    Returns a list of post entries for any .html file in *output_dir* whose
    filename is not already in *existing_slugs*.  This lets authors drop a
    plain HTML file into pages/blog/ and have it appear in the search index
    without needing Google Docs credentials.
    """
    local_posts = []
    if not os.path.isdir(output_dir):
        return local_posts

    for fname in os.listdir(output_dir):
        if not fname.endswith(".html") or fname.startswith("_") or fname in existing_slugs:
            continue

        filepath = os.path.join(output_dir, fname)
        try:
            with open(filepath, "r", encoding="utf8") as f:
                raw = f.read()
        except OSError:
            continue

        # Extract <title>…</title>
        title_match = re.search(r"<title>(.*?)</title>", raw, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).replace(" | Sullivan Steele", "").strip() if title_match else fname.replace(".html", "").replace("-", " ").title()

        # Extract meta description
        desc_match = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']*)["\']', raw, re.IGNORECASE)
        preview = desc_match.group(1).strip() if desc_match else title

        # Extract tags from a <meta name="keywords"> tag
        kw_match = re.search(r'<meta\s+name=["\']keywords["\']\s+content=["\']([^"\']*)["\']', raw, re.IGNORECASE)
        tags = [t.strip() for t in kw_match.group(1).split(",") if t.strip()] if kw_match else []

        # Use file modification time
        mtime = os.path.getmtime(filepath)
        from datetime import datetime, timezone
        date_str = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

        local_posts.append({
            "title": title,
            "slug": fname,
            "preview": preview[:200],
            "tags": tags,
            "date": date_str,
        })

    return local_posts


def save_html(filename, title, content):
    article_body = content
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{html.escape(title)} | Sullivan Steele">
    <title>{html.escape(title)} | Sullivan Steele</title>
    <link rel="canonical" href="/pages/blog/{html.escape(filename)}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <link rel="stylesheet" href="../../css/main.css">
    <script src="../../js/theme.js"></script>
    <link rel="icon" type="image/png" href="/assets/favicon.png">
    <link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
    <meta property="og:title" content="{html.escape(title)} | Sullivan Steele">
    <meta property="og:description" content="{html.escape(title)}">
    <meta property="og:image" content="https://www.sullivanrsteele.com/assets/portrait.jpg">
    <meta property="og:url" content="https://www.sullivanrsteele.com/pages/blog/{html.escape(filename)}">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary">
    <meta name="twitter:title" content="{html.escape(title)}">
    <meta name="twitter:description" content="{html.escape(title)}">
    <meta name="twitter:image" content="https://www.sullivanrsteele.com/assets/portrait.jpg">
</head>
<body data-route="blog">
    <a href="#main" class="skip-link">Skip to main content</a>

    <nav>
        <div class="nav-container">
            <a href="../../index.html" class="nav-logo">SULLIVAN STEELE</a>
            <button class="menu-toggle" aria-label="Toggle navigation" aria-expanded="false" aria-controls="nav-links">
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
                <li><button class="site-search-toggle" aria-label="Search the site"><i class="bi bi-search"></i></button></li>
                <li><button class="theme-toggle" aria-label="Toggle theme"><i class="bi bi-sun"></i></button></li>
            </ul>
        </div>
    </nav>

    <div class="site-layout">
        <main id="main" class="page-content">
            <div class="breadcrumb">
                <a href="../../index.html" data-nav-route="home">Home</a>
                <span class="sep">/</span>
                <a href="../blog.html" data-nav-route="blog">Articles &amp; Reports</a>
                <span class="sep">/</span>
                {html.escape(title)}
            </div>

            <article class="article-content">
                <header class="article-header">
                    <h1>{html.escape(title)}</h1>
                </header>
                <section class="article-body">
                    {article_body}
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
            <p>&copy; 2026 Sullivan Steele</p>
            <ul class="footer-links">
                <li><a href="mailto:sullivanrsteele@gmail.com">Email</a></li>
                <li><a href="https://github.com/IAmADoctorYes" target="_blank" rel="noopener">GitHub</a></li>
                <li><a href="https://www.linkedin.com/in/sullivan-steele-166102140" target="_blank" rel="noopener">LinkedIn</a></li>
            </ul>
        </div>
    </footer>

    <script src="../../js/search.js"></script>
    <script src="../../js/nav.js"></script>
    <script src="../../js/backgrounds.js"></script>
</body>
</html>
"""

    with open(filename, "w", encoding="utf8") as f:
        f.write(html_content)


def main():
    creds = get_credentials()
    docs_service = build("docs", "v1", credentials=creds)
    drive_service = build("drive", "v3", credentials=creds)
    docs_folder_id = get_docs_folder_id()

    try:
        docs = get_docs(drive_service, docs_folder_id)
    except HttpError as exc:
        message = str(exc)
        if getattr(exc, "resp", None) is not None and exc.resp.status == 403:
            raise RuntimeError(
                "Google Drive API returned 403. Ensure the service account has access to "
                "the target folder and credentials include Drive scope "
                "(drive.metadata.readonly or broader)."
            ) from exc
        raise RuntimeError(f"Failed to list Google Docs from Drive folder: {message}") from exc

    posts = []
    docs_content = []

    for file in docs:
        doc = docs_service.documents().get(documentId=file["id"]).execute()
        text = extract_text(doc)

        title = file["name"]
        slug = slugify(title) + ".html"
        preview = text[:200].replace("\n", " ")
        tags = extract_tags(text)

        docs_content.append((slug, title, text))
        posts.append({
            "title": title,
            "slug": slug,
            "preview": preview,
            "tags": tags,
            "date": file["modifiedTime"]
        })

    posts.sort(key=lambda x: x["date"], reverse=True)
    posts = posts[:MAX_POSTS]

    temp_output_dir = tempfile.mkdtemp(prefix="blog-sync-")
    temp_index_file = f"{INDEX_FILE}.tmp"

    os.makedirs(temp_output_dir, exist_ok=True)
    for slug, title, text in docs_content:
        save_html(os.path.join(temp_output_dir, slug), title, text)

    os.makedirs("assets", exist_ok=True)

    # ── Local fallback: index hand-written HTML already in pages/blog/ ──
    synced_slugs = {p["slug"] for p in posts}
    local_posts = index_local_html(OUTPUT_DIR, synced_slugs)
    posts.extend(local_posts)
    posts.sort(key=lambda x: x["date"], reverse=True)
    posts = posts[:MAX_POSTS]
    # ────────────────────────────────────────────────────────────────────

    with open(temp_index_file, "w", encoding="utf8") as f:
        json.dump(posts, f, indent=2)

    backup_output_dir = f"{OUTPUT_DIR}.bak"
    try:
        if os.path.exists(backup_output_dir):
            shutil.rmtree(backup_output_dir)

        if os.path.exists(OUTPUT_DIR):
            os.replace(OUTPUT_DIR, backup_output_dir)

        os.replace(temp_output_dir, OUTPUT_DIR)
        os.replace(temp_index_file, INDEX_FILE)

        if os.path.exists(backup_output_dir):
            shutil.rmtree(backup_output_dir)
    except Exception:
        if os.path.exists(temp_output_dir):
            shutil.rmtree(temp_output_dir)
        if os.path.exists(temp_index_file):
            os.remove(temp_index_file)

        if os.path.exists(backup_output_dir) and not os.path.exists(OUTPUT_DIR):
            os.replace(backup_output_dir, OUTPUT_DIR)
        raise

    print("Synced", len(posts), "posts")


if __name__ == "__main__":
    main()
