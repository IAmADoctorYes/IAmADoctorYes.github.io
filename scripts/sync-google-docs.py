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

for file in files:
    file_id = file['id']
    file_name = file['name']
    modified_time = file['modifiedTime']
    seen_ids.add(file_id)

    if state.get(file_id) == modified_time:
        print(f"Skipping unchanged: {file_name}")
        if os.path.exists(post_path):
            posts_for_index.append({
                'title': file_name,
                'date': mod_date,
                'filename': post_filename
            })
        continue
    
    # Parse date from modifiedTime or use today
    try:
        mod_date = datetime.fromisoformat(modified_time.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except:
        mod_date = datetime.now().strftime('%Y-%m-%d')
    
    # Sanitize filename
    slug = file_name.lower().replace(' ', '-').replace("'", '').replace('"', '')
    slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
    post_filename = f"{mod_date}-{slug}.html"
    post_path = os.path.join(POSTS_DIR, post_filename)
    
    print(f"Processing: {file_name} -> {post_filename}")
    
    # Export as DOCX
    docx_data = BytesIO()
    request = drive_service.files().export_media(
        fileId=file_id,
        mimeType='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    downloader = MediaIoBaseDownload(docx_data, request)
    done = False
    try:
        while not done:
            _, done = downloader.next_chunk()
    except HttpError as e:
        if 'exportSizeLimitExceeded' in str(e):
            print("  ✗ Skipped (export too large): " + file_name)
            state[file_id] = modified_time
            continue
        print("  ✗ Export failed: " + file_name + " (" + str(e) + ")")
        continue
    docx_path = f"/tmp/{file_id}.docx"
    with open(docx_path, 'wb') as f:
        f.write(docx_data.getvalue())
    
    # Convert DOCX to HTML using pandoc
    try:
        result = subprocess.run(['pandoc', docx_path, '-t', 'html'], capture_output=True, text=True)
        if result.returncode == 0:
            body_html = result.stdout
            page_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{file_name}">
    <title>{file_name} | Sullivan Steele</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Next:ital,wght@0,400;0,700;1,400;1,700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">
    <link rel="stylesheet" href="../../css/main.css">
    <script src="../../js/theme.js"></script>
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
                <li><a href="../projects.html">Projects</a></li>
                <li><a href="../blog.html">Blog</a></li>
                <li><a href="../about.html">About</a></li>
                <li><a href="../music.html">Music</a></li>
                <li><a href="../shop.html">Shop</a></li>
                <li><button class="theme-toggle" aria-label="Toggle theme"><i class="bi bi-sun"></i></button></li>
            </ul>
        </div>
    </nav>

    <div class="site-layout">
        <main id="main" class="page-content">

            <div class="breadcrumb">
                <a href="../../index.html">Home</a>
                <span class="sep">/</span>
                <a href="../blog.html">Blog</a>
                <span class="sep">/</span>
                {file_name}
            </div>

            <div class="article-content">
                <div class="article-header">
                    <h1>{file_name}</h1>
                    <div class="article-meta">
                        <span><i class="bi bi-calendar3"></i> {mod_date}</span>
                        <span><i class="bi bi-person"></i> Sullivan Steele</span>
                    </div>
                </div>

{body_html}

            </div>

        </main>

        <aside class="sidebar" aria-label="Page navigation">
            <div class="sidebar-section">
                <h4>Pages</h4>
                <ul>
                    <li><a href="../../index.html">Home</a></li>
                    <li><a href="../projects.html">Projects</a></li>
                    <li><a href="../blog.html">Blog</a></li>
                    <li><a href="../about.html">About</a></li>
                    <li><a href="../music.html">Music</a></li>
                    <li><a href="../shop.html">Shop</a></li>
                </ul>
            </div>
        </aside>
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

            with open(post_path, 'w', encoding='utf-8') as f:
                f.write(page_html)

            print(f"  ✓ Converted: {post_path}")
            state[file_id] = modified_time
            posts_for_index.append({
                'title': file_name,
                'date': mod_date,
                'filename': post_filename
            })
        else:
            print(f"  ✗ Pandoc error: {result.stderr}")
    except Exception as e:
        print(f"  ✗ Error: {e}")
    finally:
        if os.path.exists(docx_path):
            os.remove(docx_path)

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
        cards.append(
            '                <article class="article-preview">\n'
            '                    <div class="preview-meta">\n'
            '                        <span>' + post['date'] + '</span>\n'
            '                        <span class="tag tag-green">Doc</span>\n'
            '                    </div>\n'
            '                    <h3><a href="blog/' + post['filename'] + '">' + post['title'] + '</a></h3>\n'
            '                    <p>Synced from Google Docs.</p>\n'
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
