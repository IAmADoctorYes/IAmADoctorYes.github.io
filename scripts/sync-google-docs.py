import html
import json
import os
import re
import sys
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


DRIVE_FOLDER_ID = os.getenv("DRIVE_FOLDER_ID", "").strip()
CREDS_FILE = os.getenv("CREDS_FILE", "credentials.json").strip()
OUTPUT_DIR = Path("pages/blog")
INDEX_FILE = Path("assets/search-index.json")
MAX_POSTS = int(os.getenv("MAX_POSTS", "150"))

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def slugify(text):
    normalized = text.lower().strip()
    normalized = re.sub(r"[^\w\s-]", "", normalized)
    normalized = re.sub(r"\s+", "-", normalized)
    return normalized.strip("-") or "untitled"


def unique_slug(base_slug, used_slugs):
    candidate = f"{base_slug}.html"
    counter = 2

    while candidate in used_slugs:
        candidate = f"{base_slug}-{counter}.html"
        counter += 1

    used_slugs.add(candidate)
    return candidate


def normalize_whitespace(value):
    return re.sub(r"\s+", " ", value).strip()


def extract_tags(text):
    match = re.search(r"^tags\s*:(.*)$", text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return []

    tags = [normalize_whitespace(t) for t in match.group(1).split(",")]
    return [tag for tag in tags if tag]


def extract_preview(text, length=220):
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    filtered = [line for line in lines if not re.match(r"^tags\s*:", line, flags=re.IGNORECASE)]
    merged = normalize_whitespace(" ".join(filtered))
    return merged[:length].rstrip()


def render_post_html(title, content, modified_time):
    safe_title = html.escape(title)
    safe_content = html.escape(content)
    safe_modified = html.escape(modified_time or "Unknown")

    return f"""<!DOCTYPE html>
<html lang=\"en\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <meta name=\"description\" content=\"Blog post by Sullivan Steele\">
    <title>{safe_title} | Sullivan Steele</title>
    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
    <link href=\"https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap\" rel=\"stylesheet\">
    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css\">
    <link rel=\"stylesheet\" href=\"../../css/main.css\">
    <script src=\"../../js/theme.js\"></script>
    <link rel=\"icon\" type=\"image/png\" href=\"/assets/favicon.png\">
    <link rel=\"apple-touch-icon\" href=\"/assets/apple-touch-icon.png\">
</head>
<body>
    <a href=\"#main\" class=\"skip-link\">Skip to main content</a>

    <nav>
        <div class=\"nav-container\">
            <a href=\"../../index.html\" class=\"nav-logo\">SULLIVAN STEELE</a>
            <button class=\"menu-toggle\" aria-label=\"Toggle navigation\" aria-expanded=\"false\" aria-controls=\"nav-links\">
                <span></span><span></span><span></span>
            </button>
            <ul class=\"nav-links\" id=\"nav-links\">
                <li><a href=\"../../index.html\">Home</a></li>
                <li><a href=\"../my-work.html\">My Work</a></li>
                <li><a href=\"../passion-projects.html\">Passion Projects</a></li>
                <li><a href=\"../blog.html\">Articles &amp; Reports</a></li>
                <li><a href=\"../about.html\">About</a></li>
                <li><a href=\"../music.html\">Music</a></li>
                <li><a href=\"../shop.html\">Shop</a></li>
                <li><button class=\"theme-toggle\" aria-label=\"Toggle theme\"><i class=\"bi bi-sun\"></i></button></li>
            </ul>
        </div>
    </nav>

    <div class=\"site-layout\">
        <main id=\"main\" class=\"page-content article-content\">
            <div class=\"breadcrumb\">
                <a href=\"../../index.html\">Home</a><span class=\"sep\">/</span>
                <a href=\"../blog.html\">Articles &amp; Reports</a><span class=\"sep\">/</span>
                <span>{safe_title}</span>
            </div>
            <header class=\"article-header\">
                <h1>{safe_title}</h1>
                <div class=\"article-meta\"><span>Updated: {safe_modified}</span></div>
            </header>
            <pre>{safe_content}</pre>
        </main>

        <aside class=\"sidebar\" aria-label=\"Page navigation and links\">
            <div class=\"sidebar-section\">
                <h4>Pages</h4>
                <ul>
                    <li><a href=\"../../index.html\">Home</a></li>
                    <li><a href=\"../my-work.html\">My Work</a></li>
                    <li><a href=\"../passion-projects.html\">Passion Projects</a></li>
                    <li><a href=\"../blog.html\">Articles &amp; Reports</a></li>
                </ul>
            </div>
        </aside>
    </div>

    <footer>
        <div class=\"footer-inner\">
            <p>&copy; 2025 Sullivan Steele</p>
            <ul class=\"footer-links\">
                <li><a href=\"mailto:sullivanrsteele@gmail.com\">Email</a></li>
                <li><a href=\"https://github.com/IAmADoctorYes\" target=\"_blank\" rel=\"noopener\">GitHub</a></li>
                <li><a href=\"https://www.linkedin.com/in/sullivan-steele-166102140\" target=\"_blank\" rel=\"noopener\">LinkedIn</a></li>
            </ul>
        </div>
    </footer>

    <script src=\"../../js/nav.js\"></script>
    <script src=\"../../js/backgrounds.js\"></script>
</body>
</html>
"""


def read_doc_plain_text(drive_service, file_id):
    request = drive_service.files().export_media(
        fileId=file_id,
        mimeType="text/plain",
    )
    data = request.execute()
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return str(data)


def load_credentials():
    if not Path(CREDS_FILE).exists():
        sys.exit(f"Credentials file not found: {CREDS_FILE}. Set CREDS_FILE or add credentials.json.")

    return service_account.Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)


def list_docs(drive_service):
    results = drive_service.files().list(
        q=(
            f"'{DRIVE_FOLDER_ID}' in parents and "
            "mimeType='application/vnd.google-apps.document' and trashed=false"
        ),
        fields="files(id, name, modifiedTime)",
        pageSize=1000,
        orderBy="modifiedTime desc",
    ).execute()
    return results.get("files", [])


def main():
    if not DRIVE_FOLDER_ID:
        sys.exit("DRIVE_FOLDER_ID is not set. Configure it in environment variables.")

    creds = load_credentials()
    drive_service = build("drive", "v3", credentials=creds)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_FILE.parent.mkdir(parents=True, exist_ok=True)

    docs = list_docs(drive_service)
    posts = []
    used_slugs = set()

    for file_data in docs:
        try:
            text = read_doc_plain_text(drive_service, file_data["id"])
        except HttpError as error:
            print(f"Warning: skipping '{file_data.get('name', 'Untitled')}' due to API error: {error}")
            continue

        title = normalize_whitespace(file_data.get("name", "Untitled")) or "Untitled"
        slug = unique_slug(slugify(title), used_slugs)
        preview = extract_preview(text)
        tags = extract_tags(text)
        modified_time = file_data.get("modifiedTime", "")

        post_html = render_post_html(title=title, content=text, modified_time=modified_time)
        (OUTPUT_DIR / slug).write_text(post_html, encoding="utf-8")

        posts.append(
            {
                "title": title,
                "slug": slug,
                "preview": preview,
                "tags": tags,
                "date": modified_time,
            }
        )

        if len(posts) >= MAX_POSTS:
            break

    INDEX_FILE.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Synced {len(posts)} post(s) to {OUTPUT_DIR} and wrote {INDEX_FILE}.")


if __name__ == "__main__":
    main()
