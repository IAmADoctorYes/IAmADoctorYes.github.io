#!/usr/bin/env python3
from __future__ import annotations
import os, re, io, json, time, html, logging, tempfile, unicodedata
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# ---------- CONFIG ----------
POSTS_DIR = Path("pages/blog")
BLOG_HTML = Path("pages/blog.html")
STATE_FILE = Path("scripts/sync-state.json")

DRIVE_FOLDER_ID = os.environ.get("DRIVE_FOLDER_ID")
CREDS_FILE = os.environ.get("CREDS_FILE")
PREFETCH = os.environ.get("PREFETCH_PARTS","false").lower()=="true"

SCOPES=["https://www.googleapis.com/auth/drive.readonly"]
LARGE_DOC_THRESHOLD=8*1024*1024
CHUNK_SIZE=2*1024*1024

logging.basicConfig(level=logging.INFO,format="%(levelname)s: %(message)s")
log=logging.getLogger("sync")

# ---------- helpers ----------
def atomic_write(path:Path,data:str):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=str(path.parent))
    with open(fd,"w",encoding="utf-8") as f: f.write(data)
    Path(tmp).replace(path)

def slugify(t:str)->str:
    t=unicodedata.normalize("NFKD",t).encode("ascii","ignore").decode()
    t=re.sub(r"[^\w\s-]","",t).strip().lower()
    return re.sub(r"[-\s]+","-",t) or "post"

def retry(fn,tries=3):
    for i in range(tries):
        try:return fn()
        except Exception as e:
            if i==tries-1: raise
            time.sleep(1.5)

# ---------- google ----------
def service():
    creds=service_account.Credentials.from_service_account_file(CREDS_FILE,scopes=SCOPES)
    return build("drive","v3",credentials=creds,cache_discovery=False)

def list_docs(svc):
    q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.document' and trashed=false"
    r=retry(lambda:svc.files().list(q=q,fields="files(id,name,modifiedTime)").execute())
    return r.get("files",[])

def download_html(svc,id):
    req=svc.files().export_media(fileId=id,mimeType="text/html")
    fh=io.BytesIO()
    dl=MediaIoBaseDownload(fh,req)
    done=False
    while not done:_,done=dl.next_chunk()
    return fh.getvalue().decode()

# ---------- clean html ----------
def clean_html(html_str:str)->str:
    soup=BeautifulSoup(html_str,"html.parser")
    body=soup.body or soup

    # remove junk tags
    for tag in body(["style","script","meta","link"]):
        tag.decompose()

    # strip inline styles + empty spans/divs
    for t in body.find_all(True):
        t.attrs.pop("style",None)
        if t.name in ("span","div") and not t.text.strip() and not t.find():
            t.decompose()

    # optimize images
    seen=set()
    for img in body.find_all("img"):
        src=img.get("src")
        if not src or src in seen:
            img.decompose(); continue
        seen.add(src)
        img["loading"]="lazy"
        img["decoding"]="async"
        img.attrs.pop("width",None)
        img.attrs.pop("height",None)

    return "".join(str(x) for x in body.children if str(x).strip())

# ---------- chunk ----------
def split_html(html_str:str)->List[str]:
    soup=BeautifulSoup(html_str,"html.parser")
    body=soup.body or soup
    parts=[];cur=[];size=0
    for n in body.children:
        s=str(n)
        if not s.strip(): continue
        b=len(s.encode())
        if cur and size+b>CHUNK_SIZE:
            parts.append("".join(cur));cur=[s];size=b
        else:
            cur.append(s);size+=b
    if cur: parts.append("".join(cur))
    return parts or [html_str]

# ---------- page ----------
def build_post(title,author,date,content,parts):
    parts_json=json.dumps(parts or [])
    prefetch="true" if PREFETCH else "false"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<link rel="stylesheet" href="../../css/main.css">
</head>
<body>
<main class="page-content">
<h1>{html.escape(title)}</h1>
<div class="article-meta">{date} • {html.escape(author)}</div>
<div id="docs">{content}</div>
<div id="more"></div>
</main>

