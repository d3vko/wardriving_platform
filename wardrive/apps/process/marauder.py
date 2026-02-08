"""
Marauder / Flipper / ESP32 Marauder firmware file processors.
Supports Flipper format (WiFi, BLE, mixed) and classic CSV format.
"""
from datetime import datetime
from decimal import Decimal

from django.utils.timezone import make_aware

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


_SKIP_CONTAINS = (
    "stopscan",
    "Starting Wardrive",
    "Starting Continuous BT Wardrive",
    "Started BLE Scan",
    "wifi:can not get wifi protocol",
)


def _should_skip_marauder_line(line: str) -> bool:
    """Return True if the line is metadata/noise and should not be parsed."""
    if not line:
        return True
    s = line.strip()
    if not s or s.startswith("#"):
        return True
    return any(x in s for x in _SKIP_CONTAINS)


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


def _process_format_flipper_marauder_core(
    lines,
    parser_fn,
    device_source,
    uploaded_by,
):
    """
    Core processing loop: parse lines via parser_fn, normalize, validate, bulk upsert into Wardriving.
    """
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


def process_format_flipper_marauder(
    lines=None,
    device_source=SourceDevice.FLIPPER_DEV_BOARD,
    uploaded_by="Without Owner",
):
    """Process mixed Marauder output (BLE + WiFi). Tries BLE first, then WiFi."""
    lines = lines or []

    def _auto_parser(line: str):
        return _parse_marauder_ble_line(line) or _parse_marauder_wifi_line(line)

    return _process_format_flipper_marauder_core(
        lines=lines,
        parser_fn=_auto_parser,
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
    rows = []
    for line in lines:
        if line.startswith("#") or "stopscan" in line or "Starting Wardrive" in line:
            continue
        m = LINE_RE_CLASSIC_MARAUDER.match(line.strip())
        if not m:
            continue
        (
            mac,
            ssid,
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

        ssid = ssid or None
        if first_seen:
            try:
                first_seen = make_aware(
                    datetime.strptime(first_seen, "%Y-%m-%d %H:%M:%S")
                )
            except Exception:
                first_seen = None
        if isinstance(first_seen, str):
            first_seen = None

        try:
            channel = int(channel) if channel and channel.isdigit() else None
            rssi = int(rssi) if rssi not in (None, "") else None
            lat = Decimal(lat) if lat else None
            lon = Decimal(lon) if lon else None
            alt = Decimal(alt) if alt else None
            acc = Decimal(acc) if acc else None
        except Exception:
            continue

        if channel is None or (lat == 0 and lon == 0):
            continue

        row = {
            "uploaded_by": uploaded_by,
            "mac": mac,
            "channel": channel,
            "ssid": ssid,
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
        SourceDevice.FLIPPER_DEV_BOARD: process_format_flipper_marauder,
        SourceDevice.FLIPPER_DEV_BOARD_PRO: process_format_flipper_marauder,
        SourceDevice.KIISU: process_format_flipper_marauder,
    }
    cls_process = esp32_class_process.get(
        device_source, process_format_classic_marauder
    )
    return cls_process(
        device_source=device_source, uploaded_by=uploaded_by, lines=lines
    )
