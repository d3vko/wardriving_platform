"""
Resolución set-based de city/region/country/country_iso desde geos_city.

Multi-nivel:
- city ← ADM3 localidad (KNN) si el país tiene admin_level=3 vivo; si no, ADM2.
- region ← ADM1 espacial; fallback padre denormalizado (ADM2/ADM3), luego
  ADM1∋centroid(ADM2).
- country/iso ← ADM0.
Sin ST_Area(::geography).
NULL en columnas = sin match / no resuelto.

El cruce espacial se ejecuta fuera del hot path de ingest: ``enqueue_geos_labels_*``
encola la tarea Celery ``resolve_geos_labels`` (ver ``apps.wardriving.tasks``), que a
su vez llama a :func:`resolve_geos_labels_for_ids`. El matching sigue siendo set-based
(UPDATE con LATERAL), pero ya no bloquea ``process_file`` ni la transacción de write.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional, Sequence

from django.db import connection
from django.db.models import Q

logger = logging.getLogger(__name__)

TABLE_WARDRIVING = "wardriving"
TABLE_LTE = "lte_wardriving"
ALLOWED_TABLES = frozenset({TABLE_WARDRIVING, TABLE_LTE})


def _validate_table(table: str) -> str:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Tabla no permitida: {table}")
    return table


def resolve_geos_labels_for_ids(
    table: str,
    ids: Sequence[int],
    *,
    force: bool = False,
) -> int:
    """
    Actualiza city/region/country/country_iso para los ids dados vía JOIN espacial.

    Si ``force`` y un id no tiene match, deja las columnas en NULL.
    Devuelve el número de filas afectadas por el UPDATE de assignación.
    """
    table = _validate_table(table)
    id_list = [int(i) for i in ids if i is not None]
    if not id_list:
        return 0

    with connection.cursor() as cursor:
        if force:
            cursor.execute(
                f"""
                UPDATE {table}
                SET
                    city = NULL,
                    region = NULL,
                    country = NULL,
                    country_iso = NULL
                WHERE id = ANY(%s)
                  AND deleted_at IS NULL
                """,
                [id_list],
            )

        # Short-circuit ADM3: solo tiene sentido evaluar el KNN de localidades
        # cuando existen filas admin_level=3 vivas. Pre-computamos el set de
        # ISOs con ADM3 vivo para (a) omitir el lateral por completo si no hay
        # ADM3 en ningún país, y (b) restringir con `country_iso = ANY(%s)` para
        # que el planner use el índice parcial (admin_level, country_iso) +
        # GiST en vez de un KNN global sobre todos los ADM3.
        cursor.execute(
            """
            SELECT DISTINCT country_iso
            FROM geos_city
            WHERE deleted_at IS NULL
              AND admin_level = 3
              AND country_iso IS NOT NULL
            """
        )
        adm3_isos = [r[0] for r in cursor.fetchall()]

        adm3_lateral = ""
        adm3_params: list = []
        if adm3_isos:
            adm3_lateral = """
                -- ADM3 localidades (p. ej. AR Georef): nearest al punto.
                -- Restringido a ISOs con ADM3 vivo para acotar el KNN.
                LEFT JOIN LATERAL (
                    SELECT
                        gc.city,
                        gc.region AS parent_region,
                        gc.country,
                        gc.country_iso
                    FROM geos_city AS gc
                    WHERE gc.deleted_at IS NULL
                      AND gc.admin_level = 3
                      AND gc.country_iso = COALESCE(
                          adm1.country_iso, adm0.country_iso
                      )
                      AND gc.country_iso = ANY(%s)
                    ORDER BY gc.polygon <-> t2.location
                    LIMIT 1
                ) AS adm3 ON TRUE
            """
            adm3_params = [adm3_isos]

        cursor.execute(
            f"""
            UPDATE {table} AS t
            SET
                city = CASE
                    WHEN s.city IS NULL OR BTRIM(s.city) = '' THEN NULL
                    ELSE BTRIM(s.city)
                END,
                region = CASE
                    WHEN s.region IS NULL OR BTRIM(s.region) = '' THEN NULL
                    ELSE BTRIM(s.region)
                END,
                country = s.country,
                country_iso = s.country_iso
            FROM (
                SELECT
                    t2.id AS id,
                    COALESCE(adm3.city, adm2.city) AS city,
                    COALESCE(
                        NULLIF(BTRIM(adm1.region), ''),
                        NULLIF(BTRIM(COALESCE(adm3.parent_region, adm2.parent_region)), ''),
                        NULLIF(BTRIM(adm1_from_adm2.region), '')
                    ) AS region,
                    COALESCE(
                        adm0.country,
                        adm3.country,
                        adm2.country,
                        adm1.country,
                        adm1_from_adm2.country
                    ) AS country,
                    COALESCE(
                        adm0.country_iso,
                        adm3.country_iso,
                        adm2.country_iso,
                        adm1.country_iso,
                        adm1_from_adm2.country_iso
                    ) AS country_iso
                FROM {table} AS t2
                LEFT JOIN LATERAL (
                    SELECT gc.region, gc.country, gc.country_iso
                    FROM geos_city AS gc
                    WHERE gc.deleted_at IS NULL
                      AND gc.admin_level = 1
                      AND gc.polygon && t2.location
                      AND ST_Intersects(gc.polygon, t2.location)
                    ORDER BY ST_Area(gc.polygon) ASC
                    LIMIT 1
                ) AS adm1 ON TRUE
                LEFT JOIN LATERAL (
                    SELECT gc.country, gc.country_iso
                    FROM geos_city AS gc
                    WHERE gc.deleted_at IS NULL
                      AND gc.admin_level = 0
                      AND gc.polygon && t2.location
                      AND ST_Intersects(gc.polygon, t2.location)
                    ORDER BY ST_Area(gc.polygon) ASC
                    LIMIT 1
                ) AS adm0 ON TRUE
                {adm3_lateral}
                -- ADM2 polígonos: solo cuando el país no usa ADM3.
                LEFT JOIN LATERAL (
                    SELECT
                        gc.city,
                        gc.region AS parent_region,
                        gc.country,
                        gc.country_iso,
                        gc.polygon
                    FROM geos_city AS gc
                    WHERE gc.deleted_at IS NULL
                      AND gc.admin_level = 2
                      AND adm3.city IS NULL
                      AND gc.polygon && t2.location
                      AND ST_Intersects(gc.polygon, t2.location)
                    ORDER BY ST_Area(gc.polygon) ASC
                    LIMIT 1
                ) AS adm2 ON TRUE
                LEFT JOIN LATERAL (
                    -- Fallback: padre ADM1 vía centroide del ADM2 cuando el
                    -- punto cae en micro-gaps ADM1 (islas / costa / CABA).
                    SELECT gc.region, gc.country, gc.country_iso
                    FROM geos_city AS gc
                    WHERE adm2.polygon IS NOT NULL
                      AND (
                            adm1.region IS NULL
                            OR BTRIM(adm1.region) = ''
                      )
                      AND (
                            adm2.parent_region IS NULL
                            OR BTRIM(adm2.parent_region) = ''
                      )
                      AND gc.deleted_at IS NULL
                      AND gc.admin_level = 1
                      AND gc.polygon && ST_PointOnSurface(adm2.polygon)
                      AND ST_Intersects(
                          gc.polygon, ST_PointOnSurface(adm2.polygon)
                      )
                    ORDER BY ST_Area(gc.polygon) ASC
                    LIMIT 1
                ) AS adm1_from_adm2 ON TRUE
                WHERE t2.id = ANY(%s)
                  AND t2.deleted_at IS NULL
                  AND t2.location IS NOT NULL
                  AND COALESCE(
                      adm0.country_iso,
                      adm1.country_iso,
                      adm3.country_iso,
                      adm2.country_iso,
                      adm1_from_adm2.country_iso
                  ) IS NOT NULL
            ) AS s
            WHERE t.id = s.id
            """,
            [*adm3_params, id_list],
        )
        return cursor.rowcount


def resolve_geos_labels_id_range(
    table: str,
    id_from: int,
    id_to: int,
    *,
    only_unresolved: bool = True,
    force: bool = False,
) -> tuple[int, list[int]]:
    """
    Resuelve un rango inclusivo de ids.

    Retorna (updated_count, ids_seleccionados).
    """
    table = _validate_table(table)
    where = [
        "deleted_at IS NULL",
        "location IS NOT NULL",
        "id >= %s",
        "id <= %s",
    ]
    params: list = [id_from, id_to]
    if only_unresolved and not force:
        where.append("country_iso IS NULL")

    sql = f"SELECT id FROM {table} WHERE {' AND '.join(where)} ORDER BY id"
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        ids = [row[0] for row in cursor.fetchall()]

    if not ids:
        return 0, []
    updated = resolve_geos_labels_for_ids(table, ids, force=force)
    return updated, ids


def iter_id_batches(
    table: str,
    *,
    batch_size: int = 5000,
    only_unresolved: bool = True,
    force: bool = False,
    id_from: Optional[int] = None,
    id_to: Optional[int] = None,
) -> Iterable[list[int]]:
    """Yield batches of ids to resolve (ordered)."""
    table = _validate_table(table)
    batch_size = max(1, int(batch_size))
    where = ["deleted_at IS NULL", "location IS NOT NULL"]
    params: list = []
    if id_from is not None:
        where.append("id >= %s")
        params.append(id_from)
    if id_to is not None:
        where.append("id <= %s")
        params.append(id_to)
    if only_unresolved and not force:
        where.append("country_iso IS NULL")

    last_id = (id_from or 0) - 1
    while True:
        sql = (
            f"SELECT id FROM {table} "
            f"WHERE {' AND '.join(where)} AND id > %s "
            f"ORDER BY id LIMIT %s"
        )
        with connection.cursor() as cursor:
            cursor.execute(sql, [*params, last_id, batch_size])
            batch = [row[0] for row in cursor.fetchall()]
        if not batch:
            break
        yield batch
        last_id = batch[-1]


def collect_ids_for_model_keys(
    model,
    key_fields: Sequence[str],
    keys: Sequence[tuple],
    *,
    base_filter: Optional[dict] = None,
) -> list[int]:
    """
    Tras un bulk upsert: localiza ids por clave natural (sin resolver labels).

    Es la parte barata (SELECT) de ``resolve_geos_labels_for_model_keys``;
    se separa para poder encolar la resolución espacial fuera de la transacción
    de write (ver ``enqueue_geos_labels_for_model_keys``).
    """
    _validate_table(model._meta.db_table)
    if not keys:
        return []

    qs = model.objects.filter(location__isnull=False)
    if base_filter:
        qs = qs.filter(**base_filter)

    ids: list[int] = []
    chunk = 500
    for i in range(0, len(keys), chunk):
        part = keys[i : i + chunk]
        q = Q()
        for key in part:
            q |= Q(**dict(zip(key_fields, key)))
        ids.extend(qs.filter(q).values_list("id", flat=True))

    return [int(i) for i in ids if i is not None]


def resolve_geos_labels_for_model_keys(
    model,
    key_fields: Sequence[str],
    keys: Sequence[tuple],
    *,
    base_filter: Optional[dict] = None,
    force: bool = False,
) -> int:
    """
    Tras un bulk upsert: localiza ids por clave natural y resuelve labels.

    Síncrono. Usado por backfill/tests; en el hot path de ingest se debe usar
    :func:`enqueue_geos_labels_for_model_keys` para no bloquear ``process_file``.
    """
    table = _validate_table(model._meta.db_table)
    ids = collect_ids_for_model_keys(
        model, key_fields, keys, base_filter=base_filter
    )
    return resolve_geos_labels_for_ids(table, ids, force=force)


def enqueue_geos_labels_for_model_keys(
    model,
    key_fields: Sequence[str],
    keys: Sequence[tuple],
    *,
    base_filter: Optional[dict] = None,
) -> int:
    """
    Tras un bulk upsert: colecta ids por clave natural y encola la tarea Celery
    ``resolve_geos_labels`` para resolver city/region/country/country_iso de
    forma asíncrona. No bloquea la transacción de write.

    Devuelve el número de ids encolados. Si no hay ids (sin GPS / sin filas
    afectadas) o la app no tiene Celery configurado, es no-op.
    """
    table = _validate_table(model._meta.db_table)
    ids = collect_ids_for_model_keys(
        model, key_fields, keys, base_filter=base_filter
    )
    if not ids:
        return 0

    try:
        from apps.wardriving.tasks import resolve_geos_labels
    except Exception:
        logger.exception(
            "enqueue resolve_geos_labels: no se pudo importar la tarea; "
            "resolve sync fallback table=%s ids=%d",
            table,
            len(ids),
        )
        # Fallback defensivo: resolver síncrono para no perder labels.
        return resolve_geos_labels_for_ids(table, ids)

    try:
        resolve_geos_labels.apply_async(args=[table, ids])
    except Exception:
        logger.exception(
            "apply_async resolve_geos_labels failed; sync fallback "
            "table=%s ids=%d",
            table,
            len(ids),
        )
        return resolve_geos_labels_for_ids(table, ids)

    logger.info(
        "enqueued resolve_geos_labels table=%s ids=%d", table, len(ids)
    )
    return len(ids)
