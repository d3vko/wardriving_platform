"""
Minino (Electronic Cats) device file processor.
"""
from datetime import datetime
from decimal import Decimal

from pandas import read_csv, to_datetime, isna, notna

from django.utils.timezone import make_aware, is_naive

from apps.files.utils import bulk_upsert_by_keys, wardriving_better_obj_fn
from apps.wardriving.models import Wardriving, SourceDevice


def process_file_minino(
    file_path="",
    device_source=SourceDevice.MININO,
    uploaded_by="Without Owner",
):
    """
    Process Minino CSV export.
    Header: MAC,SSID,AuthMode,FirstSeen,Channel,Frequency,RSSI,CurrentLatitude,...
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

        payload = {
            "uploaded_by": uploaded_by,
            "mac": mac,
            "channel": int(channel),
            "ssid": (row.get("ssid") or None),
            "auth_mode": (row.get("auth_mode") or None),
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
