"""
Entry points for Marauder / Flipper / ESP32 Marauder file processing.

process_file_marauder_esp32  — main entry point (called from CHOICES_FUNCTION_PROCESS).
process_format_flipper_marauder_v2 — processes pre-read lines (also used in tests).

Pipeline:
  1. Read bytes / detect encoding.
  2. detect_dialect() → "csv_header" | "log_indexed" | "log_classic"
  3. Dispatch to csv_parser or log-line loop.
  4. persist_canonical_rows() → (new_added, updated, ignored).
"""

from __future__ import annotations

import logging

from apps.process._wigle_canonical.detect import detect_dialect
from apps.process._wigle_canonical.persist import persist_canonical_rows
from apps.process._wigle_canonical.schema import CanonicalRow, coerce_row
from apps.wardriving.models import SourceDevice

from .csv_parser import parse_csv_with_header
from .log_parsers import LOG_FORMAT_HEADER_MAP, parse_log_chain

logger = logging.getLogger(__name__)


def _process_log_lines(lines: list[str]) -> list[CanonicalRow]:
    """Convert raw log lines to CanonicalRow list using the chain parser."""
    rows: list[CanonicalRow] = []
    for line in lines:
        raw = parse_log_chain(line)
        if raw is None:
            continue
        canonical = coerce_row(raw, LOG_FORMAT_HEADER_MAP)
        if canonical is not None:
            rows.append(canonical)
    return rows


def process_format_flipper_marauder_v2(
    lines: list[str] | None = None,
    device_source: str = SourceDevice.FLIPPER_DEV_BOARD,
    uploaded_by: str = "Without Owner",
) -> tuple[int, int, int]:
    """
    Process pre-read Marauder log lines (mixed WiFi + BLE).
    Delegates: chain-parser → coerce_row → persist_canonical_rows.
    """
    canonical_rows = _process_log_lines(lines or [])
    return persist_canonical_rows(
        canonical_rows,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )


def process_file_marauder_esp32(
    file_path: str = "",
    device_source: str = SourceDevice.FLIPPER_DEV_BOARD,
    uploaded_by: str = "Without Owner",
) -> tuple[int, int, int]:
    """
    Entry point: process any Marauder ESP32 / Flipper file format.

    Supports:
    - Log formats: indexed (N | …), mixed WiFi+BLE, classic plain-CSV.
    - CSV-with-header formats: WigleWifi-1.1 … 1.4, Extended Timing, RF Extended,
      BLE/BT variants, BSSID alias, Capabilities / AuthMode / Encryption / AuthType.

    Encoding is auto-detected (UTF-8 → Latin-1 fallback).
    """
    encoding = "utf-8"
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
    except UnicodeDecodeError:
        encoding = "latin-1"
        with open(file_path, "r", encoding="latin-1") as fh:
            lines = fh.readlines()

    dialect = detect_dialect(lines)
    logger.debug("marauder_esp32 dialect=%s file=%s", dialect, file_path)

    if dialect == "csv_header":
        canonical_rows = parse_csv_with_header(file_path, encoding=encoding)
    else:
        canonical_rows = _process_log_lines(lines)

    return persist_canonical_rows(
        canonical_rows,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )
