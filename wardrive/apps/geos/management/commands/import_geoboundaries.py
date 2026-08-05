"""
Importa límites administrativos geoBoundaries CGAZ (ADM0 + ADM2).

Fuente: geoBoundaries / William & Mary geoLab — CC BY 4.0
  https://www.geoboundaries.org/
  https://github.com/wmgeolab/geoBoundaries

Atribución requerida al reutilizar los datos.
"""

from __future__ import annotations

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
    AMERICAS_ISO3,
    ISO2_TO_COUNTRY_NAME,
    country_name_to_iso2,
    iso3_to_iso2,
)
from apps.geos.models import City

SOURCE = "geoboundaries"
TARGET_SRID = 4326
UA = "wardriving-platform/geos-import (+https://github.com; contact=local-dev)"

CGAZ_URLS = {
    0: (
        "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/CGAZ/"
        "geoBoundariesCGAZ_ADM0.gpkg"
    ),
    2: (
        "https://github.com/wmgeolab/geoBoundaries/raw/main/releaseData/CGAZ/"
        "geoBoundariesCGAZ_ADM2.gpkg"
    ),
}


def _cache_dir() -> Path:
    base = Path(getattr(settings, "MEDIA_ROOT", None) or "/tmp")
    path = base / "geos_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fix_mojibake(text: str) -> str:
    if "Ã" not in text and "Â" not in text:
        return text
    try:
        fixed = text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text
    if fixed != text and ("Ã" not in fixed and "Â" not in fixed):
        return fixed
    return text


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return _fix_mojibake(text)


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


def _pick_field(names: list[str], candidates: tuple[str, ...]) -> Optional[str]:
    upper = {n.upper(): n for n in names}
    for cand in candidates:
        if cand.upper() in upper:
            return upper[cand.upper()]
    return None


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
    if geos.geom_type == "GeometryCollection":
        polys = [g for g in geos if isinstance(g, Polygon)]
        if polys:
            return MultiPolygon(*polys, srid=TARGET_SRID)
    converted = GEOSGeometry(geos.wkt, srid=TARGET_SRID)
    if isinstance(converted, MultiPolygon):
        return converted
    if isinstance(converted, Polygon):
        return MultiPolygon(converted, srid=TARGET_SRID)
    raise ValueError(f"Geometría no convertible a MultiPolygon: {geos.geom_type}")


def _download(url: str, dest: Path, force: bool = False) -> Path:
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


def _resolve_iso2(
    shape_group: Optional[str],
    shape_iso: Optional[str],
    shape_name: Optional[str],
    admin_level: int,
) -> Optional[str]:
    for raw in (shape_group, shape_iso):
        if not raw:
            continue
        token = raw.strip().upper().replace(";", " ").split()[0]
        if len(token) == 2 and token.isalpha() and token in AMERICAS_ISO2:
            return token
        if len(token) == 3 and token.isalpha():
            mapped = iso3_to_iso2(token)
            if mapped:
                return mapped
    # ADM0: shapeName suele ser el país
    if admin_level == 0 and shape_name:
        return country_name_to_iso2(shape_name)
    return None


def _iter_cgaz_features(
    gpkg_path: Path,
    admin_level: int,
    region_filter: str,
) -> Iterator[tuple[str, str, str, str, int, MultiPolygon]]:
    """Yields (source_id, city, country, country_iso, admin_level, multipolygon)."""
    ds = DataSource(str(gpkg_path))
    if len(ds) < 1:
        raise CommandError(f"GeoPackage sin capas: {gpkg_path}")

    layer = max(ds, key=lambda ly: ly.num_feat)
    fields = list(layer.fields)

    name_f = _pick_field(fields, ("shapeName", "shapename", "NAME", "name"))
    group_f = _pick_field(fields, ("shapeGroup", "shapegroup", "ISO", "ADM0_A3"))
    iso_f = _pick_field(fields, ("shapeISO", "shapeiso", "ISO_CODE"))
    id_f = _pick_field(fields, ("shapeID", "shapeid", "GID", "id", "FID"))

    if not name_f:
        raise CommandError(
            f"No se encontró shapeName en {gpkg_path}. Campos: {fields[:40]}"
        )

    src_srs = layer.srs
    transform = None
    if src_srs is not None:
        try:
            src_epsg = int(src_srs.srid) if src_srs.srid else None
        except (TypeError, ValueError):
            src_epsg = None
        if src_epsg != TARGET_SRID:
            try:
                transform = CoordTransform(src_srs, SpatialReference(TARGET_SRID))
            except Exception:
                transform = None

    for idx, feat in enumerate(layer):
        shape_name = _as_str(_get_attr(feat, name_f))
        shape_group = _as_str(_get_attr(feat, group_f))
        shape_iso = _as_str(_get_attr(feat, iso_f))
        raw_id = _as_str(_get_attr(feat, id_f)) if id_f else None

        iso2 = _resolve_iso2(shape_group, shape_iso, shape_name, admin_level)
        if region_filter == "americas":
            group_ok = bool(shape_group and shape_group.upper() in AMERICAS_ISO3)
            iso_ok = bool(iso2 and iso2 in AMERICAS_ISO2)
            if not (group_ok or iso_ok):
                continue
            if not iso2 or iso2 not in AMERICAS_ISO2:
                continue
        elif region_filter == "world":
            if not iso2:
                continue
        else:
            raise CommandError(f"Región desconocida: {region_filter}")

        country = ISO2_TO_COUNTRY_NAME.get(iso2) or shape_name or iso2
        if admin_level == 0:
            city = ""
            if shape_name:
                country = shape_name[:128]
        else:
            city = (shape_name or "")[:255]
            if not city:
                continue

        source_id = raw_id or f"adm{admin_level}-{iso2}-{idx}"
        # Prefijo de nivel para no colisionar IDs entre ADM0/ADM2
        if not raw_id:
            source_id = f"adm{admin_level}-{source_id}"
        else:
            source_id = f"adm{admin_level}-{raw_id}"[:64]

        ogr_geom = feat.geom
        if ogr_geom is None or ogr_geom.empty:
            continue
        try:
            poly = _to_multipolygon_4326(ogr_geom, transform)
        except Exception:
            continue

        yield source_id, city, country[:128], iso2, admin_level, poly


