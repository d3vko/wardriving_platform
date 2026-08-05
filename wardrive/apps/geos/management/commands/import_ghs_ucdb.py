"""
Importa polígonos de extensión urbana (Urban Centres) desde GHS-UCDB R2024A.

Fuente: GHSL / JRC / European Commission
  https://human-settlement.emergency.copernicus.eu/ghs_ucdb_2024.php
  https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_UCDB_GLOBE_R2024A/

Atribución requerida al reutilizar los datos.
"""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any, Iterator, Optional

import requests
from django.conf import settings
from django.contrib.gis.gdal import CoordTransform, DataSource, SpatialReference
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.geos.country_iso import (
    AMERICAS_ISO2,
    country_name_to_iso2,
    is_americas_un_region,
)
from apps.geos.models import City

SOURCE = "ghs_ucdb"
GHS_UCDB_ZIP_URL = (
    "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/"
    "GHS_UCDB_GLOBE_R2024A/GHS_UCDB_GLOBE_R2024A/V1-2/"
    "GHS_UCDB_GLOBE_R2024A_V1_2.zip"
)
TARGET_SRID = 4326
UA = (
    "wardriving-platform/geos-import "
    "(+https://github.com; contact=local-dev)"
)

# Preferencias de nombre de campo (el año puede variar entre releases).
CITY_FIELD_PREFIXES = ("GC_UCN_MAI_", "UC_NM_MN", "GC_UCN_MAI")
COUNTRY_FIELD_PREFIXES = ("GC_CNT_GAD_", "GC_CNT_UNN_", "CTR_MN_NM", "GC_CNT_GAD")
REGION_FIELD_PREFIXES = ("GC_DEV_USR_", "GRGN_L2", "GC_DEV_USR")
ISO_FIELD_PREFIXES = ("CTR_MN_ISO", "GC_CNT_ISO", "ISO3", "ISO2")
ID_FIELD_CANDIDATES = (
    "ID_UC_G0",
    "ID_HDC_G0",
    "ID",
    "FID",
    "OBJECTID",
    "GC_ID",
)


def _cache_dir() -> Path:
    base = Path(getattr(settings, "MEDIA_ROOT", None) or "/tmp")
    path = base / "geos_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _pick_field(names: list[str], prefixes: tuple[str, ...]) -> Optional[str]:
    upper = {n.upper(): n for n in names}
    for prefix in prefixes:
        p = prefix.upper()
        if p in upper:
            return upper[p]
        matches = sorted(
            (orig for key, orig in upper.items() if key.startswith(p)),
            key=len,
        )
        if matches:
            return matches[0]
    return None


def _get_attr(feat: Any, field: Optional[str]) -> Any:
    if not field:
        return None
    try:
        return feat.get(field)
    except Exception:
        try:
            return feat[field]
        except Exception:
            return None


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _iso_from_feature(
    feat: Any, iso_field: Optional[str], country_name: Optional[str]
) -> Optional[str]:
    raw = _as_str(_get_attr(feat, iso_field))
    if raw:
        # Puede venir ISO-3 o ISO-2; normalizamos.
        raw = raw.upper().replace(";", "").split()[0]
        if len(raw) == 2 and raw.isalpha():
            return raw
        if len(raw) == 3 and raw.isalpha():
            # Mapa mínimo ISO-3 → ISO-2 para América (evita dependencia extra).
            iso3_to_2 = {
                "USA": "US",
                "CAN": "CA",
                "MEX": "MX",
                "BLZ": "BZ",
                "CRI": "CR",
                "SLV": "SV",
                "GTM": "GT",
                "HND": "HN",
                "NIC": "NI",
                "PAN": "PA",
                "ATG": "AG",
                "BHS": "BS",
                "BRB": "BB",
                "CUB": "CU",
                "DMA": "DM",
                "DOM": "DO",
                "GRD": "GD",
                "HTI": "HT",
                "JAM": "JM",
                "KNA": "KN",
                "LCA": "LC",
                "VCT": "VC",
                "TTO": "TT",
                "PRI": "PR",
                "VIR": "VI",
                "VGB": "VG",
                "CYM": "KY",
                "TCA": "TC",
                "AIA": "AI",
                "MSR": "MS",
                "ABW": "AW",
                "CUW": "CW",
                "SXM": "SX",
                "MAF": "MF",
                "BLM": "BL",
                "GLP": "GP",
                "MTQ": "MQ",
                "BMU": "BM",
                "GRL": "GL",
                "ARG": "AR",
                "BOL": "BO",
                "BRA": "BR",
                "CHL": "CL",
                "COL": "CO",
                "ECU": "EC",
                "GUY": "GY",
                "PRY": "PY",
                "PER": "PE",
                "SUR": "SR",
                "URY": "UY",
                "VEN": "VE",
                "GUF": "GF",
                "FLK": "FK",
                "SGS": "GS",
            }
            mapped = iso3_to_2.get(raw)
            if mapped:
                return mapped
    return country_name_to_iso2(country_name)


