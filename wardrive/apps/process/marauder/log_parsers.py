"""
Line-level parsers for Marauder/Flipper log formats.

All parse_* functions return a dict keyed by standard WiGLE column names
(MAC, SSID, AuthMode, FirstSeen, Channel, RSSI, CurrentLatitude, …)
or None if the line cannot be parsed.  The dict is fed into coerce_row()
with LOG_FORMAT_HEADER_MAP as the header_map.
"""

from __future__ import annotations

import re

from apps.core.regex import (
    LINE_RE_CLASSIC_MARAUDER,
    LINE_RE_FLIPPER_BLE,
    LINE_RE_FLIPPER_WIFI,
    LINE_RE_FLIPPER_WIFI_V3,
)

_SKIP_CONTAINS = (
    "stopscan",
    "Starting Wardrive",
    "StartingWardrive",
    "Starting Continuous BT Wardrive",
    "Started BLE Scan",
    "wifi:can not get wifi protocol",
)

# Matches 'Device: name<MAC>,...' where name and MAC are glued together
_RE_BLE_DEVICE_MALFORMED = re.compile(
    r"^Device:\s*(.+?),\s*(.*?),\s*\[([^\]]*)\],\s*"
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"
    r"(\d+),\s*(-?\d+),\s*"
    r"(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?),\s*"
    r"(-?\d+(?:\.\d+)?),\s*(BLE|WIFI)\s*$",
    re.IGNORECASE,
)


def _should_skip(line: str) -> bool:
    if not line:
        return True
    s = line.strip()
    if not s or s.startswith("#"):
        return True
    return any(x in s for x in _SKIP_CONTAINS)


def _make_row(
    mac, ssid, auth_mode, first_seen,
    channel, rssi, lat, lon, alt, acc, data_type,
) -> dict:
    """Build a raw dict keyed by standard WiGLE column names."""
    return {
        "MAC": mac,
        "SSID": ssid,
        "AuthMode": auth_mode,
        "FirstSeen": first_seen,
        "Channel": channel,
        "RSSI": rssi,
        "CurrentLatitude": lat,
        "CurrentLongitude": lon,
        "AltitudeMeters": alt,
        "AccuracyMeters": acc,
        "Type": data_type,
    }


# ---------------------------------------------------------------------------
# Public parsers
# ---------------------------------------------------------------------------


def parse_log_ble_device_malformed(line: str) -> dict | None:
    """
    Parse 'Device: name<MAC>,...' lines where device name and MAC run together.
    Picks the last 6-octet MAC pattern from the first CSV field.
    """
    m = _RE_BLE_DEVICE_MALFORMED.match(line.strip())
    if not m:
        return None
    (
        first_field, ssid_field, auth_mode, first_seen,
        channel, rssi, lat, lon, alt, acc, data_type,
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
    return _make_row(mac, ssid_or_name, auth_mode, first_seen, channel, rssi, lat, lon, alt, acc, data_type)


def parse_log_wifi(line: str) -> dict | None:
    """Parse a Marauder WiFi log line (indexed N| format or V3 duplicate-MAC format)."""
    if _should_skip(line):
        return None
    s = line.strip()

    m = LINE_RE_FLIPPER_WIFI.match(s)
    if m:
        mac, ssid, auth, ts, ch, rssi, lat, lon, alt, acc, dtype = m.groups()
        return _make_row(mac, ssid, auth, ts, ch, rssi, lat, lon, alt, acc, dtype)

    m = LINE_RE_FLIPPER_WIFI_V3.match(s)
    if not m:
        return None
    mac, _dup_mac, ssid, ts, ch, rssi, lat, lon, alt, acc, dtype = m.groups()
    return _make_row(mac, ssid, None, ts, ch, rssi, lat, lon, alt, acc, dtype)


def parse_log_ble(line: str) -> dict | None:
    """Parse a Marauder BLE log line (Device: prefix or bare MAC)."""
    if _should_skip(line):
        return None
    m = LINE_RE_FLIPPER_BLE.match(line.strip())
    if not m:
        return None
    (
        device_name, mac, _extra, auth_mode,
        first_seen, channel, rssi, lat, lon, alt, acc, data_type,
    ) = m.groups()
    ssid_or_name = (device_name or "").strip() or None
    return _make_row(mac, ssid_or_name, auth_mode, first_seen, channel, rssi, lat, lon, alt, acc, data_type)


def parse_log_classic(line: str) -> dict | None:
    """
    Classic CSV format (no index prefix): MAC, SSID, [auth], timestamp, channel, …
    Also handles 'Device:'-prefixed malformed BLE lines.
    """
    if _should_skip(line):
        return None
    s = line.strip()
    m = LINE_RE_CLASSIC_MARAUDER.match(s)
    if m:
        mac, ssid, auth, ts, ch, rssi, lat, lon, alt, acc, dtype = m.groups()
        return _make_row(mac, ssid, auth, ts, ch, rssi, lat, lon, alt, acc, dtype)
    if s.startswith("Device:"):
        return parse_log_ble_device_malformed(s)
    return None


def parse_log_chain(line: str) -> dict | None:
    """
    Try BLE → WiFi → classic CSV.
    Used for mixed-format logs (StartingWardrive sessions).
    """
    return parse_log_ble(line) or parse_log_wifi(line) or parse_log_classic(line)


# ---------------------------------------------------------------------------
# Standard header map for log-format rows (no CSV header in file)
# Result of resolve_headers(["MAC", "SSID", "AuthMode", ...])
# ---------------------------------------------------------------------------

LOG_FORMAT_HEADER_MAP: dict[str, str] = {
    "mac": "MAC",
    "ssid": "SSID",
    "security": "AuthMode",
    "first_seen": "FirstSeen",
    "channel": "Channel",
    "rssi": "RSSI",
    "latitude": "CurrentLatitude",
    "longitude": "CurrentLongitude",
    "altitude": "AltitudeMeters",
    "accuracy": "AccuracyMeters",
    "type": "Type",
}
