"""
Marauder / Flipper / ESP32 Marauder firmware file processors.
Supports Flipper format (WiFi, BLE, mixed) and classic CSV format.
"""

import logging
import re
import time

from apps.core.regex import (
    LINE_RE_CLASSIC_MARAUDER,
    LINE_RE_FLIPPER_BLE,
    LINE_RE_FLIPPER_WIFI,
    LINE_RE_FLIPPER_WIFI_V3,
)
from apps.files.utils import (
    _parse_dt_aware,
    _to_dec,
    _to_int,
    bulk_upsert_by_keys,
    wardriving_better_obj_fn,
)
from apps.wardriving.models import Wardriving, SourceDevice

logger = logging.getLogger(__name__)

# Header fingerprints (line ~2 in common exports): v2 uses typo without space; v1 uses two words.
_HEADER_CLASSIC_V2 = "StartingWardrive"
_HEADER_INDEXED_V1 = "Starting Wardrive"

# parser_fn(line) must return None or an 11-tuple:
# (mac, ssid_or_name, auth_mode, first_seen, channel, rssi, lat, lon, alt, acc, data_type)
# first_seen is a string 'YYYY-MM-DD HH:MM:SS' or empty; core normalizes via _parse_dt_aware.

_SKIP_CONTAINS = (
    "stopscan",
    _HEADER_INDEXED_V1,
    _HEADER_CLASSIC_V2,
    "Starting Continuous BT Wardrive",
    "Started BLE Scan",
    "wifi:can not get wifi protocol",
)


_PREAMBLE_LINES = 50
_MAX_LINES_STYLE_DETECT = 200
_INDEXED_LINE_PREFIX = re.compile(r"^\s*(?:>\s*)?\d+\s*\|")

# `Device: name080:aa:..:mac,,[BLE],...` when MAC is glued to label (classic CSV).
_RE_BLE_DEVICE_MALFORMED = re.compile(
    r"^Device:\s*(.+?),\s*(.*?),\s*\[([^\]]*)\],\s*"
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"
    r"(\d+),\s*(-?\d+),\s*"
    r"(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*"
    r"(-?\d+(?:\.\d+)?),\s*(BLE|WIFI)\s*$",
    re.IGNORECASE,
)


def _should_skip_marauder_line(line: str) -> bool:
    """Return True if the line is metadata/noise and should not be parsed."""
    if not line:
        return True
    s = line.strip()
    if not s or s.startswith("#"):
        return True
    return any(x in s for x in _SKIP_CONTAINS)


def _parse_marauder_ble_device_malformed(line: str):
    """
    Parse classic-style line starting with 'Device:' where the first CSV field does not
    start with a bare MAC (name and MAC run together). Picks the last 6-octet MAC pattern.
    """
    m = _RE_BLE_DEVICE_MALFORMED.match(line.strip())
    if not m:
        return None
    (
        first_field,
        ssid_field,
        auth_mode,
        first_seen,
        channel,
        rssi,
        lat,
        lon,
        alt,
        acc,
        data_type,
    ) = m.groups()
    macs = re.findall(
        r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}", first_field, flags=re.IGNORECASE
    )
    if not macs:
        return None
    mac = macs[-1].lower()
    idx = first_field.lower().rfind(mac)
    name_prefix = (first_field[:idx].strip() if idx >= 0 else "").strip()
    ssid_or_name = name_prefix or (ssid_field or "").strip() or None
    return (
        mac,
        ssid_or_name,
        auth_mode,
        first_seen,
        channel,
        rssi,
        lat,
        lon,
        alt,
        acc,
        data_type,
    )


def _parse_marauder_wifi_line(line: str):
    """Parse a Marauder WiFi line; return tuple or None."""
    if _should_skip_marauder_line(line):
        return None
    s = line.strip()

    m = LINE_RE_FLIPPER_WIFI.match(s)
    if m:
        return m.groups()

    m = LINE_RE_FLIPPER_WIFI_V3.match(s)
    if not m:
        return None

    (
        mac,
        _dup_mac,
        ssid,
        first_seen,
        channel,
        rssi,
        lat,
        lon,
        alt,
        acc,
        data_type,
    ) = m.groups()
    return (
        mac,
        ssid,
        None,
        first_seen,
        channel,
        rssi,
        lat,
        lon,
        alt,
        acc,
        data_type,
    )


