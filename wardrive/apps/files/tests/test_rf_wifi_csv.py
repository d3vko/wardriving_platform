"""Tests for RF custom firmware WiFi CSV reading (WiGLE + LilyGo)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from apps.process.rf import (
    _fix_wigle_wifi_row,
    _read_wifi_csv_robust,
    _rf_wifi_csv_has_core_columns,
    _wifi_csv_first_line_is_wigle_metadata,
)


# Synthetic coords only (no real GPS).
_LAT = "1.2345678"
_LON = "-9.8765432"


class RfWifiCsvRobustTests(unittest.TestCase):
    def test_wigle_metadata_with_tab(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "w.csv"
            path.write_text(
                "WigleWifi-1.4\tappRelease=RFVillageMX-WarM\n"
                "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
                "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
                f"AA:BB:CC:DD:EE:01,Net,WPA2_PSK,2026-08-09 20:00:00,6,-70,"
                f"{_LAT},{_LON},100.00,1.00,WIFI\n",
                encoding="utf-8",
            )
            self.assertTrue(
                _wifi_csv_first_line_is_wigle_metadata(str(path), "utf-8")
            )
            df = _read_wifi_csv_robust(str(path), "utf-8")
            self.assertTrue(_rf_wifi_csv_has_core_columns(df))
            self.assertEqual(list(df.columns)[:3], ["MAC", "SSID", "AuthMode"])
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["Channel"], "6")

    def test_wigle_recovers_unquoted_comma_in_ssid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "w.csv"
            # SSID "Lab.v," unquoted → 12 CSV fields
            path.write_text(
                "WigleWifi-1.4,appRelease=test\n"
                "MAC,SSID,AuthMode,FirstSeen,Channel,RSSI,"
                "CurrentLatitude,CurrentLongitude,AltitudeMeters,AccuracyMeters,Type\n"
                f"AA:BB:CC:DD:EE:02,Lab.v,,OPEN,2026-08-09 20:00:00,6,-70,"
                f"{_LAT},{_LON},100.00,1.10,WIFI\n",
                encoding="utf-8",
            )
            df = _read_wifi_csv_robust(str(path), "utf-8")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["SSID"], "Lab.v,")
            self.assertEqual(df.iloc[0]["AuthMode"], "OPEN")
            self.assertEqual(df.iloc[0]["Channel"], "6")
            self.assertEqual(df.iloc[0]["Type"], "WIFI")

    def test_fix_wigle_wifi_row_merge(self):
        row = [
            "AA:BB:CC:DD:EE:03",
            "Lab.v",
            "",
            "OPEN",
            "2026-08-09 20:00:00",
            "6",
            "-70",
            _LAT,
            _LON,
            "100.00",
            "1.10",
            "WIFI",
        ]
        fixed = _fix_wigle_wifi_row(row)
        self.assertIsNotNone(fixed)
        self.assertEqual(len(fixed), 11)
        self.assertEqual(fixed[1], "Lab.v,")
        self.assertEqual(fixed[-1], "WIFI")

    def test_lilygo_eight_col_still_works(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "l.csv"
            path.write_text(
                "Timestamp,Lat,Long,SSID,BSSID,Canal,Señal,Seguridad\n"
                f"2026-08-09 20:00:00,{_LAT},{_LON},Cafe,AA:BB:CC:DD:EE:04,1,-65,WPA2\n",
                encoding="utf-8",
            )
            df = _read_wifi_csv_robust(str(path), "utf-8")
            self.assertTrue(_rf_wifi_csv_has_core_columns(df))
            self.assertEqual(df.iloc[0]["SSID"], "Cafe")
            self.assertEqual(df.iloc[0]["Canal"], "1")


if __name__ == "__main__":
    unittest.main()