<script>
const PARTS={parts_json};
const PREFETCH={prefetch};

async function loadParts(){{
 if(PARTS.length<2)return;
 const box=document.getElementById("docs");
 for(let i=1;i<PARTS.length;i++){{
  const r=await fetch(PARTS[i]);
  box.insertAdjacentHTML("beforeend",await r.text());
 }}
 document.getElementById("btn")?.remove();
}}

if(PARTS.length>1){{
 let b=document.createElement("button");
 b.id="btn";
 b.textContent="Load full document";
 b.onclick=loadParts;
 document.getElementById("more").appendChild(b);

 if(PREFETCH)
   setTimeout(loadParts,1500);
}}
</script>
</body></html>"""

# ---------- index ----------
AUTO_START="<!-- AUTO:START -->"
AUTO_END="<!-- AUTO:END -->"

def preview(text:str)->str:
    text=re.sub(r"\s+"," ",text)
    return text[:160]+"…" if len(text)>160 else text

def rebuild_index():
    posts=[]
    for f in POSTS_DIR.glob("*.html"):
        if ".part" in f.name: continue
        html=f.read_text(encoding="utf-8")
        soup=BeautifulSoup(html,"html.parser")
        h1=soup.find("h1")
        title=h1.text if h1 else f.stem
        date=re.search(r"\d{4}-\d{2}-\d{2}",html)
        date=date.group(0) if date else "0000-00-00"
        p=soup.find("p")
        snippet=preview(p.text) if p else ""
        posts.append((date,f.name,title,snippet))
    posts.sort(reverse=True)

    items="".join(f"""
<article class="article-preview">
<div class="preview-meta"><span>{d}</span><span class="tag tag-green">Doc</span></div>
<h3><a href="blog/{n}">{html.escape(t)}</a></h3>
<p>{html.escape(s)}</p>
</article>""" for d,n,t,s in posts)

    block=f"<section class=\"section-rule\" id=\"docs\"><h2>Synced Docs</h2>{items}</section>"

    txt=BLOG_HTML.read_text(encoding="utf-8")
    if AUTO_START in txt:
        before,rest=txt.split(AUTO_START,1)
        _,after=rest.split(AUTO_END,1)
        txt=before+AUTO_START+block+AUTO_END+after
    else:
        txt+=AUTO_START+block+AUTO_END
    atomic_write(BLOG_HTML,txt)

# ---------- state ----------
def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}

def save_state(s): atomic_write(STATE_FILE,json.dumps(s,indent=2))

# ---------- main ----------
def main():
    if not DRIVE_FOLDER_ID or not CREDS_FILE:
        log.error("Missing env vars");return 1

    POSTS_DIR.mkdir(parents=True,exist_ok=True)
    svc=service()
    files=list_docs(svc)
    state=load_state()
    changed=False

    for f in files:
        id,name,mod=f["id"],f["name"],f["modifiedTime"]
        if state.get(id)==mod: continue
        log.info("Syncing %s",name)

        raw=download_html(svc,id)
        soup=BeautifulSoup(raw,"html.parser")

        title=(soup.title.string if soup.title else name).strip()
        author="Unknown"
        date=re.search(r"\d{4}-\d{2}-\d{2}",mod).group(0)

        content=clean_html(raw)

        slug=f"{date}-{slugify(title)}"
        fname=slug+".html"
        i=1
        while (POSTS_DIR/fname).exists():
            fname=f"{slug}-{i}.html";i+=1

        parts=None
        if len(content.encode())>=LARGE_DOC_THRESHOLD:
            parts=split_html(content)
            for i,p in enumerate(parts):
                atomic_write(POSTS_DIR/f"{fname[:-5]}.part{i+1}.html",p)
            content=parts[0]

        html_page=build_post(title,author,date,content,
            [f"{fname[:-5]}.part{i+1}.html" for i in range(len(parts))] if parts else None)

        atomic_write(POSTS_DIR/fname,html_page)
        state[id]=mod
        changed=True

    save_state(state)
    rebuild_index()

    log.info("Done" if changed else "No changes")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