class Command(BaseCommand):
    help = (
        "Importa límites administrativos geoBoundaries CGAZ (ADM0 países + "
        "ADM2 municipios) para América. CC BY 4.0 — atribución requerida."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-download",
            action="store_true",
            help="No descargar; usa GPKG ya cacheados o --adm0/--adm2.",
        )
        parser.add_argument(
            "--force-download",
            action="store_true",
            help="Re-descargar aunque exista caché.",
        )
        parser.add_argument(
            "--adm0",
            type=str,
            default="",
            help="Ruta local al GPKG ADM0 (salta descarga ADM0).",
        )
        parser.add_argument(
            "--adm2",
            type=str,
            default="",
            help="Ruta local al GPKG ADM2 (salta descarga ADM2).",
        )
        parser.add_argument(
            "--levels",
            type=str,
            default="0,2",
            help="Niveles a importar, separados por coma (default: 0,2).",
        )
        parser.add_argument(
            "--region",
            type=str,
            default="americas",
            choices=("americas", "world"),
            help="Filtro geográfico (default: americas).",
        )
        parser.add_argument(
            "--replace-ghs",
            action="store_true",
            help="Borra filas source=ghs_ucdb antes de importar.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo reporta; no escribe en BD.",
        )
        parser.add_argument(
            "--verify-id",
            type=int,
            default=0,
            help="Tras importar, imprime city/country/country_iso de wardriving_vendor para ese id.",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=200,
            help="Tamaño de lote (default: 200).",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.NOTICE(
                "Fuente: geoBoundaries CGAZ — William & Mary geoLab (CC BY 4.0). "
                "Reutilización con atribución."
            )
        )

        try:
            levels = sorted({int(x.strip()) for x in options["levels"].split(",") if x.strip()})
        except ValueError as exc:
            raise CommandError("--levels debe ser enteros separados por coma") from exc
        for level in levels:
            if level not in (0, 2):
                raise CommandError(f"Nivel no soportado: {level} (usa 0 y/o 2)")

        if options["replace_ghs"] and not options["dry_run"]:
            deleted, _ = City.all_objects.filter(source="ghs_ucdb").hard_delete()
            self.stdout.write(
                self.style.WARNING(f"Eliminadas filas ghs_ucdb: {deleted}")
            )

        cache = _cache_dir()
        paths: dict[int, Path] = {}
        for level in levels:
            local = options.get(f"adm{level}") or ""
            if local:
                path = Path(local).expanduser().resolve()
                if not path.is_file():
                    raise CommandError(f"GPKG no encontrado: {path}")
                paths[level] = path
            else:
                filename = f"geoBoundariesCGAZ_ADM{level}.gpkg"
                dest = cache / filename
                if options["no_download"]:
                    if not dest.is_file():
                        raise CommandError(
                            f"Sin caché {dest}. Quita --no-download o pasa --adm{level}."
                        )
                    paths[level] = dest
                else:
                    url = CGAZ_URLS[level]
                    self.stdout.write(f"Descargando/usando caché ADM{level}: {url}")
                    _download(url, dest, force=options["force_download"])
                    self.stdout.write(
                        f"ADM{level} listo: {dest} ({dest.stat().st_size} bytes)"
                    )
                    paths[level] = dest

        dry_run = options["dry_run"]
        batch_size = max(1, int(options["batch_size"]))
        region = options["region"]

        created = updated = seen = 0
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

        for level in levels:
            gpkg = paths[level]
            self.stdout.write(f"Leyendo ADM{level}: {gpkg}")
            for source_id, city, country, iso2, admin_level, poly in _iter_cgaz_features(
                gpkg, level, region
            ):
                seen += 1
                defaults = {
                    "city": city,
                    "country": country,
                    "country_iso": iso2,
                    "admin_level": admin_level,
                    "polygon": poly,
                }
                if dry_run:
                    if seen <= 8:
                        label = city or "(país)"
                        self.stdout.write(
                            f"  [dry-run] ADM{admin_level} {label}, {country} "
                            f"({iso2}) id={source_id}"
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
                    f"Dry-run OK. candidates={seen} región={region} levels={levels}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import finished. created={created} updated={updated} "
                    f"seen={seen} región={region} levels={levels} source={SOURCE}"
                )
            )

        verify_id = int(options.get("verify_id") or 0)
        if verify_id:
            from django.db import connection

            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT city, country, country_iso "
                    "FROM wardriving_vendor WHERE id = %s",
                    [verify_id],
                )
                row = cursor.fetchone()
            if row is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"verify-id={verify_id}: no hay fila en wardriving_vendor"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"verify-id={verify_id}: city={row[0]!r} "
                        f"country={row[1]!r} country_iso={row[2]!r}"
                    )
                )
        elif not dry_run:
            self.stdout.write(
                "Verificación sugerida:\n"
                "  podman-compose exec -T wardrive_db psql -U postgres -c "
                "\"SELECT city, country, country_iso "
                "FROM wardriving_vendor WHERE id = 779912;\""
            )
