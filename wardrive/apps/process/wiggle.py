"""
WigleWifi Mobile (Android) file processor.

Uses the shared canonical pipeline:
  resolve_headers → coerce_row → persist_canonical_rows

coerce_row() already calls sanitize_security() internally, so bracket notation
([WPA2-PSK-CCMP][ESS]) is stripped automatically — no pre-processing needed here.

Supports any WiGLE CSV variant (1.1 … 1.4, Extended Timing, RF Extended)
via alias resolution instead of hard-coded column renames.
"""

from __future__ import annotations

import logging

from pandas import read_csv

from apps.process._wigle_canonical.aliases import resolve_headers
from apps.process._wigle_canonical.persist import persist_canonical_rows
from apps.process._wigle_canonical.sanitizers import sanitize_security as sanitize_auth_mode  # re-export compat
from apps.process._wigle_canonical.schema import CanonicalRow, coerce_row
from apps.wardriving.models import SourceDevice

logger = logging.getLogger(__name__)


def process_file_wiggle_mobile_wifi(
    file_path: str = "",
    device_source: str = SourceDevice.WIGGLE_MOBILE_WIFI,
    uploaded_by: str = "Without Owner",
) -> tuple[int, int, int]:
    """
    Process WigleWifi Mobile CSV export.

    Line 1: WiGLE metadata ('WigleWifi-1.6,appRelease=…') — skipped via skiprows=1.
    Line 2: column headers (MAC or BSSID, SSID, AuthMode or Capabilities, …).

    Uses resolve_headers() for alias resolution, so files with BSSID, Capabilities,
    or any other known variant are handled without version-specific logic.
    Security bracket sanitization is handled inside coerce_row() automatically.
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
            "wiggle: required columns (mac/channel) not found. "
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
