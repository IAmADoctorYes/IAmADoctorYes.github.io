#!/usr/bin/env python3
"""Local content sync/build entrypoint (Google-free).

This script replaces the old Google Docs/Drive synchronization flow.
It keeps the legacy command name for compatibility while running the
site's local content pipeline only.

Usage:
    python scripts/sync-google-docs.py
    python scripts/sync-google-docs.py --root . --skip-backgrounds
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PIPELINE = [
    "scripts/convert-pdfs.py",
    "scripts/build-blog.py",
    "scripts/optimize-images.py",
    "scripts/build-music-index.py",
    "scripts/build-shop-index.py",
    "scripts/build-gallery-index.py",
    "scripts/build-search-index.py",
    "scripts/build-feed.py",
    "scripts/build-sitemap.py",
    "scripts/build-changelog.py",
]

OPTIONAL_PIPELINE = [
    "scripts/fetch-backgrounds.py",
]


def run_script(repo_root: Path, script_rel: str) -> None:
    script_path = repo_root / script_rel
    if not script_path.exists():
        print(f"Skipping missing script: {script_rel}")
        return

    print(f"Running: {script_rel}")
    subprocess.run(
        [sys.executable, str(script_path)],
        cwd=str(repo_root),
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run local content synchronization/build pipeline without Google APIs"
    )
    parser.add_argument("--root", default=".", help="Repository root directory")
    parser.add_argument(
        "--skip-backgrounds",
        action="store_true",
        help="Skip optional background image fetch script",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()

    for required in PIPELINE:
        run_script(repo_root, required)

    if not args.skip_backgrounds:
        for optional in OPTIONAL_PIPELINE:
            try:
                run_script(repo_root, optional)
            except subprocess.CalledProcessError:
                print(f"Optional script {optional} failed (non-fatal), continuing…")

    print("Local sync complete. No Google Drive/Docs APIs were used.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"Pipeline failed with exit code {exc.returncode}")
        raise SystemExit(exc.returncode)
