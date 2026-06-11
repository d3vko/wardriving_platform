"""
RF custom firmware (Lilygo T-SIM7000G) processors: LTE and WiFi wardriving.
"""

import csv

from pandas import DataFrame, read_csv, to_datetime, to_numeric, isna, notna
from pandas.errors import ParserError

from django.utils.timezone import is_naive, make_aware, now
from datetime import datetime

from apps.files.utils import bulk_upsert_by_keys, wardriving_better_obj_fn
from apps.wardriving.models import LTEWardriving, Wardriving, SourceDevice


def process_lte_wardriving(
    device_source=SourceDevice.RF_CUSTOM_FIRMWARE_LTE,
    uploaded_by="Without Owner",
    dataframe=None,
):
    """
    Process LTE wardriving CSV from Lilygo T-SIM7000G or Android scanner apps.

    Accepts both Spanish (RF firmware) and English (Android) column names:
      Spanish: Timestamp, Tecnología, Estado, MCC, MNC, LAC, CellID, Banda,
               RSSI, RSRP, RSRQ, SINR, Operador, Longitud, Latitud
      English: Timestamp, Technology, State, MCC, MNC, LAC, CellID, Band,
               RSSI, RSRP, RSRQ, SINR, Operator, Longitude, Latitude

    Placeholder / unserved-cell rows are filtered out before upsert:
      - CellID == 268435455  (0x0FFFFFFF sentinel for "no cell")
      - LAC    == 65535      (0xFFFF sentinel for "no LAC")
      - MCC    == 0          (invalid country code)
      - Rows with empty Latitude or Longitude (no GPS fix)
    """
    dataframe = dataframe if dataframe is not None else DataFrame()
    if dataframe.empty:
        return 0, 0, 0

    # Drop columns that carry no model-relevant data (both languages)
    pop_keys = ["Timestamp", "Estado", "State"]
    renamed_keys = {
        # Spanish → canonical
        "Tecnología": "tech",
        "CellID": "cell_id",
        "Banda": "band",
        "Operador": "provider",
        "Longitud": "current_longitude",
        "Latitud": "current_latitude",
        # English → canonical (Android)
        "Technology": "tech",
        "Band": "band",
        "Operator": "provider",
        "Longitude": "current_longitude",
        "Latitude": "current_latitude",
    }
    downcase_keys = ["MCC", "MNC", "LAC", "RSSI", "RSRP", "RSRQ", "SINR"]

    for key in pop_keys:
        if key in dataframe.columns:
            dataframe.pop(key)
    dataframe.rename(columns=renamed_keys, inplace=True)
    for key in downcase_keys:
        if key in dataframe.columns:
            dataframe[key.lower()] = dataframe.pop(key)

    dataframe["rssi"] = (
        dataframe["rssi"].astype(str).str.replace(" dBm", "", regex=False).str.strip()
    )
    dataframe["rssi"] = to_numeric(dataframe["rssi"], errors="coerce")
    dataframe = dataframe.dropna(subset=["rssi"]).reset_index(drop=True)
    dataframe["rssi"] = dataframe["rssi"].astype(int)
    dataframe["provider"] = dataframe["provider"].fillna("Not Provided")

    # Coerce key identifier columns to numeric so sentinel comparisons work
    # regardless of whether the CSV was read as str or int.
    for _col in ("cell_id", "lac", "mcc"):
        if _col in dataframe.columns:
            dataframe[_col] = to_numeric(dataframe[_col], errors="coerce")

    # Filter placeholder / unserved-cell rows:
    #   CellID 268435455 (0x0FFFFFFF) — no cell locked
    #   LAC    65535     (0xFFFF)     — no LAC
    #   MCC    0         — invalid country code
    #   Missing lat/lon  — no GPS fix
    if "cell_id" in dataframe.columns:
        dataframe = dataframe[dataframe["cell_id"] != 268435455]
    if "lac" in dataframe.columns:
        dataframe = dataframe[dataframe["lac"] != 65535]
    if "mcc" in dataframe.columns:
        dataframe = dataframe[dataframe["mcc"] != 0]
    for _coord in ("current_latitude", "current_longitude"):
        if _coord in dataframe.columns:
            dataframe[_coord] = to_numeric(dataframe[_coord], errors="coerce")
            dataframe = dataframe.dropna(subset=[_coord])

    dataframe = dataframe.reset_index(drop=True)
    if dataframe.empty:
        return 0, 0, 0

    rows = []
    for instance_data in dataframe.to_dict(orient="records"):
        if not instance_data.get("cell_id"):
            continue
        row = {
            "uploaded_by": uploaded_by,
            "device_source": device_source,
            "tech": instance_data.get("tech"),
            "mcc": instance_data.get("mcc"),
            "mnc": instance_data.get("mnc"),
            "lac": instance_data.get("lac"),
            "cell_id": instance_data.get("cell_id"),
            "first_seen": now(),
            "rssi": instance_data.get("rssi"),
            "rsrp": instance_data.get("rsrp"),
            "rsrq": instance_data.get("rsrq"),
            "sinr": instance_data.get("sinr"),
            "band": instance_data.get("band"),
            "provider": instance_data.get("provider") or "Not Provided",
            "current_longitude": instance_data.get("current_longitude"),
            "current_latitude": instance_data.get("current_latitude"),
        }
        row = {k: v for k, v in row.items() if v is not None}
        rows.append(row)

    return bulk_upsert_by_keys(
        model=LTEWardriving,
        key_fields=[
            "uploaded_by",
            "device_source",
            "tech",
            "mcc",
            "mnc",
            "lac",
            "cell_id",
        ],
        rows=rows,
        better_obj_fn=wardriving_better_obj_fn,
        update_fields=[
            "first_seen",
            "rssi",
            "rsrp",
            "rsrq",
            "sinr",
            "band",
            "provider",
            "current_longitude",
            "current_latitude",
        ],
        only_fields=[
            "id",
            "uploaded_by",
            "device_source",
            "tech",
            "mcc",
            "mnc",
            "lac",
            "cell_id",
            "rssi",
        ],
        chunk_size=1000,
    )


def _strip_column_names(df: DataFrame) -> None:
    df.columns = [str(c).strip().lstrip("\ufeff").strip() for c in df.columns]


def _rf_wifi_csv_has_core_columns(df: DataFrame) -> bool:
    """True if the DataFrame looks like a LilyGo WiFi export / English / Minino."""
    if df is None or df.empty:
        return True
    tmp = df.copy()
    _strip_column_names(tmp)
    mac = _first_series(tmp, "BSSID", "MAC", "mac")
    channel = _first_series(tmp, "Canal", "Channel", "channel")
    rssi = _first_series(
        tmp,
        "Señal",
        "Senal",
        "RSSI",
        "rssi",
        "Signal",
        "signal",
    )
    return mac is not None and channel is not None and rssi is not None


def _first_series(df: DataFrame, *candidates):
    """Return the first existing column as a Series, or None."""
    for name in candidates:
        if name in df.columns:
            return df[name]
    return None


def _read_wifi_csv_robust(file_path: str, encoding: str) -> DataFrame:
    """
    Read LilyGo-style 8-column WiFi CSV. Uses csv.reader (quoted commas OK).
    If a row has >8 fields, assumes unquoted commas in SSID and merges fields
    3..-5 into SSID (Timestamp, Lat, Long, SSID, BSSID, Canal, Señal, Seguridad).
    """
    rows = []
    with open(file_path, "r", encoding=encoding, newline="") as handle:
        reader = csv.reader(handle)
        for row in reader:
            if not row or all(not (c or "").strip() for c in row):
                continue
            if len(row) == 8:
                rows.append(row)
            elif len(row) > 8:
                fixed = row[:3] + [",".join(row[3:-4])] + row[-4:]
                rows.append(fixed)
            # len < 8: línea corrupta, se omite
    if not rows:
        return DataFrame()
    header, *data = rows
    return DataFrame(data, columns=header)


def process_wifi_rf_wardriving(
    device_source=SourceDevice.RF_CUSTOM_FIRMWARE_WIFI,
    uploaded_by="Without Owner",
    dataframe=None,
):
    """
    Process WIFI wardriving CSV from Lilygo T-SIM7000G (y variantes).

    Cabeceras típicas (español): Timestamp,Lat,Long,SSID,BSSID,Canal,Señal,Seguridad
    Inglés: Timestamp,Lat,Long,SSID,BSSID,Channel,RSSI,Security
    Electronic Cats / Minino (si se sube como RF): MAC,SSID,AuthMode,FirstSeen,Channel,…,RSSI,CurrentLatitude,…
    """
    dataframe = dataframe if dataframe is not None else DataFrame()
    if dataframe.empty:
        return 0, 0, 0

    _strip_column_names(dataframe)

    # Quitar columnas de metadatos que no van al modelo Wardriving RF
    for drop_col in (
        "Timestamp",
        "Frequency",
        "RCOIs",
        "MfgrId",
    ):
        if drop_col in dataframe.columns:
            dataframe.pop(drop_col)

    mac = _first_series(dataframe, "BSSID", "MAC", "mac")
    channel = _first_series(dataframe, "Canal", "Channel", "channel")
    rssi_raw = _first_series(
        dataframe,
        "Señal",
        "Senal",
        "RSSI",
        "rssi",
        "Signal",
        "signal",
    )
    ssid = _first_series(dataframe, "SSID", "ssid")
    auth_mode = _first_series(
        dataframe,
        "Seguridad",
        "Security",
        "AuthMode",
        "auth_mode",
        "Auth",
    )
    lat = _first_series(
        dataframe,
        "Lat",
        "Latitude",
        "CurrentLatitude",
        "current_latitude",
    )
    lon = _first_series(
        dataframe,
        "Long",
        "Lon",
        "Lng",
        "Longitude",
        "CurrentLongitude",
        "current_longitude",
    )
    first_seen_col = _first_series(dataframe, "FirstSeen", "first_seen")
    altitude = _first_series(dataframe, "AltitudeMeters", "altitude_meters")
    accuracy = _first_series(dataframe, "AccuracyMeters", "accuracy_meters")
    net_type = _first_series(dataframe, "Type", "type")

    if mac is None or channel is None or rssi_raw is None:
        missing = []
        if mac is None:
            missing.append("BSSID/MAC")
        if channel is None:
            missing.append("Canal/Channel")
        if rssi_raw is None:
            missing.append("Señal/RSSI/Signal")
        raise KeyError(
            "Columnas obligatorias no encontradas: "
            + ", ".join(missing)
            + ". Revisa cabecera (LilyGo ES/EN o tipo de dispositivo correcto)."
        )

    work = DataFrame(
        {
            "mac": mac,
            "channel": to_numeric(channel, errors="coerce"),
            "rssi": to_numeric(
                rssi_raw.astype(str).str.replace(" dBm", "", regex=False).str.strip(),
                errors="coerce",
            ),
        }
    )
    if ssid is not None:
        work["ssid"] = ssid
    if auth_mode is not None:
        work["auth_mode"] = auth_mode
    if lat is not None:
        work["current_latitude"] = to_numeric(lat, errors="coerce")
    if lon is not None:
        work["current_longitude"] = to_numeric(lon, errors="coerce")
    if first_seen_col is not None:
        work["first_seen"] = to_datetime(first_seen_col, errors="coerce")
    if altitude is not None:
        work["altitude_meters"] = to_numeric(altitude, errors="coerce")
    if accuracy is not None:
        work["accuracy_meters"] = to_numeric(accuracy, errors="coerce")
    if net_type is not None:
        work["type"] = net_type.astype(str)

    work = work.dropna(subset=["mac", "channel", "rssi"]).reset_index(drop=True)
    work["rssi"] = work["rssi"].astype(int)
    work["channel"] = work["channel"].astype(int)

    rows = []
    for rec in work.to_dict(orient="records"):
        fs = rec.get("first_seen")
        if fs is None or isna(fs):
            fs = now()
        elif hasattr(fs, "to_pydatetime"):
            fs = fs.to_pydatetime()
            if is_naive(fs):
                fs = make_aware(fs)
        elif isinstance(fs, datetime) and is_naive(fs):
            fs = make_aware(fs)

        row = {
            "uploaded_by": uploaded_by,
            "mac": rec["mac"],
            "channel": int(rec["channel"]),
            "ssid": rec.get("ssid"),
            "auth_mode": rec.get("auth_mode"),
            "first_seen": fs,
            "current_latitude": rec.get("current_latitude"),
            "current_longitude": rec.get("current_longitude"),
            "rssi": rec.get("rssi"),
            "device_source": device_source,
            "type": (rec.get("type") or "WIFI"),
        }
        if rec.get("altitude_meters") is not None and notna(rec.get("altitude_meters")):
            row["altitude_meters"] = rec["altitude_meters"]
        if rec.get("accuracy_meters") is not None and notna(rec.get("accuracy_meters")):
            row["accuracy_meters"] = rec["accuracy_meters"]

        row = {k: v for k, v in row.items() if v is not None}
        rows.append(row)

    update_fields = [
        "ssid",
        "auth_mode",
        "first_seen",
        "current_latitude",
        "current_longitude",
        "rssi",
        "device_source",
        "type",
    ]
    if any("altitude_meters" in r for r in rows):
        update_fields.append("altitude_meters")
    if any("accuracy_meters" in r for r in rows):
        update_fields.append("accuracy_meters")

    return bulk_upsert_by_keys(
        model=Wardriving,
        key_fields=["uploaded_by", "mac", "channel"],
        rows=rows,
        better_obj_fn=wardriving_better_obj_fn,
        update_fields=update_fields,
        only_fields=["id", "uploaded_by", "mac", "channel", "rssi"],
        chunk_size=1000,
    )


