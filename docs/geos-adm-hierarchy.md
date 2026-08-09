# Jerarquía ADM completa en geos (Américas)

Fuente base: [geoBoundaries CGAZ](https://www.geoboundaries.org/) (CC BY 4.0) para Américas.

**Override local MX/PE/AR/CO/GT (ADM1+ADM2; AR también ADM3 localidades):** INEGI / INEI-IGN / IGN-Georef / DANE COD-AB / CONRED COD-AB — ver [`docs/geos-region-unknown-diagnosis.md`](geos-region-unknown-diagnosis.md).

| Nivel | Campo denormalizado | Ejemplo MX |
|------|---------------------|------------|
| ADM0 | `country` / `country_iso` | Mexico / `MX` |
| ADM1 | `region` | Jalisco / Quintana Roo |
| ADM2 | `city` (+ `region` padre denormalizado) | Guadalajara / Cozumel |
| ADM3 | `city` = localidad (KNN; AR: barrios/localidades Georef) | Recoleta (AR) |

`geos_labels`: si `country_iso` tiene filas vivas `admin_level = 3`, `city` = KNN sobre `polygon <-> location`; si no, ADM2 `ST_Intersects`.

No confundir `region` (ADM1 geográfico) con `lte_wardriving.state` (estado de celda radio).

## Apply / current state

### Máquina de despliegue (build externo)

```bash
podman-compose up --build -d
```

`start.sh` ya ejecuta `migrate` al arrancar (incl. geos 0005 ADM3). **No** hace falta `manage.py migrate` a mano.

Eso **no** regenera `geos_city` ni labels en capturas. Tras healthy:

```bash
# Pre-seed geos_cache en el host (bind .:/code → wardrive/media/geos_cache/):
#   mx_dest23gw.zip mx_mun22gw.zip pe_departamentos.zip pe_provincias.zip
#   ar_provincias.zip ar_localidades.zip co_cod_ab.zip gt_cod_ab.zip
# Si falta algún ZIP, quita --no-download (o corre solo ese ISO) para descargar.

podman-compose exec -T wardrive python wardrive/manage.py import_local_admin \
  --countries MX,PE,AR,CO,GT --levels 1,2,3 --replace-existing --no-download

podman-compose exec -T wardrive_db psql -U postgres -c \
  "SELECT country_iso, admin_level, source,
          COUNT(*) FILTER (WHERE deleted_at IS NULL) AS alive
   FROM geos_city
   WHERE country_iso IN ('MX','PE','AR','CO','GT')
   GROUP BY 1,2,3 ORDER BY 1,2,3;"
# AR: ADM3 georef_loc_ar ~4k; ADM2 ign_ar Comunas soft-deleted
# MX/PE/CO/GT: ADM1+ADM2 vivos (sin ADM3 aún)

podman-compose exec -T wardrive python wardrive/manage.py backfill_geos_labels \
  --table all --force
```

### Desarrollo local (explícito)

Desde la raíz del repo (cliente Compose: **podman-compose**):

```bash
# 1) Stack: migrate lo aplica start.sh al arrancar wardrive
podman-compose up -d wardrive_db redis
podman-compose up -d wardrive
# (o: podman-compose up --build -d)

# 2) Seed ADM0+ADM1+ADM2 América (CGAZ)
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

# 3) Override ADM1+ADM2 (+ADM3 AR) oficiales MX / PE / AR / CO / GT
# Soft-delete CGAZ es POR PAÍS y solo DESPUÉS de import OK (no borra si falla unrar/red).
# Contenedor: 7zip-rar (non-free) o unrar para pe_*.rar; o pe_*.zip en geos_cache.
# AR con levels incluyendo 3: carga localidades y retira ADM2 ign_ar (Comunas).
podman-compose exec -T wardrive python wardrive/manage.py import_local_admin \
  --countries MX,PE,AR,CO,GT --levels 1,2,3 --replace-existing
# Offline:
#   podman-compose exec -T wardrive python wardrive/manage.py import_local_admin \
#     --countries MX,PE,AR,CO,GT --levels 1,2,3 --replace-existing --no-download

# Tras import: confirmar alive counts (PE/AR/CO/GT no deben quedar en 0)
podman-compose exec -T wardrive_db psql -U postgres -c \
  "SELECT country_iso, admin_level, source,
          COUNT(*) FILTER (WHERE deleted_at IS NULL) AS alive
   FROM geos_city
   WHERE country_iso IN ('MX','PE','AR','CO','GT')
   GROUP BY 1,2,3 ORDER BY 1,2,3;"

# 4) Recompute labels en capturas
podman-compose exec -T wardrive python wardrive/manage.py backfill_geos_labels \
  --table all --force

# 5) Spot-check
podman-compose exec -T wardrive_db psql -U postgres -c \
  "SELECT country_iso, admin_level, source, COUNT(*)
   FROM geos_city WHERE deleted_at IS NULL
     AND country_iso IN ('MX','PE','AR','CO','GT')
   GROUP BY 1,2,3 ORDER BY 1,2,3;"

podman-compose exec -T wardrive_db psql -U postgres -c \
  "SELECT city, region, country_iso, COUNT(*)
   FROM wardriving
   WHERE deleted_at IS NULL
     AND city IN ('Cozumel','Callao','Recoleta','Medellín','Antigua Guatemala')
   GROUP BY 1,2,3 ORDER BY 1;"
```

### Verificación esperada post-override

| city | region esperado |
|------|-----------------|
| Cozumel | Quintana Roo |
| Callao (PE) | Callao (dept. / región) |
| Recoleta | Ciudad Autónoma de Buenos Aires |
| Medellín | Antioquia |
| Antigua Guatemala | Sacatepéquez |

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
- CO: DANE MGN vía [HDX COD-AB Colombia](https://data.humdata.org/dataset/cod-ab-col) (`dane_co`).
- GT: COD-AB vía [HDX Guatemala](https://data.humdata.org/dataset/cod-ab-gtm) (`conred_gt`; origen CONRED/OCHA).

# 4) Import localidades AR (ADM3; Georef centroides buffered)
# Sustituye city Comuna N por barrios/localidades (Recoleta, Saavedra, …).
curl -L -o wardrive/media/geos_cache/ar_localidades.zip \
  'https://apis.datos.gob.ar/georef/api/localidades?formato=shp&campos=completo&max=5000'

podman-compose exec -T wardrive python wardrive/manage.py import_local_admin \
  --countries AR --levels 3 --replace-existing --no-download
# AR ADM2 ign_ar (Comunas) queda soft-deleted si va bien el ADM3.

# Regenerar caché CO/GT (offline) — si HDX cambia la URL, actualizar PACKS
# en import_local_admin.py o bajar a mano:

```bash
# Desde el host (queda en MEDIA_ROOT vía bind .:/code)
curl -L -o wardrive/media/geos_cache/co_cod_ab.zip \
  'https://data.humdata.org/dataset/50ea7fee-f9af-45a7-8a52-abb9c790a0b6/resource/32fba556-0109-4d1c-84cb-c8abddf7775b/download/col-administrative-divisions-shapefiles.zip'
curl -L -o wardrive/media/geos_cache/gt_cod_ab.zip \
  'https://data.humdata.org/dataset/0b20f310-7d22-479c-b7e2-e1bb9737fa72/resource/56c73009-60a8-4987-88b2-bc493f8b544c/download/gtm_admin_boundaries.shp.zip'

podman-compose exec -T wardrive python wardrive/manage.py import_local_admin \
  --countries CO,GT --levels 1,2 --replace-existing --no-download
```
