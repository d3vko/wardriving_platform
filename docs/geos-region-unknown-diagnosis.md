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

1. `manage.py import_local_admin --countries MX,PE,AR --replace-existing`
2. ADM2 guarda `region` = padre ADM1 (NOM_ENT / DEPARTAMEN / prov_nombre).
3. `geos_labels`: `COALESCE(ADM1 espacial, padre denormalizado ADM2, ADM1∋centroid(ADM2))`.
4. `backfill_geos_labels --force`.

Ops y spot-check: [`docs/geos-adm-hierarchy.md`](geos-adm-hierarchy.md).
