"""
Header alias resolver for WiGLE CSV variants.

Maps any observed column header to its canonical field name.
Capability detection: winner is determined by _PRIORITY_ORDER, never by version string.
Priority for security: Capabilities > AuthMode > Encryption > AuthType.
Priority for latitude: CurrentLatitude > Latitude > trilat.
Priority for longitude: CurrentLongitude > Longitude > trilong.
"""

# Maps any observed header name → canonical field name.
HEADER_ALIASES: dict[str, str] = {
    # MAC
    "MAC": "mac",
    "BSSID": "mac",
    "netid": "mac",
    # SSID
    "SSID": "ssid",
    "ssid": "ssid",
    # Security — Capabilities wins over AuthMode wins over Encryption/AuthType
    "Capabilities": "security",
    "AuthMode": "security",
    "Encryption": "security",
    "AuthType": "security",
    # First timestamp
    "FirstSeen": "first_seen",
    "first_seen": "first_seen",
    "firsttime": "first_seen",
    # Last timestamp (Extended Timing variant)
    "LastSeen": "last_seen",
    "last_seen": "last_seen",
    # Channel
    "Channel": "channel",
    "channel": "channel",
    # Frequency (capability-detected: present only in Extended variants)
    "Frequency": "frequency",
    "frequency": "frequency",
    # RSSI
    "RSSI": "rssi",
    "rssi": "rssi",
    # Latitude
    "CurrentLatitude": "latitude",
    "Latitude": "latitude",
    "trilat": "latitude",
    # Longitude
    "CurrentLongitude": "longitude",
    "Longitude": "longitude",
    "trilong": "longitude",
    # Altitude
    "AltitudeMeters": "altitude",
    "Altitude": "altitude",
    # Accuracy
    "AccuracyMeters": "accuracy",
    "Accuracy": "accuracy",
    # Radio type (WIFI, BLE, BT)
    "Type": "type",
    "type": "type",
}

# Defines winner when multiple source headers resolve to the same canonical.
_PRIORITY_ORDER = [
    # mac
    "MAC", "BSSID", "netid",
    # security
    "Capabilities", "AuthMode", "Encryption", "AuthType",
    # latitude
    "CurrentLatitude", "Latitude", "trilat",
    # longitude
    "CurrentLongitude", "Longitude", "trilong",
    # first_seen
    "FirstSeen", "first_seen", "firsttime",
    # last_seen
    "LastSeen", "last_seen",
    # no conflict expected below
    "SSID", "ssid",
    "Channel", "channel",
    "Frequency", "frequency",
    "RSSI", "rssi",
    "AltitudeMeters", "Altitude",
    "AccuracyMeters", "Accuracy",
    "Type", "type",
]

_PRIORITY: dict[str, int] = {h: i for i, h in enumerate(_PRIORITY_ORDER)}


def resolve_headers(headers: list[str]) -> dict[str, str]:
    """
    Given a list of CSV column names (in file order), return a dict
    mapping  canonical_name -> winning_source_column.

    Uses _PRIORITY_ORDER so that, e.g., "Capabilities" always beats "AuthMode"
    when both are present — no version-string logic needed.
    """
    mapping: dict[str, str] = {}
    for h in sorted(headers, key=lambda x: _PRIORITY.get(x, 9999)):
        canonical = HEADER_ALIASES.get(h)
        if canonical and canonical not in mapping:
            mapping[canonical] = h
    return mapping
