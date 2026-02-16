import os
import re
import json
import html
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account

# ================= CONFIG =================
DOCS_FOLDER_ID = "YOUR_FOLDER_ID"
OUTPUT_DIR = "blog"
INDEX_FILE = "assets/search-index.json"
MAX_POSTS = 150
# ==========================================

SCOPES = ["https://www.googleapis.com/auth/documents.readonly"]

creds = service_account.Credentials.from_service_account_file(
    "credentials.json", scopes=SCOPES
)

docs_service = build("docs", "v1", credentials=creds)
drive_service = build("drive", "v3", credentials=creds)


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


def get_docs():
    results = drive_service.files().list(
        q=f"'{DOCS_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.document'",
        fields="files(id, name, modifiedTime)",
    ).execute()

    return results.get("files", [])


def save_html(filename, title, content):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

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

    with open(os.path.join(OUTPUT_DIR, filename), "w", encoding="utf8") as f:
        f.write(html_content)


def main():
    docs = get_docs()
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