def _to_multipolygon_4326(
    ogr_geom: Any, transform: Optional[CoordTransform]
) -> MultiPolygon:
    geom = ogr_geom.clone()
    if transform is not None:
        geom.transform(transform)
    elif geom.srid and geom.srid != TARGET_SRID:
        geom.transform(TARGET_SRID)

    geos = geom.geos
    if isinstance(geos, MultiPolygon):
        return geos
    if isinstance(geos, Polygon):
        return MultiPolygon(geos, srid=TARGET_SRID)
    # GeometryCollection u otros: intentar extraer polígonos
    if geos.geom_type == "GeometryCollection":
        polys = [g for g in geos if isinstance(g, Polygon)]
        if polys:
            return MultiPolygon(*polys, srid=TARGET_SRID)
    # Último recurso: WKT vía GEOS
    converted = GEOSGeometry(geos.wkt, srid=TARGET_SRID)
    if isinstance(converted, MultiPolygon):
        return converted
    if isinstance(converted, Polygon):
        return MultiPolygon(converted, srid=TARGET_SRID)
    raise ValueError(f"Geometría no convertible a MultiPolygon: {geos.geom_type}")


def _download_zip(url: str, dest: Path, force: bool = False) -> Path:
    if dest.exists() and dest.stat().st_size > 0 and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    partial = dest.with_suffix(dest.suffix + ".partial")
    headers = {"User-Agent": UA, "Accept": "*/*"}
    with requests.get(url, headers=headers, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        with open(partial, "wb") as fh:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    fh.write(chunk)
    partial.replace(dest)
    return dest


def _extract_gpkg(zip_path: Path, extract_dir: Path) -> Path:
    extract_dir.mkdir(parents=True, exist_ok=True)
    existing = list(extract_dir.rglob("*.gpkg"))
    if existing:
        # Preferir el gpkg más grande (dataset principal).
        return max(existing, key=lambda p: p.stat().st_size)

    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_dir)

    gpkgs = list(extract_dir.rglob("*.gpkg"))
    if not gpkgs:
        raise CommandError(f"No se encontró ningún .gpkg en {zip_path}")
    return max(gpkgs, key=lambda p: p.stat().st_size)


def _iter_americas_features(
    gpkg_path: Path,
    region_filter: str,
) -> Iterator[tuple[str, str, str, str, MultiPolygon]]:
    """Yields (source_id, city, country, country_iso, multipolygon)."""
    ds = DataSource(str(gpkg_path))
    if len(ds) < 1:
        raise CommandError(f"GeoPackage sin capas: {gpkg_path}")

    # Elegir la capa con más features (tabla principal de urban centres).
    layer = max(ds, key=lambda ly: ly.num_feat)
    field_names = list(layer.fields)

    city_field = _pick_field(field_names, CITY_FIELD_PREFIXES)
    country_field = _pick_field(field_names, COUNTRY_FIELD_PREFIXES)
    region_field = _pick_field(field_names, REGION_FIELD_PREFIXES)
    iso_field = _pick_field(field_names, ISO_FIELD_PREFIXES)
    id_field = None
    for cand in ID_FIELD_CANDIDATES:
        id_field = _pick_field(field_names, (cand,))
        if id_field:
            break

    if not city_field or not country_field:
        raise CommandError(
            "No se pudieron localizar campos de ciudad/país en el GPKG. "
            f"Campos disponibles: {field_names[:40]}..."
        )

    src_srs = layer.srs
    transform = None
    if src_srs is not None:
        try:
            src_epsg = int(src_srs.srid) if src_srs.srid else None
        except (TypeError, ValueError):
            src_epsg = None
        if src_epsg != TARGET_SRID:
            # Mollweide / lo que declare la capa → WGS84
            try:
                transform = CoordTransform(src_srs, SpatialReference(TARGET_SRID))
            except Exception:
                # Fallback explícito a EPSG:54009 si la capa no declara bien
                transform = CoordTransform(
                    SpatialReference(54009), SpatialReference(TARGET_SRID)
                )
    else:
        transform = CoordTransform(
            SpatialReference(54009), SpatialReference(TARGET_SRID)
        )

    for idx, feat in enumerate(layer):
        city = _as_str(_get_attr(feat, city_field))
        country = _as_str(_get_attr(feat, country_field))
        region = _as_str(_get_attr(feat, region_field))
        iso2 = _iso_from_feature(feat, iso_field, country)

        if not city or not country:
            continue

        if region_filter == "americas":
            in_region = is_americas_un_region(region)
            in_iso = bool(iso2 and iso2 in AMERICAS_ISO2)
            if not (in_region or in_iso):
                continue
            # Refuerzo: requiere ISO-2 del continente americano
            if not iso2 or iso2 not in AMERICAS_ISO2:
                continue
        elif region_filter == "world":
            if not iso2:
                continue
        else:
            raise CommandError(f"Región desconocida: {region_filter}")

        raw_id = _as_str(_get_attr(feat, id_field)) if id_field else None
        source_id = raw_id or f"row-{idx}"

        ogr_geom = feat.geom
        if ogr_geom is None or ogr_geom.empty:
            continue
        try:
            poly = _to_multipolygon_4326(ogr_geom, transform)
        except Exception:
            continue

        yield source_id, city[:255], country[:128], iso2, poly


class Command(BaseCommand):
    help = (
        "Importa Urban Centres de GHS-UCDB (GHSL/JRC/EC) como polígonos "
        "de extensión urbana. Por defecto filtra el continente americano."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--download",
            action="store_true",
            default=True,
            help="Descargar el ZIP oficial si no hay caché (default: sí).",
        )
        parser.add_argument(
            "--no-download",
            action="store_true",
            help="No descargar; exige --gpkg o un GPKG ya cacheado.",
        )
        parser.add_argument(
            "--force-download",
            action="store_true",
            help="Forzar re-descarga del ZIP aunque exista en caché.",
        )
        parser.add_argument(
            "--gpkg",
            type=str,
            default="",
            help="Ruta a un .gpkg local (salta descarga/extracción).",
        )
        parser.add_argument(
            "--region",
            type=str,
            default="americas",
            choices=("americas", "world"),
            help="Filtro geográfico (default: americas).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo cuenta/reporta; no escribe en BD.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Tamaño de lote para commits (default: 200).",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE(
                "Fuente: GHS-UCDB R2024A — GHSL / JRC / European Commission. "
                "Reutilización con atribución."
            )
        )

        gpkg_path: Optional[Path] = None
        if options["gpkg"]:
            gpkg_path = Path(options["gpkg"]).expanduser().resolve()
            if not gpkg_path.is_file():
                raise CommandError(f"GPKG no encontrado: {gpkg_path}")
        else:
            cache = _cache_dir()
            zip_path = cache / "GHS_UCDB_GLOBE_R2024A_V1_2.zip"
            extract_dir = cache / "GHS_UCDB_GLOBE_R2024A_V1_2"

            if options["no_download"]:
                existing = list(extract_dir.rglob("*.gpkg")) if extract_dir.exists() else []
                if not existing and not zip_path.exists():
                    raise CommandError(
                        "Sin --gpkg y sin caché. Quita --no-download o pasa --gpkg."
                    )
                if zip_path.exists() and not existing:
                    gpkg_path = _extract_gpkg(zip_path, extract_dir)
                else:
                    gpkg_path = max(existing, key=lambda p: p.stat().st_size)
            else:
                self.stdout.write(f"Descargando/usando caché: {GHS_UCDB_ZIP_URL}")
                _download_zip(
                    GHS_UCDB_ZIP_URL,
                    zip_path,
                    force=options["force_download"],
                )
                self.stdout.write(f"ZIP listo: {zip_path} ({zip_path.stat().st_size} bytes)")
                gpkg_path = _extract_gpkg(zip_path, extract_dir)

        assert gpkg_path is not None
        self.stdout.write(f"Leyendo GPKG: {gpkg_path}")

        dry_run = options["dry_run"]
        batch_size = max(1, int(options["batch_size"]))
        region = options["region"]

        created = 0
        updated = 0
        seen = 0

        buffer: list[tuple[str, dict]] = []

        def flush(batch: list[tuple[str, dict]]) -> tuple[int, int]:
            c = u = 0
            with transaction.atomic():
                for source_id, defaults in batch:
                    _, was_created = City.all_objects.update_or_create(
                        source=SOURCE,
                        source_id=source_id,
                        defaults={**defaults, "deleted_at": None},
                    )
                    if was_created:
                        c += 1
                    else:
                        u += 1
            return c, u

        for source_id, city, country, iso2, poly in _iter_americas_features(
            gpkg_path, region
        ):
            seen += 1
            defaults = {
                "city": city,
                "country": country,
                "country_iso": iso2,
                "polygon": poly,
            }
            if dry_run:
                if seen <= 5:
                    self.stdout.write(
                        f"  [dry-run] {city}, {country} ({iso2}) id={source_id}"
                    )
                continue

            buffer.append((source_id, defaults))
            if len(buffer) >= batch_size:
                c, u = flush(buffer)
                created += c
                updated += u
                self.stdout.write(
                    f"batch: created={created} updated={updated} seen={seen}"
                )
                buffer = []

        if not dry_run and buffer:
            c, u = flush(buffer)
            created += c
            updated += u

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry-run OK. candidates={seen} (sin escritura en BD). región={region}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import finished. created={created} updated={updated} "
                    f"seen={seen} región={region} source={SOURCE}"
                )
            )
