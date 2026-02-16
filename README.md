# IAmADoctorYes.github.io
Personal Website Demonstrating Experience, Projects, and Additional Skills/Training

## Content generation and deployment

`scripts/sync-google-docs.py` is kept for content ingestion, but it is a **refresh utility** and not a required deploy step. Generated artifacts are committed into the repository and served directly by the site:

- `pages/blog/*.html`
- `assets/search-index.json`

### CI workflow split

- **`sync-content`** (`.github/workflows/sync-content.yml`): manual/scheduled refresh from Google Docs. This workflow may call Google APIs and commits refreshed generated artifacts.
- **`deploy-site`** (`.github/workflows/deploy-site.yml`): publishes static files to GitHub Pages and does not call Google APIs.

### Failure policy

If content sync fails, existing generated blog output must remain untouched. The sync script writes to temporary paths and only replaces `pages/blog/` and `assets/search-index.json` after a successful refresh.

## Blog sync credentials

`scripts/sync-google-docs.py` supports multiple credential methods:

1. `GOOGLE_SERVICE_ACCOUNT_JSON` (raw JSON in env var)
2. `GOOGLE_APPLICATION_CREDENTIALS` (path to key file)
3. fallback `credentials.json` in repo root

For folder selection, set `GOOGLE_DOCS_FOLDER_ID`. Legacy env names (`CREDS_FILE`, `DRIVE_FOLDER_ID`) are still accepted for backward compatibility.
