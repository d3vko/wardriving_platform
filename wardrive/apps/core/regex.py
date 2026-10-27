"""
Centralized regex patterns for the project.
"""

import re

# -----------------------------
# Marauder / Flipper (apps.files)
# -----------------------------
#
# Two column layouts appear in the wild:
#   classic  — Channel,RSSI,Lat,Lon,Alt,Acc,Type
#   extended — Channel,Frequency,RSSI,Lat,Lon,Alt,Acc[,RCOIs,MfgrId],Type
# Extended is what ESP32 Marauder v1.19+ writes to wardrive_XX.log
# (WiGLE 1.6 dump, often without a header row). Frequency is a non-negative
# integer, so it does not collide with a typical negative RSSI in classic rows.

_GEO = (
    r"(-?\d+(?:\.\d+)?),\s*"  # lat
    r"(-?\d+(?:\.\d+)?),\s*"  # lon
    r"(-?\d+(?:\.\d+)?),\s*"  # alt
    r"(-?\d+(?:\.\d+)?)"  # acc
)
# Optional WiGLE 1.6 trailing RCOIs,MfgrId before Type.
_RCOIS_MFGRID = r"(?:,\s*[^,]*,\s*[^,]*)?"
_EXT_AFTER_CHANNEL = (
    r"(\d+),\s*"  # frequency
    r"(-?\d+),\s*"  # rssi
    + _GEO
    + _RCOIS_MFGRID
)
_CLASSIC_AFTER_CHANNEL = (
    r"(-?\d+),\s*"  # rssi
    + _GEO
)

# Flipper/Marauder WiFi format with index and auth_mode in brackets
LINE_RE_FLIPPER_WIFI = re.compile(
    r"^(?:>?\s*)?\d+\s*\|\s*"  # "1 |" with optional leading ">"
    r"([0-9A-Fa-f:]+),\s*"  # MAC/BSSID
    r"([^,]*),\s*"  # SSID
    r"\[([^\]]*)\],\s*"  # auth_mode
    r"((?:\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2})?)\s*,\s*"  # timestamp (optional)
    r"(\d+),\s*"  # channel
    + _CLASSIC_AFTER_CHANNEL
    + r",\s*(WIFI)$"
)

# Indexed WiFi + Frequency [+ RCOIs,MfgrId] (Marauder v1.19+ wardrive_XX.log)
LINE_RE_FLIPPER_WIFI_EXT = re.compile(
    r"^(?:>?\s*)?\d+\s*\|\s*"
    r"([0-9A-Fa-f:]+),\s*"
    r"([^,]*),\s*"
    r"\[([^\]]*)\],\s*"
    r"((?:\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2})?)\s*,\s*"
    r"(\d+),\s*"  # channel
    + _EXT_AFTER_CHANNEL
    + r",\s*(WIFI)$"
)

# Older wardrive_XX.log variant: no index, duplicated MAC, no AuthMode brackets
LINE_RE_FLIPPER_WIFI_V3 = re.compile(
    r"^(?:>?\s*)?"
    r"([0-9A-Fa-f:]+),\s*"  # MAC/BSSID
    r"([0-9A-Fa-f:]+),\s*"  # duplicated MAC/BSSID
    r"([^,]*),\s*"  # SSID (often empty)
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"  # timestamp
    r"(\d+),\s*"  # channel
    + _CLASSIC_AFTER_CHANNEL
    + r",\s*(WIFI)$"
)

# Flipper/Marauder BLE format (optional Device: prefix, glued name, dup MAC)
LINE_RE_FLIPPER_BLE = re.compile(
    r"^(?:>?\s*)?(?:Device:\s*)?"  # optional prefixes
    r"(?:(.*?)(?=(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}))?"  # device_name (optional)
    r"((?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})"  # MAC
    r"(?:(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})?"  # duplicated MAC (optional)
    r",\s*"
    r"([^,]*),\s*"  # extra field
    r"\[([^\]]*)\],\s*"  # auth_mode
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"  # timestamp
    r"(\d+),\s*"  # channel
    + _CLASSIC_AFTER_CHANNEL
    + r",\s*(BLE)$"
)

LINE_RE_FLIPPER_BLE_EXT = re.compile(
    r"^(?:>?\s*)?(?:Device:\s*)?"
    r"(?:(.*?)(?=(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}))?"
    r"((?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})"
    r"(?:(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})?"
    r",\s*"
    r"([^,]*),\s*"
    r"\[([^\]]*)\],\s*"
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"
    r"(\d+),\s*"  # channel
    + _EXT_AFTER_CHANNEL
    + r",\s*(BLE)$"
)

# Classic Marauder format (CSV without index): MAC, SSID, [auth], timestamp, channel, rssi, lat, lon, alt, acc, WIFI|BLE
LINE_RE_CLASSIC_MARAUDER = re.compile(
    r"^([0-9A-Fa-f:]+),\s*"  # MAC
    r"([^,]*),\s*"  # SSID
    r"\[([^\]]*)\],\s*"  # auth_mode
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"  # timestamp
    r"(\d+),\s*"  # channel
    + _CLASSIC_AFTER_CHANNEL
    + r",\s*(WIFI|BLE)$"
)

LINE_RE_CLASSIC_MARAUDER_EXT = re.compile(
    r"^([0-9A-Fa-f:]+),\s*"
    r"([^,]*),\s*"
    r"\[([^\]]*)\],\s*"
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"
    r"(\d+),\s*"  # channel
    + _EXT_AFTER_CHANNEL
    + r",\s*(WIFI|BLE)$"
)

# -----------------------------
# Vendors / IEEE OUI (apps.vendors)
# -----------------------------

# OUI line format: "28-6F-B9   (hex)     Nokia Shanghai Bell Co., Ltd."
HEX_LINE_RE = re.compile(
    r"^\s*([0-9A-Fa-f]{2}(?:-[0-9A-Fa-f]{2}){2})\s+\(hex\)\s+(.+?)\s*$"
)

# Blank line
BLANK_RE = re.compile(r"^\s*$")
