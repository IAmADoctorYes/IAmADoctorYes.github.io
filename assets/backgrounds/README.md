# Background Images

This directory contains daily background images automatically fetched by GitHub Actions.

## Files

- `bg-dark.jpg` - NASA Astronomy Picture of the Day (for dark mode)
- `bg-dark.json` - Metadata for dark mode background (title, source, link)
- `bg-light.jpg` - Unsplash nature/landscape photo (for light mode)
- `bg-light.json` - Metadata for light mode background (title, source, link)

## How it works

1. GitHub Actions runs daily at midnight UTC
2. The `fetch-backgrounds.py` script downloads fresh images from NASA and Unsplash
3. Images and metadata are committed to this directory
4. The website loads these local images instead of making API calls
5. Benefits:
   - No API keys exposed to clients
   - Faster loading (same-origin, no CORS)
   - Only 2 API calls per day instead of per-user
   - More reliable (no rate limits)

## Manual Update

To manually fetch new backgrounds locally:

```bash
python scripts/fetch-backgrounds.py
```

This will download the latest images to this directory.
