"""
Android app file processors: WiFi/BLE and LTE wardriving.

WiFi/BLE source (wifi_ble_android):
  Export from apps like WiGLE WiFi on Android. The CSV header is on line 1
  (no WiGLE metadata line), otherwise the column format matches the canonical
  WiGLE layout. BLE rows with no Channel value are discarded by coerce_row.

LTE source (lte_android):
  Export from Android LTE/cell scanner apps.

  Extended format — 22 columns in Spanish (current default):
    Timestamp, Tecnología, TipoCelda, Estado, MCC, MNC, LAC, CellID,
    eNodeB, Sector, PCI, Banda, EARFCN, FreqDL_MHz, FreqUL_MHz,
    RSSI, RSRP, RSRQ, SINR, Operador, Longitud, Latitud

  Legacy format — 15 columns in English (still accepted for backwards compatibility):
    Timestamp, Technology, State, MCC, MNC, LAC, CellID, Band,
    RSSI, RSRP, RSRQ, SINR, Operator, Longitude, Latitude

  Placeholder / unserved-cell rows are filtered automatically:
    - CellID == 268435455  (0x0FFFFFFF sentinel)
    - LAC    == 65535      (0xFFFF sentinel)
    - MCC    == 0
    - Rows with missing or non-numeric GPS coordinates

  Delegates to process_lte_wardriving (rf.py).
"""

from __future__ import annotations

import logging

from pandas import read_csv

from apps.process._wigle_canonical.aliases import resolve_headers
from apps.process._wigle_canonical.persist import persist_canonical_rows
from apps.process._wigle_canonical.schema import CanonicalRow, coerce_row
from apps.process.rf import process_lte_wardriving
from apps.wardriving.models import SourceDevice

logger = logging.getLogger(__name__)


def process_file_wifi_ble_android(
    file_path: str = "",
    device_source: str = SourceDevice.WIFI_BLE_ANDROID,
    uploaded_by: str = "Without Owner",
) -> tuple[int, int, int]:
    """
    Process WiFi/BLE CSV from Android wardriving apps.

    The header row is on line 1 — no metadata/version line precedes it,
    unlike Minino or WiGLE Mobile exports (which use skiprows=1).

    Supported column names are the canonical WiGLE aliases handled by
    resolve_headers():
      MAC (or BSSID), SSID, AuthMode, FirstSeen, Channel, RSSI,
      CurrentLatitude, CurrentLongitude, AltitudeMeters, AccuracyMeters, Type

    BLE rows that have an empty Channel column are discarded by coerce_row
    because Channel is a required field in the canonical pipeline.
    """
    try:
        df = read_csv(
            file_path,
            encoding="utf-8",
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        )
    except UnicodeDecodeError:
        df = read_csv(
            file_path,
            encoding="latin-1",
            on_bad_lines="skip",
            dtype=str,
            keep_default_na=False,
        )

    if df.empty:
        return 0, 0, 0

    header_map = resolve_headers(list(df.columns))

    if not header_map.get("mac") or not header_map.get("channel"):
        logger.warning(
            "wifi_ble_android: required columns (mac/channel) not found. "
            "Available: %s",
            list(df.columns),
        )
        return 0, 0, 0

    canonical_rows: list[CanonicalRow] = []
    for _, pandas_row in df.iterrows():
        canonical = coerce_row(pandas_row.to_dict(), header_map)
        if canonical is not None:
            canonical_rows.append(canonical)

    return persist_canonical_rows(
        canonical_rows,
        device_source=device_source,
        uploaded_by=uploaded_by,
    )


def process_file_lte_android(
    file_path: str = "",
    device_source: str = SourceDevice.LTE_ANDROID,
    uploaded_by: str = "Without Owner",
) -> tuple[int, int, int]:
    """
    Process LTE/cell CSV from Android scanner apps.

    Accepts the extended 22-column Spanish format (current default):
      Timestamp, Tecnología, TipoCelda, Estado, MCC, MNC, LAC, CellID,
      eNodeB, Sector, PCI, Banda, EARFCN, FreqDL_MHz, FreqUL_MHz,
      RSSI, RSRP, RSRQ, SINR, Operador, Longitud, Latitud

    Also accepts the legacy 15-column English format for backwards compatibility:
      Timestamp, Technology, State, MCC, MNC, LAC, CellID, Band,
      RSSI, RSRP, RSRQ, SINR, Operator, Longitude, Latitude

    Delegates to process_lte_wardriving, which handles both formats and
    filters out placeholder/unserved-cell rows automatically.
    """
    try:
        df = read_csv(file_path, encoding="utf-8", sep=",", low_memory=False)
    except UnicodeDecodeError:
        df = read_csv(file_path, encoding="latin-1", sep=",", low_memory=False)

    return process_lte_wardriving(
        device_source=device_source,
        uploaded_by=uploaded_by,
        dataframe=df,
    )
