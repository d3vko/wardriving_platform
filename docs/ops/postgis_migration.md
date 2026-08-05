# Migración Postgres → PostGIS (replicables en cualquier host)

Orquestación: siempre **`podman-compose`** (nunca `docker compose`). El fichero puede seguir llamándose `docker-compose.yml`.

Esta guía asume el volumen de datos existente (`wardriving_postgres_db`) y **no** lo recrea. `glitchtip_db` permanece en Postgres puro.

## Imagen app (GDAL)

La imagen `wardrive` instala `gdal-bin` / `libgdal36` / GEOS / PROJ.
Django apunta por defecto a:

- `GDAL_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgdal.so.36`
- `GEOS_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu/libgeos_c.so.1`

Override en `.env` solo si la distro cambia de SONAME.

## Capas (orden obligatorio)

1. **Infra**: imagen `postgis/postgis:17-3.5` en `wardrive_db` (mismo major PG 17 que el volumen).
2. **App**: imagen `wardrive` con GDAL/GEOS/PROJ + `DB_ENGINE=django.contrib.gis.db.backends.postgis`.
3. **Extensión**: migración `0021_create_postgis_extension`.
4. **ORM**: `0022` añade `location` (PointField nullable) sin tocar lat/lon.
5. **Datos**: `0023` backfill; inválidas/cero → `location IS NULL`.

## Backup (obligatorio en hosts remotos)

En este host de desarrollo el backup es opcional. En **cualquier otro despliegue** con datos reales:

```bash
podman-compose exec wardrive_db \
  pg_dump -U postgres -Fc postgres \
  > "backup_pre_postgis_$(date +%Y%m%d_%H%M%S).dump"
```

Conservar el fichero fuera del contenedor antes de `up`/`migrate`.

## Checklist de despliegue

1. Actualizar código (compose PostGIS, Dockerfile GIS, settings, migraciones `0021`–`0023`).
2. Asegurar `.env`:
   ```bash
   DB_ENGINE=django.contrib.gis.db.backends.postgis
   ```
3. Recrear solo el servicio DB (el volumen nombrado se reutiliza):
   ```bash
   podman-compose up -d wardrive_db
   ```
   Si al cambiar de `postgres:17` a `postgis/postgis:17-3.5` aparece
   *collation version mismatch*, alinear (no destruye datos):
   ```bash
   podman-compose exec wardrive_db psql -U postgres -c \
     "ALTER DATABASE postgres REFRESH COLLATION VERSION;"
   podman-compose exec wardrive_db psql -U postgres -c \
     "ALTER DATABASE template1 REFRESH COLLATION VERSION;"
   ```
4. Rebuild app/workers (GDAL):
   ```bash
   podman-compose build wardrive
   podman-compose up -d wardrive celery_proc_0 celery_proc_1 celery-beat
   ```
   (`start.sh` ejecuta `migrate` al arrancar; también puedes migrar a mano en el paso 5.)
5. Verificar plan e integridad:
   ```bash
   podman-compose exec wardrive python wardrive/manage.py makemigrations wardriving --check --dry-run
   podman-compose exec wardrive python wardrive/manage.py migrate --plan
   podman-compose exec wardrive python wardrive/manage.py migrate
   ```
6. Comprobaciones PostGIS / datos:
   ```bash
   podman-compose exec wardrive_db psql -U postgres -c "SELECT PostGIS_Version();"
   podman-compose exec wardrive_db psql -U postgres -c "
     SELECT COUNT(*) FILTER (WHERE location IS NOT NULL) AS with_location,
            COUNT(*) AS total
     FROM wardriving;"
   podman-compose exec wardrive_db psql -U postgres -c "
     SELECT COUNT(*) FILTER (WHERE location IS NOT NULL) AS with_location,
            COUNT(*) AS total
     FROM lte_wardriving;"
   ```
7. Spot-check: `current_latitude` / `current_longitude` no deben haber cambiado; solo se rellena `location`.

## Criterio de backfill

`location` se asigna solo si:

- lat/lon no son NULL,
- no son ambos `0` (placeholder de la plataforma),
- lat ∈ [-90, 90], lon ∈ [-180, 180].

El resto queda `NULL`. La API, CSV, KML y vistas SQL siguen usando los DecimalFields.

## Rollback conceptual

```bash
podman-compose exec wardrive python wardrive/manage.py migrate wardriving 0020
```

Eso revierte backfill → drop de `location` → (la extensión PostGIS puede permanecer en la BD; es inocua). Luego, si hace falta, volver `DB_ENGINE` e imagen `postgres:17`. **No** borrar el volumen.

## Qué no hacer

- No `podman-compose down -v` ni borrar `wardriving_postgres_db`.
- No migrar `glitchtip_db` a PostGIS.
- No eliminar `current_latitude` / `current_longitude` en esta fase.
