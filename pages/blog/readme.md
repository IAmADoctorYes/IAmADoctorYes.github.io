# Blog directory notes

This folder is the canonical location for generated blog post HTML files.

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
   - The sync script currently exports very plain HTML post pages.
   - Consider updating generation to use the same site shell (nav, theme toggle, footer) as other pages.

2. **Index freshness guardrails**
   - Add a CI check that fails if a post file changes without updating `assets/search-index.json`.

3. **Search quality improvements**
   - Consider stemming/synonyms (`job` vs `jobs`, `wv` vs `west virginia`) if post volume grows.

4. **Content QA**
   - Validate each generated post has a non-empty preview and at least one tag.
