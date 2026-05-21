"""
Single persistence point: CanonicalRow list → Wardriving model via bulk upsert.

All processors (Marauder log, Marauder CSV, WigleWifi) funnel through here,
so the canonical → model field mapping lives in exactly one place.
"""

from __future__ import annotations

from apps.files.utils import bulk_upsert_by_keys, wardriving_better_obj_fn

from .schema import CanonicalRow


def _to_model_dict(row: CanonicalRow, device_source: str, uploaded_by: str) -> dict:
    d = {
        "uploaded_by": uploaded_by,
        "mac": row.mac,
        "channel": row.channel,
        "ssid": row.ssid,
        "auth_mode": row.security,
        "first_seen": row.first_seen,
        "current_latitude": row.latitude,
        "current_longitude": row.longitude,
        "altitude_meters": row.altitude,
        "accuracy_meters": row.accuracy,
        "type": row.type,
        "rssi": row.rssi,
        "device_source": device_source,
    }
    return {k: v for k, v in d.items() if v is not None}


def persist_canonical_rows(
    rows: list[CanonicalRow],
    device_source: str,
    uploaded_by: str,
) -> tuple[int, int, int]:
    """
    Persist a list of CanonicalRow into Wardriving via bulk upsert.
    Returns (new_added, updated, ignored).
    """
    from apps.wardriving.models import Wardriving

    model_rows = [_to_model_dict(r, device_source, uploaded_by) for r in rows]

    return bulk_upsert_by_keys(
        model=Wardriving,
        key_fields=["uploaded_by", "mac", "channel"],
        rows=model_rows,
        better_obj_fn=wardriving_better_obj_fn,
        update_fields=[
            "ssid",
            "auth_mode",
            "first_seen",
            "current_latitude",
            "current_longitude",
            "altitude_meters",
            "accuracy_meters",
            "type",
            "rssi",
            "device_source",
        ],
        only_fields=["id", "uploaded_by", "mac", "channel", "rssi"],
        chunk_size=1000,
        log_label="canonical",
    )
