"""
Dialect detection for WiGLE/Marauder files.

Detects by *capability* (presence of fields), never by version strings.
Returns one of: "csv_header", "log_indexed", "log_classic".
"""

from __future__ import annotations

import re
from typing import Literal

from apps.core.regex import (
    LINE_RE_CLASSIC_MARAUDER,
    LINE_RE_FLIPPER_BLE,
    LINE_RE_FLIPPER_WIFI,
    LINE_RE_FLIPPER_WIFI_V3,
)
from .aliases import HEADER_ALIASES

_INDEXED_LINE_PREFIX = re.compile(r"^\s*(?:>?\s*)?\d+\s*\|")

# Known header tokens for CSV header detection
_KNOWN_HEADER_TOKENS: frozenset[str] = frozenset(HEADER_ALIASES.keys())
_MIN_HEADER_TOKENS = 3

_PREAMBLE_LINES = 50
_MAX_LINES_STYLE_DETECT = 200

_SESSION_MARKERS = ("StartingWardrive", "Starting Wardrive")
_SKIP_CONTAINS = (
    "stopscan",
    "Starting Wardrive",
    "StartingWardrive",
    "Starting Continuous BT Wardrive",
    "Started BLE Scan",
    "wifi:can not get wifi protocol",
)


def _is_header_line(line: str) -> bool:
    """Return True if the line looks like a CSV header row (≥3 known column tokens)."""
    s = line.strip()
    if not s or s.startswith("#"):
        return False
    parts = [p.strip() for p in s.split(",")]
    matches = sum(1 for p in parts if p in _KNOWN_HEADER_TOKENS)
    return matches >= _MIN_HEADER_TOKENS


def _is_metadata_line(line: str) -> bool:
    """Return True for WiGLE app metadata lines like 'WigleWifi-1.6,appRelease=...'"""
    s = line.strip()
    return bool(s and (s.startswith("WigleWifi") or s.startswith("WiGL")))


def detect_dialect(
    sample_lines: list[str],
) -> Literal["csv_header", "log_indexed", "log_classic"]:
    """
    Detect file dialect from the first lines.

    Phase A: session-start markers (StartingWardrive / Starting Wardrive) → log_indexed.
    Phase B: first meaningful non-metadata line is a CSV header row → csv_header.
    Phase C: scan data lines for indexed prefix / Flipper patterns / classic MAC pattern.
    Default: log_indexed.
    """
    preamble = sample_lines[:_PREAMBLE_LINES]

    # Phase A: session markers always mean indexed log
    for line in preamble:
        s = line.strip()
        if not s:
            continue
        if any(marker in s for marker in _SESSION_MARKERS):
            return "log_indexed"

    # Phase B: CSV header detection
    # Scan preamble; skip comments and WiGLE metadata lines.
    # Break as soon as the first real data line is encountered (it's not a header).
    for line in preamble:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if _is_metadata_line(s):
            continue
        if _is_header_line(s):
            return "csv_header"
        # First meaningful, non-metadata line is not a header → it's a data/log file
        break

    # Phase C: classify by first parseable data line
    for line in sample_lines[:_MAX_LINES_STYLE_DETECT]:
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if any(x in s for x in _SKIP_CONTAINS):
            continue
        if _INDEXED_LINE_PREFIX.match(s):
            return "log_indexed"
        if (
            LINE_RE_FLIPPER_WIFI.match(s)
            or LINE_RE_FLIPPER_WIFI_V3.match(s)
            or LINE_RE_FLIPPER_BLE.match(s)
        ):
            return "log_indexed"
        if LINE_RE_CLASSIC_MARAUDER.match(s):
            return "log_classic"
        if s.startswith("Device:"):
            return "log_classic"

    return "log_indexed"
