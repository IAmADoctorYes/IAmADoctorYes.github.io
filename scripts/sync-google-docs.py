#!/usr/bin/env python3
"""
Sync Google Docs from a Drive folder to HTML posts under pages/blog.
Requires: DRIVE_FOLDER_ID and CREDS_FILE environment variables.
"""

import os
import json
import subprocess
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO

# Setup
FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', '')
CREDS_FILE = os.getenv('CREDS_FILE', '/tmp/creds.json')
POSTS_DIR = os.path.join('pages', 'blog')
BLOG_INDEX_PATH = os.path.join('pages', 'blog.html')
STATE_PATH = os.path.join('scripts', 'sync-state.json')

if not os.path.exists(POSTS_DIR):
    os.makedirs(POSTS_DIR)

if not FOLDER_ID:
    print("ERROR: GOOGLE_DRIVE_FOLDER_ID not set. Skipping sync.")
    exit(0)

if not os.path.exists(CREDS_FILE):
    print(f"ERROR: Credentials file not found at {CREDS_FILE}. Skipping sync.")
    exit(0)

# Authenticate
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# Load sync state
state = {}
if os.path.exists(STATE_PATH):
    try:
        with open(STATE_PATH, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except Exception:
        state = {}

# Find all Google Docs in the folder
query = f"'{FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
results = drive_service.files().list(q=query, spaces='drive', fields='files(id, name, modifiedTime)', pageSize=100).execute()
files = results.get('files', [])

print(f"Found {len(files)} Google Docs to sync")

posts_for_index = []

seen_ids = set()


# --- BEGIN PATCH: Export as HTML and extract images ---
import zipfile
import shutil
from bs4 import BeautifulSoup


# Remove any blog articles and images not in the targeted Google Drive folder (do this BEFORE the sync loop)
existing_files = set(os.listdir(POSTS_DIR))
expected_htmls = set()
expected_images = set()
for file in files:
    try:
        mod_dt = datetime.fromisoformat(file['modifiedTime'].replace('Z', '+00:00'))
    except:
        mod_dt = datetime.now()
    mod_date = mod_dt.strftime('%Y-%m-%d')
    mod_time = mod_dt.strftime('%H-%M-%S')
    slug = file['name'].lower().replace(' ', '-').replace("'", '').replace('"', '')
    slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
    expected_htmls.add(f"{mod_date}-{mod_time}-{slug}.html")
    expected_images.add(f"{mod_date}-{mod_time}-{slug}_images")
for fname in existing_files:
    if fname.endswith('.html') and fname not in expected_htmls:
        os.remove(os.path.join(POSTS_DIR, fname))
    if fname.endswith('_images') and fname not in expected_images:
        shutil.rmtree(os.path.join(POSTS_DIR, fname), ignore_errors=True)

# Now do the sync loop
for file in files:
    file_id = file['id']
    file_name = file['name']
    modified_time = file['modifiedTime']
    seen_ids.add(file_id)

    # Parse date and time from modifiedTime or use now
    try:
        mod_dt = datetime.fromisoformat(modified_time.replace('Z', '+00:00'))
    except:
        mod_dt = datetime.now()
    mod_date = mod_dt.strftime('%Y-%m-%d')
    mod_time = mod_dt.strftime('%H-%M-%S')

    # Sanitize filename
    slug = file_name.lower().replace(' ', '-').replace("'", '').replace('"', '')
    slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
    post_filename = f"{mod_date}-{mod_time}-{slug}.html"
    post_path = os.path.join(POSTS_DIR, post_filename)
    images_dir = os.path.join(POSTS_DIR, f"{mod_date}-{mod_time}-{slug}_images")

    if state.get(file_id) == modified_time and os.path.exists(post_path):
        print(f"Skipping unchanged: {file_name}")
        posts_for_index.append({
            'title': file_name,
            'date': mod_date,
            'filename': post_filename,
            'summary': state.get(f"summary_{file_id}", '')
        })
        continue

    print(f"Processing: {file_name} -> {post_filename}")

    # Export as zipped HTML
    html_zip_data = BytesIO()
    try:
        request = drive_service.files().export_media(
            fileId=file_id,
            mimeType='application/zip'
        )
        downloader = MediaIoBaseDownload(html_zip_data, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
    except HttpError as e:
        # Fallback for large docs: download as DOCX, compress as ZIP, create placeholder HTML
        try:
            # Download DOCX
            docx_data = BytesIO()
            request = drive_service.files().export_media(
                fileId=file_id,
                mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
            )
            downloader = MediaIoBaseDownload(docx_data, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            # Save DOCX to temp file
            temp_docx_path = f"/tmp/{file_id}.docx"
            with open(temp_docx_path, 'wb') as f:
                f.write(docx_data.getvalue())
            # Compress DOCX and place in blog directory
            zip_filename = f"{mod_date}-{mod_time}-{slug}.zip"
            zip_path = os.path.join(POSTS_DIR, zip_filename)
            import zipfile as zf
            with zf.ZipFile(zip_path, 'w', zf.ZIP_DEFLATED) as zipf:
                zipf.write(temp_docx_path, arcname=os.path.basename(temp_docx_path))
            print(f"  ✓ Compressed DOCX for large doc: {zip_path}")
            # Add a placeholder HTML file with a download link
            page_html = f"""<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <meta name=\"description\" content=\"{file_name}\">\n    <title>{file_name} | Sullivan Steele</title>\n    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n    <link href=\"https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"../../css/main.css\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css\">\n    <script src=\"../../js/theme.js\"></script>\n</head>\n<body>\n    <a href=\"#main\" class=\"skip-link\">Skip to main content</a>\n    <nav>\n        <div class=\"nav-container\">\n            <a href=\"../../index.html\" class=\"nav-logo\">SULLIVAN STEELE</a>\n            <button class=\"menu-toggle\" aria-label=\"Toggle navigation\" aria-expanded=\"false\" aria-controls=\"nav-links\">\n                <span></span><span></span><span></span>\n            </button>\n            <ul class=\"nav-links\" id=\"nav-links\">\n                <li><a href=\"../../index.html\">Home</a></li>\n                <li><a href=\"../projects.html\">Projects</a></li>\n                <li><a href=\"../blog.html\">Blog</a></li>\n                <li><a href=\"../about.html\">About</a></li>\n                <li><a href=\"../music.html\">Music</a></li>\n                <li><a href=\"../shop.html\">Shop</a></li>\n                <li><button class=\"theme-toggle\" aria-label=\"Toggle theme\"><i class=\"bi bi-sun\"></i></button></li>\n            </ul>\n        </div>\n    </nav>\n    <div class=\"site-layout\">\n        <main id=\"main\" class=\"page-content\">\n            <div class=\"breadcrumb\">\n                <a href=\"../../index.html\">Home</a>\n                <span class=\"sep\">/</span>\n                <a href=\"../blog.html\">Blog</a>\n                <span class=\"sep\">/</span>\n                {file_name}\n            </div>\n            <div class=\"article-content\">\n                <div class=\"article-header\">\n                    <h1>{file_name}</h1>\n                    <div class=\"article-meta\">\n                        <span><i class=\"bi bi-calendar3\"></i> {mod_date}</span>\n                        <span><i class=\"bi bi-person\"></i> Sullivan Steele</span>\n                    </div>\n                </div>\n                <div class=\"large-doc-download\">\n                    <p>This document is too large to display directly. <a href=\"{zip_filename}\" download>Download the compressed DOCX</a> to view the full content.</p>\n                </div>\n            </div>\n        </main>\n        <aside class=\"sidebar\" aria-label=\"Page navigation\">\n            <div class=\"sidebar-section\">\n                <h4>Pages</h4>\n                <ul>\n                    <li><a href=\"../../index.html\">Home</a></li>\n                    <li><a href=\"../projects.html\">Projects</a></li>\n                    <li><a href=\"../blog.html\">Blog</a></li>\n                    <li><a href=\"../about.html\">About</a></li>\n                    <li><a href=\"../music.html\">Music</a></li>\n                    <li><a href=\"../shop.html\">Shop</a></li>\n                </ul>\n            </div>\n        </aside>\n    </div>\n    <footer>\n        <div class=\"footer-inner\">\n            <p>&copy; 2025 Sullivan Steele</p>\n            <ul class=\"footer-links\">\n                <li><a href=\"mailto:sullivanrsteele@gmail.com\">Email</a></li>\n                <li><a href=\"https://github.com/IAmADoctorYes\" target=\"_blank\" rel=\"noopener\">GitHub</a></li>\n                <li><a href=\"https://www.linkedin.com/in/sullivan-steele-166102140\" target=\"_blank\" rel=\"noopener\">LinkedIn</a></li>\n            </ul>\n        </div>\n    </footer>\n    <script src=\"../../js/nav.js\"></script>\n    <script src=\"../../js/backgrounds.js\"></script>\n</body>\n</html>\n"""
            with open(post_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            print(f"  ✓ Large doc placeholder and ZIP created: {post_path}")
            state[file_id] = modified_time
            summary = state.get(f"summary_{file_id}", '')
            if not summary:
                summary = ''
                state[f"summary_{file_id}"] = summary
            posts_for_index.append({
                'title': file_name,
                'date': mod_date,
                'filename': post_filename,
                'summary': summary
            })
            continue
        except Exception as e:
            # Try to fetch text from the document using the Google Docs API
            try:
                docs_service = build('docs', 'v1', credentials=creds)
                doc = docs_service.documents().get(documentId=file_id).execute()
                text_chunks = []
                for elem in doc.get('body', {}).get('content', []):
                    if 'paragraph' in elem:
                        for para_elem in elem['paragraph'].get('elements', []):
                            if 'textRun' in para_elem:
                                text_chunks.append(para_elem['textRun'].get('content', ''))
                doc_text = ''.join(text_chunks)
            except Exception:
                doc_text = '<p>Unable to extract text from this document.</p>'

            print(f"  ✓ Large doc text and carousel created: {post_path}")
            state[file_id] = modified_time
            summary = state.get(f"summary_{file_id}", '')
            if not summary:
                summary = ''
                state[f"summary_{file_id}"] = summary
            posts_for_index.append({
                'title': file_name,
                'date': mod_date,
                'filename': post_filename,
                'summary': summary
            })
            continue

    # Unzip HTML and images
    temp_zip_path = f"/tmp/{file_id}.zip"
    with open(temp_zip_path, 'wb') as f:
        f.write(html_zip_data.getvalue())

    temp_extract_dir = f"/tmp/{file_id}_extract"
    if os.path.exists(temp_extract_dir):
        shutil.rmtree(temp_extract_dir)
    os.makedirs(temp_extract_dir, exist_ok=True)

    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_extract_dir)

    # Find HTML file and images
    html_file = None
    for fname in os.listdir(temp_extract_dir):
            with open(post_path, 'w', encoding='utf-8') as f:
                f.write(page_html)
            print(f"  ✓ Large doc text and carousel created: {post_path}")
            state[file_id] = modified_time
            summary = state.get(f"summary_{file_id}", '')
            if not summary:
                summary = ''
                state[f"summary_{file_id}"] = summary
            posts_for_index.append({
                'title': file_name,
                'date': mod_date,
                'filename': post_filename,
                'summary': summary
            })
            continue
        shutil.rmtree(temp_extract_dir)
        os.remove(temp_zip_path)
        continue

    # Copy images to images_dir
    if os.path.exists(images_dir):
        shutil.rmtree(images_dir)
    os.makedirs(images_dir, exist_ok=True)
    for fname in os.listdir(temp_extract_dir):
        if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp')):
            shutil.copy(os.path.join(temp_extract_dir, fname), os.path.join(images_dir, fname))

    # Read and update HTML to point to local images
    with open(html_file, 'r', encoding='utf-8') as f:
        body_html = f.read()

    soup = BeautifulSoup(body_html, 'html.parser')
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if src and os.path.exists(os.path.join(temp_extract_dir, src)):
            img['src'] = f"{mod_date}-{slug}_images/{os.path.basename(src)}"

    body_html = str(soup)
    # Write the Google Docs HTML as the main content, preserving its structure
    # Remove the outer wrappers and inject the Google Docs HTML directly after the <body> tag
    # Find the <body>...</body> in body_html and extract only the inner content
    from bs4 import BeautifulSoup as BS
    soup_doc = BS(body_html, 'html.parser')
    doc_body = soup_doc.body
    doc_content = doc_body.decode_contents() if doc_body else body_html
    # Compose a full HTML page with site layout and styled Google Docs content
    page_html = f"""<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n    <meta name=\"description\" content=\"{file_name}\">\n    <title>{file_name} | Sullivan Steele</title>\n    <link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">\n    <link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>\n    <link href=\"https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"../../css/main.css\">\n    <link rel=\"stylesheet\" href=\"https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css\">\n    <style>\n    .docs-content-container {{ max-width: 800px; margin: 2em auto; padding: 2em; background: var(--docs-bg, #fff); border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}\n    .docs-content-container h1, .docs-content-container h2, .docs-content-container h3, .docs-content-container h4, .docs-content-container h5, .docs-content-container h6 {{ margin-top: 1.2em; }}\n    .docs-content-container p {{ margin: 1em 0; }}\n    .docs-content-container mark {{ background: #ffe066; color: #222; padding: 0.2em 0.4em; border-radius: 4px; }}\n    .docs-content-container pre, .docs-content-container code {{ background: #222; color: #fff; padding: 0.2em 0.4em; border-radius: 4px; font-family: monospace; }}\n    @media (prefers-color-scheme: dark) {{\n        .docs-content-container {{ background: #222; color: #fff; }}\n        .docs-content-container mark {{ background: #ffd700; color: #222; }}\n        .docs-content-container pre, .docs-content-container code {{ background: #fff; color: #222; }}\n    }}\n    @media (prefers-color-scheme: light) {{\n        .docs-content-container {{ background: #fff; color: #222; }}\n        .docs-content-container mark {{ background: #ffe066; color: #222; }}\n        .docs-content-container pre, .docs-content-container code {{ background: #222; color: #fff; }}\n    }}\n    </style>\n    <script src=\"../../js/theme.js\"></script>\n</head>\n<body>\n    <a href=\"#main\" class=\"skip-link\">Skip to main content</a>\n    <nav>\n        <div class=\"nav-container\">\n            <a href=\"../../index.html\" class=\"nav-logo\">SULLIVAN STEELE</a>\n            <button class=\"menu-toggle\" aria-label=\"Toggle navigation\" aria-expanded=\"false\" aria-controls=\"nav-links\">\n                <span></span><span></span><span></span>\n            </button>\n            <ul class=\"nav-links\" id=\"nav-links\">\n                <li><a href=\"../../index.html\">Home</a></li>\n                <li><a href=\"../projects.html\">Projects</a></li>\n                <li><a href=\"../blog.html\">Blog</a></li>\n                <li><a href=\"../about.html\">About</a></li>\n                <li><a href=\"../music.html\">Music</a></li>\n                <li><a href=\"../shop.html\">Shop</a></li>\n                <li><button class=\"theme-toggle\" aria-label=\"Toggle theme\"><i class=\"bi bi-sun\"></i></button></li>\n            </ul>\n        </div>\n    </nav>\n    <div class=\"site-layout\">\n        <main id=\"main\" class=\"page-content\">\n            <div class=\"breadcrumb\">\n                <a href=\"../../index.html\">Home</a>\n                <span class=\"sep\">/</span>\n                <a href=\"../blog.html\">Blog</a>\n                <span class=\"sep\">/</span>\n                {file_name}\n            </div>\n            <div class=\"article-content\">\n                <div class=\"article-header\">\n                    <h1>{file_name}</h1>\n                    <div class=\"article-meta\">\n                        <span><i class=\"bi bi-calendar3\"></i> {mod_date}</span>\n                        <span><i class=\"bi bi-person\"></i> Sullivan Steele</span>\n                    </div>\n                </div>\n                <div class=\"docs-content-container">{doc_content}</div>\n            </div>\n        </main>\n        <aside class=\"sidebar\" aria-label=\"Page navigation\">\n            <div class=\"sidebar-section\">\n                <h4>Pages</h4>\n                <ul>\n                    <li><a href=\"../../index.html\">Home</a></li>\n                    <li><a href=\"../projects.html\">Projects</a></li>\n                    <li><a href=\"../blog.html\">Blog</a></li>\n                    <li><a href=\"../about.html\">About</a></li>\n                    <li><a href=\"../music.html\">Music</a></li>\n                    <li><a href=\"../shop.html\">Shop</a></li>\n                </ul>\n            </div>\n        </aside>\n    </div>\n    <footer>\n        <div class=\"footer-inner\">\n            <p>&copy; 2025 Sullivan Steele</p>\n            <ul class=\"footer-links\">\n                <li><a href=\"mailto:sullivanrsteele@gmail.com\">Email</a></li>\n                <li><a href=\"https://github.com/IAmADoctorYes\" target=\"_blank\" rel=\"noopener\">GitHub</a></li>\n                <li><a href=\"https://www.linkedin.com/in/sullivan-steele-166102140\" target=\"_blank\" rel=\"noopener\">LinkedIn</a></li>\n            </ul>\n        </div>\n    </footer>\n    <script src=\"../../js/nav.js\"></script>\n    <script src=\"../../js/backgrounds.js\"></script>\n</body>\n</html>\n"""
    with open(post_path, 'w', encoding='utf-8') as f:
        f.write(page_html)
    print(f"  ✓ Converted: {post_path} (with images)")
    state[file_id] = modified_time
    summary = state.get(f"summary_{file_id}", '')
    if not summary:
        summary = ''
        state[f"summary_{file_id}"] = summary
    posts_for_index.append({
        'title': file_name,
        'date': mod_date,
        'filename': post_filename,
        'summary': summary
    })
    shutil.rmtree(temp_extract_dir)
    os.remove(temp_zip_path)
# --- END PATCH ---

# Remove state for docs that no longer exist
for file_id in list(state.keys()):
    if file_id not in seen_ids:
        state.pop(file_id, None)

def update_blog_index(posts):
    if not os.path.exists(BLOG_INDEX_PATH):
        return
    try:
        with open(BLOG_INDEX_PATH, 'r', encoding='utf-8') as f:
            html = f.read()
    except Exception:
        return

    start_tag = '<!-- AUTO:START -->'
    end_tag = '<!-- AUTO:END -->'
    start_idx = html.find(start_tag)
    end_idx = html.find(end_tag)
    if start_idx == -1 or end_idx == -1:
        return

    posts_sorted = sorted(posts, key=lambda p: p['date'], reverse=True)
    cards = []
    for post in posts_sorted:
        summary = post.get('summary', '')
        summary_html = f'<p class="article-summary">{summary}</p>' if summary else ''
        cards.append(
            '                <article class="article-preview">\n'
            '                    <div class="preview-meta">\n'
            '                        <span>' + post['date'] + '</span>\n'
            '                        <span class="tag tag-green">Doc</span>\n'
            '                    </div>\n'
            '                    <h3><a href="blog/' + post['filename'] + '">' + post['title'] + '</a></h3>\n'
            f'                    {summary_html}\n'
            '                </article>'
        )

    if cards:
        section_body = '\n\n'.join(cards)
    else:
        section_body = (
            '                <div class="placeholder-section">\n'
            '                    <p>Synced posts will appear here after the workflow runs.</p>\n'
            '                </div>'
        )

    section = (
        start_tag + '\n'
        '            <section class="section-rule" id="docs">\n'
        '                <h2>Synced Docs</h2>\n'
        + section_body + '\n'
        '            </section>\n'
        '            ' + end_tag
    )

    new_html = html[:start_idx] + section + html[end_idx + len(end_tag):]
    try:
        with open(BLOG_INDEX_PATH, 'w', encoding='utf-8') as f:
            f.write(new_html)
    except Exception:
        return

try:
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, sort_keys=True)
except Exception:
    pass

update_blog_index(posts_for_index)

print("Sync complete!")
