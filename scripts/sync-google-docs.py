# --- ADD / REPLACE THESE CONSTANTS NEAR THE TOP OF FILE ---
LARGE_DOC_THRESHOLD = 8 * 1024 * 1024  # 8 MB before using chunked processing
CHUNK_SIZE = 2 * 1024 * 1024  # target chunk size for parts (2 MB)

# --- NEW HELPER: split_html_into_chunks ---
def split_html_into_chunks(html_str: str, approx_chunk_bytes: int = CHUNK_SIZE) -> List[str]:
    """
    Split an HTML fragment into a list of HTML fragments of roughly approx_chunk_bytes each.
    We split at top-level body children to keep logical sections intact.
    """
    soup = BeautifulSoup(html_str, "html.parser")
    # Use body children if present, else use top-level children
    body = soup.body or soup
    parts: List[str] = []
    current: List[str] = []
    current_size = 0

    # iterate through the immediate children so we keep headings/sections together
    for node in list(body.children):
        # ignore empty strings (whitespace)
        s = str(node)
        if not s.strip():
            continue
        b = len(s.encode("utf-8"))
        # If adding this node would exceed target and we already have content, start new chunk
        if current and (current_size + b > approx_chunk_bytes):
            parts.append("".join(current))
            current = [s]
            current_size = b
        else:
            current.append(s)
            current_size += b

    if current:
        parts.append("".join(current))
    # if somehow nothing split, return the entire HTML as one part
    if not parts:
        parts = [html_str]
    return parts


# --- REPLACE build_post_html WITH THE FOLLOWING (improves styling + contrast + JS hook for parts) ---
def build_post_html(title: str, author: str, date_str: str, doc_content_html: str, parts_filenames: Optional[List[str]] = None) -> str:
    """
    Wrap the extracted doc HTML in your site layout, with improved styles to mimic
    Google Docs-like typographic styling and accessible dark/light contrast.
    If parts_filenames is provided and length > 1, the page includes JS to lazy-load them.
    """
    esc_title = html_escape.escape(title)
    esc_author = html_escape.escape(author)
    esc_date = html_escape.escape(date_str)
    parts_json = json.dumps(parts_filenames or [])
    # Use google fonts for nice typography; you can change families if you want.
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta name="description" content="{esc_title}">
  <title>{esc_title} | {esc_author}</title>

  <!-- Google Fonts for clean reading -->
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&family=Noto+Serif:wght@400;700&display=swap" rel="stylesheet">

  <link rel="stylesheet" href="../../css/main.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css">

  <style>
    /* Color variables — strong, high-contrast defaults */
    :root {{
      --bg: #ffffff;
      --text: #0b0b0b;
      --muted: #5b5b5b;
      --accent: #0b66ff;
      --card-bg: #ffffff;
      --code-bg: #f5f5f5;
      --shadow: rgba(11,12,15,0.06);
    }}
    @media (prefers-color-scheme: dark) {{
      :root {{
        --bg: #080808;
        --text: #f6f6f6;
        --muted: #cfcfcf;
        --accent: #6ea8ff;
        --card-bg: #0b0b0b;
        --code-bg: #111111;
        --shadow: rgba(0,0,0,0.6);
      }}
    }}

    html,body {{
      height: 100%;
      margin: 0;
      background: var(--bg);
      color: var(--text);
      -webkit-font-smoothing:antialiased;
      font-family: 'Roboto', system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial;
    }}
    .page-content {{ padding: 24px; max-width: 1200px; margin: 0 auto; }}
    .docs-content-container {{
      max-width: 900px;
      margin: 1.25rem auto;
      padding: 2em;
      background: var(--card-bg);
      border-radius: 12px;
      box-shadow: 0 6px 20px var(--shadow);
      line-height: 1.6;
      font-size: 18px;
    }}

    /* Typography closer to Google Docs */
    .docs-content-container h1, .docs-content-container h2, .docs-content-container h3 {{
      font-family: 'Noto Serif', Georgia, serif;
      color: var(--text);
      margin-top: 1.2em;
    }}
    .docs-content-container h1 {{ font-size: 2.0rem; }}
    .docs-content-container h2 {{ font-size: 1.5rem; }}
    .docs-content-container p {{ margin: 0.9em 0; color: var(--text); }}
    .docs-content-container img {{ max-width: 100%; height: auto; display:block; margin: .8rem 0; }}

    blockquote {{
      border-left: 4px solid var(--muted);
      margin: 1rem 0;
      padding: 0.6rem 1rem;
      color: var(--muted);
      background: transparent;
      border-radius: 4px;
    }}

    pre, code {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, 'Roboto Mono', monospace;
      border-radius: 6px;
      padding: 0.4rem 0.6rem;
      background: var(--code-bg);
      overflow-x: auto;
      display: block;
      margin: 0.75rem 0;
    }}

    table {{
      border-collapse: collapse;
      width: 100%;
      margin: 1rem 0;
    }}
    table th, table td {{
      border: 1px solid #ddd;
      padding: 0.5rem;
      text-align: left;
      background: transparent;
    }}

    /* Buttons & links */
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}

    .load-more-btn {{
      display:inline-block;
      margin: 1rem 0;
      padding: 0.5rem 0.9rem;
      border-radius: 8px;
      border: none;
      background: var(--accent);
      color: white;
      cursor: pointer;
      font-weight: 600;
    }}
  </style>