def process_file_rf(
    file_path="",
    device_source=SourceDevice.RF_CUSTOM_FIRMWARE_WIFI,
    uploaded_by="Without Owner",
):
    """Entry point: process RF firmware CSV (LTE or WiFi)."""
    rf_class_process = {
        SourceDevice.RF_CUSTOM_FIRMWARE_LTE: process_lte_wardriving,
        SourceDevice.RF_CUSTOM_FIRMWARE_WIFI: process_wifi_rf_wardriving,
    }
    cls_process = rf_class_process.get(device_source)
    if not cls_process:
        return 0, 0, 0

    df = None
    if device_source == SourceDevice.RF_CUSTOM_FIRMWARE_WIFI:
        for enc in ("utf-8", "latin-1"):
            try:
                df = read_csv(
                    file_path,
                    encoding=enc,
                    sep=",",
                    low_memory=False,
                )
                if not _rf_wifi_csv_has_core_columns(df):
                    df = read_csv(
                        file_path,
                        encoding=enc,
                        sep=",",
                        low_memory=False,
                        skiprows=1,
                    )
                break
            except UnicodeDecodeError:
                continue
            except ParserError:
                try:
                    df = _read_wifi_csv_robust(file_path, enc)
                    break
                except UnicodeDecodeError:
                    continue
        if df is None:
            for enc in ("utf-8", "latin-1"):
                try:
                    df = _read_wifi_csv_robust(file_path, enc)
                    break
                except UnicodeDecodeError:
                    continue
        if df is None:
            raise ValueError(
                "No se pudo decodificar el CSV WiFi como UTF-8 ni latin-1."
            )
    else:
        try:
            df = read_csv(file_path, encoding="utf-8", sep=",", low_memory=False)
        except UnicodeDecodeError:
            df = read_csv(file_path, encoding="latin-1", sep=",", low_memory=False)

    return cls_process(
        device_source=device_source, uploaded_by=uploaded_by, dataframe=df
    )
