# Plan: collectstatic y estáticos en MinIO

## Decisión actual

| Tipo                       | Ubicación | Cómo se sirve                                        |
| -------------------------- | --------- | ---------------------------------------------------- |
| **Static** (collectstatic) | **MinIO** (bucket `wardrive-storage`, prefijo `static/`) | Nginx `/static-wardrive/` → proxy a MinIO             |
| **Media** (uploads)        | **MinIO** (bucket `wardrive-storage`) cuando `USE_S3_STORAGE=true` | Nginx `location /media/` → proxy a MinIO             |

## Configuración

- **URL estáticos Django:** `static-wardrive/` (y `/wardriving/static-wardrive/` si hay `FORCE_SCRIPT_NAME`).
- **Settings:** Con `USE_S3_STORAGE=true`, staticfiles y default usan MinIO; static con `location: "static"`.
- **Nginx:** `/static-wardrive/` y `/wardriving/static-wardrive/` → proxy a `minio:9000/wardrive-storage/static/`. `/media/` → proxy a MinIO.

## Despliegue

1. `collectstatic` sube estáticos a MinIO (bucket `wardrive-storage`, prefijo `static/`).
2. Nginx hace proxy de `/static-wardrive/` a MinIO para servirlos.
3. Media se sube y sirve desde MinIO.

**403 en estáticos:** Al arrancar, la app aplica una bucket policy de lectura pública en el bucket wardrive (vía `ensure_media_bucket`). Si MinIO tiene "Block Public Access" activo, la policy puede fallar; desactívalo para ese bucket en MinIO Console (puerto 8081) si sigue el 403.
