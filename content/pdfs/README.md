# PDF Content Pipeline

Drop PDF files in this folder to have them automatically converted to web pages
during the GitHub Actions build.

## How it works

1. Place a `.pdf` file here (e.g. `my-paper.pdf`).
2. Optionally create a matching `.json` sidecar (e.g. `my-paper.json`) with metadata:

```json
{
  "title": "My Paper Title",
  "description": "A short summary for search and meta tags.",
  "date": "2025-01-15",
  "type": "Published Research",
  "route": "my-work",
  "tags": ["machine-learning", "python"],
  "category": "project-detail"
}
```

3. On push, GitHub Actions runs `scripts/convert-pdfs.py`, which:
   - Extracts text from the PDF (first ~3000 chars for the page body).
   - Generates an HTML page at `pages/projects/<slug>.html`.
   - Copies the PDF to `assets/pdfs/<slug>.pdf` for download.
   - Rebuilds the search index to include the new page.

## Sidecar fields

| Field         | Required | Default                      |
|---------------|----------|------------------------------|
| `title`       | No       | Derived from filename        |
| `description` | No       | First ~200 chars of PDF text |
| `date`        | No       | File modification date       |
| `type`        | No       | `"Document"`                 |
| `route`       | No       | `"my-work"`                  |
| `tags`        | No       | `[]`                         |
| `category`    | No       | `"project-detail"`           |

If no `.json` sidecar is present the script uses sensible defaults.