def _parse_marauder_ble_line(line: str):
    """Parse a Marauder BLE line; return normalized tuple or None."""
    if _should_skip_marauder_line(line):
        return None
    m = LINE_RE_FLIPPER_BLE.match(line.strip())
    if not m:
        return None
    (
        device_name,
        mac,
        _extra,
        auth_mode,
        first_seen,
        channel,
        rssi,
        lat,
        lon,
        alt,
        acc,
        data_type,
    ) = m.groups()
    ssid_or_name = (device_name or "").strip() or None
    return (
        mac,
        ssid_or_name,
        auth_mode,
        first_seen,
        channel,
        rssi,
        lat,
        lon,
        alt,
        acc,
        data_type,
    )


def _parse_marauder_line_classic(line: str):
    """
    Classic CSV (LINE_RE_CLASSIC_MARAUDER) or Device:-prefixed malformed BLE line.
    """
    if _should_skip_marauder_line(line):
        return None
    s = line.strip()
    m = LINE_RE_CLASSIC_MARAUDER.match(s)
    if m:
        return m.groups()
    if s.startswith("Device:"):
        return _parse_marauder_ble_device_malformed(s)
    return None


def _parse_marauder_line_flipper_indexed_chain(line: str):
    """BLE index format, then WiFi index/V3, then classic CSV as last resort."""
    return (
        _parse_marauder_ble_line(line)
        or _parse_marauder_wifi_line(line)
        or _parse_marauder_line_classic(line)
    )


def _detect_flipper_marauder_log_style(lines):
    """
    Return 'classic' (v2 CSV) or 'indexed' (v1 with 'N |').

    Phase A: preamble lines may contain StartingWardrive (v2) vs Starting Wardrive (v1).
    Phase B: first non-noise data line: classic regex, indexed prefix, or Flipper patterns.
    """
    preamble = lines[:_PREAMBLE_LINES]
    for line in preamble:
        s = line.strip()
        if not s:
            continue
        if _HEADER_CLASSIC_V2 in s:
            return "classic"
    for line in preamble:
        s = line.strip()
        if not s:
            continue
        if _HEADER_INDEXED_V1 in s:
            return "indexed"

    for line in lines[:_MAX_LINES_STYLE_DETECT]:
        if _should_skip_marauder_line(line):
            continue
        s = line.strip()
        if not s:
            continue
        if _INDEXED_LINE_PREFIX.match(s):
            return "indexed"
        if LINE_RE_CLASSIC_MARAUDER.match(s):
            return "classic"
        if (
            LINE_RE_FLIPPER_WIFI.match(s)
            or LINE_RE_FLIPPER_WIFI_V3.match(s)
            or LINE_RE_FLIPPER_BLE.match(s)
        ):
            return "indexed"
    return "indexed"


def _process_format_flipper_marauder_core(
    lines,
    parser_fn,
    device_source,
    uploaded_by,
):
    """
    Core processing loop: parse lines via parser_fn, normalize, validate, bulk upsert into Wardriving.

    parser_fn(line) -> None | (mac, ssid_or_name, auth_mode, first_seen, channel, rssi,
                              lat, lon, alt, acc, data_type)
    """
    t_parse0 = time.perf_counter()
    rows = []

    for line in lines:
        g = parser_fn(line)
        if not g:
            continue

        (
            mac,
            ssid_or_name,
            auth_mode,
            first_seen,
            channel,
            rssi,
            lat,
            lon,
            alt,
            acc,
            data_type,
        ) = g

        mac = (mac or "").strip().lower() or None
        ssid_or_name = (ssid_or_name or "").strip() or None
        auth_mode = (auth_mode or "").strip() or None
        data_type = (data_type or "").strip() or None

        first_seen = _parse_dt_aware(first_seen)
        channel = _to_int(channel)
        rssi = _to_int(rssi)
        lat = _to_dec(lat)
        lon = _to_dec(lon)
        alt = _to_dec(alt)
        acc = _to_dec(acc)

        if mac is None or channel is None or lat is None or lon is None:
            continue
        if lat == 0 and lon == 0:
            continue

        row = {
            "uploaded_by": uploaded_by,
            "mac": mac,
            "channel": channel,
            "ssid": ssid_or_name,
            "auth_mode": auth_mode,
            "first_seen": first_seen,
            "current_latitude": lat,
            "current_longitude": lon,
            "altitude_meters": alt,
            "accuracy_meters": acc,
            "type": data_type,
            "rssi": rssi,
            "device_source": device_source,
        }
        row = {k: v for k, v in row.items() if v is not None}
        rows.append(row)

    t_parse1 = time.perf_counter()
    if logger.isEnabledFor(logging.INFO):
        logger.info(
            "marauder_core parse=%.3fs lines_in=%d rows_out=%d",
            t_parse1 - t_parse0,
            len(lines),
            len(rows),
        )

    return bulk_upsert_by_keys(
        model=Wardriving,
        key_fields=["uploaded_by", "mac", "channel"],
        rows=rows,
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
        log_label="marauder",
    )


def process_format_flipper_marauder_wifi(
    lines=None,
    device_source=SourceDevice.FLIPPER_DEV_BOARD,
    uploaded_by="Without Owner",
):
    """Process Marauder Flipper-format WiFi lines."""
    lines = lines or []
    return _process_format_flipper_marauder_core(
        lines=lines,
        parser_fn=_parse_marauder_wifi_line,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )


def process_format_flipper_marauder_ble(
    lines=None,
    device_source=SourceDevice.FLIPPER_DEV_BOARD,
    uploaded_by="Without Owner",
):
    """Process Marauder Flipper-format BLE lines."""
    lines = lines or []
    return _process_format_flipper_marauder_core(
        lines=lines,
        parser_fn=_parse_marauder_ble_line,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )


def process_format_flipper_marauder_v2(
    lines=None,
    device_source=SourceDevice.FLIPPER_DEV_BOARD,
    uploaded_by="Without Owner",
):
    """
    Mixed Marauder output (BLE + WiFi). Detects classic CSV vs indexed Flipper format
    (header and/or first data lines), then runs the appropriate parser chain on all lines.
    """
    lines = lines or []
    style = _detect_flipper_marauder_log_style(lines)
    parser_fn = (
        _parse_marauder_line_classic
        if style == "classic"
        else _parse_marauder_line_flipper_indexed_chain
    )
    return _process_format_flipper_marauder_core(
        lines=lines,
        parser_fn=parser_fn,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )


def process_format_flipper_marauder(
    lines=None,
    device_source=SourceDevice.FLIPPER_DEV_BOARD,
    uploaded_by="Without Owner",
):
    """Process mixed Marauder output (BLE + WiFi). Delegates to process_format_flipper_marauder_v2."""
    return process_format_flipper_marauder_v2(
        lines=lines,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )


def process_format_classic_marauder(
    lines=None,
    device_source=SourceDevice.MARAUDER_V6,
    uploaded_by="Without Owner",
):
    """Process Marauder classic CSV format (no index)."""
    lines = lines or []
    return _process_format_flipper_marauder_core(
        lines=lines,
        parser_fn=_parse_marauder_line_classic,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )


def process_file_marauder_esp32(
    file_path="",
    device_source=SourceDevice.FLIPPER_DEV_BOARD,
    uploaded_by="Without Owner",
):
    """Entry point: process Marauder ESP32 / Flipper log file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            lines = f.readlines()

    esp32_class_process = {
        SourceDevice.FLIPPER_DEV_BOARD: process_format_flipper_marauder_v2,
        SourceDevice.FLIPPER_DEV_BOARD_PRO: process_format_flipper_marauder_v2,
        SourceDevice.KIISU: process_format_flipper_marauder_v2,
    }
    cls_process = esp32_class_process.get(
        device_source, process_format_classic_marauder
    )
    return cls_process(
        device_source=device_source, uploaded_by=uploaded_by, lines=lines
    )
