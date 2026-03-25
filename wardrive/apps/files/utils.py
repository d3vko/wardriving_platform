import logging
import re
import time
from decimal import Decimal
from datetime import datetime
from functools import reduce
from contextlib import contextmanager

from django.db import connection, router, transaction
from django.db.models import Q
from django.utils.timezone import make_aware

from apps.core.services import get_redis_client

logger = logging.getLogger(__name__)


def safe_storage_name(name, max_length=255, default="upload"):
    """
    Return a name safe for S3/MinIO object keys (avoids 400 Bad Request on HeadObject).
    Uses basename, strips backslashes and leading slashes, and removes characters
    that can cause issues with some S3-compatible backends.
    """
    if not name or not str(name).strip():
        return default
    name = str(name).replace("\\", "/").strip()
    name = name.split("/")[-1] if "/" in name else name
    name = name.lstrip("/").strip() or default
    if name.startswith("."):
        name = default + name
    name = re.sub(r"[^\w\s.\-]", "_", name)
    name = re.sub(r"\s+", "_", name).strip("_") or default
    return name[:max_length]


@contextmanager
def record_lock(mac, channel, uploaded_by, timeout=10, wait=60, **kwargs):
    """Context manager for lock by (mac, channel, uploaded_by). No-op when Redis is unavailable."""
    client = get_redis_client()
    if client is None:
        yield
        return
    key = get_lock_key(mac, channel, uploaded_by)
    lock = client.lock(key, timeout=timeout, blocking_timeout=wait)
    try:
        lock.acquire()
        yield
    finally:
        lock.release()


@contextmanager
def record_lte_lock(mcc, mnc, lac, cell_id, timeout=10, wait=60, **kwargs):
    """Context manager for LTE lock by (mcc, mnc, lac, cell_id). No-op when Redis is unavailable."""
    client = get_redis_client()
    if client is None:
        yield
        return
    key = get_lock_lte_key(mcc, mnc, lac, cell_id)
    lock = client.lock(key, timeout=timeout, blocking_timeout=wait)
    try:
        lock.acquire()
        yield
    finally:
        lock.release()


def get_lock_key(mac, channel, uploaded_by):
    return f"lock:wardriving:{mac}:{channel}:{uploaded_by}"


def get_lock_lte_key(mcc, mnc, lac, cell_id):
    return f"lock:lte-wardriving:{mcc}:{mnc}:{lac}:{cell_id}"


# -----------------------------
# Helpers of upsert
# -----------------------------


def _build_q(keys, key_fields):
    ors = []
    for tup in keys:
        q = Q(**{f: v for f, v in zip(key_fields, tup)})
        ors.append(q)
    # If no keys, avoid reduce([])
    if not ors:
        return Q(pk=None)
    return reduce(lambda a, b: a | b, ors)


def _dedupe_keep_best(rows, key_fields, better_row_fn):
    """
    rows: list[dict] (must contain key_fields)
    better_row_fn(new_row, cur_row) -> bool
    """
    by_key = {}
    for r in rows:
        k = tuple(r.get(f) for f in key_fields)
        cur = by_key.get(k)
        if cur is None or better_row_fn(r, cur):
            by_key[k] = r
    return by_key


def default_better_row_fn(new_row, cur_row):
    nr = new_row.get("rssi")
    cr = cur_row.get("rssi")
    if cr is None:
        return True
    if nr is None:
        return False
    return nr > cr


def wardriving_better_obj_fn(new_row, old_obj):
    # If have "default" values (without valid data), always perform
    is_default = False
    if hasattr(old_obj, "is_default_data"):
        try:
            is_default = bool(old_obj.is_default_data())
        except Exception:
            is_default = False
    if is_default:
        return True

    nrssi = new_row.get("rssi")
    orssi = getattr(old_obj, "rssi", None)

    # Check RSSI, if New RSSI don't change
    if nrssi is None:
        return False

    # If RSSI is better (less value)
    return (orssi is None) or (nrssi > orssi)


def _load_existing_orm(model, batch, key_fields, only_fields, base_filter):
    """Fallback: OR-chained Q() filters (works on all backends)."""
    cond = _build_q(batch, key_fields)
    qs = model.objects.filter(cond)
    if base_filter:
        qs = qs.filter(**base_filter)
    if only_fields:
        qs = qs.only(*only_fields)
    existing = {}
    for obj in qs:
        k = tuple(getattr(obj, f) for f in key_fields)
        existing[k] = obj
    return existing


def _load_existing_postgresql(model, batch, key_fields, only_fields, base_filter):
    """
    Use row IN ((a,b,c),...) for fewer planner surprises than long OR chains.
    """
    if not batch:
        return {}
    qn = connection.ops.quote_name
    db_table = qn(model._meta.db_table)
    only_fields = list(only_fields)
    col_names = [qn(model._meta.get_field(fn).column) for fn in only_fields]
    key_cols = [qn(model._meta.get_field(f).column) for f in key_fields]

    placeholders = ",".join(
        ["(" + ",".join(["%s"] * len(key_fields)) + ")"] * len(batch)
    )
    flat_params = [item for tup in batch for item in tup]

    where_parts = []
    params = []

    try:
        model._meta.get_field("deleted_at")
        where_parts.append(f"{qn('deleted_at')} IS NULL")
    except Exception:
        pass

    if base_filter:
        for k, v in base_filter.items():
            f = model._meta.get_field(k)
            where_parts.append(f"{qn(f.column)} = %s")
            params.append(v)

    where_parts.append(f"({', '.join(key_cols)}) IN ({placeholders})")
    params.extend(flat_params)

    sql = f"SELECT {', '.join(col_names)} FROM {db_table} WHERE {' AND '.join(where_parts)}"

    db_alias = router.db_for_write(model)
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    existing = {}
    for row in rows:
        obj = model.from_db(db_alias, only_fields, row)
        k = tuple(getattr(obj, f) for f in key_fields)
        existing[k] = obj
    return existing


