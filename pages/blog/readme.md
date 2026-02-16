# Blog directory notes

This folder is the canonical location for generated blog post HTML files.

## Sync configuration

The sync script now uses the Google Drive API only (no Google Docs API dependency), which avoids failures when the Docs API is disabled.

Required environment variables for `scripts/sync-google-docs.py`:

- `DRIVE_FOLDER_ID`: Google Drive folder containing Google Docs posts.
- `CREDS_FILE`: Path to your service account JSON key (defaults to `credentials.json`).
- `MAX_POSTS` (optional): Max posts to sync (defaults to `150`).

## Consistency checklist

- Keep post output in `pages/blog/` so links from `pages/blog.html` resolve without redirects.
- Keep the index file at `assets/search-index.json` and ensure each item includes:
  - `title`
  - `slug` (filename inside this folder)
  - `preview`
  - `tags` (array)
  - `date` (ISO timestamp when available)
- Use lowercase, hyphenated slugs (`my-post-title.html`) for stable URLs.
- Prefer publishing tags from a controlled vocabulary (economy, labor, education, housing, policy, etc.) to improve search consistency.

## Things to review next

1. **Template parity for generated posts**
   - Generated pages now use the global site shell.
   - If needed, migrate from `<pre>`-based rendering to richer Markdown/HTML conversion.

2. **Index freshness guardrails**
   - Keep workflow commit step adding `assets/search-index.json` every sync.
   - Optionally add CI checks for stale index entries.

3. **Search quality improvements**
   - Consider stemming/synonyms (`job` vs `jobs`, `wv` vs `west virginia`) if post volume grows.

4. **Content QA**
   - Validate each generated post has a non-empty preview and at least one tag.
