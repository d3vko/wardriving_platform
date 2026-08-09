"""
Importa límites ADM1+ADM2 oficiales locales para MX / PE / AR.

Reemplaza (soft-delete) filas CGAZ `geoboundaries` de esos ISO en niveles 1–2.
No toca ADM0 ni otros países.

Fuentes:
  MX — INEGI MG vía espejo CONABIO (AGEE/AGEM)
  PE — IGN/INEI límites departamentales/provinciales (.rar)
  AR — IGN vía API Georef (provincias / departamentos-comunas)
"""

from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Optional

import requests
from django.conf import settings
from django.contrib.gis.gdal import CoordTransform, DataSource, SpatialReference
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.timezone import now

from apps.geos.country_iso import ISO2_TO_COUNTRY_NAME
from apps.geos.models import City

TARGET_SRID = 4326
UA = "wardriving-platform/geos-local-import (+local-dev)"
CGAZ_SOURCE = "geoboundaries"
LOCAL_ISOS = frozenset({"MX", "PE", "AR"})


@dataclass(frozen=True)
class PackSpec:
    iso: str
    source: str
    level: int
    url: str
    archive_name: str
    extract_subdir: str


PACKS: dict[str, list[PackSpec]] = {
    "MX": [
        PackSpec(
            "MX",
            "inegi_mg",
            1,
            "http://www.conabio.gob.mx/informacion/gis/maps/geo/dest23gw.zip",
            "mx_dest23gw.zip",
            "mx_adm1",
        ),
        PackSpec(
            "MX",
            "inegi_mg",
            2,
            "http://www.conabio.gob.mx/informacion/gis/maps/geo/mun22gw.zip",
            "mx_mun22gw.zip",
            "mx_adm2",
        ),
    ],
    "PE": [
        PackSpec(
            "PE",
            "inei_pe",
            1,
            # Origen IGN es .rar; en despliegue preferimos ZIP preconvertido
            # (pe_departamentos.zip) para no depender de unrar en el contenedor.
            "https://www.idep.gob.pe/descargas_CN/limites/departamentos.rar",
            "pe_departamentos.zip",
            "pe_adm1",
        ),
        PackSpec(
            "PE",
            "inei_pe",
            2,
            "https://www.idep.gob.pe/descargas_CN/limites/provincias.rar",
            "pe_provincias.zip",
            "pe_adm2",
        ),
    ],
    "AR": [
        PackSpec(
            "AR",
            "ign_ar",
            1,
            "https://apis.datos.gob.ar/georef/api/provincias"
            "?formato=shp&campos=completo&max=30",
            "ar_provincias.zip",
            "ar_adm1",
        ),
        PackSpec(
            "AR",
            "ign_ar",
            2,
            "https://apis.datos.gob.ar/georef/api/departamentos"
            "?formato=shp&campos=completo&max=600",
            "ar_departamentos.zip",
            "ar_adm2",
        ),
    ],
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


def _title_es(value: str) -> str:
    """Title-case conservador para capas INEI en MAYÚSCULAS."""
    text = value.strip()
    if not text:
        return text
    if text != text.upper():
        return text
    small = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "E", "DA", "DO"}
    parts = []
    for i, tok in enumerate(text.split()):
        if i > 0 and tok in small:
            parts.append(tok.lower())
        else:
            parts.append(tok.capitalize())
    return " ".join(parts)


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


