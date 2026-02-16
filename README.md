# IAmADoctorYes.github.io
Personal Website Demonstrating Experience, Projects, and Additional Skills/Training


## Blog sync credentials

`scripts/sync-google-docs.py` supports multiple credential methods:

1. `GOOGLE_SERVICE_ACCOUNT_JSON` (raw JSON in env var)
2. `GOOGLE_APPLICATION_CREDENTIALS` (path to key file)
3. fallback `credentials.json` in repo root

For folder selection, set `GOOGLE_DOCS_FOLDER_ID`. Legacy env names (`CREDS_FILE`, `DRIVE_FOLDER_ID`) are still accepted for backward compatibility.
