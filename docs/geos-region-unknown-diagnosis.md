# Diagnóstico: `region = Unknown` (MX / PE / AR)

- **Fecha:** 2026-08-08
- **Estado:** corregido vía capas locales + fallback en resolver (ver abajo)

## Qué significa Unknown

En las vistas BI:

```sql
COALESCE(NULLIF(BTRIM(wardriving.region), ''), 'Unknown') AS region
```

`Unknown` = captura con `region` NULL/vacío. El resolver une ADM2 (`city`), ADM1 (`region`) y ADM0 (`country`) de forma independiente; city puede acertar y region fallar.

## Evidencia (host CTF, 2026-08-08)

| ISO | region null | region OK | Nota |
|-----|-------------|-----------|------|
| MX | ~3.8k | ~1.59M | Cozumel: punto dentro ADM2, ~2.3 m fuera de ADM1 CGAZ |
| PE | ~1k | ~19k | Callao / costa |
| AR | ~40k | ~4k | Comunas CABA ~3.4 km del ADM1 CABA CGAZ |

Causa raíz: desalineación geométrica CGAZ entre niveles (no faltaba el catálogo ADM1).

## Fuentes locales oficiales (reemplazo scoped)

| País | Agencia | ADM1 | ADM2 | Descarga usada por `import_local_admin` | Licencia / atribución |
|------|---------|------|------|------------------------------------------|------------------------|
| MX | INEGI MG (espejo CONABIO) | AGEE / estados | AGEM / municipios | `http://www.conabio.gob.mx/informacion/gis/maps/geo/dest23gw.zip`, `mun22gw.zip` | Datos INEGI; citar INEGI; no implicar endorsement |
| PE | IGN / INEI | Departamentos | Provincias | `https://www.idep.gob.pe/descargas_CN/limites/departamentos.rar`, `provincias.rar` | ODC-By / datos abiertos; citar INEI/IGN |
| AR | IGN vía API Georef | Provincias (+ CABA) | Departamentos / partidos / comunas | `https://apis.datos.gob.ar/georef/api/provincias?formato=shp&…`, `…/departamentos?formato=shp&…` | Datos IGN; citar IGN / Georef |

`source` en `geos_city`: `inegi_mg`, `inei_pe`, `ign_ar`. Solo se reemplazan ADM1+ADM2 CGAZ de MX/PE/AR; ADM0 CGAZ Americas se mantiene.

## Corrección aplicada en código

1. `python wardrive/manage.py import_local_admin --countries MX,PE,AR --replace-existing`
2. ADM2 guarda `region` = padre ADM1 (NOM_ENT / DEPARTAMEN / prov_nombre).
3. `geos_labels`: `COALESCE(ADM1 espacial, padre denormalizado ADM2, ADM1∋centroid(ADM2))`.
4. `python wardrive/manage.py backfill_geos_labels --force`.

Ops y spot-check: [`docs/geos-adm-hierarchy.md`](geos-adm-hierarchy.md). Siempre usar `wardrive/manage.py` (nunca `manage.py` suelto).

## Incident 2026-08-08 — PE/AR en Unknown tras replace

**Causa:** `import_local_admin --replace-existing` hacía soft-delete de CGAZ para **todos** los ISO al inicio. MX (`inegi_mg`) cargó bien; PE (`.rar` sin `unrar`/`7z` en la imagen) y/o AR fallaron → `geos_city` se quedó **sin ADM1/ADM2 vivos** para PE/AR. El backfill `--force` dejó `city`/`region` NULL → UI `Unknown`. Country (ADM0 CGAZ) seguía OK.

**Estado CTF observado:** `inegi_mg` vivo (MX); `inei_pe`/`ign_ar` ausentes; CGAZ ADM1+ADM2 de PE/AR con `deleted_at` set.

### Recuperación inmediata en el host (restaura city vía CGAZ)

```bash
podman-compose exec -T wardrive_db psql -U postgres -c "
UPDATE geos_city
SET deleted_at = NULL
WHERE country_iso IN ('PE','AR')
  AND admin_level IN (1,2)
  AND source = 'geoboundaries'
  AND deleted_at IS NOT NULL;
"

podman-compose exec -T wardrive python wardrive/manage.py backfill_geos_labels \
  --table all --force
```

### Reintento correcto del override local (después de desplegar el fix)

Requisitos: código con soft-delete **post**-import; para PE: `7zip-rar` en la imagen
(Dockerfile, repo non-free) o ZIP en `wardrive/media/geos_cache/`.

```bash
# 0) Rebuild con 7zip-rar (codec RAR)
podman-compose build wardrive
podman-compose up -d wardrive

# 1) Alternativa sin RAR: ZIPs en wardrive/media/geos_cache/
#    pe_departamentos.zip / pe_provincias.zip

# 2) Solo PE+AR (MX ya puede estar con inegi_mg)
podman-compose exec -T wardrive python wardrive/manage.py import_local_admin \
  --countries PE,AR --levels 1,2 --replace-existing
# Con ZIPs en caché: añade --no-download
# Si falla el .rar: falta 7zip-rar (rebuild) o usa ZIP + --no-download

# 3) Verificación obligatoria antes del backfill
podman-compose exec -T wardrive_db psql -U postgres -c "
SELECT country_iso, admin_level, source, COUNT(*) FILTER (WHERE deleted_at IS NULL) AS alive
FROM geos_city
WHERE country_iso IN ('PE','AR','MX')
GROUP BY 1,2,3 ORDER BY 1,2,3;
"
# Esperado: PE → inei_pe ADM1≥20 ADM2≥150 alive; AR → ign_ar ADM1≥20 ADM2≥400 alive

podman-compose exec -T wardrive python wardrive/manage.py backfill_geos_labels \
  --table all --force
```
