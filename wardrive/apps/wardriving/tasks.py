"""
Tareas Celery de wardriving.

Hoy aloja la resolución asíncrona de labels geográficos (city/region/country/
country_iso) post-ingest, para que ``process_file`` no bloquee el cruce PostGIS.
"""

from __future__ import annotations

import logging

from celery import shared_task

from apps.wardriving.geos_labels import (
    ALLOWED_TABLES,
    resolve_geos_labels_for_ids,
)

logger = logging.getLogger(__name__)


def _validate_table(table: str) -> str:
    if table not in ALLOWED_TABLES:
        raise ValueError(f"Tabla no permitida: {table}")
    return table


@shared_task(
    bind=True,
    acks_late=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
    reject_on_worker_lost=True,
)
def resolve_geos_labels(
    self,
    table: str,
    ids,
    *,
    force: bool = False,
    batch_size: int = 2000,
) -> int:
    """
    Resuelve city/region/country/country_iso para los ids dados vía JOIN espacial
    set-based contra ``geos_city``.

    Se encola desde el hot path de ingest (``bulk_upsert_by_keys`` vía
    ``transaction.on_commit``) para no alargar ``process_file``. Procesa en
    lotes para no mantener un UPDATE gigante cuando el chunk de ingest era grande.

    Devuelve el total de filas afectadas por el UPDATE de asignación.
    """
    table = _validate_table(table)
    id_list = [int(i) for i in ids if i is not None]
    if not id_list:
        return 0

    batch_size = max(1, int(batch_size))
    total = 0
    for i in range(0, len(id_list), batch_size):
        batch = id_list[i : i + batch_size]
        total += resolve_geos_labels_for_ids(table, batch, force=force)

    logger.info(
        "resolve_geos_labels table=%s ids=%d updated=%d",
        table,
        len(id_list),
        total,
    )
    return total
