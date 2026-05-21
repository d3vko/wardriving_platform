"""
Marauder / Flipper / ESP32 Marauder file processor package.

Public API (stable):
  process_file_marauder_esp32     — called from CHOICES_FUNCTION_PROCESS
  process_format_flipper_marauder_v2 — used in tests / direct calls

Internal parsers (may change between releases):
  parse_log_wifi / parse_log_ble / parse_log_classic / parse_log_ble_device_malformed
  parse_log_chain
  detect_dialect
"""

from .detect import detect_dialect
from .entrypoint import process_file_marauder_esp32, process_format_flipper_marauder_v2
from .log_parsers import (
    parse_log_ble,
    parse_log_ble_device_malformed,
    parse_log_chain,
    parse_log_classic,
    parse_log_wifi,
)

__all__ = [
    # stable public API
    "process_file_marauder_esp32",
    "process_format_flipper_marauder_v2",
    # detection
    "detect_dialect",
    # line parsers (internal, exported for tests)
    "parse_log_wifi",
    "parse_log_ble",
    "parse_log_classic",
    "parse_log_ble_device_malformed",
    "parse_log_chain",
]
