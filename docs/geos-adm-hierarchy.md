# Jerarquía ADM completa en geos (Américas)

Fuente base: [geoBoundaries CGAZ](https://www.geoboundaries.org/) (CC BY 4.0) para Américas.

**Override local MX/PE/AR (ADM1+ADM2):** INEGI / INEI-IGN / IGN-Georef — ver [`docs/geos-region-unknown-diagnosis.md`](geos-region-unknown-diagnosis.md).

| Nivel | Campo denormalizado | Ejemplo MX |
|------|---------------------|------------|
| ADM0 | `country` / `country_iso` | Mexico / `MX` |
| ADM1 | `region` | Jalisco / Quintana Roo |
| ADM2 | `city` (+ `region` padre denormalizado en capas locales) | Guadalajara / Cozumel |

No confundir `region` (ADM1 geográfico) con `lte_wardriving.state` (estado de celda radio).

## Apply / current state

Desde la raíz del repo (cliente Compose: **podman-compose**):

```bash
# 1) Stack DB + app
podman-compose up -d wardrive_db redis
podman-compose up -d wardrive

# 2) Migraciones (geos region, capturas region, vistas con region)
# Siempre invocar Django vía wardrive/manage.py (WORKDIR del contenedor: /code).
podman-compose exec -T wardrive python wardrive/manage.py migrate geos
podman-compose exec -T wardrive python wardrive/manage.py migrate wardriving
podman-compose exec -T wardrive python wardrive/manage.py migrate misc

# 3) Seed ADM0+ADM1+ADM2 América (CGAZ)
# Preferir caché local (descargas grandes pueden SIGKILL el contenedor app):
#   curl -L -o wardrive/media/geos_cache/geoBoundariesCGAZ_ADM1.gpkg \
#     https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/CGAZ/geoBoundariesCGAZ_ADM1.gpkg
#   (igual para ADM0/ADM2)
podman-compose exec -T wardrive python wardrive/manage.py import_geoboundaries \
  --levels 0,1,2 --region americas --replace-ghs --no-download
# Si falla por memoria, importar por nivel:
#   ... --levels 0 --replace-ghs
#   ... --levels 1 --no-download
#   ... --levels 2 --no-download --batch-size 25

# 4) Override ADM1+ADM2 oficiales MX / PE / AR (corrige region Unknown)
# Soft-delete CGAZ es POR PAÍS y solo DESPUÉS de import OK (no borra si falla unrar/red).
# Contenedor: necesita `7z` (p7zip-full en Dockerfile) o `unrar` para pe_*.rar.
podman-compose exec -T wardrive python wardrive/manage.py import_local_admin \
  --countries MX,PE,AR --levels 1,2 --replace-existing
# Si PE/AR quedaron Unknown tras un replace fallido, ver
# docs/geos-region-unknown-diagnosis.md § «Incident 2026-08-08».
# Offline:
#   podman-compose exec -T wardrive python wardrive/manage.py import_local_admin \
#     --countries MX,PE,AR --replace-existing --no-download

# Tras import: confirmar alive counts (PE/AR no deben quedar en 0)
podman-compose exec -T wardrive_db psql -U postgres -c \
  "SELECT country_iso, admin_level, source,
          COUNT(*) FILTER (WHERE deleted_at IS NULL) AS alive
   FROM geos_city
   WHERE country_iso IN ('MX','PE','AR') AND admin_level IN (1,2)
   GROUP BY 1,2,3 ORDER BY 1,2,3;"

# 5) Recompute labels en capturas
podman-compose exec -T wardrive python wardrive/manage.py backfill_geos_labels \
  --table all --force

# 6) Spot-check
podman-compose exec -T wardrive_db psql -U postgres -c \
  "SELECT country_iso, admin_level, source, COUNT(*)
   FROM geos_city WHERE deleted_at IS NULL
     AND country_iso IN ('MX','PE','AR')
   GROUP BY 1,2,3 ORDER BY 1,2,3;"

podman-compose exec -T wardrive_db psql -U postgres -c \
  "SELECT city, region, country_iso, COUNT(*)
   FROM wardriving
   WHERE deleted_at IS NULL AND city IN ('Cozumel','Callao','Comuna 1')
   GROUP BY 1,2,3 ORDER BY 1;"
```

### Verificación esperada post-override

| city | region esperado |
|------|-----------------|
| Cozumel | Quintana Roo |
| Callao (PE) | Callao (dept. / región) |
| Comuna 1 | Ciudad Autónoma de Buenos Aires |

Si `region` sigue vacío en BI: el filtro muestra `Unknown` por `COALESCE` en vistas — re-ejecutar backfill `--force`.

## Metabase (pasos del operador)

Tras migrar y backfill:

1. Admin → Databases → sync schema de la DB de wardriving (aparecen columnas `region` en vistas).
2. En cada card nativa WiFi/LTE que use `{{city}}` / `{{country}}` / `{{country_iso}}`, añadir template-tag `region` como **Field Filter** (`type: dimension`, `widget-type: string/=`) mapeado a `wardriving_vendor.region` o `wardriving_mobile.region`.
3. En dashboard DB00, añadir filtro compartido **Region** y `parameter_mappings` a `["dimension", ["template-tag", "region"]]`.
4. No usar MCP `construct_native_query` / reescritura de SQL que colapse tags a `text` (ver [`sql_bi_sources/README.md`](../sql_bi_sources/README.md) y skill `metabase-wardriving-bi`).

## Atribución

- geoBoundaries CGAZ: William & Mary geoLab (CC BY 4.0).
- MX: INEGI Marco Geoestadístico (espejo CONABIO para descarga SHP).
- PE: INEI / IGN límites político-administrativos.
- AR: IGN vía servicio Georef / datos.gob.ar.
