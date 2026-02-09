#!/usr/bin/env python3
"""
Sync Google Docs from a Drive folder to Jekyll _posts/ as Markdown
Requires: DRIVE_FOLDER_ID and CREDS_FILE environment variables
"""

import os
import json
import subprocess
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
from google.auth.exceptions import DefaultCredentialsError
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
from io import BytesIO

# Setup
FOLDER_ID = os.getenv('DRIVE_FOLDER_ID', '')
CREDS_FILE = os.getenv('CREDS_FILE', '/tmp/creds.json')
POSTS_DIR = '_posts'
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

seen_ids = set()

for file in files:
    file_id = file['id']
    file_name = file['name']
    modified_time = file['modifiedTime']
    seen_ids.add(file_id)

    if state.get(file_id) == modified_time:
        print(f"Skipping unchanged: {file_name}")
        continue
    
    # Parse date from modifiedTime or use today
    try:
        mod_date = datetime.fromisoformat(modified_time.replace('Z', '+00:00')).strftime('%Y-%m-%d')
    except:
        mod_date = datetime.now().strftime('%Y-%m-%d')
    
    # Sanitize filename for Jekyll post
    slug = file_name.lower().replace(' ', '-').replace("'", '').replace('"', '')
    slug = ''.join(c for c in slug if c.isalnum() or c in '-_')
    post_filename = f"{mod_date}-{slug}.md"
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
    
    # Convert DOCX to Markdown using pandoc
    try:
        result = subprocess.run(['pandoc', docx_path, '-t', 'markdown', '-o', post_path], capture_output=True, text=True)
        if result.returncode == 0:
            # Read the markdown content
            with open(post_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add Jekyll frontmatter
            frontmatter = f"""---
layout: post
title: "{file_name}"
date: {mod_date}
categories: blog
---

"""
            with open(post_path, 'w', encoding='utf-8') as f:
                f.write(frontmatter + content)
            
            print(f"  ✓ Converted: {post_path}")
            state[file_id] = modified_time
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

try:
    with open(STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, sort_keys=True)
except Exception:
    pass

print("Sync complete!")
