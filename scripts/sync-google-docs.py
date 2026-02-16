import os
import re
import json
import html
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


def save_html(filename, title, content):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    paragraphs = []
    for block in re.split(r"\n\s*\n", content.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        paragraph_text = " ".join(lines)
        if re.match(r"^#{1,6}\s+", paragraph_text):
            heading_level = min(paragraph_text.count("#", 0, paragraph_text.find(" ")), 6)
            heading_text = paragraph_text[heading_level:].strip()
            paragraphs.append(f"<h{heading_level + 1}>{html.escape(heading_text)}</h{heading_level + 1}>")
            continue

        if len(lines) == 1 and paragraph_text.endswith(":") and len(paragraph_text) < 80:
            paragraphs.append(f"<h2>{html.escape(paragraph_text[:-1])}</h2>")
            continue

        paragraphs.append(f"<p>{html.escape(paragraph_text)}</p>")

    article_body = "\n                    ".join(paragraphs) if paragraphs else "<p></p>"

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
        <main id="main" class="page-content">
            <article class="section-rule">
                <header class="hero">
                    <p class="small muted"><a href="../blog.html">&larr; Back to Articles &amp; Reports</a></p>
                    <h1>{html.escape(title)}</h1>
                </header>
                <section class="article-body">
                    {article_body}
                </section>
            </article>
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

    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf8") as f:
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

    for file in docs:
        doc = docs_service.documents().get(documentId=file["id"]).execute()
        text = extract_text(doc)

        title = file["name"]
        slug = slugify(title) + ".html"
        preview = text[:200].replace("\n", " ")
        tags = extract_tags(text)

        save_html(slug, title, text)

        posts.append({
            "title": title,
            "slug": slug,
            "preview": preview,
            "tags": tags,
            "date": file["modifiedTime"]
        })

    posts.sort(key=lambda x: x["date"], reverse=True)
    posts = posts[:MAX_POSTS]

    os.makedirs("assets", exist_ok=True)
    with open(INDEX_FILE, "w", encoding="utf8") as f:
        json.dump(posts, f, indent=2)

    print("Synced", len(posts), "posts")


if __name__ == "__main__":
    main()
