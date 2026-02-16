# Adding Music

Drop audio files into this folder and they'll appear on the Music page automatically
after the next push to `main`.

## Supported formats

`.mp3`, `.ogg`, `.wav`, `.flac`

## Adding metadata

Create a JSON sidecar with the same name as the audio file:

```
assets/audio/
  river-song.mp3
  river-song.json      ← metadata for river-song.mp3
  campfire-jam.mp3      ← no sidecar = defaults from filename
```

### Sidecar fields

```json
{
  "title": "River Song",
  "artist": "Sullivan Steele",
  "instrument": "Guitar",
  "date": "2025",
  "description": "Fingerstyle piece recorded at home.",
  "tags": ["guitar", "fingerstyle"]
}
```

All fields are optional. If omitted:

| Field       | Default                          |
|-------------|----------------------------------|
| title       | Derived from filename            |
| artist      | "Sullivan Steele"                |
| instrument  | empty                            |
| date        | empty                            |
| description | empty                            |
| tags        | empty array                      |

## What happens

1. You push audio files (and optional sidecars) to `main`.
2. GitHub Actions runs `scripts/build-music-index.py`.
3. `assets/music.json` is regenerated and committed.
4. The site deploys and `music.js` loads the updated JSON.