def _load_existing_for_batch(model, batch, key_fields, only_fields, base_filter):
    if connection.vendor == "postgresql":
        return _load_existing_postgresql(
            model, batch, key_fields, only_fields, base_filter
        )
    return _load_existing_orm(model, batch, key_fields, only_fields, base_filter)


def _bulk_upsert_chunk(
    *,
    model,
    key_fields,
    best_by_key,
    better_obj_fn,
    better_row_fn,
    update_fields,
    only_fields,
    base_filter,
    chunk_size,
):
    """Run steps 2–4 for one transactional subset (already deduped)."""
    keys = list(best_by_key.keys())
    existing = {}

    t_sel0 = time.perf_counter()
    for i in range(0, len(keys), chunk_size):
        batch = keys[i : i + chunk_size]
        batch_existing = _load_existing_for_batch(
            model, batch, key_fields, only_fields, base_filter
        )
        existing.update(batch_existing)
    t_sel1 = time.perf_counter()

    to_create = []
    to_update = []

    t_cls0 = time.perf_counter()
    for k, row in best_by_key.items():
        obj = existing.get(k)
        if obj is None:
            to_create.append(model(**row))
        else:
            if better_obj_fn(row, obj):
                for f in update_fields:
                    if f in row and row[f] is not None:
                        setattr(obj, f, row[f])
                to_update.append(obj)
    t_cls1 = time.perf_counter()

    created = updated = 0
    t_wr0 = time.perf_counter()
    if to_create:
        model.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=1000)
        created = len(to_create)
    if to_update:
        model.objects.bulk_update(to_update, update_fields, batch_size=1000)
        updated = len(to_update)
    t_wr1 = time.perf_counter()

    ignored = max(0, len(best_by_key) - (created + updated))

    return created, updated, ignored, (t_sel1 - t_sel0, t_cls1 - t_cls0, t_wr1 - t_wr0)


def bulk_upsert_by_keys(
    *,
    model,
    key_fields,  # e.g. ['uploaded_by','mac','channel']
    rows,  # list[dict]
    better_obj_fn,  # (new_row:dict, old_obj:model)->bool
    better_row_fn=default_better_row_fn,
    update_fields=None,  # list[str]
    only_fields=None,  # list[str]
    base_filter=None,  # dict
    chunk_size=1000,
    transaction_chunk_size=5000,
    log_label=None,
):
    """
    Upsert rows by natural key. On PostgreSQL, existence lookups use row-IN instead of OR(Q).

    transaction_chunk_size: max keys per DB transaction (smaller = shorter locks). None = one transaction.
    log_label: optional prefix for INFO timing logs (dedupe / select / classify / write).
    """
    if not rows:
        return 0, 0, 0

    update_fields = update_fields or []

    t0 = time.perf_counter()
    best_by_key = _dedupe_keep_best(rows, key_fields, better_row_fn)
    t_dedupe = time.perf_counter() - t0
    all_keys = list(best_by_key.keys())
    nkeys = len(all_keys)

    if nkeys == 0:
        return 0, 0, 0

    tcs = (
        transaction_chunk_size
        if transaction_chunk_size is not None
        else nkeys
    )
    if tcs < 1:
        tcs = nkeys

    total_created = total_updated = total_ignored = 0
    sum_sel = sum_cls = sum_wr = 0.0

    for start in range(0, nkeys, tcs):
        subset_keys = all_keys[start : start + tcs]
        subset = {k: best_by_key[k] for k in subset_keys}
        with transaction.atomic():
            c, u, ign, (tsel, tcls, twr) = _bulk_upsert_chunk(
                model=model,
                key_fields=key_fields,
                best_by_key=subset,
                better_obj_fn=better_obj_fn,
                better_row_fn=better_row_fn,
                update_fields=update_fields,
                only_fields=only_fields,
                base_filter=base_filter,
                chunk_size=chunk_size,
            )
        total_created += c
        total_updated += u
        total_ignored += ign
        sum_sel += tsel
        sum_cls += tcls
        sum_wr += twr

    if logger.isEnabledFor(logging.INFO) and nkeys > 0:
        label = f"{log_label} " if log_label else ""
        logger.info(
            "%sbulk_upsert_by_keys model=%s keys=%d dedupe=%.3fs "
            "select=%.3fs classify=%.3fs write=%.3fs tx_chunks=%d chunk_size=%d",
            label,
            model.__name__,
            nkeys,
            t_dedupe,
            sum_sel,
            sum_cls,
            sum_wr,
            (nkeys + tcs - 1) // tcs,
            chunk_size,
        )

    return total_created, total_updated, total_ignored


# -----------------------------
# Shared helpers (used by apps.process)
# -----------------------------


def _parse_dt_aware(s: str):
    """Parse 'YYYY-MM-DD HH:MM:SS' into a timezone-aware datetime; return None on failure."""
    if not s:
        return None
    try:
        return make_aware(datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S"))
    except Exception:
        return None


def _to_int(s: str):
    """Convert string to int; return None when empty/invalid."""
    if s is None:
        return None
    s = str(s).strip()
    if s == "":
        return None
    try:
        return int(s)
    except Exception:
        return None


def _to_dec(s: str):
    """Convert string to Decimal; return None when empty/invalid."""
    if s is None:
        return None
    s = str(s).strip()
    if s == "":
        return None
    try:
        return Decimal(s)
    except Exception:
        return None
