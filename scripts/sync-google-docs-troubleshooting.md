# Google Docs sync troubleshooting and improvement options

If your site tooling complains about `credentials.json`, use one (or more) of these fixes.

> Backward compatibility note: the sync script also accepts legacy env names `CREDS_FILE` and `DRIVE_FOLDER_ID` used by older CI workflows.

## 1) Keep a local key file (quickest local fix)
- Create a Google Cloud service account key with Docs read access.
- Save it as `credentials.json` in the repository root.
- Run `python scripts/sync-google-docs.py` again.

## 2) Use `GOOGLE_APPLICATION_CREDENTIALS` (better than hardcoding a path)
- Keep your key file outside the repo (for example, `~/.config/gcp/blog-sync.json`).
- Export:
  - `export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcp/blog-sync.json`
- Run sync without copying secrets into the project.

## 3) Use `GOOGLE_SERVICE_ACCOUNT_JSON` (CI-friendly)
- Store the JSON key as a CI secret.
- Inject it as an environment variable named `GOOGLE_SERVICE_ACCOUNT_JSON`.
- This avoids writing credentials to disk in CI/CD pipelines.

## 4) Move folder ID to env (`GOOGLE_DOCS_FOLDER_ID`)
- Set `export GOOGLE_DOCS_FOLDER_ID=<your-drive-folder-id>`.
- This makes config portable across local, staging, and production jobs.
- It also prevents accidentally committing real IDs in source files.

## 5) Add a graceful fallback deployment path
- Do **not** run Google sync during static-site runtime.
- Commit generated `pages/blog/*.html` and `assets/search-index.json` so the site can serve content even when Google APIs are unavailable.

## 6) Improve reliability with validation checks
- Before generating pages, validate that:
  - credentials are present,
  - folder ID is configured,
  - Google API calls succeed.
- Fail with actionable errors and non-zero exit code in CI.

## 7) Security and maintenance improvements
- Add secret scanning in CI to prevent accidental key commits.
- Rotate service account keys regularly.
- Restrict the service account to read-only scopes and only required Docs/Drive resources.

## 8) If you see `insufficient authentication scopes`
- Recreate credentials or token with both Docs and Drive metadata scopes.
- Ensure the service account can access (or is shared on) the target Drive folder.
