"""
Centralized regex patterns for the project.
"""
import re

# -----------------------------
# Marauder / Flipper (apps.files)
# -----------------------------

# Flipper/Marauder WiFi format with index and auth_mode in brackets
# Timestamp may be empty (,,) on some firmware exports (v1 / Untitled-2 style).
LINE_RE_FLIPPER_WIFI = re.compile(
    r"^(?:>?\s*)?\d+\s*\|\s*"  # "1 |" with optional leading ">"
    r"([0-9A-Fa-f:]+),\s*"  # MAC/BSSID
    r"([^,]*),\s*"  # SSID
    r"\[([^\]]*)\],\s*"  # auth_mode
    r"((?:\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2})?)\s*,\s*"  # timestamp (optional)
    r"(\d+),\s*"  # channel
    r"(-?\d+),\s*"  # rssi
    r"(-?\d+(?:\.\d+)?),\s*"  # lat
    r"(-?\d+(?:\.\d+)?),\s*"  # lon
    r"(-?\d+(?:\.\d+)?),\s*"  # alt
    r"(-?\d+(?:\.\d+)?),\s*"  # acc
    r"(WIFI)$"  # Technology
)

# Flipper/Marauder wardrive_XX.log format (no index, duplicated MAC)
LINE_RE_FLIPPER_WIFI_V3 = re.compile(
    r"^(?:>?\s*)?"
    r"([0-9A-Fa-f:]+),\s*"  # MAC/BSSID
    r"([0-9A-Fa-f:]+),\s*"  # duplicated MAC/BSSID
    r"([^,]*),\s*"  # SSID (often empty)
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"  # timestamp
    r"(\d+),\s*"  # channel
    r"(-?\d+),\s*"  # rssi
    r"(-?\d+(?:\.\d+)?),\s*"  # lat
    r"(-?\d+(?:\.\d+)?),\s*"  # lon
    r"(-?\d+(?:\.\d+)?),\s*"  # alt
    r"(-?\d+(?:\.\d+)?),\s*"  # acc
    r"(WIFI)$"  # Technology
)

# Flipper/Marauder BLE format
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
    r"(-?\d+),\s*"  # rssi
    r"(-?\d+(?:\.\d+)?),\s*"  # lat
    r"(-?\d+(?:\.\d+)?),\s*"  # lon
    r"(-?\d+(?:\.\d+)?),\s*"  # alt
    r"(-?\d+(?:\.\d+)?),\s*"  # acc
    r"(BLE)$"  # Technology
)

# Classic Marauder format (CSV without index): MAC, SSID, [auth], timestamp, channel, rssi, lat, lon, alt, acc, WIFI|BLE
LINE_RE_CLASSIC_MARAUDER = re.compile(
    r"^([0-9A-Fa-f:]+),\s*"  # MAC
    r"([^,]*),\s*"  # SSID
    r"\[([^\]]*)\],\s*"  # auth_mode
    r"(\d{4}-\d{1,2}-\d{1,2} \d{2}:\d{2}:\d{2}),\s*"  # timestamp
    r"(\d+),\s*"  # channel
    r"(-?\d+),\s*"  # rssi
    r"(-?\d+(?:\.\d+)?),\s*"  # lat
    r"(-?\d+(?:\.\d+)?),\s*"  # lon
    r"(-?\d+(?:\.\d+)?),\s*"  # alt
    r"(-?\d+(?:\.\d+)?),\s*"  # acc
    r"(WIFI|BLE)$"  # Technology
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