def _can_extract_rar() -> bool:
    """True solo si unrar existe o 7z tiene el codec RAR (paquete 7zip-rar)."""
    if shutil.which("unrar"):
        return True
    seven = shutil.which("7z") or shutil.which("7za")
    if not seven:
        return False
    # Debian 7zip sin 7zip-rar falla en extracción aunque el binario exista.
    for codecs in (Path("/usr/lib/7zip/Codecs"), Path("/usr/lib/p7zip/Codecs")):
        if codecs.is_dir() and any(codecs.glob("*[Rr]ar*")):
            return True
    try:
        proc = subprocess.run(
            [seven, "i"],
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    info = f"{proc.stdout or ''}\n{proc.stderr or ''}"
    return bool(
        re.search(r"(?i)\bRar(?:\d+)?\b", info)
        and "Codec" in info
    )


def _resolve_pack_archive(
    pack: PackSpec,
    cache: Path,
    *,
    no_download: bool,
    force_download: bool,
    log,
) -> Path:
    """
    Resuelve el archivo a extraer.

    PE: archive_name es .zip (sin dependencia unrar). Si falta el ZIP:
    descarga el .rar oficial y lo usa solo si hay unrar/7z+RAR; si no, error claro.
    """
    preferred = cache / pack.archive_name
    url_is_rar = pack.url.rstrip("/").lower().endswith(".rar")
    prefers_zip = preferred.suffix.lower() == ".zip"

    if prefers_zip and url_is_rar:
        rar_path = cache / f"{preferred.stem}.rar"
        if (
            preferred.is_file()
            and preferred.stat().st_size > 0
            and not force_download
        ):
            log(f"Usando ZIP en caché: {preferred.name}")
            return preferred
        if no_download:
            if preferred.is_file() and preferred.stat().st_size > 0:
                return preferred
            raise CommandError(
                f"Falta {preferred}. Copia pe_departamentos.zip / pe_provincias.zip "
                "a MEDIA_ROOT/geos_cache/ (convertidos desde los .rar IGN) "
                "o instala 7zip-rar en la imagen y quita --no-download."
            )
        log(f"Descargando origen RAR: {pack.url}")
        _download(pack.url, rar_path, force=force_download)
        # Preferir ZIP si apareció en caché (p. ej. convertido en host).
        if preferred.is_file() and preferred.stat().st_size > 0:
            log(f"  Usando ZIP en caché: {preferred.name}")
            return preferred
        if _can_extract_rar():
            log(f"  RAR listo (extraíble): {rar_path.name}")
            return rar_path
        raise CommandError(
            "PE viene en .rar y 7z no tiene codec RAR (falta 7zip-rar) ni unrar.\n"
            "Opción A: copia pe_departamentos.zip y pe_provincias.zip "
            "a wardrive/media/geos_cache/ y reintenta con --no-download.\n"
            "Opción B: rebuild (Dockerfile incluye 7zip-rar via non-free).\n"
            "Opción C: podman-compose exec -u root wardrive bash -c "
            "'sed -i \"s/^Components: main$/Components: main contrib non-free "
            "non-free-firmware/\" /etc/apt/sources.list.d/debian.sources && "
            "apt-get update && apt-get install -y 7zip-rar'"
        )

    if no_download:
        if not preferred.is_file():
            raise CommandError(
                f"Sin caché {preferred}. Quita --no-download o coloca el archivo."
            )
        return preferred

    log(f"Descargando/usando {pack.url}")
    _download(pack.url, preferred, force=force_download)
    log(f"  listo {preferred.name} ({preferred.stat().st_size} bytes)")
    return preferred


def _extract_archive(archive: Path, dest_dir: Path) -> Path:
    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    suffix = archive.suffix.lower()
    if suffix == ".zip":
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(dest_dir)
        return dest_dir
    if suffix == ".rar":
        unrar = shutil.which("unrar")
        seven = shutil.which("7z") or shutil.which("7za")
        if unrar:
            subprocess.run(
                [unrar, "x", "-o+", str(archive), str(dest_dir) + "/"],
                check=True,
                capture_output=True,
            )
            return dest_dir
        if seven:
            subprocess.run(
                [seven, "x", f"-o{dest_dir}", str(archive), "-y"],
                check=True,
                capture_output=True,
            )
            return dest_dir
        raise CommandError(
            f"Se necesita unrar o 7z para extraer {archive.name}. "
            "Instálalo en el host/contenedor o pasa un ZIP/SHP ya extraído."
        )
    raise CommandError(f"Archivo no soportado: {archive}")


def _find_shapefile(root: Path) -> Path:
    shps = sorted(root.rglob("*.shp"))
    if not shps:
        raise CommandError(f"No hay .shp bajo {root}")
    # Prefer files with most siblings that look like main layer name
    return max(shps, key=lambda p: p.stat().st_size)


def _open_layer(shp_path: Path):
    ds = DataSource(str(shp_path))
    if len(ds) < 1:
        raise CommandError(f"Shapefile vacío: {shp_path}")
    layer = max(ds, key=lambda ly: ly.num_feat)
    transform = None
    srs = layer.srs
    if srs is not None:
        try:
            if srs.srid and int(srs.srid) != TARGET_SRID:
                transform = CoordTransform(srs, SpatialReference(TARGET_SRID))
            elif not srs.srid:
                # Geographic without EPSG: assume already lon/lat; GDAL may still need WGS84
                wgs84 = SpatialReference(TARGET_SRID)
                if not srs == wgs84:
                    try:
                        transform = CoordTransform(srs, wgs84)
                    except Exception:
                        transform = None
        except Exception:
            transform = None
    return layer, transform


def _iter_mx(
    shp_path: Path, level: int
) -> Iterator[tuple[str, str, str, MultiPolygon]]:
    layer, transform = _open_layer(shp_path)
    fields = list(layer.fields)
    name_f = _pick_field(fields, ("NOMGEO", "NOM_MUN", "NAME"))
    ent_f = _pick_field(fields, ("NOM_ENT", "ENTIDAD"))
    id_f = _pick_field(fields, ("CVEGEO", "CVE_ENT", "CVE_MUN"))
    if not name_f or not id_f:
        raise CommandError(f"MX campos insuficientes en {shp_path}: {fields}")
    for feat in layer:
        name = _as_str(_get_attr(feat, name_f))
        sid = _as_str(_get_attr(feat, id_f))
        if not name or not sid:
            continue
        parent = _as_str(_get_attr(feat, ent_f)) if ent_f else None
        geom = feat.geom
        if geom is None:
            continue
        try:
            poly = _to_multipolygon_4326(geom, transform)
        except Exception:
            continue
        if level == 1:
            yield f"mx-adm1-{sid}", "", name, poly
        else:
            yield f"mx-adm2-{sid}", name, parent or "", poly


def _iter_pe(
    shp_path: Path, level: int
) -> Iterator[tuple[str, str, str, MultiPolygon]]:
    layer, transform = _open_layer(shp_path)
    fields = list(layer.fields)
    if level == 1:
        name_f = _pick_field(fields, ("DEPARTAMEN", "NOMBDEP", "NOMBRE", "NAME"))
        id_f = _pick_field(fields, ("IDDPTO", "CCDDEP", "CODDEP"))
        if not name_f or not id_f:
            raise CommandError(f"PE ADM1 campos insuficientes: {fields}")
        for feat in layer:
            name = _as_str(_get_attr(feat, name_f))
            sid = _as_str(_get_attr(feat, id_f))
            if not name or not sid:
                continue
            geom = feat.geom
            if geom is None:
                continue
            try:
                poly = _to_multipolygon_4326(geom, transform)
            except Exception:
                continue
            yield f"pe-adm1-{sid}", "", _title_es(name), poly
    else:
        city_f = _pick_field(fields, ("PROVINCIA", "NOMBPROV", "NAME"))
        parent_f = _pick_field(fields, ("DEPARTAMEN", "NOMBDEP"))
        id_f = _pick_field(fields, ("IDPROV", "CCDPRO", "CODPROV"))
        if not city_f or not id_f:
            raise CommandError(f"PE ADM2 campos insuficientes: {fields}")
        for feat in layer:
            city = _as_str(_get_attr(feat, city_f))
            sid = _as_str(_get_attr(feat, id_f))
            parent = _as_str(_get_attr(feat, parent_f)) if parent_f else None
            if not city or not sid:
                continue
            geom = feat.geom
            if geom is None:
                continue
            try:
                poly = _to_multipolygon_4326(geom, transform)
            except Exception:
                continue
            yield (
                f"pe-adm2-{sid}",
                _title_es(city),
                _title_es(parent) if parent else "",
                poly,
            )


def _iter_ar(
    shp_path: Path, level: int
) -> Iterator[tuple[str, str, str, MultiPolygon]]:
    layer, transform = _open_layer(shp_path)
    fields = list(layer.fields)
    if level == 1:
        name_f = _pick_field(fields, ("nombre", "NOMBRE", "name", "NAM"))
        id_f = _pick_field(fields, ("id", "ID", "IN1", "in1"))
        if not name_f or not id_f:
            raise CommandError(f"AR ADM1 campos insuficientes: {fields}")
        for feat in layer:
            name = _as_str(_get_attr(feat, name_f))
            sid = _as_str(_get_attr(feat, id_f))
            if not name or not sid:
                continue
            geom = feat.geom
            if geom is None:
                continue
            try:
                poly = _to_multipolygon_4326(geom, transform)
            except Exception:
                continue
            yield f"ar-adm1-{sid}", "", name, poly
    else:
        city_f = _pick_field(fields, ("nombre", "NOMBRE", "name"))
        parent_f = _pick_field(
            fields, ("prov_nombre", "PROV_NOMBRE", "nam", "NAM", "provincia")
        )
        id_f = _pick_field(fields, ("id", "ID", "IN1", "in1"))
        if not city_f or not id_f:
            raise CommandError(f"AR ADM2 campos insuficientes: {fields}")
        for feat in layer:
            city = _as_str(_get_attr(feat, city_f))
            sid = _as_str(_get_attr(feat, id_f))
            parent = _as_str(_get_attr(feat, parent_f)) if parent_f else None
            if not city or not sid:
                continue
            geom = feat.geom
            if geom is None:
                continue
            try:
                poly = _to_multipolygon_4326(geom, transform)
            except Exception:
                continue
            yield f"ar-adm2-{sid}", city, parent or "", poly


def _iter_features(
    iso: str, level: int, shp_path: Path
) -> Iterator[tuple[str, str, str, MultiPolygon]]:
    if iso == "MX":
        yield from _iter_mx(shp_path, level)
    elif iso == "PE":
        yield from _iter_pe(shp_path, level)
    elif iso == "AR":
        yield from _iter_ar(shp_path, level)
    else:
        raise CommandError(f"ISO no soportado: {iso}")


class Command(BaseCommand):
    help = (
        "Importa ADM1+ADM2 oficiales locales (MX INEGI, PE INEI/IGN, AR IGN/Georef) "
        "y reemplaza CGAZ geoboundaries de esos países en niveles 1–2."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--countries",
            type=str,
            default="MX,PE,AR",
            help="ISO2 separados por coma (default: MX,PE,AR).",
        )
        parser.add_argument(
            "--levels",
            type=str,
            default="1,2",
            help="Niveles a importar (default: 1,2).",
        )
        parser.add_argument(
            "--no-download",
            action="store_true",
            help="Usa archivos ya en MEDIA_ROOT/geos_cache.",
        )
        parser.add_argument(
            "--force-download",
            action="store_true",
            help="Re-descarga aunque exista caché.",
        )
        parser.add_argument(
            "--replace-existing",
            action="store_true",
            help=(
                "Tras importar OK un país, soft-delete CGAZ ADM1+ADM2 de ese ISO "
                "(y huérfanos del source local). Nunca borra antes de cargar."
            ),
        )
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--batch-size", type=int, default=100)

    def handle(self, *args, **options):
        countries = [
            c.strip().upper()
            for c in options["countries"].split(",")
            if c.strip()
        ]
        for iso in countries:
            if iso not in LOCAL_ISOS:
                raise CommandError(f"País no soportado: {iso} (usa MX, PE, AR)")
        try:
            levels = sorted(
                {int(x.strip()) for x in options["levels"].split(",") if x.strip()}
            )
        except ValueError as exc:
            raise CommandError("--levels inválido") from exc
        for level in levels:
            if level not in (1, 2):
                raise CommandError("Solo se admiten levels 1 y 2")

        cache = _cache_dir()
        dry_run = options["dry_run"]
        batch_size = max(1, int(options["batch_size"]))
        replace = options["replace_existing"] and not dry_run

        created = updated = seen = 0
        # mínimos conocidos de las fuentes canónicas
        min_expected = {
            ("MX", 1): 30,
            ("MX", 2): 2000,
            ("PE", 1): 20,
            ("PE", 2): 150,
            ("AR", 1): 20,
            ("AR", 2): 400,
        }

        def flush(batch: list[tuple[str, str, dict]]) -> tuple[int, int]:
            c = u = 0
            with transaction.atomic():
                for source, source_id, defaults in batch:
                    _, was_created = City.all_objects.update_or_create(
                        source=source,
                        source_id=source_id,
                        defaults={**defaults, "deleted_at": None},
                    )
                    if was_created:
                        c += 1
                    else:
                        u += 1
            return c, u

        for iso in countries:
            country_name = ISO2_TO_COUNTRY_NAME.get(iso, iso)
            local_source = PACKS[iso][0].source
            imported_ids: set[str] = set()
            country_seen = 0
            buffer: list[tuple[str, str, dict]] = []

            self.stdout.write(self.style.NOTICE(f"=== {iso} ({local_source}) ==="))

            for pack in PACKS[iso]:
                if pack.level not in levels:
                    continue
                archive = _resolve_pack_archive(
                    pack,
                    cache,
                    no_download=options["no_download"],
                    force_download=options["force_download"],
                    log=self.stdout.write,
                )

                extract_dir = cache / pack.extract_subdir
                self.stdout.write(f"Extrayendo {archive.name} → {extract_dir}")
                try:
                    _extract_archive(archive, extract_dir)
                except CommandError:
                    raise
                except subprocess.CalledProcessError as exc:
                    raise CommandError(
                        f"Fallo extrayendo {archive} (PE suele requerir unrar/7z "
                        f"en el contenedor, o pe_*.zip en geos_cache): {exc}"
                    ) from exc

                shp = _find_shapefile(extract_dir)
                self.stdout.write(f"Leyendo {iso} ADM{pack.level}: {shp}")

                level_seen = 0
                for source_id, city, region_name, poly in _iter_features(
                    iso, pack.level, shp
                ):
                    seen += 1
                    country_seen += 1
                    level_seen += 1
                    imported_ids.add(source_id)
                    defaults = {
                        "city": city[:255],
                        "region": region_name[:255],
                        "country": country_name[:128],
                        "country_iso": iso,
                        "admin_level": pack.level,
                        "polygon": poly,
                    }
                    if dry_run:
                        if level_seen <= 3:
                            self.stdout.write(
                                f"  [dry-run] {iso} ADM{pack.level} "
                                f"city={city!r} region={region_name!r} id={source_id}"
                            )
                        continue
                    buffer.append((pack.source, source_id, defaults))
                    if len(buffer) >= batch_size:
                        c, u = flush(buffer)
                        created += c
                        updated += u
                        self.stdout.write(
                            f"batch: created={created} updated={updated} seen={seen}"
                        )
                        buffer = []

                need = min_expected.get((iso, pack.level), 1)
                if level_seen < need:
                    raise CommandError(
                        f"{iso} ADM{pack.level}: solo {level_seen} features "
                        f"(mínimo esperado {need}). Abortado sin soft-delete de {iso}."
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  {iso} ADM{pack.level}: {level_seen} features OK"
                    )
                )

            if not dry_run and buffer:
                c, u = flush(buffer)
                created += c
                updated += u

            if replace and country_seen > 0:
                # Solo ahora: retirar CGAZ del país y huérfanos del source local
                n_cgaz = City.objects.filter(
                    country_iso=iso,
                    admin_level__in=levels,
                    source=CGAZ_SOURCE,
                ).update(deleted_at=now())
                n_orph = (
                    City.objects.filter(
                        country_iso=iso,
                        admin_level__in=levels,
                        source=local_source,
                    )
                    .exclude(source_id__in=imported_ids)
                    .update(deleted_at=now())
                )
                self.stdout.write(
                    self.style.WARNING(
                        f"  Soft-delete post-import {iso}: "
                        f"cgaz={n_cgaz} local_orphans={n_orph}"
                    )
                )

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Dry-run OK. seen={seen} countries={countries} levels={levels}"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import finished. created={created} updated={updated} "
                    f"seen={seen} countries={countries} levels={levels}"
                )
            )
            self.stdout.write(
                "Siguiente paso:\n"
                "  podman-compose exec -T wardrive python wardrive/manage.py "
                "backfill_geos_labels --table all --force"
            )
