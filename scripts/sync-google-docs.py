#!/usr/bin/env python3
"""
Google Docs → Blog Sync Script
Production-grade static publishing pipeline for GitHub Pages
Author: Sullivan Steele system

Features
--------
• Pulls docs from Google Drive folder
• Converts to HTML
• Generates blog post pages
• Splits large docs into lazy-load parts
• Updates blog index automatically
• Prevents duplicate posts
• Atomic writes
• Retry logic for API
• CI-friendly logging
"""

from __future__ import annotations
import os, re, json, html, logging, time, tempfile, unicodedata
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from bs4 import BeautifulSoup

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

# ================= CONFIG =================

LARGE_DOC_THRESHOLD = 8 * 1024 * 1024
CHUNK_SIZE = 2 * 1024 * 1024

POSTS_DIR = Path("pages/blog")
BLOG_HTML = Path("pages/blog.html")
STATE_FILE = Path("scripts/sync-state.json")

DRIVE_FOLDER_ID = os.environ["DRIVE_FOLDER_ID"]
CREDS_FILE = os.environ["CREDS_FILE"]

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# ==========================================

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("sync")


# ---------- helpers ----------

def retry(func, attempts=3, delay=3):
    for i in range(attempts):
        try:
            return func()
        except Exception as e:
            if i == attempts - 1:
                raise
            log.warning(f"Retry {i+1} failed: {e}")
            time.sleep(delay)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii","ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    text = re.sub(r"[-\s]+","-", text)
    return text or "post"


def atomic_write(path: Path, data: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=path.parent, encoding="utf8") as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def split_html(html_str: str) -> List[str]:
    soup = BeautifulSoup(html_str,"html.parser")
    body = soup.body or soup

    parts=[]
    cur=[]
    size=0

    for node in body.children:
        s=str(node)
        if not s.strip(): continue
        b=len(s.encode())
        if cur and size+b>CHUNK_SIZE:
            parts.append("".join(cur))
            cur=[s]; size=b
        else:
            cur.append(s); size+=b

    if cur: parts.append("".join(cur))
    return parts or [html_str]


# ---------- metadata ----------

def extract_meta(html_text:str, fallback_name:str):
    soup=BeautifulSoup(html_text,"html.parser")

    title=None
    if soup.title: title=soup.title.text.strip()
    if not title:
        h1=soup.find("h1")
        if h1: title=h1.text.strip()
    if not title: title=fallback_name

    author="Unknown"
    meta=soup.find("meta",{"name":"author"})
    if meta and meta.get("content"):
        author=meta["content"]

    date=None
    meta=soup.find("meta",{"name":"date"})
    if meta: date=meta.get("content")

    if not date:
        date=datetime.utcnow().strftime("%Y-%m-%d")

    return title,author,date


# ---------- HTML wrapper ----------

def build_page(title,author,date,content,parts):

    esc=lambda x: html.escape(x)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<link rel="stylesheet" href="../../css/main.css">
</head>
<body>

<main class="page-content">
<h1>{esc(title)}</h1>
<div class="meta">{esc(date)} • {esc(author)}</div>

<div id="docs-container">{content}</div>
<div id="docs-loading-placeholder"></div>
</main>

<script>
const PARTS={json.dumps(parts or [])};
if(PARTS.length>1){{
let btn=document.createElement("button");
btn.textContent="Load full document";
btn.onclick=async()=>{{
btn.disabled=true;
for(let i=1;i<PARTS.length;i++){{
let r=await fetch(PARTS[i]);
let t=await r.text();
let d=document.createElement("div");
d.innerHTML=t;
document.getElementById("docs-container").appendChild(d);
}}
btn.remove();
}};
document.getElementById("docs-loading-placeholder").appendChild(btn);
}}
</script>
</body></html>"""


# ---------- blog index updater ----------

def update_blog_index(posts):

    html_text=BLOG_HTML.read_text(encoding="utf8")

    start="<!-- AUTO:START -->"
    end="<!-- AUTO:END -->"

    before,rest=html_text.split(start)
    auto,after=rest.split(end)

    posts.sort(reverse=True,key=lambda p:p["date"])

    items=[]
    for p in posts:
        items.append(f"""
<article class="article-preview">
<div class="preview-meta">
<span>{p['date']}</span>
<span class="tag tag-green">Doc</span>
</div>
<h3><a href="blog/{p['file']}">{html.escape(p['title'])}</a></h3>
</article>
""")

    new_auto=f"""
{start}
<section class="section-rule" id="docs">
<h2>Synced Docs</h2>
{''.join(items)}
</section>
{end}
"""

    atomic_write(BLOG_HTML, before+new_auto+after)
    log.info("Updated blog index")


# ---------- drive ----------

def build_service():
    creds=service_account.Credentials.from_service_account_file(CREDS_FILE,scopes=SCOPES)
    return build("drive","v3",credentials=creds)


def fetch_docs(service):
    q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
    res=retry(lambda: service.files().list(q=q,fields="files(id,name,modifiedTime)").execute())
    return res["files"]


def download_html(service,file_id):
    request=service.files().export_media(fileId=file_id,mimeType="text/html")
    fh=io.BytesIO()
    downloader=MediaIoBaseDownload(fh,request)
    done=False
    while not done:
        _,done=downloader.next_chunk()
    return fh.getvalue().decode("utf8")


# ---------- state ----------

def load_state():
    if not STATE_FILE.exists(): return {}
    return json.loads(STATE_FILE.read_text())


def save_state(state):
    atomic_write(STATE_FILE,json.dumps(state,indent=2))


# ---------- main sync ----------

def main():

    service=build_service()
    files=fetch_docs(service)
    state=load_state()

    new_posts=[]

    for f in files:

        if state.get(f["id"])==f["modifiedTime"]:
            continue

        log.info(f"Syncing: {f['name']}")

        html_doc=download_html(service,f["id"])
        title,author,date=extract_meta(html_doc,f["name"])

        slug=slugify(title)
        filename=f"{date}-{slug}.html"
        path=POSTS_DIR/filename

        content=BeautifulSoup(html_doc,"html.parser").body
        content=str(content) if content else html_doc

        parts=None
        if len(content.encode())>LARGE_DOC_THRESHOLD:
            pieces=split_html(content)
            parts=[]
            for i,p in enumerate(pieces):
                name=f"{filename[:-5]}.part{i+1}.html"
                atomic_write(POSTS_DIR/name,p)
                parts.append(name)
            content=pieces[0]

        page=build_page(title,author,date,content,parts)
        atomic_write(path,page)

        state[f["id"]]=f["modifiedTime"]

        new_posts.append({"title":title,"date":date,"file":filename})

    save_state(state)

    if new_posts:
        update_blog_index(new_posts)
    else:
        log.info("No changes")



if __name__=="__main__":
    main()
