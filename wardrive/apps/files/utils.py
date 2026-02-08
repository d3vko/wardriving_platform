import re
from decimal import Decimal
from datetime import datetime
from functools import reduce
from contextlib import contextmanager

from django.db import transaction
from django.db.models import Q
from django.utils.timezone import make_aware

from apps.core.services import get_redis_client


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


@transaction.atomic
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
):
    if not rows:
        return 0, 0, 0

    update_fields = update_fields or []

    # 1) In-memory deduplication: keep best candidate per key
    best_by_key = _dedupe_keep_best(rows, key_fields, better_row_fn)
    keys = list(best_by_key.keys())

    # 2) Load existing records in 1..N queries
    existing = {}
    for i in range(0, len(keys), chunk_size):
        batch = keys[i : i + chunk_size]
        cond = _build_q(batch, key_fields)
        qs = model.objects.filter(cond)
        if base_filter:
            qs = qs.filter(**base_filter)
        if only_fields:
            qs = qs.only(*only_fields)
        for obj in qs:
            k = tuple(getattr(obj, f) for f in key_fields)
            existing[k] = obj

    # 3) Classify for create/update
    to_create = []
    to_update = []

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

    # 4) Execute in bulk
    created = updated = 0
    if to_create:
        model.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=1000)
        created = len(to_create)
    if to_update:
        model.objects.bulk_update(to_update, update_fields, batch_size=1000)
        updated = len(to_update)

    ignored = max(0, len(best_by_key) - (created + updated))
    return created, updated, ignored


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
