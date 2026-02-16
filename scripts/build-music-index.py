#!/usr/bin/env python3
"""Auto-build music.json from audio files in assets/audio/.

Scans for .mp3, .ogg, .wav, and .flac files. Metadata comes from an
optional JSON sidecar (same name, .json extension) next to each file.

Sidecar example  (assets/audio/river-song.json):
{
  "title": "River Song",
  "artist": "Sullivan Steele",
  "instrument": "Guitar",
  "date": "2025",
  "description": "Fingerstyle piece recorded at home.",
  "tags": ["guitar", "fingerstyle"]
}

Fields the sidecar doesn't supply are filled with sensible defaults
derived from the filename.

Usage:  python scripts/build-music-index.py
"""

import json
import re
import sys
from pathlib import Path

AUDIO_DIR = Path("assets/audio")
OUTPUT = Path("assets/music.json")
EXTENSIONS = {".mp3", ".ogg", ".wav", ".flac"}


def title_from_filename(name: str) -> str:
    stem = Path(name).stem
    return re.sub(r"[-_]+", " ", stem).strip().title()


def load_sidecar(audio_path: Path) -> dict:
    sidecar = audio_path.with_suffix(".json")
    if sidecar.exists():
        try:
            return json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def scan_tracks(audio_dir: Path) -> list[dict]:
    if not audio_dir.is_dir():
        return []

    tracks = []
    for f in sorted(audio_dir.iterdir()):
        if f.suffix.lower() not in EXTENSIONS:
            continue

        meta = load_sidecar(f)
        track = {
            "title": meta.get("title", title_from_filename(f.name)),
            "artist": meta.get("artist", "Sullivan Steele"),
            "instrument": meta.get("instrument", ""),
            "date": meta.get("date", ""),
            "description": meta.get("description", ""),
            "src": "/" + f.as_posix(),
            "tags": meta.get("tags", []),
        }
        tracks.append(track)

    return tracks


def main():
    tracks = scan_tracks(AUDIO_DIR)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(tracks, indent=2) + "\n", encoding="utf-8")
    print(f"music.json: {len(tracks)} track(s)")
    for t in tracks:
        print(f"  • {t['title']}")


if __name__ == "__main__":
    main()
