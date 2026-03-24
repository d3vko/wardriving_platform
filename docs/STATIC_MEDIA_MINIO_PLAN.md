# Plan: collectstatic and static files on MinIO

## Current decision

| Kind | Location | How it is served |
| ---- | -------- | ---------------- |
| **Static** (collectstatic) | **MinIO** (bucket `wardrive-storage`, prefix `static/`) | Nginx `/static-wardrive/` → proxy to MinIO |
| **Media** (uploads) | **MinIO** (bucket `wardrive-storage`) when `USE_S3_STORAGE=true` | Nginx `location /media/` → proxy to MinIO |

## Configuration

- **Django static URL:** `static-wardrive/` (and `/wardriving/static-wardrive/` if `FORCE_SCRIPT_NAME` is set).
- **Settings:** With `USE_S3_STORAGE=true`, staticfiles and default storage use MinIO; static with `location: "static"`.
- **Nginx:** `/static-wardrive/` and `/wardriving/static-wardrive/` → proxy to `minio:9000/wardrive-storage/static/`. `/media/` → proxy to MinIO.

## Deployment

1. `collectstatic` uploads static assets to MinIO (bucket `wardrive-storage`, prefix `static/`).
2. Nginx proxies `/static-wardrive/` to MinIO to serve them.
3. Media is uploaded and served from MinIO.

**403 on static files:** On startup the app applies a public-read bucket policy on the wardrive bucket (via `ensure_media_bucket`). If MinIO has “Block Public Access” enabled, the policy may fail; disable it for that bucket in MinIO Console (port 8081) if 403 persists.