</head>
<body>
  <nav> ... </nav>
  <main id="main" class="page-content">
    <div class="breadcrumb"><a href="../../index.html">Home</a> / <a href="../blog.html">Blog</a> / {esc_title}</div>
    <article class="article-content">
      <header>
        <h1>{esc_title}</h1>
        <div class="article-meta" style="color:var(--muted);font-size:0.95rem;margin-top:.25rem;">
          <span><i class="bi bi-calendar3"></i> {esc_date}</span>
          <span style="margin-left:1rem;"><i class="bi bi-person"></i> {esc_author}</span>
        </div>
      </header>

      <div id="docs-container" class="docs-content-container">
        {doc_content_html}
      </div>

      <div id="docs-loading-placeholder" style="margin-top: 0.5rem;"></div>
    </article>
  </main>
  <footer> ... </footer>

  <script>
    // Parts metadata injected server-side
    const PARTS = {parts_json};
    // If there are multiple parts, we lazy-load them in order (after user action)
    if (Array.isArray(PARTS) && PARTS.length > 1) {{
      // create a button to load the rest
      const placeholder = document.getElementById('docs-loading-placeholder');
      const btn = document.createElement('button');
      btn.className = 'load-more-btn';
      btn.textContent = 'Load full document';
      btn.onclick = async function() {{
        btn.disabled = true;
        btn.textContent = 'Loading...';
        const container = document.getElementById('docs-container');
        // Fetch parts 2..N (first part is already inline)
        for (let i = 1; i < PARTS.length; i++) {{
          try {{
            // fetch relative to this page
            const resp = await fetch(PARTS[i]);
            if (!resp.ok) {{
              console.error('Failed to load part', PARTS[i]);
              continue;
            }}
            const html = await resp.text();
            const wrapper = document.createElement('div');
            wrapper.innerHTML = html;
            container.appendChild(wrapper);
          }} catch (e) {{
            console.error('Error loading part', PARTS[i], e);
          }}
        }}
        btn.style.display = 'none';
      }};
      placeholder.appendChild(btn);
    }}
  </script>
  <script src="../../js/nav.js"></script>
</body>
</html>
"""

# --- IN THE MAIN SYNC FLOW: after you have doc_content_html, detect large docs and split/write parts ---
# Replace the block where you currently build final_html and write post file with the code below
# (this snippet expects you have `post_path`, `posts_dir`, `post_basename` variables as in your script).

# Example placement in your existing flow (inside the with tempfile.TemporaryDirectory block),
# AFTER doc_content_html has been computed:

# Determine whether to split
try:
    doc_bytes_len = len(doc_content_html.encode("utf-8"))
except Exception:
    doc_bytes_len = 0

if doc_bytes_len >= LARGE_DOC_THRESHOLD:
    # split the HTML into parts
    parts_html = split_html_into_chunks(doc_content_html, approx_chunk_bytes=CHUNK_SIZE)
    base_noext = post_basename[:-5]  # remove .html
    parts_filenames: List[str] = []
    # We'll keep the first part inline (so for SEO/preview), and write parts[1..] to files
    # But we create part filenames for all parts (for consistency) — the main will fetch parts[1..]
    for idx, part_html in enumerate(parts_html):
        part_name = f"{base_noext}.part{idx+1}.html"  # 1-based part numbering
        part_path = posts_dir / part_name
        # write each part as full fragment (no outer HTML wrapper) — that's how our main page injects it
        try:
            part_path.write_text(part_html, encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to write part file %s: %s", part_path, e)
        parts_filenames.append(part_name)
    # use first part inline as doc_content_html
    doc_content_html = parts_html[0]
else:
    parts_filenames = None

# Build final page HTML and write to posts dir (unless dry-run)
final_html = build_post_html(title=docmeta.name, author=author_name, date_str=mod_date, doc_content_html=doc_content_html, parts_filenames=parts_filenames)
if dry_run:
    logger.info("Dry-run mode: not writing post file for %s", post_basename)
else:
    try:
        post_path.write_text(final_html, encoding="utf-8")
    except Exception as e:
        logger.error("Failed to write post file %s: %s", post_path, e)
        return None

