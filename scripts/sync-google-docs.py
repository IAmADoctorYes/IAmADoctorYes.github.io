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


def save_html(filename, title, content):
    html_content = f"""<html>
<head>
<title>{html.escape(title)}</title>
<meta charset="UTF-8">
</head>
<body>
<h1>{html.escape(title)}</h1>
<pre>{html.escape(content)}</pre>
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
