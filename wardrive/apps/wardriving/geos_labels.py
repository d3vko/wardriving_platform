"""
Resolución set-based de city/region/country/country_iso desde geos_city.

Multi-nivel: city←ADM2, region←ADM1, country/iso←ADM0 (fallback cualquier nivel).
Sin ST_Area(::geography).
NULL en columnas = sin match / no resuelto.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence

from django.db import connection

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
                    adm2.city AS city,
                    adm1.region AS region,
                    COALESCE(
                        adm0.country, adm2.country, adm1.country
                    ) AS country,
                    COALESCE(
                        adm0.country_iso, adm2.country_iso, adm1.country_iso
                    ) AS country_iso
                FROM {table} AS t2
                LEFT JOIN LATERAL (
                    SELECT gc.city, gc.country, gc.country_iso
                    FROM geos_city AS gc
                    WHERE gc.deleted_at IS NULL
                      AND gc.admin_level = 2
                      AND gc.polygon && t2.location
                      AND ST_Intersects(gc.polygon, t2.location)
                    ORDER BY ST_Area(gc.polygon) ASC
                    LIMIT 1
                ) AS adm2 ON TRUE
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
                WHERE t2.id = ANY(%s)
                  AND t2.deleted_at IS NULL
                  AND t2.location IS NOT NULL
                  AND COALESCE(
                      adm0.country_iso, adm2.country_iso, adm1.country_iso
                  ) IS NOT NULL
            ) AS s
            WHERE t.id = s.id
            """,
            [id_list],
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
    """
    table = _validate_table(model._meta.db_table)
    if not keys:
        return 0

    qs = model.objects.filter(location__isnull=False)
    if base_filter:
        qs = qs.filter(**base_filter)

    # Construir Q por tuplas de claves (en lotes para no exceder límites)
    from django.db.models import Q

    ids: list[int] = []
    chunk = 500
    for i in range(0, len(keys), chunk):
        part = keys[i : i + chunk]
        q = Q()
        for key in part:
            q |= Q(**dict(zip(key_fields, key)))
        ids.extend(qs.filter(q).values_list("id", flat=True))

    return resolve_geos_labels_for_ids(table, ids, force=force)
