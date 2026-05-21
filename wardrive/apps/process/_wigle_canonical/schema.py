"""
Canonical row schema and type coercion for WiGLE CSV variants.

CanonicalRow is the internal representation shared by all processors.
coerce_row() converts a raw string dict + header_map into a CanonicalRow or None.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from apps.files.utils import _parse_dt_aware, _to_dec, _to_int

from .sanitizers import sanitize_security

REQUIRED_FIELDS = frozenset({"mac", "channel", "latitude", "longitude"})
VALID_TYPES = frozenset({"WIFI", "BLE", "BT"})

# Strings that pandas or other sources produce for missing/null values.
# We treat all of these as None throughout the pipeline.
_MISSING_SENTINELS = frozenset({
    "", "nan", "NaN", "NaT", "None", "none", "null", "NULL", "<NA>",
})


@dataclass
class CanonicalRow:
    # Required fields
    mac: str
    channel: int
    latitude: Decimal
    longitude: Decimal
    # Optional fields
    ssid: Optional[str] = None
    security: Optional[str] = None
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    frequency: Optional[int] = None
    rssi: Optional[int] = None
    altitude: Optional[Decimal] = None
    accuracy: Optional[Decimal] = None
    type: str = "WIFI"
    source_format: str = ""
    source_version: str = ""


def coerce_row(raw: dict, header_map: dict[str, str]) -> Optional[CanonicalRow]:
    """
    Build a CanonicalRow from a raw dict keyed by *source* column names.

    header_map: canonical_name -> source_column_name (from resolve_headers).
    Returns None when any required field is missing/invalid, or lat == lon == 0.

    Handles string values (from log parsers or dtype=str CSV reads) as well as
    mixed pandas types (float NaN appears as "nan" after str()).

    SSID contract: always None (never empty string) when the cell is blank,
    whitespace-only, or any missing sentinel.
    Security contract: always returned without enclosing brackets — sanitize_security
    strips [TOKEN1][TOKEN2] notation automatically for both CSV and log inputs.
    """

    def get(canonical: str) -> Optional[str]:
        src_col = header_map.get(canonical)
        if src_col is None:
            return None
        val = raw.get(src_col)
        if val is None:
            return None
        s = str(val).strip()
        # Discard any missing/null sentinel, including whitespace-only strings
        if not s or s in _MISSING_SENTINELS:
            return None
        return s

    mac_raw = get("mac")
    mac = mac_raw.lower() if mac_raw else None
    channel = _to_int(get("channel"))
    lat = _to_dec(get("latitude"))
    lon = _to_dec(get("longitude"))

    if not mac or channel is None or lat is None or lon is None:
        return None
    if lat == 0 and lon == 0:
        return None

    type_raw = (get("type") or "WIFI").strip().upper()
    if type_raw not in VALID_TYPES:
        type_raw = "WIFI"

    # ssid: None when blank/whitespace/sentinel (get() already guarantees this)
    ssid = get("ssid") or None

    # security: normalize brackets and slashes regardless of source format
    security = sanitize_security(get("security"))

    return CanonicalRow(
        mac=mac,
        channel=channel,
        latitude=lat,
        longitude=lon,
        ssid=ssid,
        security=security,
        first_seen=_parse_dt_aware(get("first_seen")),
        last_seen=_parse_dt_aware(get("last_seen")),
        frequency=_to_int(get("frequency")),
        rssi=_to_int(get("rssi")),
        altitude=_to_dec(get("altitude")),
        accuracy=_to_dec(get("accuracy")),
        type=type_raw,
    )
