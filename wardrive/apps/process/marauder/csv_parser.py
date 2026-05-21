"""
CSV-with-header parser for Marauder/WiGLE CSV variants.

Supports all known header permutations (WigleWifi-1.1 … 1.4, Extended Timing,
RF Extended, BLE/BT variants, BSSID alias, Capabilities vs AuthMode, etc.)
by delegating header resolution to _wigle_canonical.aliases.resolve_headers.

Files may start with a WiGLE metadata line (e.g. 'WigleWifi-1.6,appRelease=…')
or directly with the header row.  _find_header_skiprows() locates the header
row automatically so no version-specific skip-count is hardcoded.
"""

from __future__ import annotations

import logging

from pandas import read_csv

from apps.process._wigle_canonical.aliases import HEADER_ALIASES, resolve_headers
from apps.process._wigle_canonical.schema import CanonicalRow, coerce_row

logger = logging.getLogger(__name__)


def _find_header_skiprows(file_path: str, encoding: str) -> int:
    """
    Scan the first 20 lines and return the 0-based line index of the CSV header row.
    That index equals the `skiprows` value for pandas (rows to skip before the header).

    A line is considered a header when it contains ≥3 known WiGLE column tokens.
    Returns 0 (no skip) if no explicit header is found.
    """
    try:
        with open(file_path, "r", encoding=encoding, errors="replace") as fh:
            for i, line in enumerate(fh):
                if i >= 20:
                    break
                parts = [p.strip() for p in line.strip().split(",")]
                known = sum(1 for p in parts if p in HEADER_ALIASES)
                if known >= 3:
                    return i
    except OSError:
        pass
    return 0


def parse_csv_with_header(
    file_path: str,
    encoding: str = "utf-8",
) -> list[CanonicalRow]:
    """
    Parse a Marauder/WiGLE CSV file that has a column-header row.

    Handles:
    - WiGLE metadata line before the header (skiprows auto-detected).
    - Any combination of MAC/BSSID/netid, AuthMode/Capabilities/Encryption/AuthType,
      with or without Frequency/LastSeen columns.
    - BLE rows (Type=BLE) alongside WiFi rows.

    Returns a list of CanonicalRow (already type-coerced); invalid/incomplete rows
    are silently dropped.
    """
    skiprows = _find_header_skiprows(file_path, encoding)
    try:
        df = read_csv(
            file_path,
            encoding=encoding,
            skiprows=skiprows,
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        )
    except Exception as exc:
        logger.warning("csv_parser: failed to read %s: %s", file_path, exc)
        return []

    if df.empty:
        return []

    header_map = resolve_headers(list(df.columns))

    if not header_map.get("mac") or not header_map.get("channel"):
        logger.warning(
            "csv_parser: required columns (mac/channel) not found in %s. "
            "Available columns: %s",
            file_path,
            list(df.columns),
        )
        return []

    rows: list[CanonicalRow] = []
    for _, pandas_row in df.iterrows():
        canonical = coerce_row(pandas_row.to_dict(), header_map)
        if canonical is not None:
            rows.append(canonical)

    return rows
