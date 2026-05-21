"""
Minino (Electronic Cats) and PwnTerrey Marauder file processor.

Uses the shared canonical pipeline:
  resolve_headers → coerce_row → persist_canonical_rows

coerce_row() handles automatically:
  - auth_mode bracket sanitization: [WPA2-PSK-CCMP][ESS] → "WPA2-PSK-CCMP"
  - SSID empty / whitespace / "nan" sentinel → None
  - Type normalization (WIFI, BLE, BT)

dtype=str + keep_default_na=False prevent pandas from silently converting
empty cells to float NaN which would later be stored as the string "nan".
"""

from __future__ import annotations

import logging

from pandas import read_csv

from apps.process._wigle_canonical.aliases import resolve_headers
from apps.process._wigle_canonical.persist import persist_canonical_rows
from apps.process._wigle_canonical.schema import CanonicalRow, coerce_row
from apps.wardriving.models import SourceDevice

logger = logging.getLogger(__name__)


def process_file_minino(
    file_path: str = "",
    device_source: str = SourceDevice.MININO,
    uploaded_by: str = "Without Owner",
) -> tuple[int, int, int]:
    """
    Process Minino / PwnTerrey Marauder CSV export.

    Line 1: metadata (WigleWifi-style or device header) — skipped via skiprows=1.
    Line 2: column headers (MAC, SSID, AuthMode, FirstSeen, Channel, …).

    Supports alias variants via resolve_headers() (BSSID, Capabilities, etc.)
    and applies sanitize_security() automatically through coerce_row().
    """
    try:
        df = read_csv(
            file_path,
            encoding="utf-8",
            skiprows=1,
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        )
    except UnicodeDecodeError:
        df = read_csv(
            file_path,
            encoding="latin-1",
            skiprows=1,
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        )

    if df.empty:
        return 0, 0, 0

    header_map = resolve_headers(list(df.columns))

    if not header_map.get("mac") or not header_map.get("channel"):
        logger.warning(
            "minino: required columns (mac/channel) not found. "
            "Available: %s",
            list(df.columns),
        )
        return 0, 0, 0

    canonical_rows: list[CanonicalRow] = []
    for _, pandas_row in df.iterrows():
        canonical = coerce_row(pandas_row.to_dict(), header_map)
        if canonical is not None:
            canonical_rows.append(canonical)

    return persist_canonical_rows(
        canonical_rows,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )
