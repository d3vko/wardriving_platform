"""
RF custom firmware (Lilygo T-SIM7000G) processors: LTE and WiFi wardriving.
"""
from pandas import read_csv, to_numeric, DataFrame

from django.utils.timezone import now

from apps.files.utils import bulk_upsert_by_keys, wardriving_better_obj_fn
from apps.wardriving.models import LTEWardriving, Wardriving, SourceDevice


def process_lte_wardriving(
    device_source=SourceDevice.RF_CUSTOM_FIRMWARE_LTE,
    uploaded_by="Without Owner",
    dataframe=None,
):
    """
    Process LTE wardriving CSV from Lilygo T-SIM7000G.
    Header example (device may output Spanish column names):
    Timestamp,Tecnología,Estado,MCC,MNC,LAC,CellID,Banda,RSSI,RSRP,RSRQ,SINR,Operador,Longitud,Latitud
    """
    dataframe = dataframe if dataframe is not None else DataFrame()
    if dataframe.empty:
        return 0, 0, 0

    pop_keys = ["Timestamp", "Estado"]
    renamed_keys = {
        "CellID": "cell_id",
        "Banda": "band",
        "Operador": "provider",
        "Longitud": "current_longitude",
        "Latitud": "current_latitude",
        "Tecnología": "tech",
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
        dataframe["rssi"]
        .astype(str)
        .str.replace(" dBm", "", regex=False)
        .str.strip()
    )
    dataframe["rssi"] = to_numeric(dataframe["rssi"], errors="coerce")
    dataframe = dataframe.dropna(subset=["rssi"]).reset_index(drop=True)
    dataframe["rssi"] = dataframe["rssi"].astype(int)
    dataframe["provider"] = dataframe["provider"].fillna("Not Provided")

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


def process_wifi_rf_wardriving(
    device_source=SourceDevice.RF_CUSTOM_FIRMWARE_WIFI,
    uploaded_by="Without Owner",
    dataframe=None,
):
    """
    Process WIFI wardriving CSV from Lilygo T-SIM7000G.
    Header example (device may output Spanish column names):
    Timestamp,Lat,Long,SSID,BSSID,Canal,Señal,Seguridad
    """
    dataframe = dataframe if dataframe is not None else DataFrame()
    if dataframe.empty:
        return 0, 0, 0

    if "Timestamp" in dataframe.columns:
        dataframe.pop("Timestamp")

    dataframe.rename(
        columns={
            "Lat": "current_latitude",
            "Long": "current_longitude",
            "SSID": "ssid",
            "BSSID": "mac",
            "Canal": "channel",
            "Señal": "rssi",
            "Seguridad": "auth_mode",
        },
        inplace=True,
    )

    dataframe["rssi"] = dataframe["rssi"].astype(str).str.strip()
    dataframe["rssi"] = to_numeric(dataframe["rssi"], errors="coerce")
    dataframe = dataframe.dropna(subset=["rssi"]).reset_index(drop=True)
    dataframe["rssi"] = dataframe["rssi"].astype(int)

    rows = []
    for rec in dataframe.to_dict(orient="records"):
        if rec.get("mac") is None or rec.get("channel") is None:
            continue
        row = {
            "uploaded_by": uploaded_by,
            "mac": rec["mac"],
            "channel": int(rec["channel"]),
            "ssid": rec.get("ssid"),
            "auth_mode": rec.get("auth_mode"),
            "first_seen": now(),
            "current_latitude": rec.get("current_latitude"),
            "current_longitude": rec.get("current_longitude"),
            "rssi": rec.get("rssi"),
            "device_source": device_source,
            "type": "WIFI",
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
            "rssi",
            "device_source",
            "type",
        ],
        only_fields=["id", "uploaded_by", "mac", "channel", "rssi"],
        chunk_size=1000,
    )


def process_file_rf(
    file_path="",
    device_source=SourceDevice.RF_CUSTOM_FIRMWARE_WIFI,
    uploaded_by="Without Owner",
):
    """Entry point: process RF firmware CSV (LTE or WiFi)."""
    try:
        df = read_csv(file_path, encoding="utf-8", sep=",")
    except UnicodeDecodeError:
        df = read_csv(file_path, encoding="latin-1", sep=",")

    rf_class_process = {
        SourceDevice.RF_CUSTOM_FIRMWARE_LTE: process_lte_wardriving,
        SourceDevice.RF_CUSTOM_FIRMWARE_WIFI: process_wifi_rf_wardriving,
    }
    cls_process = rf_class_process.get(device_source)
    if cls_process:
        return cls_process(
            device_source=device_source, uploaded_by=uploaded_by, dataframe=df
        )
    return 0, 0, 0
