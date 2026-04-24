"""
WigleWifi Mobile (Android) file processor.
"""

import re
from datetime import datetime
from decimal import Decimal

from pandas import read_csv, to_datetime, isna, notna

from django.utils.timezone import make_aware, is_naive

from apps.files.utils import bulk_upsert_by_keys, wardriving_better_obj_fn
from apps.wardriving.models import Wardriving, SourceDevice


def sanitize_auth_mode(raw):
    """
    Extract the primary auth mode from WigleWifi bracket notation.

    Examples:
        "[ESS]"                                      -> "ESS"
        "[WPA2-PSK-CCMP-128][RSN-PSK-CCMP-128][ESS]" -> "WPA2-PSK-CCMP-128"
        "[WPA2-EAP/SHA1-CCMP-128][RSN-...][ESS]"    -> "WPA2-EAP"
    """
    if not raw or not isinstance(raw, str):
        return raw
    tokens = re.findall(r"\[([^\]]+)\]", raw)
    if not tokens:
        return raw.strip() or None
    first = tokens[0]
    if "/" in first:
        first = first.split("/")[0]
    return first


def process_file_wiggle_mobile_wifi(
    file_path="",
    device_source=SourceDevice.WIGGLE_MOBILE_WIFI,
    uploaded_by="Without Owner",
):
    """
    Process WigleWifi Mobile CSV export.
    Line 1: metadata (WigleWifi-1.6,appRelease=...) — skipped via skiprows=1.
    Line 2: MAC,SSID,AuthMode,FirstSeen,Channel,Frequency,RSSI,CurrentLatitude,...
    """
    try:
        df = read_csv(file_path, encoding="utf-8", skiprows=1, on_bad_lines="skip")
    except UnicodeDecodeError:
        df = read_csv(file_path, encoding="latin-1", skiprows=1, on_bad_lines="skip")

    deleted_rows = ["Frequency", "RCOIs", "MfgrId"]
    renamed_headers = {
        "MAC": "mac",
        "SSID": "ssid",
        "AuthMode": "auth_mode",
        "FirstSeen": "first_seen",
        "Channel": "channel",
        "RSSI": "rssi",
        "CurrentLatitude": "current_latitude",
        "CurrentLongitude": "current_longitude",
        "AltitudeMeters": "altitude_meters",
        "AccuracyMeters": "accuracy_meters",
        "Type": "type",
    }

    df = df.drop(columns=[col for col in deleted_rows if col in df.columns])
    df.rename(columns=renamed_headers, inplace=True)

    if "first_seen" in df:
        fs = to_datetime(df["first_seen"], errors="coerce")
        df["first_seen"] = fs

    rows = []
    for _, row in df.iterrows():
        mac = row.get("mac")
        channel = row.get("channel")
        if isna(mac) or isna(channel):
            continue

        first_seen = row.get("first_seen")
        if isna(first_seen):
            first_seen = None
        elif hasattr(first_seen, "to_pydatetime"):
            first_seen = first_seen.to_pydatetime()
            if is_naive(first_seen):
                first_seen = make_aware(first_seen)
        elif isinstance(first_seen, datetime):
            if is_naive(first_seen):
                first_seen = make_aware(first_seen)

        rssi_val = int(row["rssi"]) if "rssi" in row and notna(row["rssi"]) else None

        raw_auth = row.get("auth_mode")
        auth_mode = sanitize_auth_mode(raw_auth) if notna(raw_auth) else None

        payload = {
            "uploaded_by": uploaded_by,
            "mac": mac,
            "channel": int(channel),
            "ssid": (row.get("ssid") or None),
            "auth_mode": auth_mode,
            "first_seen": first_seen,
            "current_latitude": (
                Decimal(row["current_latitude"])
                if notna(row.get("current_latitude"))
                else None
            ),
            "current_longitude": (
                Decimal(row["current_longitude"])
                if notna(row.get("current_longitude"))
                else None
            ),
            "altitude_meters": (
                Decimal(row["altitude_meters"])
                if notna(row.get("altitude_meters"))
                else None
            ),
            "accuracy_meters": (
                Decimal(row["accuracy_meters"])
                if notna(row.get("accuracy_meters"))
                else None
            ),
            "type": (row.get("type") or "WIFI"),
            "rssi": rssi_val,
            "device_source": device_source,
        }
        payload = {k: v for k, v in payload.items() if v is not None}
        rows.append(payload)

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
